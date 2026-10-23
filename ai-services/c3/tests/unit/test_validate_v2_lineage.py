"""The validator accepts the v2 lineage only where it is recorded, and still catches real corruption.

Each test copies the committed v2 directory to a temporary folder, damages the copy and validates it. The committed
files are never written.
"""

import csv
import json
import shutil
from pathlib import Path

import pytest

from datasets.repair.common import ARCHIVE_DIR
from datasets.repair.validate_repaired import validate_dir

DATASETS = Path(__file__).resolve().parents[2] / "datasets"
V1_DIR, V2_DIR = DATASETS / "c3_phase3_v5_repaired", DATASETS / "c3_phase3_v5_repaired_v2"

pytestmark = [
    pytest.mark.dataset,
    pytest.mark.skipif(
        not ((ARCHIVE_DIR / "SHA256SUMS.txt").exists() and (V2_DIR / "manifest.json").exists()),
        reason="archived original or v2 directory not present",
    ),
]

LINEAGE_CHECKS = ("schema_required_fields", "preserved_vs_original", "repair_manifest_consistent")


def _status(report):
    return {c["name"]: c["status"] for c in report["checks"]}


def _edit_csv(path, edit):
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    edit(rows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _edit_manifest(directory, edit):
    path = directory / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    edit(manifest)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


@pytest.fixture()
def copy(tmp_path):
    target = tmp_path / "v2"
    shutil.copytree(V2_DIR, target)
    return target


def _v2_row(rows):
    return next(r for r in rows if r["quarantine_reason"].startswith("v2:"))


def test_committed_v2_passes_the_three_lineage_checks(copy):
    status = _status(validate_dir(copy))
    assert {status[c] for c in LINEAGE_CHECKS} == {"pass"}
    assert status["ratio_concentration"] == "fail"  # the genuine failure stays visible


def test_unrecorded_change_to_a_v2_quarantined_answer_is_caught(copy):
    _edit_csv(copy / "quarantine.csv", lambda rows: _v2_row(rows).__setitem__("student_answer", "tampered"))
    assert _status(validate_dir(copy))["preserved_vs_original"] == "fail"


def test_changed_value_that_differs_from_the_ledger_entry_is_caught(copy):
    def edit(rows):
        row = next(r for r in rows if r["quarantine_reason"].startswith("v2:") and "nan" not in r["expected_relationships"]
                   and r["expected_relationships"].startswith("["))
        row["expected_relationships"] = '["an invented relationship"]'

    _edit_csv(copy / "quarantine.csv", edit)
    assert _status(validate_dir(copy))["preserved_vs_original"] == "fail"


def test_version_stamp_on_a_v1_quarantined_row_is_still_rejected(copy):
    def edit(rows):
        next(r for r in rows if not r["quarantine_reason"].startswith("v2:")).__setitem__(
            "dataset_version", "C3-Phase3-v5-REPAIRED-r2")

    _edit_csv(copy / "quarantine.csv", edit)
    assert _status(validate_dir(copy))["preserved_vs_original"] == "fail"


def test_row_with_the_wrong_version_stamp_is_caught(copy):
    _edit_csv(copy / "02_controlled_answers_eligible.csv", lambda rows: rows[0].__setitem__("dataset_version", "other"))
    assert _status(validate_dir(copy))["schema_required_fields"] == "fail"


def test_removing_the_row_stamp_declaration_is_caught(copy):
    _edit_manifest(copy, lambda m: m.pop("row_dataset_version"))
    assert _status(validate_dir(copy))["schema_required_fields"] == "fail"


def test_row_stamp_must_be_the_repair_tools_own_stamp(copy):
    def stamp_all(rows):
        for r in rows:
            r["dataset_version"] = "made-up-version"

    for name in ("01_question_bank.csv", "02_controlled_answers_eligible.csv", "03_rubric_criteria.csv",
                 "repaired_ineligible_controls.csv"):
        _edit_csv(copy / name, stamp_all)
    _edit_manifest(copy, lambda m: m.__setitem__("row_dataset_version", "made-up-version"))
    assert _status(validate_dir(copy))["schema_required_fields"] == "fail"


def test_quarantined_answer_missing_from_the_v2_ledger_is_caught(copy):
    _edit_csv(copy / "v2_repair_ledger.csv", lambda rows: rows.pop())
    assert _status(validate_dir(copy))["repair_manifest_consistent"] == "fail"


def test_v2_ledger_entry_for_an_answer_that_is_still_eligible_is_caught(copy):
    with open(copy / "02_controlled_answers_eligible.csv", encoding="utf-8", newline="") as f:
        row = next(csv.DictReader(f))
    _edit_csv(copy / "v2_repair_ledger.csv", lambda rows: rows.append(
        {"answer_id": row["answer_id"], "question_id": row["question_id"], "split": row["split"], "reason": "x"}))
    assert _status(validate_dir(copy))["repair_manifest_consistent"] == "fail"


def test_a_plain_repair_directory_is_validated_exactly_as_strictly_as_before():
    if not (V1_DIR / "manifest.json").exists():
        pytest.skip("v1 directory not present")
    status = _status(validate_dir(V1_DIR))
    assert {status[c] for c in LINEAGE_CHECKS} == {"pass"}
