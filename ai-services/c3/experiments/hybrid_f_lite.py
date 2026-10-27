"""Condition F-lite: non-LLM hybrid ensemble of the already-evaluated component scores.

NOT the proposal's Condition F (that one fuses Condition E, embedding similarity and a rubric-prompted LLM and needs LLM
calls). F-lite stacks Condition E (binary rubric), TF-IDF-ridge (A1), SBERT-ridge (B1) and RoBERTa (C) with non-negative
least squares. Weights are fit on VALIDATION predictions only (saved by model_comparison.py); the test split is scored once.
Caveat: the RoBERTa validation predictions come from the validation-selected epoch, so validation is slightly optimistic for
that component and the learned weights lean towards it.

Usage: python -m experiments.hybrid_f_lite --results DIR

STATUS: offline research script (weights fitted on validation predictions only). Not used by live marking.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

# Make the repo root importable when the script is run directly.
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from experiments.model_comparison import load, score  # noqa: E402

# component -> (results file suffix, candidate name inside it). Their saved predictions are stacked, not retrained.
PARTS = {"E": ("REF", "R2_condition_E_binary_rubric"), "A1": ("A", "A1_tfidf_ridge"), "B1": ("B", "B1_sbert_features_ridge"),
         "C": ("C", "C_roberta_base_finetuned")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, required=True)
    a = ap.parse_args(argv)
    d = load()
    pv, pt = {}, {}
    for key, (file, name) in PARTS.items():
        r = json.loads((a.results / f"results_{file}.json").read_text(encoding="utf-8"))["results"][name]
        pv[key], pt[key] = np.array(r["pred_validation"], float), np.array(r["pred_test"], float)
        # Guard: predictions must align with the frozen split and contain no failed (negative) entries.
        assert len(pv[key]) == len(d["validation"]) and len(pt[key]) == len(d["test"]), f"{key}: prediction length mismatch"
        assert (pv[key] >= 0).all() and (pt[key] >= 0).all(), f"{key}: failed/missing predictions present"
    # Rows = answers, columns = components; weights come from VALIDATION predictions only.
    keys = list(PARTS)
    xv, xt = np.c_[[pv[k] for k in keys]].T, np.c_[[pt[k] for k in keys]].T
    # Non-negative least squares keeps every weight >= 0 so the blend stays interpretable.
    w, _ = nnls(xv, d["validation"]["y"].to_numpy())  # validation only
    # Clip to the valid [0, 1] mark ratio; the test split is scored once with the frozen weights.
    fv, ft = np.clip(xv @ w, 0, 1), np.clip(xt @ w, 0, 1)
    comp = {k: {"validation": score(d["validation"], pv[k]), "test": score(d["test"], pt[k])} for k in keys}
    # Best single component chosen on validation, for a fair comparison with the blend.
    best_val = min(keys, key=lambda k: comp[k]["validation"]["nmae"])
    out = {"definition": "F-lite = NNLS stack of E, A1, B1, C (no LLM). Differs from the proposal's Condition F.",
           "weights": dict(zip(keys, map(float, w), strict=True)), "weights_sum": float(w.sum()),
           "fit_data": "validation predictions only (n=%d)" % len(d["validation"]),
           "f_lite": {"validation": score(d["validation"], fv), "test": score(d["test"], ft)},
           "components": comp, "best_component_by_validation": best_val,
           "caveats": ["validation set has only 66 answers from 11 questions", "RoBERTa validation predictions are from the validation-selected epoch (optimistic)",
                       "single run, single seed, tier-derived synthetic labels, ratio-concentration check failed"]}
    (a.results / "hybrid_f_lite.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("weights", out["weights"])
    print("F-lite  val nMAE %.4f  test nMAE %.4f" % (out["f_lite"]["validation"]["nmae"], out["f_lite"]["test"]["nmae"]))
    print("best component by val:", best_val, "test nMAE %.4f" % comp[best_val]["test"]["nmae"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
