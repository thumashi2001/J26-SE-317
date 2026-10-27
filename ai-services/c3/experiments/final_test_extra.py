"""Phase 2: score the held-out TEST split ONCE for the candidates frozen in phase 1 (model_comparison_extra.py).

Run this only after the candidate list is final and you have approved scoring the held-out split. For every candidate in
results_extra_phase1.json it rebuilds the validation-selected model (classical heads: refit on TRAIN with the selected
hyper-parameter; fine-tuned transformers: load the saved checkpoint) and predicts the test split a single time. Nothing is
tuned here. Refuses to run twice into the same output directory.

Usage: python -m experiments.final_test_extra --phase1 results_extra_phase1.json --ckpt DIR --out DIR

STATUS: offline research script. Not used by live marking.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from experiments.model_comparison import DATASET, dataset_hashes, load, score  # noqa: E402
from experiments.model_comparison_extra import EMBED_SPECS, embedding_features  # noqa: E402


def predict_checkpoint(ckpt_dir: Path, df) -> np.ndarray:
    """Load a checkpoint written by model_comparison_extra.finetune_one and predict normalised marks for df."""
    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    blob = torch.load(ckpt_dir / "model.pt", map_location="cpu", weights_only=True)  # checkpoint holds only tensors and plain values
    tok = AutoTokenizer.from_pretrained(ckpt_dir)

    class Reg(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = AutoModel.from_pretrained(blob["model_name"])
            self.head = nn.Linear(self.enc.config.hidden_size, 1)

        def forward(self, **kw):
            return torch.sigmoid(self.head(self.enc(**kw).last_hidden_state[:, 0])).squeeze(-1)

    model = Reg()
    model.load_state_dict(blob["state_dict"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(df), 32):
            sub = df.iloc[i:i + 32]
            b = tok(sub["reference_answer"].tolist(), sub["student_answer"].tolist(), truncation=True,
                    max_length=blob["max_len"], padding=True, return_tensors="pt")
            out.append(model(**{k: v.to(device) for k, v in b.items()}).float().cpu().numpy())
    return np.concatenate(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase1", type=Path, required=True)
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    target = a.out / "results_extra_final_test.json"
    if target.exists():
        raise SystemExit(f"{target} already exists: the held-out split is scored once. Delete it deliberately to redo.")
    a.out.mkdir(parents=True, exist_ok=True)
    phase1 = json.loads(a.phase1.read_text(encoding="utf-8"))
    if phase1["meta"].get("smoke"):
        raise SystemExit("phase 1 file is a smoke run; its numbers are not evidence")
    if phase1["meta"]["dataset_sha256"] != dataset_hashes():
        raise SystemExit("dataset files changed since phase 1 (hash mismatch)")
    d = load()
    results: dict[str, Any] = {}
    features: dict[str, dict[str, np.ndarray]] = {}
    for name, r in phase1["results"].items():
        if name in EMBED_SPECS:
            encoder, _, make, _ = EMBED_SPECS[name]
            x = features.setdefault(encoder, embedding_features(d, encoder))
            model = make(r["hyperparameters"]["selected"]).fit(x["train"], d["train"]["y"])
            pt = model.predict(x["test"])
        else:
            pt = predict_checkpoint(a.ckpt / name, d["test"])
        results[name] = {"validation_from_phase1": r["validation"], "test": score(d["test"], pt), "pred_test": pt.tolist(),
                         "hyperparameters": r["hyperparameters"]}
    meta = {"dataset": DATASET.name, "dataset_sha256": phase1["meta"]["dataset_sha256"],
            "phase": "2 (held-out split scored once)", "label_caveat": "expected marks are tier-derived, not human-marked"}
    target.write_text(json.dumps({"meta": meta, "results": results}, indent=1), encoding="utf-8")
    for name, r in sorted(results.items(), key=lambda kv: kv[1]["validation_from_phase1"]["nmae"]):
        print(f"{name:45s} val nMAE {r['validation_from_phase1']['nmae']:.4f}  test nMAE {r['test']['nmae']:.4f}"
              f"  QWK {r['test']['qwk_11bins']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
