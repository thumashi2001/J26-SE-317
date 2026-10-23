"""The committed v2 dataset's documentation must agree with its own CSVs.

Read-only: every expected number is derived from the CSV files in datasets/c3_phase3_v5_repaired_v2 (nothing is hardcoded
except the 0.45 research-integrity threshold, which is guarded on purpose). Nothing is generated, written or relabelled.
"""

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from datasets.repair.common import (
    ARCHIVE_DIR,
    LABELS,
    REPAIRED_VERSION,
    SPLITS,
    TIER_SPEC_PATH,
    ratio_concentration,
    truncate_value,
)

V2_DIR = Path(__file__).resolve().parents[2] / "datasets" / "c3_phase3_v5_repaired_v2"

pytestmark = [
    pytest.mark.dataset,
    pytest.mark.skipif(not (V2_DIR / "manifest.json").exists(), reason="v2 dataset directory not present"),
]


def _rows(name):
    with open(V2_DIR / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def data():
    answers = _rows("02_controlled_answers_eligible.csv")
    return {
        "answers": answers,
        "bank": _rows("01_question_bank.csv"),
        "quarantine": _rows("quarantine.csv"),
        "controls": _rows("repaired_ineligible_controls.csv"),
        "ledger_v2": _rows("v2_repair_ledger.csv"),
        "questions": {r["question_id"] for r in answers},
    }


@pytest.fixture(scope="module")
def manifest():
    return json.loads((V2_DIR / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report():
    return json.loads((V2_DIR / "validation_report.json").read_text(encoding="utf-8"))


def _check(report, name):
    return next(c for c in report["checks"] if c["name"] == name)


def _questions_by_split(answers):
    out = {s: set() for s in SPLITS}
    for r in answers:
        out[r["split"]].add(r["question_id"])
    return {s: len(q) for s, q in out.items()}


# --------------------------------------------------------------------------------------- manifest vs CSVs
def test_manifest_eligible_totals_match_csv(manifest, data):
    rep = manifest["counts"]["repaired"]
    assert rep["eligible_answers"] == len(data["answers"])
    assert rep["eligible_questions"] == len(data["questions"])


def test_manifest_split_accounting_matches_csv(manifest, data):
    rep = manifest["counts"]["repaired"]
    assert rep["eligible_by_split"] == dict(Counter(r["split"] for r in data["answers"]))
    assert rep["eligible_questions_by_split"] == _questions_by_split(data["answers"])


def test_manifest_label_distribution_matches_csv(manifest, data):
    expected = dict(Counter(r["answer_quality"] for r in data["answers"]))
    assert set(expected) == set(LABELS)
    assert manifest["counts"]["repaired"]["eligible_label_distribution"] == expected


def test_manifest_quarantine_counts_match_csv(manifest, data):
    rep = manifest["counts"]["repaired"]
    assert rep["quarantined_answers"] == len(data["quarantine"])
    by_reason = rep["quarantine_by_reason"]
    assert sum(by_reason.values()) == len(data["quarantine"])
    v2_rows = [r for r in data["quarantine"] if r["quarantine_reason"].startswith("v2:")]
    assert by_reason["v2_question_quarantine"] == len(v2_rows)
    for reason, n in by_reason.items():
        if reason != "v2_question_quarantine":
            assert n == sum(1 for r in data["quarantine"] if r["quarantine_reason"] == reason)


def test_manifest_template_control_count_matches_csv(manifest, data):
    n = sum(1 for r in data["answers"] if r["template_negative_control"] == "True")
    assert manifest["counts"]["repaired"]["template_negative_controls_eligible"] == n


def test_manifest_accounting_covers_every_original_answer(manifest, data):
    acc = manifest["accounting"].values()
    assert sum(g["eligible"] for g in acc) == len(data["answers"])
    assert sum(g["quarantined"] for g in acc) == len(data["quarantine"])
    assert sum(g["repaired_ineligible_controls"] for g in acc) == len(data["controls"])
    total = len(data["answers"]) + len(data["quarantine"]) + len(data["controls"])
    assert sum(g["original_answers"] for g in acc) == manifest["counts"]["original"]["answers"] == total


def test_split_files_and_question_bank_match_eligible_csv(data):
    by_split = Counter(r["split"] for r in data["answers"])
    q_by_split = _questions_by_split(data["answers"])
    for s in SPLITS:
        assert len(_rows(f"controlled_answers_{s}.csv")) == by_split[s]
        assert len(_rows(f"question_bank_{s}.csv")) == q_by_split[s]


def test_question_bank_status_matches_answers_and_v2_derivation(manifest, data):
    status = Counter(r["eligibility_status"] for r in data["bank"])
    assert status["eligible"] == len(data["questions"])
    v2 = manifest["v2_derivation"]
    assert status["quarantined_v2"] == len(v2["quarantined_questions"])
    assert not data["questions"] & set(v2["quarantined_questions"])
    v2_rows = [r for r in data["quarantine"] if r["quarantine_reason"].startswith("v2:")]
    assert len(data["ledger_v2"]) == v2["answers_moved"] == len(v2_rows)


def test_manifest_file_hashes_match_files(manifest):
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((V2_DIR / name).read_bytes()).hexdigest() == digest, name


# --------------------------------------------------------------------------------- validation report vs data
def test_ratio_threshold_is_unchanged_and_report_uses_it(report):
    spec = json.loads(TIER_SPEC_PATH.read_text(encoding="utf-8"))
    assert spec["thresholds"]["max_share_on_top7_ratios"] == 0.45  # integrity guard: never weaken to pass
    assert _check(report, "ratio_concentration")["details"]["threshold"] == 0.45


def test_validation_report_ratio_is_recomputed_from_v2_csv(report, data):
    ratios = [float(r["expected_mark"]) / float(r["max_marks"]) for r in data["answers"]]
    inner = [x for x in ratios if 0.0 < x < 1.0]
    check = _check(report, "ratio_concentration")
    assert check["details"]["n_inner"] == len(inner)
    assert check["details"]["value"] == pytest.approx(ratio_concentration(ratios), abs=1e-6)
    # a failure must stay a failure: the status follows the value, never the other way round
    assert (check["status"] == "fail") == (check["details"]["value"] > check["details"]["threshold"])


def test_validation_report_counts_match_csv(report, data):
    parts = _check(report, "counts_reconcile")["details"]["parts"]
    assert parts == {
        "eligible": len(data["answers"]),
        "quarantine": len(data["quarantine"]),
        "repaired_ineligible_controls": len(data["controls"]),
    }
    assert "eligible questions differ" not in " ".join(_check(report, "counts_reconcile")["details"]["problems"])


def test_manifest_qa_status_follows_validation_report(manifest, report):
    assert manifest["qa"]["status"] == report["overall"]
    assert manifest["qa"]["hard_checks_failed"] == report["hard_failures"]


# ------------------------------------------------------------------------------------------- card vs data
def _card_v2_rows():
    text = (V2_DIR / "DATASET_CARD.md").read_text(encoding="utf-8")
    m = re.search(r"^## v2 build \(authoritative.*?^## ", text + "\n## ", re.S | re.M)
    assert m, "DATASET_CARD.md has no '## v2 build (authoritative ...)' section"
    rows = {}
    for line in m.group(0).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 2 and not set(cells[0]) <= {"-", " "}:
            rows[cells[0]] = cells[1:]
    return rows


def test_card_v2_section_matches_csv(data):
    rows = _card_v2_rows()
    assert rows["eligible questions"] == [str(len(data["questions"]))]
    assert rows["eligible answers"] == [str(len(data["answers"]))]
    assert rows["quarantined answers"] == [str(len(data["quarantine"]))]
    assert rows["repaired ineligible controls"] == [str(len(data["controls"]))]
    by_split, q_by_split = Counter(r["split"] for r in data["answers"]), _questions_by_split(data["answers"])
    for s in SPLITS:
        assert rows[s] == [str(q_by_split[s]), str(by_split[s])]
    tiers = Counter(r["answer_quality"] for r in data["answers"])
    for label in LABELS:
        assert rows[label] == [str(tiers[label])]


def test_card_reports_the_ratio_failure_honestly(report):
    row = _card_v2_rows()["ratio concentration"]
    check = _check(report, "ratio_concentration")
    assert row[0] == f"{check['details']['value']:.4f}"
    assert row[1] == str(check["details"]["threshold"])
    assert row[2].upper() == check["status"].upper()


# ------------------------------------------------------------------- lineage: archive -> v1 -> v2 -> quarantine
ARCHIVE = Path(ARCHIVE_DIR)
V1_DIR = V2_DIR.parent / "c3_phase3_v5_repaired"
SNAPSHOT = Path(__file__).resolve().parents[4] / "reports" / "c3_remediation" / "dataset_v2_hash_manifest.json"
needs_archive = pytest.mark.skipif(not (ARCHIVE / "02_FINAL_controlled_answers.csv").exists(), reason="archive not present")


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_rows_carry_the_declared_row_stamp(manifest):
    assert manifest["row_dataset_version"] == REPAIRED_VERSION
    for name in ("01_question_bank.csv", "02_controlled_answers_eligible.csv", "03_rubric_criteria.csv",
                 "repaired_ineligible_controls.csv"):
        assert {r["dataset_version"] for r in _rows(name)} == {manifest["row_dataset_version"]}, name


@needs_archive
def test_every_archive_difference_of_a_v2_quarantined_answer_is_in_the_v1_ledger(data):
    archive = {r["answer_id"]: r for r in _read(ARCHIVE / "02_FINAL_controlled_answers.csv")}
    ledger = _rows("repair_manifest.csv")
    stamps = {(r["original_value"], r["repaired_value"]) for r in ledger
              if r["record_type"] == "file" and r["field"] == "dataset_version"}
    logged = {(r["record_id"], r["field"], r["original_value"], r["repaired_value"])
              for r in ledger if r["record_type"] == "answer"}
    by_id = {r["answer_id"]: r for r in data["quarantine"]}
    for led in data["ledger_v2"]:
        row, orig = by_id[led["answer_id"]], archive[led["answer_id"]]
        for col, old in orig.items():
            if col == "answer_id" or row[col] == old:
                continue
            ok = (old, row[col]) in stamps if col == "dataset_version" else (
                (led["answer_id"], col, truncate_value(old), truncate_value(row[col])) in logged)
            assert ok, f"{led['answer_id']}.{col} differs from the archive without a ledger entry"


@pytest.mark.skipif(not (V1_DIR / "02_controlled_answers_eligible.csv").exists(), reason="v1 directory not present")
def test_v2_quarantined_rows_are_copies_of_their_v1_eligible_rows(data):
    v1 = {r["answer_id"]: r for r in _read(V1_DIR / "02_controlled_answers_eligible.csv")}
    by_id = {r["answer_id"]: r for r in data["quarantine"]}
    for led in data["ledger_v2"]:
        row, source = by_id[led["answer_id"]], v1[led["answer_id"]]
        shared = [c for c in row if c in source and c != "quarantine_reason"]  # quarantine.csv carries fewer columns
        assert "answer_quality" in shared and "student_answer" in shared
        assert {c: row[c] for c in shared} == {c: source[c] for c in shared}


def test_v2_ledger_extends_the_v1_ledger_without_duplicates(data):
    v2_ids = [r["answer_id"] for r in data["ledger_v2"]]
    v1_quarantined = {r["record_id"] for r in _rows("repair_manifest.csv") if r["repair_status"] == "quarantined"}
    assert len(v2_ids) == len(set(v2_ids))
    assert not set(v2_ids) & v1_quarantined
    assert not set(v2_ids) & {r["answer_id"] for r in data["answers"]}
    assert {r["answer_id"] for r in data["quarantine"]} == v1_quarantined | set(v2_ids)


def test_snapshot_hash_manifest_equals_the_canonical_manifest(manifest):
    if not SNAPSHOT.exists():
        pytest.skip("hash-manifest snapshot not present")
    assert json.loads(SNAPSHOT.read_text(encoding="utf-8")) == manifest


def test_only_the_genuine_ratio_failure_remains(report):
    assert set(report["hard_failures"]) - {"ratio_concentration"} == set()
