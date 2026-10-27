"""Reproducible, read-only audit of how the marks in a repaired C3 dataset relate to tiers, concepts, rubrics and length.

Usage: python -m datasets.repair.label_audit <dataset dir> [--json -]

Every number is computed from the CSV files in the directory (eligible answers, rubric rows, criterion-id map) and from
validation_spec.json; nothing is hardcoded, nothing is written. The output is descriptive: correlations and counts show
how the labels are structured, not why they were assigned that way. Each section carries the sample size it used and a
plain-language `method`.
"""

import argparse
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from datasets.repair.common import LABELS, TIER_SPEC_PATH, parse_json_list, ratio_concentration

EPS = 1e-9
MIDDLE_TIERS = ("MOSTLY_CORRECT", "PARTIAL", "MISSING_CONCEPT", "MISCONCEPTION")

CAVEATS = [
    "Descriptive statistics only: a correlation or an equal-marks count shows how the labels are structured, not how or why "
    "they were assigned.",
    "The dataset is synthetic and author-labelled; none of these figures measures agreement with an independent marker.",
    "Concept lists and criterion marks are taken as recorded in the CSVs; this audit does not judge whether they are right.",
    "Pearson r is computed on the stated subset only and is sensitive to a few extreme groups (see the per-subset values).",
]


def _read(path: Path) -> list[dict[str, str]]:
    """Read a CSV file as a list of dictionaries (one per row, all values text)."""
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _r(x: float | None, nd: int = 4) -> float | None:
    """Round a number, keeping None."""
    return None if x is None else round(x, nd)


def _corr(xs: list[float], ys: list[float]) -> float | None:
    """Correlation of two lists, or None when there are too few values."""
    try:
        return statistics.correlation(xs, ys) if len(xs) >= 3 else None
    except statistics.StatisticsError:  # constant input
        return None


def _ratio(row: dict[str, str]) -> float:
    """A row's expected mark divided by its maximum marks."""
    return float(row["expected_mark"]) / float(row["max_marks"])


def _count(cell: str) -> int | None:
    """Length of a JSON list cell, or None if it cannot be parsed."""
    lst = parse_json_list(cell or "")
    return None if lst is None else len(lst)


def _tier_marks(answers: list[dict[str, str]]) -> dict:
    """Per-tier mark-ratio spread and per-question checks of the tier ordering."""
    by_q: dict[str, dict[str, float]] = defaultdict(dict)
    per_tier: dict[str, list[float]] = defaultdict(list)
    for r in answers:
        by_q[r["question_id"]][r["answer_quality"]] = _ratio(r)
        per_tier[r["answer_quality"]].append(_ratio(r))
    complete = {q: t for q, t in by_q.items() if all(label in t for label in LABELS)}

    def same(a: float, b: float) -> bool:
        """True when two numbers are equal within a tiny tolerance."""
        return abs(a - b) < EPS

    return {
        "method": "mark ratio = expected_mark / max_marks per answer. Per-question comparisons use only questions that have "
                  "all six tiers.",
        "per_tier": {t: {"n": len(v), "mean_ratio": _r(statistics.fmean(v)), "min": _r(min(v)), "max": _r(max(v)),
                         "distinct_ratios": len({round(x, 6) for x in v})} for t, v in sorted(per_tier.items())},
        "questions_with_all_six_tiers": len(complete),
        "per_question": {
            "full_ratio_is_1": sum(1 for t in complete.values() if same(t["FULL"], 1.0)),
            "irrelevant_ratio_is_0": sum(1 for t in complete.values() if same(t["IRRELEVANT"], 0.0)),
            "mostly_missing_misconception_equal": sum(
                1 for t in complete.values()
                if same(t["MOSTLY_CORRECT"], t["MISSING_CONCEPT"]) and same(t["MISSING_CONCEPT"], t["MISCONCEPTION"])),
            "partial_below_mostly": sum(1 for t in complete.values() if t["PARTIAL"] < t["MOSTLY_CORRECT"] - EPS),
            "partial_at_or_below_missing": sum(1 for t in complete.values() if t["PARTIAL"] <= t["MISSING_CONCEPT"] + EPS),
        },
    }


def _concepts(answers: list[dict[str, str]], bank_expected: dict[str, int | None]) -> dict:
    """Consistency of the demonstrated, missing and incorrect concept lists."""
    cols = ("demonstrated_concepts", "missing_concepts", "incorrect_concepts")
    unparsable = Counter()
    per_tier: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    fractions, ratios, accounted, accountable = [], [], 0, 0
    answer_column_empty = sum(1 for r in answers if not r.get("expected_concepts", "").strip())
    for r in answers:
        counts = [_count(r[c]) for c in cols]
        for c, n in zip(cols, counts, strict=True):
            unparsable[c] += n is None
        if None in counts:
            continue
        dem, mis, inc = counts
        per_tier[r["answer_quality"]].append((dem, mis, inc))
        expected = bank_expected.get(r["question_id"])
        if expected is not None:
            accountable += 1
            accounted += dem + mis + inc == expected
        if dem + mis + inc > 0:
            fractions.append(dem / (dem + mis + inc))
            ratios.append(_ratio(r))
    return {
        "method": "Concept counts are the lengths of the JSON lists in demonstrated/missing/incorrect_concepts. The "
                  "'demonstrated fraction' is demonstrated / (demonstrated + missing + incorrect), defined only when that "
                  "sum is above zero; r is Pearson against the mark ratio over those answers. Concept accounting compares "
                  "that sum with the length of the question's expected_concepts list in 01_question_bank.csv (the answers "
                  "file's own expected_concepts column is empty, see the count below).",
        "unparsable_cells": dict(unparsable),
        "per_tier_mean_counts": {t: {k: _r(statistics.fmean(x[i] for x in v)) for i, k in enumerate(("demonstrated", "missing", "incorrect"))}
                                 for t, v in sorted(per_tier.items())},
        "demonstrated_fraction_vs_mark_ratio": {"n": len(fractions), "pearson_r": _r(_corr(fractions, ratios))},
        "expected_concepts_column_empty_in_answers_file": answer_column_empty,
        "concept_accounting": {"answers_checked": accountable,
                               "demonstrated_plus_missing_plus_incorrect_equals_question_expected_concepts": accounted},
    }


def _rubric(directory: Path, eligible: set[str]) -> dict:
    """Rubric-table checks for the eligible questions."""
    rows = [r for r in _read(directory / "03_rubric_criteria.csv") if r["question_id"] in eligible]
    columns = list(_read(directory / "03_rubric_criteria.csv")[0])
    per_q = Counter(r["question_id"] for r in rows)
    return {
        "method": "Rubric rows of the eligible questions, from 03_rubric_criteria.csv.",
        "eligible_questions": len(eligible),
        "questions_with_rubric_rows": len(per_q),
        "criteria_per_question": {str(k): v for k, v in sorted(Counter(per_q.values()).items())},
        "criterion_texts": dict(Counter(r["criterion"] for r in rows).most_common(5)),
        "columns_naming_levels_or_descriptors": [c for c in columns if "level" in c.lower() or "descriptor" in c.lower()],
        "rows_with_expected_concepts": sum(1 for r in rows if r["expected_concepts"].strip()),
        "rows_with_evidence_requirements": sum(1 for r in rows if r["evidence_requirements"].strip()),
        "rubric_status": dict(Counter(r["rubric_status"] for r in rows)),
    }


def _criterion_ids(directory: Path, answers: list[dict[str, str]], eligible: set[str]) -> dict:
    """Whether per-answer criterion marks refer to real rubric criteria and sum correctly."""
    rubric_ids = {r["criterion_id"] for r in _read(directory / "03_rubric_criteria.csv") if r["question_id"] in eligible}
    parsed = per_answer = exact = referenced = sums_match = 0
    sizes: Counter = Counter()
    for r in answers:
        try:
            items = json.loads(r["criterion_marks"])
            ids = [i["criterion_id"] for i in items]
            total = sum(float(i["mark"]) for i in items)
        except (ValueError, KeyError, TypeError):
            continue
        parsed += 1
        sizes[len(ids)] += 1
        referenced += len(ids)
        exact += sum(1 for i in ids if i in rubric_ids)
        sums_match += abs(total - float(r["expected_mark"])) < 1e-6
    cmap = [r for r in _read(directory / "criterion_id_map.csv") if r["question_id"] in eligible]
    return {
        "method": "criterion_marks is a JSON list of {criterion_id, mark} per answer. 'exact id match' compares each id with "
                  "the criterion_id column of the rubric rows of the eligible questions; the map section counts "
                  "criterion_id_map.csv rows of the eligible questions (its own normalised matching rule).",
        "answers": len(answers),
        "answers_with_parsable_criterion_marks": parsed,
        "criteria_per_answer": {str(k): v for k, v in sorted(sizes.items())},
        "criterion_marks_sum_equals_expected_mark": sums_match,
        "referenced_criterion_ids": referenced,
        "exact_match_to_a_rubric_criterion_id": exact,
        "rubric_criterion_ids": len(rubric_ids),
        "map_rows_for_eligible_questions": len(cmap),
        "map_status": dict(Counter(r["mapping_status"] for r in cmap)),
        "map_resolved_marks_agree": dict(Counter(r["marks_agree"] for r in cmap if r["mapping_status"] == "RESOLVED")),
    }


def _length(answers: list[dict[str, str]]) -> dict:
    """Correlation between answer length and mark ratio (a shortcut risk)."""
    words = [len(r["student_answer"].split()) for r in answers]
    ratios = [_ratio(r) for r in answers]
    tiers = [r["answer_quality"] for r in answers]
    per_tier: dict[str, list[int]] = defaultdict(list)
    for t, w in zip(tiers, words, strict=True):
        per_tier[t].append(w)

    def subset(keep) -> dict:
        """Length/mark correlation for the answers whose tier passes the filter."""
        idx = [i for i, t in enumerate(tiers) if keep(t)]
        return {"n": len(idx), "pearson_r": _r(_corr([words[i] for i in idx], [ratios[i] for i in idx]))}

    return {
        "method": "words = number of whitespace-separated tokens of student_answer; r is Pearson(words, mark ratio) on the "
                  "named subset.",
        "per_tier_words": {t: {"n": len(v), "mean": _r(statistics.fmean(v), 1), "median": statistics.median(v),
                               "sd": _r(statistics.pstdev(v), 1)} for t, v in sorted(per_tier.items())},
        "length_vs_mark_ratio": {"all_tiers": subset(lambda t: True), "without_IRRELEVANT": subset(lambda t: t != "IRRELEVANT"),
                                 "four_middle_tiers_only": subset(lambda t: t in MIDDLE_TIERS)},
    }


def _ratio_concentration(answers: list[dict[str, str]], spec_path: Path) -> dict:
    """Share of answers on the most common mark ratios against the allowed threshold."""
    threshold = float(json.loads(Path(spec_path).read_text(encoding="utf-8"))["thresholds"]["max_share_on_top7_ratios"])
    ratios = [_ratio(r) for r in answers]
    inner = [(round(x, 3), r["answer_quality"]) for x, r in zip(ratios, answers, strict=True) if 0.0 < x < 1.0]
    top7 = Counter(v for v, _ in inner).most_common(7)
    value = ratio_concentration(ratios)
    by_tier: dict[str, Counter] = defaultdict(Counter)
    for v, t in inner:
        by_tier[t][v] += 1
    return {
        "method": "Same definition as the validator: among answers with 0 < ratio < 1 (ratios rounded to 3 d.p.), the share "
                  "that sits on the 7 most frequent ratios. Threshold is read from validation_spec.json.",
        "threshold": threshold,
        "answers": len(ratios),
        "anchor_answers_ratio_0_or_1": len(ratios) - len(inner),
        "inner_label_answers": len(inner),
        "distinct_inner_ratios": len({v for v, _ in inner}),
        "top7_ratios": [[v, c] for v, c in top7],
        "share_on_top7": _r(value, 6),
        "exceeds_threshold": value > threshold,
        "inner_answers_by_tier": {t: sum(c.values()) for t, c in sorted(by_tier.items())},
        "most_common_ratio_by_tier": {t: [c.most_common(1)[0][0], c.most_common(1)[0][1]] for t, c in sorted(by_tier.items())},
    }


def audit(directory: Path, spec_path: Path = TIER_SPEC_PATH) -> dict:
    """Read-only audit of how marks relate to tiers, concepts, rubrics and length."""
    d = Path(directory)
    answers = _read(d / "02_controlled_answers_eligible.csv")
    eligible = {r["question_id"] for r in answers}
    bank_expected = {r["question_id"]: _count(r["expected_concepts"]) for r in _read(d / "01_question_bank.csv")
                     if r["question_id"] in eligible}
    return {
        "dataset": d.name,
        "sizes": {"eligible_answers": len(answers), "eligible_questions": len(eligible),
                  "answers_by_split": dict(sorted(Counter(r["split"] for r in answers).items())),
                  "answers_by_tier": dict(sorted(Counter(r["answer_quality"] for r in answers).items()))},
        "tier_marks": _tier_marks(answers),
        "concepts": _concepts(answers, bank_expected),
        "rubric": _rubric(d, eligible),
        "criterion_ids": _criterion_ids(d, answers, eligible),
        "length": _length(answers),
        "ratio_concentration": _ratio_concentration(answers, spec_path),
        "caveats": CAVEATS,
    }


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description="Read-only audit of how marks relate to tiers, concepts, rubrics and length")
    ap.add_argument("directory", type=Path)
    ap.add_argument("--json", nargs="?", const="-", default="-", help="'-' (the default) prints the JSON report to stdout")
    args = ap.parse_args(argv)
    print(json.dumps(audit(args.directory), indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
