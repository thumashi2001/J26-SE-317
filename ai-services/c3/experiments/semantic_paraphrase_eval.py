"""Evaluate lexical vs semantic concept detection on the human-labelled paraphrase benchmark (`semantic_paraphrase_benchmark_v1`).

PROTOCOL (fixed before any held-out item is scored)
    Question per item: does this answer demonstrate this concept?  Truth = human final label; "positive" = `demonstrated`.
      lexical : the live rule (analyzer, semantic layer off)
      semantic: lexical OR best-sentence cosine >= threshold (the analyzer's rule, C3_SEMANTIC_MATCH=local)
    The threshold is chosen on DEV items only (best macro-F1 over a fixed grid, ties -> higher threshold) and written to
    frozen_config.json together with the dataset hash. The held-out split is scored once with that frozen configuration;
    a second attempt is refused. Nothing is lowered to make a particular example pass.

    dev          python -m experiments.semantic_paraphrase_eval dev --out DIR
    heldout      python -m experiments.semantic_paraphrase_eval heldout --out DIR
    pipeline     python -m experiments.semantic_paraphrase_eval pipeline-check --out DIR
                 (runs the models on the AI-DRAFT proposed labels to exercise the code; the output is stamped NOT EVIDENCE)

REFUSALS
    dev / heldout stop with exit code 3 unless EVERY item of the split has human labels (>= 2 annotators, adjudicated when
    they disagree). Draft labels are never used as ground truth.

STATUS: harness only. At the time of writing no human labels exist, so no benchmark result has been produced.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from datasets.paraphrase_benchmark.validate import (
    DATASET_DIR,
    SCORED_STATUSES,
    content_hash,
    derive_final_label,
    derive_status,
    load_doc,
    validate_items,
)

MODEL_NOTE = "sentence-transformers/all-MiniLM-L6-v2 (pretrained, not trained here)"
THRESHOLD_GRID = [round(0.20 + 0.02 * k, 2) for k in range(36)]  # 0.20 .. 0.90
DEFAULT_THRESHOLD = 0.5
SCORE_ONLY_THRESHOLD = "2.0"  # above any cosine: the analyzer records scores but never upgrades a status
EXIT_NO_LABELS = 3
EXIT_REFUSED = 2


# ---------------------------------------------------------------- predictions


def real_runner(item: dict, semantic: bool) -> dict:
    """Run the production analyzer on one item; returns its lexical status and (semantic run) best-sentence cosine."""
    from app.schemas.analysis import AnswerAnalysisRequest
    from services.semantic import analyzer

    keys = ("C3_SEMANTIC_MATCH", "C3_SEMANTIC_THRESHOLD")
    saved = {k: os.environ.get(k) for k in keys}
    try:
        if semantic:
            os.environ["C3_SEMANTIC_MATCH"], os.environ["C3_SEMANTIC_THRESHOLD"] = "local", SCORE_ONLY_THRESHOLD
        else:
            os.environ.pop("C3_SEMANTIC_MATCH", None)
        request = AnswerAnalysisRequest(
            question_id=item["question_id"],
            question_text=item["question_text"],
            student_answer=item["student_answer"],
            expected_concepts=[item["concept"]],
            answer_type="short",
        )
        match = analyzer.analyze_answer(request).concept_matches[0]
        return {"status": match.status, "semantic_score": match.semantic_score}
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def collect_rows(items: list[dict], truth_of, runner=real_runner) -> list[dict]:
    """One row per item: truth, category, lexical status (layer off) and semantic score (layer on, never upgrading)."""
    rows = []
    for item in items:
        lexical = runner(item, False)
        scored = runner(item, True)
        if scored["status"] != lexical["status"]:
            raise RuntimeError(
                f"{item['item_id']}: score-only run changed the status; the threshold override is not working"
            )
        rows.append(
            {
                "item_id": item["item_id"],
                "group_id": item["group_id"],
                "concept": item["concept"],
                "category": item["category"],
                "truth": truth_of(item),
                "lexical_status": lexical["status"],
                "semantic_score": scored["semantic_score"],
            }
        )
    return rows


# -------------------------------------------------------------------- metrics


def system_status(row: dict, threshold: float | None) -> str:
    """Status the analyzer would report: the lexical status, upgraded to demonstrated by a high-enough cosine."""
    if threshold is not None and row["lexical_status"] != "demonstrated":
        score = row["semantic_score"]
        if score is not None and score >= threshold:
            return "demonstrated"
    return row["lexical_status"]


def _f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Precision, recall and F1 (0.0 when undefined)."""
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def binary_counts(rows: list[dict], threshold: float | None) -> dict:
    """Confusion counts for 'concept demonstrated' (positive) against the human label."""
    tp = fp = fn = tn = 0
    for row in rows:
        truth, pred = row["truth"] == "demonstrated", system_status(row, threshold) == "demonstrated"
        tp += truth and pred
        fp += (not truth) and pred
        fn += truth and (not pred)
        tn += (not truth) and (not pred)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def prf_report(counts: dict) -> dict:
    """Positive-class and negative-class precision/recall/F1 and their mean (macro-F1) from confusion counts."""
    p, r, f = _f1(counts["tp"], counts["fp"], counts["fn"])
    np_, nr, nf = _f1(counts["tn"], counts["fn"], counts["fp"])  # negative class as the positive one
    return {
        **counts,
        "positive": {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4)},
        "negative": {"precision": round(np_, 4), "recall": round(nr, 4), "f1": round(nf, 4)},
        "macro_f1": round((f + nf) / 2, 4),
        "accuracy": round((counts["tp"] + counts["tn"]) / max(1, sum(counts.values())), 4),
    }


def macro_f1(rows: list[dict], threshold: float | None) -> float:
    """Macro-F1 (positive and negative class) at a threshold; None means lexical only."""
    return prf_report(binary_counts(rows, threshold))["macro_f1"]


def label_by_status_matrix(rows: list[dict], threshold: float | None) -> dict:
    """Human label (rows) against the status the system reported (columns)."""
    matrix: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        matrix[row["truth"]][system_status(row, threshold)] += 1
    return {label: dict(counts) for label, counts in sorted(matrix.items())}


def by_group_key(rows: list[dict], threshold: float | None, key: str) -> dict:
    """Binary report per value of a row field (`category` or `concept`)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return {name: prf_report(binary_counts(g, threshold)) | {"n": len(g)} for name, g in sorted(groups.items())}


def errors(rows: list[dict], threshold: float | None) -> dict:
    """False positives (wrongly detected) and false negatives (missed) with their ids and scores."""
    out = {"false_positives": [], "false_negatives": []}
    for row in rows:
        truth, pred = row["truth"] == "demonstrated", system_status(row, threshold) == "demonstrated"
        entry = {k: row[k] for k in ("item_id", "category", "truth", "lexical_status", "semantic_score")}
        if pred and not truth:
            out["false_positives"].append(entry)
        elif truth and not pred:
            out["false_negatives"].append(entry)
    return out


def threshold_curve(rows: list[dict], grid: list[float] = THRESHOLD_GRID) -> list[dict]:
    """Missed vs wrongly-detected concepts at every threshold of the grid (for reporting the trade-off)."""
    curve = []
    for t in grid:
        report = prf_report(binary_counts(rows, t))
        curve.append(
            {
                "threshold": t,
                "missed": report["fn"],
                "wrongly_detected": report["fp"],
                "positive_f1": report["positive"]["f1"],
                "macro_f1": report["macro_f1"],
            }
        )
    return curve


def select_threshold(dev_rows: list[dict], grid: list[float] = THRESHOLD_GRID) -> dict:
    """Best macro-F1 on DEV over the grid; ties go to the higher (more cautious) threshold. Also reports lexical-only."""
    best = max(grid, key=lambda t: (macro_f1(dev_rows, t), t))
    lexical = macro_f1(dev_rows, None)
    chosen = macro_f1(dev_rows, best)
    return {
        "threshold": best,
        "dev_macro_f1_at_threshold": chosen,
        "dev_macro_f1_lexical": lexical,
        "dev_gain_over_lexical": round(chosen - lexical, 4),
        "grid": [grid[0], grid[-1], len(grid)],
        "rule": "max macro-F1 on DEV, ties -> higher threshold",
    }


def full_report(rows: list[dict], threshold: float) -> dict:
    """Everything reported for one split: lexical, semantic at the chosen and default thresholds, breakdowns, errors, curve."""

    def one(t: float | None) -> dict:
        return {
            "overall": prf_report(binary_counts(rows, t)),
            "label_by_status": label_by_status_matrix(rows, t),
            "by_category": by_group_key(rows, t, "category"),
            "by_concept": by_group_key(rows, t, "concept"),
            "errors": errors(rows, t),
        }

    return {
        "n_items": len(rows),
        "n_positive": sum(r["truth"] == "demonstrated" for r in rows),
        "lexical_layer_off": one(None),
        "semantic_layer_on_chosen_threshold": {"threshold": threshold, **one(threshold)},
        "semantic_layer_on_default_threshold": {"threshold": DEFAULT_THRESHOLD, **one(DEFAULT_THRESHOLD)},
        "threshold_sensitivity": threshold_curve(rows),
    }


# ------------------------------------------------------------------- protocol


def split_items(items: list[dict], split: str) -> list[dict]:
    """Items of one split."""
    return [i for i in items if i["split"] == split]


def unscorable(items: list[dict]) -> list[str]:
    """Ids of items without a settled human label."""
    return [i["item_id"] for i in items if derive_status(i) not in SCORED_STATUSES]


def _write(path: Path, payload: dict) -> None:
    """Write sorted JSON with Unix line endings."""
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def run_dev(items: list[dict], out: Path, runner=real_runner) -> dict:
    """Choose the threshold on DEV and freeze the configuration. Raises PermissionError without human labels."""
    dev = split_items(items, "dev")
    missing = unscorable(dev)
    if missing:
        raise PermissionError(
            f"{len(missing)} of {len(dev)} dev items have no settled human label (e.g. {missing[:3]})"
        )
    rows = collect_rows(dev, derive_final_label, runner)
    selection = select_threshold(rows)
    frozen = {"dataset_sha256": content_hash(items), "model": MODEL_NOTE, "selection": selection, "split_used": "dev"}
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "frozen_config.json", frozen)
    _write(out / "dev_report.json", full_report(rows, selection["threshold"]) | {"rows": rows})
    return frozen


def run_heldout(items: list[dict], out: Path, runner=real_runner) -> dict:
    """Score the held-out split once with the frozen configuration."""
    final = out / "heldout_final.json"
    if final.exists():
        raise FileExistsError("the held-out split was already scored once")
    if not (out / "frozen_config.json").exists():
        raise ValueError("no frozen_config.json: run the dev phase first")
    frozen = json.loads((out / "frozen_config.json").read_text(encoding="utf-8"))
    if frozen["dataset_sha256"] != content_hash(items):
        raise ValueError("dataset changed since the configuration was frozen; re-run the dev phase")
    held = split_items(items, "heldout")
    missing = unscorable(held)
    if missing:
        raise PermissionError(
            f"{len(missing)} of {len(held)} held-out items have no settled human label (e.g. {missing[:3]})"
        )
    rows = collect_rows(held, derive_final_label, runner)
    result = full_report(rows, frozen["selection"]["threshold"]) | {"frozen_config": frozen, "rows": rows}
    _write(final, result)
    return result


def run_pipeline_check(items: list[dict], out: Path, runner=real_runner) -> dict:
    """Exercise the whole pipeline on the AI-draft proposed labels. The result is stamped NOT EVIDENCE and freezes nothing."""
    rows = collect_rows(items, lambda i: i["draft"]["proposed_label"], runner)
    dev_rows = [r for r in rows if r["item_id"] in {i["item_id"] for i in split_items(items, "dev")}]
    held_rows = [r for r in rows if r not in dev_rows]
    selection = select_threshold(dev_rows)
    result = {
        "STAMP": "NOT EVIDENCE: labels are AI-drafted proposals, not human labels. Pipeline check only.",
        "label_source": "draft.proposed_label",
        "selection_on_dev": selection,
        "dev": full_report(dev_rows, selection["threshold"]),
        "heldout": full_report(held_rows, selection["threshold"]),
    }
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "DRAFT_NOT_EVIDENCE_pipeline_check.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module docstring)."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("phase", choices=["dev", "heldout", "pipeline-check"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--dataset", default=str(DATASET_DIR))
    args = ap.parse_args(argv)
    items = load_doc(Path(args.dataset))["items"]
    problems = validate_items(items)
    if not problems["ok"]:
        print("REFUSED: dataset failed validation", json.dumps(problems, indent=2), file=sys.stderr)
        return EXIT_REFUSED
    out = Path(args.out)
    try:
        result = {"dev": run_dev, "heldout": run_heldout, "pipeline-check": run_pipeline_check}[args.phase](items, out)
    except PermissionError as exc:
        print(f"NO HUMAN LABELS: {exc}", file=sys.stderr)
        return EXIT_NO_LABELS
    except (FileExistsError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(
        json.dumps(
            result.get("selection") or result.get("selection_on_dev") or result["lexical_layer_off"]["overall"],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
