"""The label audit computes what it claims: checked on hand-built toy datasets, on the committed v2 data, and against the report.

The toy datasets are tiny, synthetic and exist only to give the metrics known answers; they say nothing about real marks.
The audit and these tests are read-only.
"""

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from datasets.repair import label_audit
from datasets.repair.common import LABELS, TIER_SPEC_PATH
from datasets.repair.label_audit import _corr, audit

pytestmark = pytest.mark.dataset

V2_DIR = Path(__file__).resolve().parents[2] / "datasets" / "c3_phase3_v5_repaired_v2"
REPORT = Path(__file__).resolve().parents[4] / "reports" / "c3_remediation" / "24_stage2_label_audit.md"


# ------------------------------------------------------------------------------------------------ toy dataset
def _write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# tier -> (ratio, demonstrated, missing, incorrect, words)
TOY = {"FULL": (1.0, 3, 0, 0, 10), "MOSTLY_CORRECT": (0.8, 2, 1, 0, 8), "PARTIAL": (0.5, 1, 2, 0, 4),
       "MISSING_CONCEPT": (0.8, 2, 1, 0, 9), "MISCONCEPTION": (0.8, 2, 0, 1, 9), "IRRELEVANT": (0.0, 0, 0, 0, 1)}
MAX_MARKS = {"Q1": 10, "Q2": 20}


def _concepts(n, prefix):
    return json.dumps([f"{prefix}{i}" for i in range(n)])


@pytest.fixture()
def toy(tmp_path):
    answers, bank, rubric, cmap = [], [], [], []
    for q, mx in MAX_MARKS.items():
        bank.append({"question_id": q, "expected_concepts": _concepts(3, "c")})
        rubric.append({"question_id": q, "criterion_id": "Q1-C01" if q == "Q1" else "R-Q2-v1-C01", "criterion": "generic",
                       "expected_concepts": "", "evidence_requirements": "", "rubric_status": "draft"})
        cmap.append({"answer_criterion_id": f"{q}-C01", "question_id": q, "mapping_status": "RESOLVED", "marks_agree": "False"})
        cmap.append({"answer_criterion_id": f"{q}-C02", "question_id": q, "mapping_status": "UNRESOLVED", "marks_agree": ""})
        for tier, (ratio, dem, mis, inc, words) in TOY.items():
            mark = ratio * mx
            half = mark / 2
            answers.append({
                "question_id": q, "answer_id": f"{q}-{tier}", "answer_quality": tier, "split": "test",
                "expected_mark": str(mark), "max_marks": str(mx), "student_answer": " ".join(["w"] * words),
                "demonstrated_concepts": _concepts(dem, "d"), "missing_concepts": _concepts(mis, "m"),
                "incorrect_concepts": _concepts(inc, "i"), "expected_concepts": "",
                "criterion_marks": json.dumps([{"criterion_id": f"{q}-C01", "mark": half}, {"criterion_id": f"{q}-C02", "mark": half}]),
            })
    cmap.append({"answer_criterion_id": "Q9-C01", "question_id": "Q9", "mapping_status": "RESOLVED", "marks_agree": "True"})
    _write(tmp_path / "02_controlled_answers_eligible.csv", answers)
    _write(tmp_path / "01_question_bank.csv", bank)
    _write(tmp_path / "03_rubric_criteria.csv", rubric)
    _write(tmp_path / "criterion_id_map.csv", cmap)
    return tmp_path


def _spec(tmp_path, threshold):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps({"thresholds": {"max_share_on_top7_ratios": threshold}}), encoding="utf-8")
    return path


def test_sizes_and_tier_marks_on_the_toy_dataset(toy):
    r = audit(toy, _spec(toy, 0.9))
    assert r["sizes"]["eligible_answers"] == 12 and r["sizes"]["eligible_questions"] == 2
    assert r["sizes"]["answers_by_tier"] == {t: 2 for t in LABELS}
    pq = r["tier_marks"]["per_question"]
    assert r["tier_marks"]["questions_with_all_six_tiers"] == 2
    assert pq == {"full_ratio_is_1": 2, "irrelevant_ratio_is_0": 2, "mostly_missing_misconception_equal": 2,
                  "partial_below_mostly": 2, "partial_at_or_below_missing": 2}
    assert r["tier_marks"]["per_tier"]["MOSTLY_CORRECT"]["mean_ratio"] == 0.8


def test_tier_comparisons_notice_when_tiers_differ(toy):
    rows = list(csv.DictReader(open(toy / "02_controlled_answers_eligible.csv", encoding="utf-8", newline="")))
    for row in rows:
        if row["answer_id"] == "Q1-MISCONCEPTION":
            row["expected_mark"] = "2.0"
    _write(toy / "02_controlled_answers_eligible.csv", rows)
    pq = audit(toy, _spec(toy, 0.9))["tier_marks"]["per_question"]
    assert pq["mostly_missing_misconception_equal"] == 1
    assert pq["partial_at_or_below_missing"] == 2


def test_concept_counts_fraction_and_accounting(toy):
    c = audit(toy, _spec(toy, 0.9))["concepts"]
    assert c["per_tier_mean_counts"]["PARTIAL"] == {"demonstrated": 1.0, "missing": 2.0, "incorrect": 0.0}
    assert c["per_tier_mean_counts"]["MISCONCEPTION"] == {"demonstrated": 2.0, "missing": 0.0, "incorrect": 1.0}
    assert c["demonstrated_fraction_vs_mark_ratio"]["n"] == 10  # the two IRRELEVANT answers have no concepts at all
    assert 0.9 < c["demonstrated_fraction_vs_mark_ratio"]["pearson_r"] <= 1.0
    assert c["concept_accounting"] == {
        "answers_checked": 12, "demonstrated_plus_missing_plus_incorrect_equals_question_expected_concepts": 10}
    assert c["expected_concepts_column_empty_in_answers_file"] == 12


def test_unparsable_concept_cells_are_counted_and_skipped(toy):
    rows = list(csv.DictReader(open(toy / "02_controlled_answers_eligible.csv", encoding="utf-8", newline="")))
    rows[0]["missing_concepts"] = "nan"
    _write(toy / "02_controlled_answers_eligible.csv", rows)
    c = audit(toy, _spec(toy, 0.9))["concepts"]
    assert c["unparsable_cells"]["missing_concepts"] == 1
    assert c["demonstrated_fraction_vs_mark_ratio"]["n"] == 9


def test_ratio_concentration_uses_the_spec_threshold_and_anchors(toy):
    low, high = audit(toy, _spec(toy, 0.4))["ratio_concentration"], audit(toy, _spec(toy, 0.9))["ratio_concentration"]
    for r in (low, high):
        assert (r["answers"], r["anchor_answers_ratio_0_or_1"], r["inner_label_answers"]) == (12, 4, 8)
        assert r["top7_ratios"] == [[0.8, 6], [0.5, 2]] and r["share_on_top7"] == 1.0
    assert low["threshold"] == 0.4 and low["exceeds_threshold"] is True
    assert high["threshold"] == 0.9 and high["exceeds_threshold"] is True  # 1.0 > 0.9 as well
    assert audit(toy, _spec(toy, 1.0))["ratio_concentration"]["exceeds_threshold"] is False


def test_length_statistics(toy):
    ln = audit(toy, _spec(toy, 0.9))["length"]
    assert ln["per_tier_words"]["FULL"] == {"n": 2, "mean": 10.0, "median": 10, "sd": 0.0}
    assert ln["per_tier_words"]["IRRELEVANT"]["mean"] == 1.0
    assert ln["length_vs_mark_ratio"]["all_tiers"]["n"] == 12
    assert ln["length_vs_mark_ratio"]["without_IRRELEVANT"]["n"] == 10
    assert ln["length_vs_mark_ratio"]["four_middle_tiers_only"]["n"] == 8


def test_rubric_and_criterion_id_sections(toy):
    r = audit(toy, _spec(toy, 0.9))
    assert r["rubric"]["criteria_per_question"] == {"1": 2}
    assert r["rubric"]["criterion_texts"] == {"generic": 2}
    assert r["rubric"]["columns_naming_levels_or_descriptors"] == []
    assert r["rubric"]["rows_with_expected_concepts"] == 0
    ci = r["criterion_ids"]
    assert ci["answers_with_parsable_criterion_marks"] == 12 and ci["criterion_marks_sum_equals_expected_mark"] == 12
    assert ci["referenced_criterion_ids"] == 24
    assert ci["exact_match_to_a_rubric_criterion_id"] == 6  # only Q1's C01 id equals a rubric criterion_id
    assert ci["map_rows_for_eligible_questions"] == 4  # the Q9 row belongs to a question that is not eligible
    assert ci["map_status"] == {"RESOLVED": 2, "UNRESOLVED": 2} and ci["map_resolved_marks_agree"] == {"False": 2}


def test_positional_criterion_marks_are_reported_as_unparsable(toy):
    rows = list(csv.DictReader(open(toy / "02_controlled_answers_eligible.csv", encoding="utf-8", newline="")))
    rows[0]["criterion_marks"] = "5,5"
    _write(toy / "02_controlled_answers_eligible.csv", rows)
    ci = audit(toy, _spec(toy, 0.9))["criterion_ids"]
    assert ci["answers_with_parsable_criterion_marks"] == 11 and ci["referenced_criterion_ids"] == 22


def test_correlation_helper():
    assert _corr([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) == pytest.approx(1.0)
    assert _corr([1.0, 2.0, 3.0], [6.0, 4.0, 2.0]) == pytest.approx(-1.0)
    assert _corr([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None  # constant input
    assert _corr([1.0, 2.0], [1.0, 2.0]) is None  # too few points


# ----------------------------------------------------------------------------------------------- committed v2
@pytest.fixture(scope="module")
def v2():
    if not (V2_DIR / "02_controlled_answers_eligible.csv").exists():
        pytest.skip("v2 dataset not present")
    return audit(V2_DIR)


def test_v2_sizes_match_the_csv(v2):
    with open(V2_DIR / "02_controlled_answers_eligible.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert v2["sizes"]["eligible_answers"] == len(rows)
    assert v2["sizes"]["eligible_questions"] == len({r["question_id"] for r in rows})
    assert v2["sizes"]["answers_by_tier"] == dict(sorted(Counter(r["answer_quality"] for r in rows).items()))


def test_v2_ratio_concentration_agrees_with_the_validation_report_and_spec(v2):
    report = json.loads((V2_DIR / "validation_report.json").read_text(encoding="utf-8"))
    check = next(c for c in report["checks"] if c["name"] == "ratio_concentration")["details"]
    rc = v2["ratio_concentration"]
    assert rc["share_on_top7"] == pytest.approx(check["value"], abs=1e-6)
    assert rc["inner_label_answers"] == check["n_inner"]
    assert rc["threshold"] == check["threshold"] == json.loads(TIER_SPEC_PATH.read_text(encoding="utf-8"))["thresholds"][
        "max_share_on_top7_ratios"]
    assert rc["exceeds_threshold"] is (rc["share_on_top7"] > rc["threshold"])  # the genuine failure is not hidden


def test_v2_audit_is_deterministic_and_does_not_write(v2):
    def digest():
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(V2_DIR.iterdir()) if p.is_file()}

    before = digest()
    again = audit(V2_DIR)
    assert json.dumps(again, sort_keys=True) == json.dumps(v2, sort_keys=True)
    assert digest() == before


def test_v2_every_section_states_its_sample_size_and_method(v2):
    for section in ("tier_marks", "concepts", "rubric", "criterion_ids", "length", "ratio_concentration"):
        assert v2[section]["method"]
    assert v2["tier_marks"]["questions_with_all_six_tiers"] == v2["sizes"]["eligible_questions"]
    assert v2["concepts"]["demonstrated_fraction_vs_mark_ratio"]["n"] > 0
    assert v2["criterion_ids"]["answers"] == v2["sizes"]["eligible_answers"]
    assert v2["caveats"]


def test_cli_prints_the_same_json(capsys):
    assert label_audit.main([str(V2_DIR)]) == 0
    assert json.loads(capsys.readouterr().out) == json.loads(json.dumps(audit(V2_DIR)))


# ---------------------------------------------------------------------------------------------------- report
def test_report_embeds_the_current_audit_output(v2):
    text = REPORT.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    assert blocks, "report has no machine-generated audit block"
    assert json.loads(blocks[-1]) == json.loads(json.dumps(v2))
