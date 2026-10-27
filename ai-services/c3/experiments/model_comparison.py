"""Fair comparison of the planned C3 candidates on the frozen repaired dataset (c3_phase3_v5_repaired_v2).

Candidates (Day 22/23 hierarchy): A TF-IDF + classical ML, B SBERT embeddings + regressor, C RoBERTa-base fine-tuned,
plus the two deterministic references that were already evaluated: the lexical token-recall baseline and Condition E.

Protocol: same eligible rows, same question-disjoint splits, same target (expected_mark / max_marks); every hyper-parameter and
the epoch of the fine-tuned model are chosen on VALIDATION only; the test split is predicted once with the selected
configuration; fixed seeds; library versions and dataset hashes recorded. Nothing is tuned on test. No LLM / network call
except the one-off download of public pretrained weights (sentence-transformers/all-MiniLM-L6-v2, roberta-base).

Usage: python -m experiments.model_comparison --run A|B|C|REF|all --out DIR

STATUS: offline research script (run from ai-services/c3, use --out with a temporary folder to keep the repository
clean). This is where models are actually TRAINED: TF-IDF and SBERT-feature Ridge/GBR heads (scikit-learn) and a
RoBERTa-base fine-tune (about 33 min on CPU; the trained weights are not saved). None of these models is used by live
marking. Evidence of the run: reports/c3_remediation/experiments/ (log_C.txt, results_*.json) and the charts in
reports/c3_remediation/figures/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

SEED = 20261021
DATASET = HERE / "datasets" / "c3_phase3_v5_repaired_v2"
N_BOOT = 2000


def seed_all(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.use_deterministic_algorithms(False)
    except ImportError:
        pass


def load_answers_with_reference(dataset: Path = DATASET) -> pd.DataFrame:
    """Eligible answers with the REAL reference answer attached.

    DATA NOTE: the `reference_answer` column inside 02_controlled_answers_eligible.csv is empty for every row; the
    reference answers live in 01_question_bank.csv. Results produced before 2026-10-27 (reports 03, 12, F-lite, the
    first extra comparison) therefore saw the student answer only. This function fills the column from the question bank.
    """
    ans = pd.read_csv(dataset / "02_controlled_answers_eligible.csv", dtype=str, keep_default_na=False)
    bank = pd.read_csv(dataset / "01_question_bank.csv", dtype=str, keep_default_na=False)[["question_id", "reference_answer"]]
    ans = ans.drop(columns=["reference_answer"]).merge(bank, on="question_id", how="left", validate="many_to_one")
    if (ans["reference_answer"].fillna("").str.strip() == "").any():
        raise ValueError("some eligible answers have no reference answer in the question bank")
    return ans


def load(dataset: Path = DATASET, with_reference: bool = True) -> dict[str, pd.DataFrame]:
    """Frozen splits. with_reference=False reproduces the earlier answer-only inputs (empty reference) for ablations."""
    ans = load_answers_with_reference(dataset)
    if not with_reference:
        ans["reference_answer"] = ""
    ans["max"] = ans["max_marks"].astype(float)
    ans["gt"] = ans["expected_mark"].astype(float)
    ans["y"] = (ans["gt"] / ans["max"]).clip(0, 1)
    return {s: ans[ans["split"] == s].reset_index(drop=True) for s in ("train", "validation", "test")}


def dataset_hashes(dataset: Path = DATASET) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dataset.glob("*.csv")) + [dataset / "manifest.json"]}


def qwk(y_true: np.ndarray, y_pred: np.ndarray, levels: int = 11) -> float:
    """Quadratic weighted kappa after quantising normalised marks into `levels` ordinal bins (0.1 steps)."""
    a = np.clip(np.rint(y_true * (levels - 1)).astype(int), 0, levels - 1)
    b = np.clip(np.rint(np.clip(y_pred, 0, 1) * (levels - 1)).astype(int), 0, levels - 1)
    o = np.zeros((levels, levels))
    for i, j in zip(a, b):
        o[i, j] += 1
    w = np.array([[(i - j) ** 2 for j in range(levels)] for i in range(levels)], float) / (levels - 1) ** 2
    e = np.outer(o.sum(1), o.sum(0)) / max(o.sum(), 1)
    den = (w * e).sum()
    return float(1 - (w * o).sum() / den) if den > 0 else float("nan")


def score(df: pd.DataFrame, pred: np.ndarray) -> dict[str, Any]:
    y = df["y"].to_numpy()
    p = np.clip(np.asarray(pred, float), 0, 1)
    err = np.abs(p - y)
    marks_err = np.abs(p * df["max"].to_numpy() - df["gt"].to_numpy())
    q = df["question_id"].to_numpy()
    uniq = sorted(set(q))
    idx = {u: np.where(q == u)[0] for u in uniq}
    rng = np.random.default_rng(SEED)
    boots = [float(err[np.concatenate([idx[uniq[i]] for i in rng.integers(0, len(uniq), len(uniq))])].mean()) for _ in range(N_BOOT)]
    r = float(np.corrcoef(p, y)[0, 1]) if np.std(p) > 0 and np.std(y) > 0 else None
    return {
        "n": int(len(y)), "n_questions": len(uniq),
        "nmae": float(err.mean()), "nmae_ci95_question_bootstrap": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        "nrmse": float(np.sqrt(np.mean((p - y) ** 2))), "mae_marks": float(marks_err.mean()),
        "pearson_r": r, "qwk_11bins": qwk(y, p), "within_0.10_of_max": float(np.mean(err <= 0.10)),
    }


def versions() -> dict[str, str]:
    out = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    for mod in ("sklearn", "torch", "transformers", "sentence_transformers"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:  # not installed
            out[mod] = "not installed"
    return out


# ----------------------------------------------------------------------------------------------------------- A: TF-IDF
def run_tfidf(d: dict[str, pd.DataFrame]) -> dict[str, Any]:
    from scipy.sparse import csr_matrix, hstack
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import Ridge
    from sklearn.metrics.pairwise import cosine_similarity

    t0 = time.time()
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2, max_features=3000, lowercase=True)
    vec.fit(d["train"]["student_answer"])  # fitted on TRAIN only

    def feats(df: pd.DataFrame):
        a = vec.transform(df["student_answer"])
        r = vec.transform(df["reference_answer"])
        cos = np.asarray(a.multiply(r).sum(1)).ravel()  # tf-idf vectors are l2-normalised -> dot = cosine
        return a, cos

    fa = {s: feats(d[s]) for s in d}
    results: dict[str, Any] = {}
    # A1: Ridge on tf-idf(answer) + cosine-to-reference
    best = None
    for alpha in (0.1, 0.3, 1.0, 3.0, 10.0):
        m = Ridge(alpha=alpha, random_state=SEED).fit(hstack([fa["train"][0], csr_matrix(fa["train"][1][:, None])]).tocsr(), d["train"]["y"])
        pv = m.predict(hstack([fa["validation"][0], csr_matrix(fa["validation"][1][:, None])]).tocsr())
        v = score(d["validation"], pv)["nmae"]
        if best is None or v < best[0]:
            best = (v, alpha, m)
    _, alpha, m = best
    pt = m.predict(hstack([fa["test"][0], csr_matrix(fa["test"][1][:, None])]).tocsr())
    pv = m.predict(hstack([fa["validation"][0], csr_matrix(fa["validation"][1][:, None])]).tocsr())
    results["A1_tfidf_ridge"] = {"hyperparameters": {"alpha": alpha, "ngram": [1, 2], "max_features": 3000, "min_df": 2, "features": "tfidf(answer) + cosine(answer, reference)"},
                                 "validation": score(d["validation"], pv), "test": score(d["test"], pt), "pred_validation": pv.tolist(), "pred_test": pt.tolist()}
    # A2: gradient boosting on two overlap features only (no length features, to avoid the known length shortcut)
    def small(df, cos):
        return np.c_[cos, [len(set(a.lower().split()) & set(r.lower().split())) / max(len(set(r.lower().split())), 1) for a, r in zip(df["student_answer"], df["reference_answer"])]]

    xs = {s: small(d[s], fa[s][1]) for s in d}
    best = None
    for depth, n_est in ((2, 80), (3, 100), (2, 200)):
        g = GradientBoostingRegressor(n_estimators=n_est, max_depth=depth, learning_rate=0.05, subsample=0.8, random_state=SEED).fit(xs["train"], d["train"]["y"])
        v = score(d["validation"], g.predict(xs["validation"]))["nmae"]
        if best is None or v < best[0]:
            best = (v, depth, n_est, g)
    _, depth, n_est, g = best
    pv, pt = g.predict(xs["validation"]), g.predict(xs["test"])
    results["A2_tfidf_cosine_overlap_gbr"] = {"hyperparameters": {"max_depth": depth, "n_estimators": n_est, "learning_rate": 0.05, "features": "tfidf cosine + token recall vs reference"},
                                              "validation": score(d["validation"], pv), "test": score(d["test"], pt), "pred_validation": pv.tolist(), "pred_test": pt.tolist()}
    for k in results:
        results[k]["runtime_seconds"] = round(time.time() - t0, 2)
    return results


# ------------------------------------------------------------------------------------------------------------- B: SBERT
def run_sbert(d: dict[str, pd.DataFrame]) -> dict[str, Any]:
    from sentence_transformers import SentenceTransformer
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import Ridge

    t0 = time.time()
    name = "sentence-transformers/all-MiniLM-L6-v2"
    model = SentenceTransformer(name, device="cpu")
    emb = {}
    for s, df in d.items():
        emb[s] = (model.encode(df["student_answer"].tolist(), batch_size=32, normalize_embeddings=True, show_progress_bar=False),
                  model.encode(df["reference_answer"].tolist(), batch_size=32, normalize_embeddings=True, show_progress_bar=False))
    cos = {s: (emb[s][0] * emb[s][1]).sum(1) for s in d}
    results: dict[str, Any] = {}
    # B0: raw cosine mapped to a mark with a monotone calibration fitted on TRAIN (not used as a mark directly)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(cos["train"], d["train"]["y"])
    pv, pt = iso.predict(cos["validation"]), iso.predict(cos["test"])
    results["B0_sbert_cosine_isotonic"] = {"hyperparameters": {"model": name, "mapping": "isotonic regression cosine->normalised mark, fit on train"},
                                           "validation": score(d["validation"], pv), "test": score(d["test"], pt), "pred_validation": pv.tolist(), "pred_test": pt.tolist()}
    # B1: ridge on [cosine, |u-v|, u*v]
    def x(s):
        u, v = emb[s]
        return np.c_[cos[s], np.abs(u - v), u * v]

    best = None
    for alpha in (0.1, 0.3, 1.0, 3.0, 10.0, 30.0):
        m = Ridge(alpha=alpha, random_state=SEED).fit(x("train"), d["train"]["y"])
        v = score(d["validation"], m.predict(x("validation")))["nmae"]
        if best is None or v < best[0]:
            best = (v, alpha, m)
    _, alpha, m = best
    pv, pt = m.predict(x("validation")), m.predict(x("test"))
    results["B1_sbert_features_ridge"] = {"hyperparameters": {"model": name, "alpha": alpha, "features": "cosine, |u-v|, u*v"},
                                          "validation": score(d["validation"], pv), "test": score(d["test"], pt), "pred_validation": pv.tolist(), "pred_test": pt.tolist()}
    for k in results:
        results[k]["runtime_seconds"] = round(time.time() - t0, 2)
    return results


# ---------------------------------------------------------------------------------------------------------- C: RoBERTa
def run_roberta(d: dict[str, pd.DataFrame], epochs: int = 6, batch: int = 8, lr: float = 2e-5, max_len: int = 256) -> dict[str, Any]:
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    seed_all()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    t0 = time.time()
    name = "roberta-base"
    tok = AutoTokenizer.from_pretrained(name)

    class Reg(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = AutoModel.from_pretrained(name)
            self.head = nn.Linear(self.enc.config.hidden_size, 1)

        def forward(self, **kw):
            h = self.enc(**kw).last_hidden_state[:, 0]
            return torch.sigmoid(self.head(h)).squeeze(-1)

    model = Reg()

    def enc(df, idx):
        return tok(df["reference_answer"].iloc[idx].tolist(), df["student_answer"].iloc[idx].tolist(), truncation=True, max_length=max_len, padding=True, return_tensors="pt")

    def predict(df):
        model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(df), 16):
                out.append(model(**enc(df, list(range(i, min(i + 16, len(df)))))).numpy())
        return np.concatenate(out)

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps = epochs * int(np.ceil(len(d["train"]) / batch))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / (0.1 * steps)) * max(0.0, (steps - s) / steps))
    y = torch.tensor(d["train"]["y"].to_numpy(), dtype=torch.float32)
    history, best, best_state = [], None, None
    gen = np.random.default_rng(SEED)
    for ep in range(1, epochs + 1):
        model.train()
        order = gen.permutation(len(d["train"]))
        tot = 0.0
        for i in range(0, len(order), batch):
            ix = order[i:i + batch].tolist()
            loss = nn.functional.mse_loss(model(**enc(d["train"], ix)), y[ix])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            tot += float(loss) * len(ix)
        pv = predict(d["validation"])
        v = score(d["validation"], pv)["nmae"]
        history.append({"epoch": ep, "train_mse": tot / len(order), "validation_nmae": v, "elapsed_s": round(time.time() - t0, 1)})
        print(history[-1], flush=True)
        if best is None or v < best[0]:
            best = (v, ep, pv)
            best_state = {k: t.detach().clone() for k, t in model.state_dict().items()}
    model.load_state_dict(best_state)  # validation-selected epoch
    pt = predict(d["test"])  # test is predicted ONCE, with the validation-selected checkpoint
    return {"C_roberta_base_finetuned": {
        "hyperparameters": {"model": name, "epochs_max": epochs, "selected_epoch": best[1], "batch": batch, "lr": lr, "max_len": max_len, "input": "(reference, answer) pair", "head": "CLS->linear->sigmoid, MSE loss"},
        "validation": score(d["validation"], best[2]), "test": score(d["test"], pt), "history": history,
        "pred_validation": best[2].tolist(), "pred_test": pt.tolist(), "runtime_seconds": round(time.time() - t0, 2)}}


# -------------------------------------------------------------------------------------- references: baseline and Condition E
def run_reference(d: dict[str, pd.DataFrame]) -> dict[str, Any]:
    from datasets.repair.common import read_csv
    from datasets.repair.evaluate_repaired import _rubric_index, run_rows

    q = read_csv(DATASET / "01_question_bank.csv")
    questions = {r["question_id"]: r for r in q.to_dict("records")}
    rub = _rubric_index(read_csv(DATASET / "03_rubric_criteria.csv"))
    out: dict[str, Any] = {}
    preds = {"R1_lexical_token_recall_baseline": {}, "R2_condition_E_binary_rubric": {}}
    for s in ("validation", "test"):
        rows, ne = run_rows(d[s], questions, rub, "question_marks", allow_fallback=False)
        byid = {r["answer_id"]: r for r in rows}
        for key, field in (("R1_lexical_token_recall_baseline", "pred_b"), ("R2_condition_E_binary_rubric", "pred_e")):
            p = []
            for a in d[s].to_dict("records"):
                r = byid.get(a["answer_id"])
                p.append(float("nan") if r is None or (key.startswith("R2") and r["failed"]) else r[field] / r["max"])
            preds[key][s] = np.array(p)
    for key, v in preds.items():
        res: dict[str, Any] = {"hyperparameters": {"note": "deterministic, nothing fitted"}, "runtime_seconds": 0.0}
        for s in ("validation", "test"):
            ok = ~np.isnan(v[s])
            res[s] = score(d[s][ok].reset_index(drop=True), v[s][ok])
            res[s]["excluded_failed_or_not_evaluable"] = int((~ok).sum())
        res["pred_validation"] = np.nan_to_num(v["validation"], nan=-1).tolist()
        res["pred_test"] = np.nan_to_num(v["test"], nan=-1).tolist()
        out[key] = res
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="all", choices=["A", "B", "C", "REF", "all"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=6)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    seed_all()
    d = load()
    meta = {"dataset": DATASET.name, "dataset_sha256": dataset_hashes(), "split_sizes": {s: len(v) for s, v in d.items()}, "seed": SEED,
            "target": "expected_mark / max_marks (0..1)", "selection_rule": "lowest validation nMAE per family; test predicted once", "versions": versions()}
    todo = {"A": run_tfidf, "B": run_sbert, "C": lambda x: run_roberta(x, epochs=a.epochs), "REF": run_reference}
    for key in (["REF", "A", "B", "C"] if a.run == "all" else [a.run]):
        print(f"== running {key}", flush=True)
        res = todo[key](d)
        (a.out / f"results_{key}.json").write_text(json.dumps({"meta": meta, "results": res}, indent=1), encoding="utf-8")
        for name, r in res.items():
            print(name, "val nMAE", round(r["validation"]["nmae"], 4), "test nMAE", round(r["test"]["nmae"], 4), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
