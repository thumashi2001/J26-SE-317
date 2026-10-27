"""Extra model comparison for C3 (GPU-ready, e.g. Google Colab): more transformers, more classical heads, several seeds.

Extends experiments/model_comparison.py (same frozen v2 data, same question-disjoint splits, same target and metrics) with
  X1/X2/X3  SBERT-feature heads: SVR, random forest, and a larger sentence encoder (all-mpnet-base-v2) + ridge
  D*        fine-tuned transformer regressors (default: distilroberta-base, bert-base-uncased, deberta-v3-base,
            cross-encoder/ms-marco-MiniLM-L-6-v2, roberta-base), each over several seeds

TWO-PHASE PROTOCOL (the held-out test split is locked until the selection is finished)
  Phase 1 (this script): train on TRAIN, choose hyper-parameters, epoch and seed on VALIDATION only, save the
  validation-best checkpoint of each family (--save-dir) and write validation metrics. The held-out split is dropped right after loading and never scored here.
  Phase 2 (separate, run once after the candidate list is frozen and approved): load the saved checkpoints and predict the
  held-out split a single time.

Caveats that stay true: labels are tier-derived (not human-marked); a length-only model is a strong baseline on this data (see
reports/c3_remediation/03_*.md); the validation split is small (66 answers, 11 questions), so differences are noisy.

Usage (Colab, GPU):  python -m experiments.model_comparison_extra --out /content/out --save-dir /content/ckpt
Smoke (CPU, tiny):   python -m experiments.model_comparison_extra --smoke --out OUT

STATUS: offline research script. Not used by live marking.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from experiments.model_comparison import DATASET, SEED, dataset_hashes, load, score, seed_all, versions  # noqa: E402

DEFAULT_FINETUNE = ["distilroberta-base", "bert-base-uncased", "microsoft/deberta-v3-base",
                    "cross-encoder/ms-marco-MiniLM-L-6-v2", "roberta-base"]
SMOKE_MODEL = "google/bert_uncased_L-2_H-128_A-2"  # ~17 MB, only to prove the pipeline runs on CPU; its numbers mean nothing


def _key(model_name: str) -> str:
    """Result key for a fine-tuned model, e.g. 'D_roberta-base'."""
    return "D_" + model_name.split("/")[-1].replace(".", "_")


def _val_only(d: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Phase 1 never needs the held-out split; dropping it makes accidental use impossible."""
    return {s: v for s, v in d.items() if s in ("train", "validation")}


# ----------------------------------------------------------------------------------------- classical heads on embeddings
# name -> (sentence encoder, hyper-parameter labels searched on VALIDATION, label -> unfitted sklearn model, feature note).
# Module level so the final-test script rebuilds exactly the validation-selected model.
def _svr(label: str):
    """Build an SVR regressor from a label such as 'C=1'."""
    from sklearn.svm import SVR
    return SVR(C=float(label.split("=")[1]), epsilon=0.02)


def _forest(label: str):
    """Build a random-forest regressor from a label such as 'depth=8'."""
    from sklearn.ensemble import RandomForestRegressor
    depth = label.split("=")[1]
    return RandomForestRegressor(n_estimators=200, max_depth=None if depth == "None" else int(depth), random_state=SEED, n_jobs=-1)


def _ridge(label: str):
    """Build a Ridge regressor from a label such as 'alpha=1'."""
    from sklearn.linear_model import Ridge
    return Ridge(alpha=float(label.split("=")[1]), random_state=SEED)


EMBED_SPECS: dict[str, tuple[str, list[str], Any, str]] = {
    "X1_minilm_svr": ("sentence-transformers/all-MiniLM-L6-v2", [f"C={c}" for c in (0.3, 1.0, 3.0, 10.0)], _svr,
                      "MiniLM cosine,|u-v|,u*v -> RBF SVR"),
    "X2_minilm_random_forest": ("sentence-transformers/all-MiniLM-L6-v2", [f"depth={x}" for x in (6, 12, None)], _forest,
                                "MiniLM cosine,|u-v|,u*v -> random forest"),
    "X3_mpnet_features_ridge": ("sentence-transformers/all-mpnet-base-v2", [f"alpha={x}" for x in (0.3, 1, 3, 10, 30)], _ridge,
                                "all-mpnet-base-v2 cosine,|u-v|,u*v -> ridge"),
}


def embedding_features(d: dict[str, pd.DataFrame], model_name: str) -> dict[str, np.ndarray]:
    """[cosine, |u-v|, u*v] of normalised sentence embeddings of (student answer, reference answer), per split."""
    from sentence_transformers import SentenceTransformer

    enc = SentenceTransformer(model_name)
    out = {}
    for s, df in d.items():
        u = enc.encode(df["student_answer"].tolist(), batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        v = enc.encode(df["reference_answer"].tolist(), batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        out[s] = np.c_[(u * v).sum(1), np.abs(u - v), u * v]
    return out


def run_embedding_heads(d: dict[str, pd.DataFrame], names: list[str] | None = None) -> dict[str, Any]:
    """Fit each head on TRAIN for every label in its grid and keep the label with the lowest VALIDATION nMAE."""
    results: dict[str, Any] = {}
    cache: dict[str, dict[str, np.ndarray]] = {}
    for name in names or list(EMBED_SPECS):
        encoder, labels, make, note = EMBED_SPECS[name]
        t0, best = time.time(), None
        x = cache.setdefault(encoder, embedding_features(d, encoder))
        for label in labels:
            model = make(label).fit(x["train"], d["train"]["y"])
            pv = model.predict(x["validation"])
            v = score(d["validation"], pv)["nmae"]
            if best is None or v < best[0]:
                best = (v, label, pv)
        _, label, pv = best
        results[name] = {"hyperparameters": {"selected": label, "encoder": encoder, "features": note},
                         "validation": score(d["validation"], pv), "pred_validation": pv.tolist(),
                         "runtime_seconds": round(time.time() - t0, 2)}
    return results


# ---------------------------------------------------------------------------------------------- fine-tuned transformers
def finetune_one(d: dict[str, pd.DataFrame], model_name: str, seed: int, *, epochs: int, batch: int, lr: float,
                 max_len: int) -> dict[str, Any]:
    """Train on TRAIN, keep the epoch with the lowest VALIDATION nMAE. Returns metrics plus the best weights."""
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    seed_all(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(model_name)

    class Reg(nn.Module):
        """Regression model: transformer encoder, first-token vector, one linear layer, sigmoid (a 0..1 mark ratio)."""
        def __init__(self):
            super().__init__()
            self.enc = AutoModel.from_pretrained(model_name)
            self.head = nn.Linear(self.enc.config.hidden_size, 1)

        def forward(self, **kw):
            """Encode the (reference, answer) pair and return the estimated mark ratio."""
            return torch.sigmoid(self.head(self.enc(**kw).last_hidden_state[:, 0])).squeeze(-1)

    model = Reg().to(device)

    def enc(df: pd.DataFrame, idx: list[int]):
        """Tokenise (reference, answer) pairs for the given rows and move them to the device."""
        b = tok(df["reference_answer"].iloc[idx].tolist(), df["student_answer"].iloc[idx].tolist(), truncation=True,
                max_length=max_len, padding=True, return_tensors="pt")
        return {k: v.to(device) for k, v in b.items()}

    def predict(df: pd.DataFrame) -> np.ndarray:
        """Predict mark ratios for a dataframe in batches."""
        model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(df), 32):
                out.append(model(**enc(df, list(range(i, min(i + 32, len(df)))))).float().cpu().numpy())
        return np.concatenate(out)

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * int(np.ceil(len(d["train"]) / batch))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (0.1 * steps)) * max(0.0, (steps - s) / steps))
    scaler = torch.amp.GradScaler("cuda", enabled=device == "cuda")  # fp16 loss scaling on GPU only
    y = torch.tensor(d["train"]["y"].to_numpy(), dtype=torch.float32, device=device)
    gen = np.random.default_rng(seed)
    history, best, best_state = [], None, None
    for ep in range(1, epochs + 1):
        model.train()
        order = gen.permutation(len(d["train"]))
        tot = 0.0
        for i in range(0, len(order), batch):
            ix = order[i:i + batch].tolist()
            with torch.autocast(device_type=device, dtype=torch.float16, enabled=device == "cuda"):
                pred = model(**enc(d["train"], ix))
            loss = nn.functional.mse_loss(pred.float(), y[ix])
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            opt.zero_grad()
            tot += loss.item() * len(ix)
        pv = predict(d["validation"])
        v = score(d["validation"], pv)["nmae"]
        history.append({"epoch": ep, "train_mse": tot / len(order), "validation_nmae": v, "elapsed_s": round(time.time() - t0, 1)})
        print(model_name, seed, history[-1], flush=True)
        if best is None or v < best[0]:
            best = (v, ep, pv)
            best_state = {k: t.detach().cpu().clone() for k, t in model.state_dict().items()}
    return {"seed": seed, "selected_epoch": best[1], "validation": score(d["validation"], best[2]), "history": history,
            "device": device, "pred_validation": best[2].tolist(), "runtime_seconds": round(time.time() - t0, 1),
            "_state": best_state, "_tok": tok}


def run_finetune_family(d: dict[str, pd.DataFrame], model_name: str, seeds: list[int], save_dir: Path | None, **kw) -> dict[str, Any]:
    """Several seeds per model; the family winner is the seed with the lowest VALIDATION nMAE, and only it is saved."""
    import torch

    runs, winner = [], None
    for s in seeds:
        r = finetune_one(d, model_name, s, **kw)
        if winner is None or r["validation"]["nmae"] < winner["validation"]["nmae"]:
            winner = r
        runs.append(r)
    if save_dir is not None:
        path = save_dir / _key(model_name)
        path.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": winner["_state"], "model_name": model_name, "max_len": kw["max_len"], "seed": winner["seed"],
                    "selected_epoch": winner["selected_epoch"]}, path / "model.pt")
        winner["_tok"].save_pretrained(path)
    for r in runs:  # weights/tokenizer are not JSON
        r.pop("_state", None)
        r.pop("_tok", None)
    val = np.array([r["validation"]["nmae"] for r in runs])
    return {"hyperparameters": {"model": model_name, "seeds": seeds, **{k: kw[k] for k in ("epochs", "batch", "lr", "max_len")},
                                "head": "CLS->linear->sigmoid, MSE loss, fp16 on GPU"},
            "validation": winner["validation"], "selected_seed": winner["seed"], "selected_epoch": winner["selected_epoch"],
            "seed_summary": {"validation_nmae_mean": float(val.mean()), "validation_nmae_sd": float(val.std()), "n_seeds": len(seeds)},
            "runs": runs, "pred_validation": winner["pred_validation"],
            "runtime_seconds": round(sum(r["runtime_seconds"] for r in runs), 1)}


def main(argv=None) -> int:
    """Phase 1: compare the extra models on the validation split only and save the best checkpoints."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--save-dir", type=Path, default=None, help="where to save each family's validation-best checkpoint")
    ap.add_argument("--models", default=",".join(DEFAULT_FINETUNE), help="comma list of Hugging Face model ids to fine-tune")
    ap.add_argument("--seeds", default="20261021,20261022,20261023")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--skip-embedding-heads", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="tiny CPU pipeline check; results are NOT experimental evidence")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    d = _val_only(load())
    models, seeds = [m for m in a.models.split(",") if m], [int(s) for s in a.seeds.split(",") if s]
    if a.smoke:
        d = {s: v.head(24 if s == "train" else 8).reset_index(drop=True) for s, v in d.items()}
        models, seeds, a.epochs, a.batch = [SMOKE_MODEL], seeds[:1], 1, 8
        a.skip_embedding_heads = True
    meta = {"dataset": DATASET.name, "dataset_sha256": dataset_hashes(), "split_sizes": {s: len(v) for s, v in d.items()},
            "versions": versions(), "smoke": a.smoke, "phase": "1 (selection on validation; held-out split dropped, not scored)",
            "label_caveat": "expected marks are tier-derived, not human-marked",
            "selection_rule": "lowest validation nMAE (seed and epoch)"}
    results: dict[str, Any] = {}
    if not a.skip_embedding_heads:
        results.update(run_embedding_heads(d))  # X1-X3
    for name in models:
        print(f"== fine-tuning {name}", flush=True)
        results[_key(name)] = run_finetune_family(d, name, seeds, a.save_dir, epochs=a.epochs, batch=a.batch, lr=a.lr,
                                                  max_len=a.max_len)
    (a.out / ("results_extra_SMOKE.json" if a.smoke else "results_extra_phase1.json")).write_text(
        json.dumps({"meta": meta, "results": results}, indent=1), encoding="utf-8")
    for name, r in results.items():
        print(name, "val nMAE", round(r["validation"]["nmae"], 4),
              ("seeds mean/sd %.4f/%.4f" % (r["seed_summary"]["validation_nmae_mean"], r["seed_summary"]["validation_nmae_sd"]))
              if "seed_summary" in r else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
