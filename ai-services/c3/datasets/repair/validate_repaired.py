"""Validator for the repaired C3 dataset. Real checks only: a failing check is reported, never relaxed.

Hard checks decide the exit code; warn/info checks are reported prominently but do not.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from datasets.repair.common import (
    ARCHIVE_DIR,
    LABELS,
    NAN_WORD,
    NULL_TOKENS,
    REPAIRED_VERSION,
    SPLITS,
    TIER_SPEC_PATH,
    normalise_text,
    parse_json_list,
    ratio_concentration,
    read_csv,
    truncate_value,
)

REQUIRED_FILES = (
    "01_question_bank.csv", "02_controlled_answers_eligible.csv", "03_rubric_criteria.csv", "quarantine.csv",
    "repaired_ineligible_controls.csv", "review_queue.csv", "criterion_id_map.csv", "repair_manifest.csv",
    "manifest.json", *[f"controlled_answers_{s}.csv" for s in SPLITS], *[f"question_bank_{s}.csv" for s in SPLITS],
)
ANSWER_REQUIRED = ("question_id", "answer_id", "student_answer", "answer_quality", "expected_mark", "criterion_marks",
                   "split", "max_marks", "dataset_version")
QUESTION_REQUIRED = ("question_id", "question_text", "marks", "split", "eligibility_status", "dataset_version")
RUBRIC_REQUIRED = ("question_id", "rubric_id", "criterion_id", "criterion_marks")
LIST_COLS = ("demonstrated_concepts", "missing_concepts", "incorrect_concepts", "expected_concepts",
             "expected_relationships", "evidence_requirements")
SECRET_RE = re.compile(r"AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,}|GEMINI_API_KEY\s*=\s*\S+|OPENAI_API_KEY\s*=\s*\S+")
EPS = 1e-6


def _f(value: str) -> float:
    """Text to float (0.0 if it cannot be read)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def criterion_sum(cell: str) -> float | None:
    """Sum of per-criterion marks from the JSON or positional ('5,5') representation."""
    parsed = parse_json_list(cell)
    try:
        if parsed is not None:
            return float(sum(float(e["mark"]) for e in parsed))
        return float(sum(float(x) for x in cell.split(",")))
    except (KeyError, TypeError, ValueError):
        return None


def null_cell_problems(value: str) -> list[str]:
    """Reasons a cell contains a literal missing-value token (whole cell, list element or the word nan)."""
    problems = []
    text = value.strip()
    if text.lower() in NULL_TOKENS - {""}:
        problems.append("whole_cell_null_token")
    parsed = parse_json_list(text)
    if parsed is not None:
        if any(str(e).strip().lower() in NULL_TOKENS for e in parsed):
            problems.append("null_list_element")
    elif not problems and NAN_WORD.search(text):
        problems.append("embedded_nan_token")
    return problems


class Report:
    """Collects validation checks, each marked pass, fail or warning."""
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []
        self.sections: dict[str, Any] = {}

    def add(self, name: str, hard: bool, ok: bool, summary: str, details: Any = None, kind: str | None = None) -> None:
        """Record one check with its outcome and details."""
        status = kind or ("pass" if ok else ("fail" if hard else "warn"))
        self.checks.append({"name": name, "hard": hard, "status": status, "summary": summary,
                            "details": details if details is not None else {}})

    def as_dict(self, scope: str) -> dict[str, Any]:
        """The report as a dictionary with an overall PASS or FAIL."""
        hard_failures = [c["name"] for c in self.checks if c["hard"] and c["status"] == "fail"]
        return {"scope": scope, "overall": "FAIL" if hard_failures else "PASS",
                "hard_failures": hard_failures,
                "warnings": [c["name"] for c in self.checks if c["status"] == "warn"],
                "checks": self.checks, "sections": self.sections}


def _label_distribution(df: pd.DataFrame, mark_col: str = "expected_mark", max_col: str = "max_marks") -> dict[str, Any]:
    """Mark-ratio distribution per split."""
    out: dict[str, Any] = {}
    for split in (*SPLITS, "ALL"):
        sub = df if split == "ALL" else df[df["split"] == split]
        tiers = {}
        for lab in LABELS:
            t = sub[sub["answer_quality"] == lab]
            ratio = t[mark_col].map(_f) / t[max_col].map(_f) if len(t) else pd.Series(dtype=float)
            tiers[lab] = {"n": len(t), "share": round(len(t) / len(sub), 4) if len(sub) else 0.0,
                          "mean_ratio": round(float(ratio.mean()), 4) if len(t) else None}
        out[split] = {"n": len(sub), "tiers": tiers}
    return out


def _pearson(x: list[float], y: list[float]) -> float | None:
    """Pearson correlation, or None when it is undefined."""
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def validate_dir(directory: Path, archive_dir: Path | None = ARCHIVE_DIR, spec_path: Path = TIER_SPEC_PATH
                 ) -> dict[str, Any]:  # noqa: C901 - one linear sequence of checks
    """Run every dataset check (counts, splits, labels, rubrics, lineage) and return the report."""
    d = Path(directory)
    rep = Report()
    missing = [f for f in REQUIRED_FILES if not (d / f).exists()]
    rep.add("files_present", True, not missing, f"{len(REQUIRED_FILES) - len(missing)}/{len(REQUIRED_FILES)} files",
            {"missing": missing})
    if missing:
        return rep.as_dict("unknown")
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    scope = manifest.get("scope", "unknown")
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    q, ea, ru = read_csv(d / "01_question_bank.csv"), read_csv(d / "02_controlled_answers_eligible.csv"), read_csv(d / "03_rubric_criteria.csv")
    qa, ic = read_csv(d / "quarantine.csv"), read_csv(d / "repaired_ineligible_controls.csv")
    rq, cmap, rman = read_csv(d / "review_queue.csv"), read_csv(d / "criterion_id_map.csv"), read_csv(d / "repair_manifest.csv")
    # v2 lineage: a derived release lists the answers it moved to quarantine (from the repaired set) in v2_repair_ledger.csv.
    # Absent for a plain repair output, in which case every rule below stays exactly as strict as before.
    v2_ledger = read_csv(d / "v2_repair_ledger.csv") if (d / "v2_repair_ledger.csv").exists() else None
    v2_ids = set(v2_ledger["answer_id"]) if v2_ledger is not None else set()
    ocols = manifest["original_columns"]

    # 1 schema -----------------------------------------------------------------------------------------------
    problems: list[str] = []
    for name, df, orig, req in (("answers", ea, ocols["answers"], ANSWER_REQUIRED),
                                ("controls", ic, ocols["answers"], ANSWER_REQUIRED),
                                ("questions", q, ocols["question_bank"], QUESTION_REQUIRED),
                                ("rubric", ru, ocols["rubric"], RUBRIC_REQUIRED)):
        if list(df.columns[: len(orig)]) != orig:
            problems.append(f"{name}: original column order not preserved")
        for col in req:
            if col not in df.columns:
                problems.append(f"{name}: missing column {col}")
            elif (df[col].str.strip() == "").any():
                problems.append(f"{name}: empty required field {col} ({int((df[col].str.strip() == '').sum())} rows)")
    if list(qa.columns[: len(ocols["answers"])]) != ocols["answers"]:
        problems.append("quarantine: original column order not preserved")
    # The rows carry the stamp of the repair release that produced them. A derived release (v2) removes rows but never
    # rewrites them, so its manifest declares that stamp as row_dataset_version; it must be the repair tool's own stamp.
    row_version = manifest.get("row_dataset_version", manifest["dataset_version"])
    if "row_dataset_version" in manifest and manifest["row_dataset_version"] != REPAIRED_VERSION:
        problems.append(f"row_dataset_version {manifest['row_dataset_version']!r} is not the repair stamp {REPAIRED_VERSION!r}")
    wrong_version = [n for n, df in (("answers", ea), ("questions", q), ("rubric", ru), ("controls", ic))
                     if set(df["dataset_version"]) - {row_version}]
    if wrong_version:
        problems.append(f"dataset_version differs from {row_version} in {wrong_version}")
    rep.add("schema_required_fields", True, not problems, f"{len(problems)} problem(s)", {"problems": problems})

    # 2 counts -----------------------------------------------------------------------------------------------
    n_orig = manifest["counts"]["original"]["answers"]
    parts = {"eligible": len(ea), "quarantine": len(qa), "repaired_ineligible_controls": len(ic)}
    all_ids = list(ea["answer_id"]) + list(qa["answer_id"]) + list(ic["answer_id"])
    count_problems = []
    if sum(parts.values()) != n_orig:
        count_problems.append(f"{n_orig} original answers != {sum(parts.values())} accounted")
    if len(set(all_ids)) != len(all_ids):
        count_problems.append("an answer_id appears in more than one output table")
    q_orig = manifest["counts"]["original"]["questions"]
    if len(q) != q_orig:
        count_problems.append(f"question bank has {len(q)} rows, original scope {q_orig}")
    if int((q["eligibility_status"] == "eligible").sum()) != manifest["counts"]["repaired"]["eligible_questions"]:
        count_problems.append("eligible question count differs from manifest")
    if len(ru) != manifest["counts"]["original"]["rubric_rows"]:
        count_problems.append("rubric rows differ from original scope")
    arch = None
    if archive_dir is not None and (Path(archive_dir) / "01_FINAL_question_bank.csv").exists():
        arch = {"q": read_csv(Path(archive_dir) / "01_FINAL_question_bank.csv"),
                "a": read_csv(Path(archive_dir) / "02_FINAL_controlled_answers.csv")}
        scope_ids = set(manifest["scope_question_ids"])
        expected_ids = set(arch["a"][arch["a"]["question_id"].isin(scope_ids)]["answer_id"])
        if set(all_ids) != expected_ids:
            count_problems.append(f"answer ids differ from the original: {len(expected_ids - set(all_ids))} lost, "
                                  f"{len(set(all_ids) - expected_ids)} unexpected")
        if set(q["question_id"]) != scope_ids:
            count_problems.append("question ids differ from the original scope")
    rep.add("counts_reconcile", True, not count_problems,
            f"original {n_orig} = eligible {parts['eligible']} + quarantine {parts['quarantine']} + "
            f"ineligible controls {parts['repaired_ineligible_controls']}", {"parts": parts, "problems": count_problems,
                                                                             "compared_to_archive": arch is not None})

    # 3 ids ----------------------------------------------------------------------------------------------------
    dup = {"answer_id": int(pd.Series(all_ids).duplicated().sum()), "question_id": int(q["question_id"].duplicated().sum()),
           "criterion_id": int(ru["criterion_id"].duplicated().sum())}
    rep.add("id_uniqueness", True, not any(dup.values()), f"duplicate ids: {dup}", dup)

    # 4 split files ----------------------------------------------------------------------------------------------
    sp_problems = []
    for s in SPLITS:
        a_s = read_csv(d / f"controlled_answers_{s}.csv")
        q_s = read_csv(d / f"question_bank_{s}.csv")
        if list(a_s["answer_id"]) != list(ea[ea["split"] == s]["answer_id"]):
            sp_problems.append(f"controlled_answers_{s}.csv differs from the master")
        if list(q_s["question_id"]) != list(q[(q["split"] == s) & (q["eligibility_status"] == "eligible")]["question_id"]):
            sp_problems.append(f"question_bank_{s}.csv differs from the master")
        if set(a_s["split"]) - {s}:
            sp_problems.append(f"controlled_answers_{s}.csv contains other splits")
    rep.add("split_files_consistent", True, not sp_problems, f"{len(sp_problems)} problem(s)", {"problems": sp_problems})

    # 5 ranges / labels --------------------------------------------------------------------------------------------
    qmarks = dict(zip(q["question_id"], q["marks"].map(_f), strict=True))
    bad_range, bad_maxmarks = [], []
    for df in (ea, ic):
        for r in df.to_dict("records"):
            em, mx = _f(r["expected_mark"]), _f(r["max_marks"])
            if not (np.isfinite(em) and np.isfinite(mx)) or em < -EPS or em > mx + EPS:
                bad_range.append(r["answer_id"])
            if abs(mx - qmarks.get(r["question_id"], float("nan"))) > EPS:
                bad_maxmarks.append(r["answer_id"])
    rep.add("score_ranges", True, not bad_range and not bad_maxmarks,
            f"{len(bad_range)} out of 0<=expected_mark<=max_marks, {len(bad_maxmarks)} max_marks != question marks",
            {"out_of_range": bad_range[:20], "max_marks_mismatch": bad_maxmarks[:20]})
    bad_labels = sorted((set(ea["answer_quality"]) | set(ic["answer_quality"]) | set(qa["answer_quality"])) - set(LABELS))
    rep.add("label_values", True, not bad_labels, f"labels outside the 6 core tiers: {bad_labels}", {"bad": bad_labels})
    irr = pd.concat([ea[ea["answer_quality"] == "IRRELEVANT"], ic[ic["answer_quality"] == "IRRELEVANT"]])
    nonzero = [a for a, m in zip(irr["answer_id"], irr["expected_mark"], strict=True) if abs(_f(m)) > EPS]
    rep.add("irrelevant_marks_zero", True, not nonzero, f"{len(irr)} IRRELEVANT answers, {len(nonzero)} non-zero",
            {"non_zero": nonzero[:20]})

    # 6 rubric association ------------------------------------------------------------------------------------------
    elig_q = q[q["eligibility_status"] == "eligible"]
    elig_ids = set(elig_q["question_id"])
    rub_by_q = ru.groupby("question_id")
    no_rubric = sorted(elig_ids - set(ru["question_id"]))
    unknown = sorted(set(ru["question_id"]) - set(q["question_id"]))
    rid_mismatch = [qid for qid, rid in zip(elig_q["question_id"], elig_q["rubric_id"], strict=True)
                    if qid in rub_by_q.groups and set(rub_by_q.get_group(qid)["rubric_id"]) != {rid}]
    rep.add("rubric_association", True, not (no_rubric or unknown or rid_mismatch),
            f"{len(no_rubric)} eligible questions without rubric rows, {len(unknown)} rubric rows for unknown questions, "
            f"{len(rid_mismatch)} rubric_id mismatches", {"no_rubric": no_rubric, "unknown_question": unknown,
                                                           "rubric_id_mismatch": rid_mismatch})
    sums = {qid: float(g["criterion_marks"].map(_f).sum()) for qid, g in rub_by_q}
    bad_e = sorted(qid for qid in elig_ids if qid in sums and abs(sums[qid] - qmarks[qid]) > EPS)
    bad_i = sorted(qid for qid in set(q["question_id"]) - elig_ids if qid in sums and abs(sums[qid] - qmarks[qid]) > EPS)
    rep.add("rubric_criterion_sums_eligible", True, not bad_e, f"{len(bad_e)} eligible questions where rubric marks != question marks",
            {"mismatch": bad_e})
    rep.add("rubric_criterion_sums_ineligible", False, not bad_i,
            f"{len(bad_i)} ineligible questions where re-keyed rubric marks != question marks (the rows keep the replaced "
            "original's allocation)", {"mismatch": {k: [sums[k], qmarks[k]] for k in bad_i}})

    # 7 missing values / literal nan ---------------------------------------------------------------------------------
    nan_hits: dict[str, Counter] = {}
    empty_counts: dict[str, dict[str, int]] = {}
    for name, df in (("eligible_answers", ea), ("question_bank", q), ("rubric", ru), ("repaired_ineligible_controls", ic)):
        hits: Counter = Counter()
        for col in df.columns:
            for v in df[col]:
                for p in null_cell_problems(v):
                    hits[f"{col}:{p}"] += 1
        nan_hits[name] = hits
        empty_counts[name] = {c: int((df[c] == "").sum()) for c in df.columns if (df[c] == "").any()}
    n_hits = sum(sum(h.values()) for k, h in nan_hits.items() if k != "repaired_ineligible_controls")
    rep.add("no_literal_nan_none", True, n_hits == 0, f"{n_hits} literal nan/None/null cells or embedded tokens in the eligible "
            "answers, question bank and rubric", {k: dict(v) for k, v in nan_hits.items() if k != "repaired_ineligible_controls"})
    n_ctrl = sum(nan_hits["repaired_ineligible_controls"].values())
    rep.add("nan_in_ineligible_controls", False, n_ctrl == 0,
            f"{n_ctrl} literal nan cells remain in repaired_ineligible_controls (unrecoverable concept names, kept as in the "
            "original and listed in repair_manifest.csv as unrecoverable_nan_field; outside the primary set)",
            dict(nan_hits["repaired_ineligible_controls"]))
    rep.sections["empty_cells_by_table"] = empty_counts
    rep.sections["quarantine_cells_with_nan_expected"] = sum(
        1 for v in qa["student_answer"] if null_cell_problems(v))

    # 8 duplicates -----------------------------------------------------------------------------------------------------
    ea["_norm"] = ea["student_answer"].map(normalise_text)
    in_q: dict[tuple[str, str], list[str]] = defaultdict(list)
    for qid, nt, aid in zip(ea["question_id"], ea["_norm"], ea["answer_id"], strict=True):
        in_q[(qid, nt)].append(aid)
    dup_groups = {k: v for k, v in in_q.items() if len(v) > 1}
    flagged = set(ea[ea["review_status"] == "needs_review"]["answer_id"]) & set(rq["answer_id"])
    unflagged = [a for v in dup_groups.values() for a in v if a not in flagged]
    rep.add("duplicates_within_question", True, not unflagged,
            f"{sum(len(v) for v in dup_groups.values())} answers share their text with another variant of the same question; "
            f"{len(unflagged)} not flagged for review", {"groups": [v for v in dup_groups.values()], "unflagged": unflagged})
    ea["_template"] = ea["template_negative_control"] == "True"
    cross: dict[str, set[str]] = defaultdict(set)
    for nt, qid in zip(ea["_norm"], ea["question_id"], strict=True):
        cross[nt].add(qid)
    shared = {t for t, s in cross.items() if len(s) > 1}
    shared_rows = ea[ea["_norm"].isin(shared)]
    intentional = shared_rows[shared_rows["_template"]]
    accidental = shared_rows[~shared_rows["_template"]]
    rep.add("duplicates_across_questions", False, len(accidental) == 0,
            f"{len(intentional)} answers are intentional template negative controls (flagged); {len(accidental)} answers in "
            f"{accidental['_norm'].nunique()} strings are shared across questions without a flag (accidental)",
            {"intentional_answers": len(intentional), "intentional_strings": int(intentional["_norm"].nunique()),
             "accidental_answers": len(accidental), "accidental_strings": int(accidental["_norm"].nunique()),
             "accidental_by_tier": dict(Counter(accidental["answer_quality"])),
             "accidental_answer_ids": list(accidental["answer_id"])[:40]})
    exact_full_rows = int(ea.drop(columns=["answer_id", "_norm", "_template"]).duplicated().sum())
    rep.add("duplicates_exact_rows", True, exact_full_rows == 0, f"{exact_full_rows} exact duplicate rows (ignoring answer_id)")
    q["_norm"] = q["question_text"].map(normalise_text)
    qd_exact, qd_norm = int(q["question_text"].duplicated().sum()), int(q["_norm"].duplicated().sum())
    ref_rep = int(elig_q["reference_answer"].map(normalise_text).duplicated(keep=False).sum())
    rep.add("duplicates_question_content", True, qd_norm == 0, f"{qd_exact} exact / {qd_norm} normalised duplicate question "
            f"texts; {ref_rep} eligible questions share a reference_answer with another question (report-only)",
            {"reference_answer_shared": ref_rep})

    # 9 leakage ----------------------------------------------------------------------------------------------------------
    qs_by_split = {s: set(elig_q[elig_q["split"] == s]["question_id"]) for s in SPLITS}
    overlap = {f"{a}&{b}": sorted(qs_by_split[a] & qs_by_split[b]) for a in SPLITS for b in SPLITS if a < b}
    rep.add("split_question_disjoint", True, not any(overlap.values()), "question ids shared between splits: "
            f"{ {k: len(v) for k, v in overlap.items()} }", overlap)
    q_split = dict(zip(q["question_id"], q["split"], strict=True))
    mism = [a for a, qid, s in zip(pd.concat([ea, ic])["answer_id"], pd.concat([ea, ic])["question_id"],
                                   pd.concat([ea, ic])["split"], strict=True) if q_split.get(qid) != s]
    rep.add("answer_split_matches_question", True, not mism, f"{len(mism)} answers whose split differs from their question's",
            {"mismatch": mism[:20]})
    thr = float(spec["thresholds"]["max_cross_split_cosine"])
    texts = list(elig_q["question_text"])
    top: list[tuple[float, str, str]] = []
    max_cos = 0.0
    n_above = 0
    if len(texts) > 1:
        mat = TfidfVectorizer(token_pattern=r"[A-Za-z0-9']+").fit_transform(texts)
        sim = (mat @ mat.T).toarray()
        ids, spl = list(elig_q["question_id"]), list(elig_q["split"])
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if spl[i] != spl[j]:
                    top.append((float(sim[i, j]), ids[i], ids[j]))
        top.sort(reverse=True)
        if top:
            max_cos = top[0][0]
            n_above = sum(1 for t in top if t[0] > thr)
    rep.add("near_duplicate_questions_across_splits", False, n_above == 0,
            f"max TF-IDF cosine between questions of different splits = {max_cos:.3f} (threshold {thr}); {n_above} pairs above "
            "(report-only)", {"threshold": thr, "max": round(max_cos, 4), "pairs_above": n_above,
                              "top5": [[round(c, 4), a, b] for c, a, b in top[:5]]})
    split_of_text: dict[str, set[str]] = defaultdict(set)
    for nt, s in zip(ea["_norm"], ea["split"], strict=True):
        split_of_text[nt].add(s)
    x_split = {t for t, s in split_of_text.items() if len(s) > 1}
    xs_rows = ea[ea["_norm"].isin(x_split)]
    xs_int = xs_rows[xs_rows["_template"]]
    xs_acc = xs_rows[~xs_rows["_template"]]
    rep.add("cross_split_identical_answer_strings", False, len(xs_acc) == 0,
            f"{len(x_split)} answer strings occur in more than one split: {xs_int['_norm'].nunique()} intentional template "
            f"strings ({len(xs_int)} answers), {xs_acc['_norm'].nunique()} unflagged strings ({len(xs_acc)} answers) (report-only)",
            {"intentional_strings": int(xs_int["_norm"].nunique()), "unflagged_strings": int(xs_acc["_norm"].nunique()),
             "unflagged_by_tier": dict(Counter(xs_acc["answer_quality"]))})

    # 10 distributions / coverage -------------------------------------------------------------------------------------------
    rep.sections["label_distribution_eligible"] = _label_distribution(ea)
    rep.add("label_distribution", False, True, "per split and tier in sections.label_distribution_eligible", kind="info")
    bad_cov = {}
    for qid, g in ea.groupby("question_id"):
        if sorted(g["answer_quality"]) != sorted(LABELS):
            bad_cov[qid] = dict(Counter(g["answer_quality"]))
    uncovered = sorted(elig_ids - set(ea["question_id"]))
    ic_q = set(ic["question_id"]) & elig_ids
    rep.add("per_question_coverage", True, not bad_cov and not uncovered and not ic_q,
            f"{len(elig_ids) - len(bad_cov) - len(uncovered)}/{len(elig_ids)} eligible questions have exactly one answer per "
            "tier (6 variants)", {"bad": bad_cov, "no_answers": uncovered, "eligible_with_controls": sorted(ic_q)})
    # criterion sums
    bad_sum = []
    for r in pd.concat([ea, ic]).to_dict("records"):
        s = criterion_sum(r["criterion_marks"])
        if s is None or abs(s - _f(r["expected_mark"])) > EPS:
            bad_sum.append(r["answer_id"])
    rep.add("criterion_marks_sum_equals_expected_mark", True, not bad_sum,
            f"{len(bad_sum)} answers where sum(criterion_marks) != expected_mark", {"mismatch": bad_sum[:30]})
    cm_status = Counter(cmap["mapping_status"])
    rep.add("criterion_id_map", False, cm_status.get("UNRESOLVED", 0) == 0,
            f"{cm_status.get('RESOLVED', 0)} answer criterion ids resolved to a rubric row, {cm_status.get('UNRESOLVED', 0)} "
            "unresolved; resolved with equal marks: "
            f"{int((cmap['marks_agree'] == 'True').sum())}, with different marks: {int((cmap['marks_agree'] == 'False').sum())}",
            dict(cm_status))

    # 11 ratio concentration ------------------------------------------------------------------------------------------------
    thr_ratio = float(spec["thresholds"]["max_share_on_top7_ratios"])
    ratios = [_f(m) / _f(x) for m, x in zip(ea["expected_mark"], ea["max_marks"], strict=True)]
    value = ratio_concentration(ratios)
    inner = [round(r, 3) for r in ratios if 0.0 < r < 1.0]
    top7 = Counter(inner).most_common(7)
    rep.add("ratio_concentration", True, value <= thr_ratio,
            f"share of the {len(inner)} inner-label answers on the top-7 ratios = {value:.4f} (threshold {thr_ratio}, "
            f"definition: validation_spec.json max_share_on_top7_ratios)" + ("" if value <= thr_ratio else
                                                                       " - THRESHOLD EXCEEDED; threshold and labels NOT changed"),
            {"value": round(value, 6), "threshold": thr_ratio, "n_inner": len(inner), "top7": [[r, c] for r, c in top7]})
    # length vs mark
    excl = set(spec["thresholds"].get("length_corr_exclude_tiers", []))
    sub = ea[~ea["answer_quality"].isin(excl)]
    lens = [len(t.split()) for t in sub["student_answer"]]
    rr = [_f(m) / _f(x) for m, x in zip(sub["expected_mark"], sub["max_marks"], strict=True)]
    pr = _pearson([float(x) for x in lens], rr)
    thr_len = float(spec["thresholds"]["max_length_mark_pearson"])
    rep.add("answer_length_vs_mark_pearson", False, pr is None or abs(pr) <= thr_len,
            f"Pearson(words, expected_mark/max_marks) = {None if pr is None else round(pr, 4)} (spec threshold {thr_len}; "
            "report-only)", {"r": pr, "n": len(sub), "threshold": thr_len})

    # 12 preservation vs original, quarantine fidelity ------------------------------------------------------------------------
    if arch is not None:
        oa = arch["a"].set_index("answer_id")
        diffs = []
        for r in ea.to_dict("records"):
            o = oa.loc[r["answer_id"]]
            for col in ("answer_quality", "split", "expected_mark", "marks", "student_answer", "question_id", "criterion_marks"):
                if r[col] != o[col]:
                    diffs.append(f"{r['answer_id']}.{col}")
        q_diffs = [qid for qid, s in q_split.items() if s != dict(zip(arch["q"]["question_id"], arch["q"]["split"], strict=True))[qid]]
        # A quarantine row normally keeps the archive values. A row moved there by a derived release (v2 ledger) is a copy of
        # the repaired row, so a field may differ from the archive only where repair_manifest.csv records exactly that change
        # (file-level dataset_version stamp, or an answer-level entry whose original/repaired values match). Anything else fails.
        stamped = set(zip(*(rman[(rman["record_type"] == "file") & (rman["field"] == "dataset_version")][c]
                            for c in ("original_value", "repaired_value")), strict=True))
        logged = {(a, f, ov, rv) for a, f, ov, rv in zip(*(rman[rman["record_type"] == "answer"][c] for c in (
            "record_id", "field", "original_value", "repaired_value")), strict=True)}
        qa_diffs, explained = [], 0
        for r in qa.to_dict("records"):
            o = oa.loc[r["answer_id"]]
            for c in ocols["answers"]:
                if c == "answer_id" or r[c] == o[c]:
                    continue
                if r["answer_id"] in v2_ids and (
                        (o[c], r[c]) in stamped if c == "dataset_version"
                        else (r["answer_id"], c, truncate_value(o[c]), truncate_value(r[c])) in logged):
                    explained += 1
                else:
                    qa_diffs.append(f"{r['answer_id']}.{c}")
        no_reason = int((qa["quarantine_reason"].str.strip() == "").sum())
        rep.add("preserved_vs_original", True, not (diffs or q_diffs or qa_diffs or no_reason),
                f"{len(diffs)} eligible-answer fields differ from the original in labels/marks/text/split, {len(q_diffs)} question splits "
                f"changed, {len(qa_diffs)} quarantine fields differ from the original, {no_reason} quarantine rows without reason"
                + (f" ({explained} further fields of v2-quarantined answers differ only as recorded in repair_manifest.csv)"
                   if explained else ""),
                {"eligible_diffs": diffs[:20], "question_split_diffs": q_diffs, "quarantine_diffs": qa_diffs[:20],
                 "quarantine_diffs_explained_by_ledger": explained})
        oq = arch["q"]
        sc_orig = {s: int((arch["a"]["split"] == s).sum()) for s in SPLITS}
        oratios = [_f(m) / qmarks_orig for m, qmarks_orig in zip(
            arch["a"]["expected_mark"], arch["a"]["question_id"].map(dict(zip(oq["question_id"], oq["marks"].map(_f), strict=True))),
            strict=True)]
        olens = [len(t.split()) for t in arch["a"]["student_answer"]]
        rep.sections["original_vs_repaired"] = {
            "questions": {"original": len(oq), "eligible": len(elig_q), "ineligible": len(q) - len(elig_q)},
            "answers": {"original": len(arch["a"]), "eligible": len(ea), "quarantine": len(qa), "controls": len(ic)},
            "answers_by_split": {"original": sc_orig, "eligible": dict(Counter(ea["split"]))},
            "label_distribution": {"original": dict(Counter(arch["a"]["answer_quality"])),
                                   "eligible": dict(Counter(ea["answer_quality"]))},
            "ratio_concentration": {"original_all": round(ratio_concentration(oratios), 4), "repaired_eligible": round(value, 4)},
            "length_mark_pearson": {"original_all": _pearson([float(x) for x in olens], oratios), "repaired_eligible": pr},
        }
        canon_ids = set(oq[oq["is_replacement"] != "True"]["question_id"])
        keep = [i for i, qid in enumerate(arch["a"]["question_id"]) if qid in canon_ids]
        rep.sections["original_canonical_only"] = {
            "answers": len(keep),
            "ratio_concentration": round(ratio_concentration([oratios[i] for i in keep]), 4),
            "length_mark_pearson": _pearson([float(olens[i]) for i in keep], [oratios[i] for i in keep]),
        }
        rep.add("original_vs_repaired_counts", False, True, "see sections.original_vs_repaired", kind="info")
    else:
        rep.add("preserved_vs_original", False, True, "archive not available; comparison skipped", kind="info")

    # 13 manifest ledger / secrets ---------------------------------------------------------------------------------------------
    quar_in_ledger = set(rman[rman["repair_status"] == "quarantined"]["record_id"])
    ledger_problems = []
    if quar_in_ledger | v2_ids != set(qa["answer_id"]):
        ledger_problems.append("quarantined answers and ledger rows differ")
    if v2_ledger is not None:
        # the v2 ledger extends the v1 ledger: its answers are quarantined only in v2, listed once, and no longer eligible
        if quar_in_ledger & v2_ids:
            ledger_problems.append("v2 ledger answers already quarantined in repair_manifest.csv")
        if len(v2_ledger) != len(v2_ids):
            ledger_problems.append("duplicate answers in v2_repair_ledger.csv")
        if v2_ids != set(qa[qa["quarantine_reason"].str.startswith("v2:")]["answer_id"]):
            ledger_problems.append("v2 ledger and the v2 quarantine rows differ")
        if v2_ids & set(ea["answer_id"]):
            ledger_problems.append("v2 ledger answers still in the eligible set")
    if set(rman["repair_status"]) - {"repaired", "recovered", "quarantined", "needs_review", "flagged"}:
        ledger_problems.append("unknown repair_status in repair_manifest.csv")
    if (rman["validation_result"] == "fail").any():
        ledger_problems.append("ledger rows with validation_result=fail")
    if int(rman["record_type"].isin(["answer", "question", "rubric_row", "file"]).sum()) != len(rman):
        ledger_problems.append("unknown record_type")
    rep.add("repair_manifest_consistent", True, not ledger_problems, f"{len(rman)} ledger rows; {len(ledger_problems)} problem(s)",
            {"problems": ledger_problems})
    leaked = [f.name for f in d.glob("*.csv") if SECRET_RE.search(f.read_text(encoding="utf-8", errors="replace"))]
    rep.add("no_secrets_in_outputs", True, not leaked, f"files matching secret patterns: {leaked}")
    return rep.as_dict(scope)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description="Validate a repaired C3 dataset directory")
    ap.add_argument("directory", type=Path)
    ap.add_argument("--json", nargs="?", const="-", default=None, help="write the JSON report (path, or '-' for stdout)")
    ap.add_argument("--archive", type=Path, default=ARCHIVE_DIR)
    args = ap.parse_args(argv)
    report = validate_dir(args.directory, archive_dir=args.archive)
    if args.json == "-":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        if args.json:
            Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        for c in report["checks"]:
            print(f"[{c['status'].upper():4}] {'HARD' if c['hard'] else 'soft'}  {c['name']}: {c['summary']}")
        print(f"OVERALL: {report['overall']}  hard failures: {report['hard_failures'] or 'none'}  warnings: {report['warnings'] or 'none'}")
    return 1 if report["hard_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
