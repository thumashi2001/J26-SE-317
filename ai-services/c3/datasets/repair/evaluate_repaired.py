"""Offline recomputation of the lexical-overlap baseline and Condition E on the repaired (and original) splits.

The rubric construction (`build_legacy_rubric`), the question/concept parsing and the token-overlap baseline are the
minimal logic of `ai-services/c3/experiments/run_evaluation.py` at git commit f21dba4 (that file was deleted later);
they are copied here, not imported. Condition E is `services.marking.marking_engine.mark_answer`, the same
deterministic engine `assess_answer` used for its marks. No LLM / network call, nothing is tuned on any split.

Differences from the legacy run, all deliberate: (1) the repaired set uses `max_marks` (the question's marks) because the
legacy script read the overloaded `marks` column, which for non-FULL canonical rows equals the expected mark; (2) a
question whose rubric cannot be built is recorded as `not_evaluable` (the legacy single-criterion fallback is used only for
the ORIGINAL comparison, flagged per row); (3) failed marking calls are excluded and counted, never scored 0.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.schemas.marking import MarkingRequest, Rubric, RubricCriterion, ScoringLevel
from datasets.repair.common import ARCHIVE_DIR, LABELS, read_csv, write_json
from services.marking.marking_engine import mark_answer
from services.preprocessing.text_normalizer import tokenize

BOOTSTRAP_SEED = 20261021
BOOTSTRAP_N = 2000
DOC_CLAIMS = {  # quoted from docs/pp1/component-3/DATASET_AND_EVALUATION_REPORT.md; "reported by documentation, not recomputed here"
    "condition_e_mae": 4.640, "baseline_mae": 5.609, "condition_e_rmse": 7.220, "condition_e_pearson": 0.7243,
    "condition_e_within_2": "56.0% (84/150)", "baseline_within_2": "20.7%",
}


def parse_concepts(val: str) -> list[str]:
    """f21dba4 datasets/loader.py::parse_concepts - JSON array or semicolon-delimited string."""
    if not val or val.strip().lower() in ("nan", "none", "", "null"):
        return []
    val = val.strip()
    if val.startswith("["):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return [str(c).strip() for c in parsed if str(c).strip()]
        except json.JSONDecodeError:
            pass
    return [c.strip() for c in val.split(";") if c.strip()]


def build_legacy_rubric(question_id: str, max_marks: float, expected_concepts: list[str],
                        rubric_rows: list[dict[str, str]], allow_fallback: bool) -> tuple[Rubric | None, str]:
    """f21dba4 experiments/run_evaluation.py::build_synthetic_rubric. Returns (rubric, source)."""
    if rubric_rows:
        criteria = []
        for idx, row in enumerate(rubric_rows):
            c_marks = float(row.get("criterion_marks") or max_marks / len(rubric_rows))
            c_id = row.get("criterion_id") or f"C{idx + 1}"
            c_desc = row.get("criterion") or f"Criterion {idx + 1}"
            levels = [ScoringLevel(level_id="L0", label="None", mark=0.0, descriptor="No evidence provided."),
                      ScoringLevel(level_id="L1", label="Proficient", mark=c_marks,
                                   descriptor=f"Meets expectations for {c_desc}.")]
            criteria.append(RubricCriterion(criterion_id=c_id, description=c_desc, max_marks=c_marks,
                                            required_concepts=expected_concepts[:2] if expected_concepts else [],
                                            scoring_levels=levels))
        total = sum(c.max_marks for c in criteria)
        if abs(total - max_marks) > 0.001:
            factor = max_marks / total
            for c in criteria:
                c.max_marks = round(c.max_marks * factor, 2)
                c.scoring_levels[-1].mark = c.max_marks
        return Rubric(rubric_id=f"R-{question_id}", title=f"Rubric for {question_id}", criteria=criteria), "rubric_file"
    if not allow_fallback:
        return None, "no_rubric_rows"
    return Rubric(rubric_id=f"R-{question_id}", title=f"Rubric for {question_id}", criteria=[RubricCriterion(
        criterion_id="C1", description="General answer accuracy and completeness", max_marks=max_marks,
        required_concepts=expected_concepts,
        scoring_levels=[ScoringLevel(level_id="L0", label="None", mark=0.0, descriptor="No concepts identified."),
                        ScoringLevel(level_id="L1", label="Partial", mark=round(max_marks * 0.5, 2),
                                     descriptor="Partially demonstrated."),
                        ScoringLevel(level_id="L2", label="Proficient", mark=max_marks,
                                     descriptor="Fully demonstrated.")])]), "legacy_single_criterion_fallback"


def lexical_baseline(student: str, reference: str, max_marks: float) -> float:
    """f21dba4 token-overlap baseline: |answer tokens & reference tokens| / |reference tokens| x max marks."""
    a, r = set(tokenize(student)), set(tokenize(reference)) if reference else set()
    return round(len(a & r) / len(r) * max_marks, 2) if r and a else 0.0


def _pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    """Pearson correlation, or None when it is undefined."""
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def metrics(pred: list[float], gt: list[float], mx: list[float], clusters: list[str]) -> dict[str, Any]:
    """Error metrics (MAE, RMSE, correlation, tolerance rates) with a bootstrap interval grouped by question."""
    p, g, m = np.asarray(pred, float), np.asarray(gt, float), np.asarray(mx, float)
    n = len(p)
    if n == 0:
        return {"n": 0}
    err = np.abs(p - g)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boots = [float(err[rng.integers(0, n, n)].mean()) for _ in range(BOOTSTRAP_N)]
    uniq = sorted(set(clusters))
    cl_idx = {c: np.array([i for i, x in enumerate(clusters) if x == c]) for c in uniq}
    rng2 = np.random.default_rng(BOOTSTRAP_SEED)
    cboots = []
    for _ in range(BOOTSTRAP_N):
        pick = rng2.integers(0, len(uniq), len(uniq))
        cboots.append(float(err[np.concatenate([cl_idx[uniq[i]] for i in pick])].mean()))
    r = _pearson(p, g)
    return {
        "n": n, "mae": float(err.mean()), "rmse": float(math.sqrt(float(np.mean((p - g) ** 2)))),
        "pearson_r": r, "within_2_marks": float(np.mean(err <= 2.0)), "within_2_marks_n": int((err <= 2.0).sum()),
        "within_10pct_of_max": float(np.mean(err <= 0.1 * m)), "within_10pct_of_max_n": int((err <= 0.1 * m).sum()),
        "mae_ci95_answer_bootstrap": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        "mae_ci95_question_cluster_bootstrap": [float(np.percentile(cboots, 2.5)), float(np.percentile(cboots, 97.5))],
    }


def evaluate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """rows: dicts with tier, gt, max, pred_e, pred_b, failed_e, question_id."""
    out: dict[str, Any] = {}
    for method, key in (("baseline", "pred_b"), ("condition_e", "pred_e")):
        ok = [r for r in rows if not (r["failed"] and not r.get("scored_zero") and method == "condition_e")]
        block = {"overall": metrics([r[key] for r in ok], [r["gt"] for r in ok], [r["max"] for r in ok],
                                    [r["question_id"] for r in ok]), "per_tier": {}}
        for lab in LABELS:
            sub = [r for r in ok if r["tier"] == lab]
            block["per_tier"][lab] = metrics([r[key] for r in sub], [r["gt"] for r in sub], [r["max"] for r in sub],
                                             [r["question_id"] for r in sub])
        block["failures"] = sum(1 for r in rows if r["failed"]) if method == "condition_e" else 0
        block["failures_scored_zero"] = sum(1 for r in rows if r.get("scored_zero")) if method == "condition_e" else 0
        out[method] = block
    out["n_total"] = len(rows)
    return out


def run_rows(answers: pd.DataFrame, questions: dict[str, dict[str, str]], rubric_by_q: dict[str, list[dict[str, str]]],
             max_mode: str, allow_fallback: bool, score_failures_zero: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Run the baseline and the rubric engine on every answer and collect predictions and failures."""
    rows: list[dict[str, Any]] = []
    not_evaluable: list[dict[str, str]] = []
    cache: dict[str, tuple[Rubric | None, str]] = {}
    for a in answers.to_dict("records"):
        qid = a["question_id"]
        q = questions[qid]
        qmax = float(q["marks"])
        mx = float(a["marks"] or qmax) if max_mode == "legacy_answer_marks_column" else qmax
        concepts = parse_concepts(q["expected_concepts"])
        key = f"{qid}|{mx}"
        if key not in cache:
            try:
                cache[key] = build_legacy_rubric(qid, mx, concepts, rubric_by_q.get(qid, []), allow_fallback)
            except Exception as exc:  # e.g. max_marks 0 -> invalid criterion
                cache[key] = (None, f"rubric_build_error: {type(exc).__name__}")
        rubric, source = cache[key]
        if rubric is None:
            not_evaluable.append({"answer_id": a["answer_id"], "question_id": qid, "reason": source})
            continue
        ref = q["reference_answer"] or a.get("reference_answer", "")
        row = {"answer_id": a["answer_id"], "question_id": qid, "tier": a["answer_quality"], "gt": float(a["expected_mark"]),
               "max": mx, "rubric_source": source, "pred_b": lexical_baseline(a["student_answer"], ref, mx),
               "pred_e": float("nan"), "failed": False, "error": ""}
        try:
            req = MarkingRequest.model_validate({
                "question_id": qid, "question_text": q["question_text"], "student_answer": a["student_answer"],
                "reference_answer": ref, "expected_concepts": concepts, "answer_type": "short", "rubric": rubric})
            row["pred_e"] = float(mark_answer(req).total_awarded_marks)
        except Exception as exc:  # excluded and counted, never scored 0
            row["failed"], row["error"] = True, f"{type(exc).__name__}: {exc}"
            if score_failures_zero:  # legacy behaviour (run_evaluation.py: pred_mark = 0.0 on exception)
                row["pred_e"], row["scored_zero"] = 0.0, True
        rows.append(row)
    return rows, not_evaluable


def _rubric_index(df: pd.DataFrame) -> dict[str, list[dict[str, str]]]:
    """Group rubric rows by question id."""
    idx: dict[str, list[dict[str, str]]] = {}
    for r in df.to_dict("records"):
        idx.setdefault(r["question_id"], []).append(r)
    return idx


def _fmt(v: Any, nd: int = 3) -> str:
    """Format a number to fixed decimals, or 'n/a'."""
    return "n/a" if v is None else f"{v:.{nd}f}"


def _row_md(label: str, m: dict[str, Any]) -> str:
    """One Markdown table row for a metrics block."""
    if not m or m.get("n", 0) == 0:
        return f"| {label} | 0 | - | - | - | - | - | - |"
    lo, hi = m["mae_ci95_answer_bootstrap"]
    return (f"| {label} | {m['n']} | {_fmt(m['mae'])} | {_fmt(m['rmse'])} | {_fmt(m['pearson_r'], 4)} | "
            f"{m['within_2_marks_n']}/{m['n']} ({m['within_2_marks'] * 100:.1f}%) | "
            f"{m['within_10pct_of_max_n']}/{m['n']} ({m['within_10pct_of_max'] * 100:.1f}%) | [{lo:.3f}, {hi:.3f}] |")


def render_table(report: dict[str, Any]) -> str:
    """Markdown table of the evaluation report."""
    head = ("| set / method | n | MAE | RMSE | Pearson r | within +-2 marks | within 10% of max | MAE 95% CI (answer bootstrap) |\n"
            "|---|---|---|---|---|---|---|---|")
    lines = ["Recomputed offline on 2026-10-21 by `datasets/repair/evaluate_repaired.py` (no LLM, nothing tuned). "
             "Numbers quoted in older documents are 'reported by documentation, not recomputed here' unless listed in the "
             "last section.", ""]
    for name, blocks in report["sets"].items():
        lines += [f"### {name}", "", head]
        for method in ("baseline", "condition_e"):
            b = blocks[method]
            lines.append(_row_md(f"{method} overall", b["overall"]))
            for lab in LABELS:
                lines.append(_row_md(f"{method} {lab}", b["per_tier"][lab]))
            if method == "condition_e":
                zeroed = b.get("failures_scored_zero", 0)
                how = f"scored 0.0 as the legacy script did: {zeroed}" if zeroed else "excluded and counted, not scored"
                lines.append(f"\nfailed marking calls: {b['failures']} ({how})\n")
        ne = report["not_evaluable"].get(name, [])
        lines.append(f"not_evaluable answers: {len(ne)}\n")
    lines += ["### Documentation claims vs recomputation", "",
              "| quantity | reported by documentation (not recomputed here) | recomputed here on the original test split "
              "(legacy settings) | reproduced |", "|---|---|---|---|"]
    cmp = report["documentation_vs_recomputed"]
    for k, v in cmp["rows"].items():
        lines.append(f"| {k} | {v['documented']} | {v['recomputed']} | {v.get('reproduced', '')} |")
    lines += ["", cmp["note"], ""]
    return "\n".join(lines)


def evaluate(directory: Path, archive_dir: Path = ARCHIVE_DIR) -> dict[str, Any]:
    """Recompute baseline and rubric-engine metrics on a repaired dataset directory."""
    d = Path(directory)
    q = read_csv(d / "01_question_bank.csv")
    questions = {r["question_id"]: r for r in q.to_dict("records")}
    rubric = _rubric_index(read_csv(d / "03_rubric_criteria.csv"))
    ea = read_csv(d / "02_controlled_answers_eligible.csv")
    sets: dict[str, Any] = {}
    not_eval: dict[str, list] = {}
    for split in ("test", "validation", "train"):
        rows, ne = run_rows(ea[ea["split"] == split], questions, rubric, "question_marks", allow_fallback=False)
        name = f"repaired eligible {split}"
        sets[name] = evaluate_rows(rows)
        not_eval[name] = ne
    # ORIGINAL test split, all 150 answers with original labels; legacy settings and corrected max marks
    oq = read_csv(Path(archive_dir) / "01_FINAL_question_bank.csv")
    oa = read_csv(Path(archive_dir) / "02_FINAL_controlled_answers.csv")
    oru = read_csv(Path(archive_dir) / "03_FINAL_rubric_criteria.csv")
    oquestions = {r["question_id"]: r for r in oq.to_dict("records")}
    orub = _rubric_index(oru)
    otest = oa[oa["split"] == "test"]
    legacy_name = "original test (legacy reproduction: max=answers.marks column, fallback rubric, failed calls scored 0)"
    for name, mode, zero in ((legacy_name, "legacy_answer_marks_column", True),
                             ("original test (like-for-like: max=question marks, fallback rubric, failures excluded)",
                              "question_marks", False)):
        rows, ne = run_rows(otest, oquestions, orub, mode, allow_fallback=True, score_failures_zero=zero)
        blocks = evaluate_rows(rows)
        blocks["fallback_rubric_answers"] = sum(1 for r in rows if r["rubric_source"] != "rubric_file")
        sets[name] = blocks
        not_eval[name] = ne
    legacy = sets[legacy_name]
    lg_e, lg_b = legacy["condition_e"]["overall"], legacy["baseline"]["overall"]
    rows_cmp = {
        "Condition E MAE": {"documented": DOC_CLAIMS["condition_e_mae"], "recomputed": _fmt(lg_e["mae"])},
        "Condition E RMSE": {"documented": DOC_CLAIMS["condition_e_rmse"], "recomputed": _fmt(lg_e["rmse"])},
        "Condition E Pearson r": {"documented": DOC_CLAIMS["condition_e_pearson"], "recomputed": _fmt(lg_e["pearson_r"], 4)},
        "Condition E within +-2 marks": {"documented": DOC_CLAIMS["condition_e_within_2"],
                                         "recomputed": f"{lg_e['within_2_marks'] * 100:.1f}% ({lg_e['within_2_marks_n']}/{lg_e['n']})"},
        "Lexical baseline MAE": {"documented": DOC_CLAIMS["baseline_mae"], "recomputed": _fmt(lg_b["mae"])},
        "Lexical baseline within +-2 marks": {"documented": DOC_CLAIMS["baseline_within_2"],
                                              "recomputed": f"{lg_b['within_2_marks'] * 100:.1f}% ({lg_b['within_2_marks_n']}/{lg_b['n']})"},
    }
    repro = {
        "Condition E MAE": abs(lg_e["mae"] - DOC_CLAIMS["condition_e_mae"]) < 0.0005,
        "Condition E RMSE": abs(lg_e["rmse"] - DOC_CLAIMS["condition_e_rmse"]) < 0.0005,
        "Condition E Pearson r": abs(lg_e["pearson_r"] - DOC_CLAIMS["condition_e_pearson"]) < 0.00005,
        "Lexical baseline MAE": abs(lg_b["mae"] - DOC_CLAIMS["baseline_mae"]) < 0.0005,
    }
    for k, v in rows_cmp.items():
        v["reproduced"] = str(repro[k]) if k in repro else ""
    zeroed = legacy["condition_e"]["failures_scored_zero"]
    note = ("Reproduced: " + (", ".join(k for k, ok in repro.items() if ok) or "none") + ". Not reproduced: "
            + (", ".join(k for k, ok in repro.items() if not ok) or "none") + ". In the legacy reproduction "
            + f"{zeroed} of {legacy['n_total']} marking calls raised an exception (the overloaded `marks` column is 0 "
            "for IRRELEVANT answers, so the legacy rubric had max_marks 0) and were scored 0.0, which equals their label: "
            "the documented Condition E figures are therefore flattered on IRRELEVANT answers. The like-for-like row above "
            "uses max=question marks and excludes no answer.")
    reproduced = all(repro.values())
    report: dict[str, Any] = {
        "method": "offline recomputation; lexical token-overlap baseline and Condition E (mark_answer); logic from "
                  "git f21dba4 experiments/run_evaluation.py",
        "bootstrap": {"seed": BOOTSTRAP_SEED, "resamples": BOOTSTRAP_N},
        "sets": sets, "not_evaluable": not_eval,
        "documentation_vs_recomputed": {"rows": rows_cmp, "reproduced": reproduced, "note": note},
        "caveats": [
            "ground truth marks of the canonical questions are researcher-constructed tier marks, not expert marks",
            "reference answers are generic templates, rubric rows are question-level (1-2 criteria); Condition E sees at "
            "most the first two expected concepts per criterion (legacy rubric construction)",
            "repaired test = 15 questions / 90 answers (original 25 / 150); not comparable to any earlier figure except "
            "through the like-for-like original rows above",
        ],
    }
    report["table_md"] = render_table(report)
    return report


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description="Recompute baseline / Condition E metrics on the repaired dataset")
    ap.add_argument("directory", type=Path)
    ap.add_argument("--archive", type=Path, default=ARCHIVE_DIR)
    args = ap.parse_args(argv)
    report = evaluate(args.directory, args.archive)
    write_json(report, args.directory / "metrics_report.json")
    (args.directory / "metrics_table.md").write_text(report["table_md"], encoding="utf-8", newline="\n")
    from datasets.repair.repair import finalize_outputs

    finalize_outputs(args.directory)
    print(report["table_md"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
