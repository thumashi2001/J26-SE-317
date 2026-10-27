"""Concept-detection evaluation for the semantic matcher (FR-C3-09), lexical baseline vs semantic.

PROTOCOL
    Ground truth per answer: concepts listed in `demonstrated_concepts` are positives, concepts in `missing_concepts` are
    negatives (both are tier-derived synthetic annotations, not human annotations). A concept is "found" by
      lexical  : services.semantic.baseline.token_overlap_score == 1.0 (the live rule) -- also reported at > 0
      semantic : lexical == 1.0 OR best-sentence cosine >= threshold
    The threshold is chosen on TRAIN only (max F1), reported on validation, and the test split is scored once
    (`--final`, refuses to run twice). Metrics are pooled over (answer, concept) pairs; the CI is a question bootstrap.

    Phase 1:  python -m experiments.semantic_concept_eval --out DIR
    Phase 2:  python -m experiments.semantic_concept_eval --out DIR --final

STATUS: offline experiment. Annotations are synthetic and tier-derived; a result here is not agreement with human annotators.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from services.preprocessing.text_normalizer import process_text
from services.semantic.baseline import token_overlap_score
from services.semantic.semantic_matcher import SemanticMatcher

DATASET = Path(__file__).resolve().parents[1] / "datasets" / "c3_phase3_v5_repaired_v2"
MODEL_NOTE = "sentence-transformers/all-MiniLM-L6-v2 (pretrained, not trained here)"


def _list(cell: str) -> list[str]:
    try:
        value = json.loads(cell) if cell else []
    except json.JSONDecodeError:
        return []
    return [str(v) for v in value] if isinstance(value, list) else []


def build_pairs(split: str, matcher: SemanticMatcher) -> pd.DataFrame:
    """One row per (answer, candidate concept) with the lexical overlap, best-sentence cosine and the label."""
    df = pd.read_csv(DATASET / f"controlled_answers_{split}.csv", dtype=str, keep_default_na=False)
    rows = []
    for _, r in df.iterrows():
        pos, neg = _list(r["demonstrated_concepts"]), _list(r["missing_concepts"])
        concepts = pos + neg
        if not concepts:
            continue
        processed = process_text(r["student_answer"])
        sims = matcher.similarities(concepts, processed.sentences)
        if sims is None:
            raise RuntimeError("semantic matcher unavailable (is sentence-transformers installed?)")
        for i, concept in enumerate(concepts):
            rows.append({
                "question_id": r["question_id"], "answer_id": r["answer_id"], "concept": concept,
                "label": int(i < len(pos)),
                "lexical": token_overlap_score(concept, processed.tokens),
                "cosine": float(sims[i].max()),
            })
    return pd.DataFrame(rows)


def prf(label: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    tp = int(((pred == 1) & (label == 1)).sum())
    fp = int(((pred == 1) & (label == 0)).sum())
    fn = int(((pred == 0) & (label == 1)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4), "tp": tp, "fp": fp, "fn": fn}


def predictions(pairs: pd.DataFrame, threshold: float | None) -> np.ndarray:
    lex = pairs["lexical"].to_numpy() == 1.0
    if threshold is None:
        return lex.astype(int)
    return (lex | (pairs["cosine"].to_numpy() >= threshold)).astype(int)


def choose_threshold(train: pd.DataFrame) -> tuple[float, list[dict]]:
    grid = [round(t, 2) for t in np.arange(0.20, 0.91, 0.02)]
    curve = [{"threshold": t, **prf(train["label"].to_numpy(), predictions(train, t))} for t in grid]
    best = max(curve, key=lambda c: (c["f1"], c["threshold"]))
    return best["threshold"], curve


def bootstrap_f1(pairs: pd.DataFrame, threshold: float | None, n: int = 1000, seed: int = 20261027) -> list[float]:
    rng = np.random.default_rng(seed)
    groups = {q: g for q, g in pairs.groupby("question_id")}
    qs = list(groups)
    scores = []
    for _ in range(n):
        sample = pd.concat([groups[q] for q in rng.choice(qs, size=len(qs), replace=True)])
        scores.append(prf(sample["label"].to_numpy(), predictions(sample, threshold))["f1"])
    return [round(float(np.percentile(scores, 2.5)), 4), round(float(np.percentile(scores, 97.5)), 4)]


def report(pairs: pd.DataFrame, threshold: float) -> dict:
    lab = pairs["label"].to_numpy()
    lexical_partial = (pairs["lexical"].to_numpy() > 0).astype(int)
    return {
        "n_pairs": int(len(pairs)), "n_positive": int(lab.sum()), "n_negative": int((1 - lab).sum()),
        "lexical_live_rule": prf(lab, predictions(pairs, None)),
        "lexical_any_overlap": prf(lab, lexical_partial),
        "semantic": prf(lab, predictions(pairs, threshold)),
        "f1_ci95_lexical": bootstrap_f1(pairs, None), "f1_ci95_semantic": bootstrap_f1(pairs, threshold),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--final", action="store_true", help="score the test split once")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    matcher = SemanticMatcher()

    if not args.final:
        train, val = build_pairs("train", matcher), build_pairs("validation", matcher)
        threshold, curve = choose_threshold(train)
        result = {"model": MODEL_NOTE, "labels": "tier-derived synthetic annotations", "threshold_from": "TRAIN max F1",
                  "threshold": threshold, "train": report(train, threshold), "validation": report(val, threshold), "curve": curve}
        (out / "semantic_phase1.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({k: result[k] for k in ("threshold", "train", "validation")}, indent=2))
        return 0

    final_path = out / "semantic_test_final.json"
    if final_path.exists():
        print("REFUSED: the test split was already scored once.", file=sys.stderr)
        return 2
    phase1 = json.loads((out / "semantic_phase1.json").read_text(encoding="utf-8"))
    test = build_pairs("test", matcher)
    result = {"model": MODEL_NOTE, "threshold": phase1["threshold"], "test": report(test, phase1["threshold"])}
    final_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
