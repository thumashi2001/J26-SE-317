"""Offline tests of the C3-Phase3-v5-FINAL repair, its validator and the metrics recomputation.

They run the real repair against the archived original (read-only) into temporary directories.
"""

import json
import shutil

import pandas as pd
import pytest

from datasets.repair.common import (
    ARCHIVE_DIR,
    OriginalIntegrityError,
    OutputExistsError,
    drop_null_elements,
    read_csv,
    truncate_value,
    verify_original,
)
from datasets.repair.evaluate_repaired import build_legacy_rubric, evaluate, lexical_baseline, metrics
from datasets.repair.repair import run_repair
from datasets.repair.validate_repaired import criterion_sum, null_cell_problems, validate_dir
from datasets.repair.validate_repaired import main as validate_main

pytestmark = [
    pytest.mark.dataset,
    pytest.mark.skipif(not (ARCHIVE_DIR / "SHA256SUMS.txt").exists(), reason="archived original not present"),
]


@pytest.fixture(scope="module")
def full(tmp_path_factory):
    out = tmp_path_factory.mktemp("repaired_full")
    result = run_repair(out, allow_nonempty=True)
    return out, result


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    out = tmp_path_factory.mktemp("repaired_sample")
    result = run_repair(out, sample=True, allow_nonempty=True)
    return out, result


def _orig():
    return {
        "q": read_csv(ARCHIVE_DIR / "01_FINAL_question_bank.csv"),
        "a": read_csv(ARCHIVE_DIR / "02_FINAL_controlled_answers.csv"),
        "r": read_csv(ARCHIVE_DIR / "03_FINAL_rubric_criteria.csv"),
    }


def _checks(report):
    return {c["name"]: c for c in report["checks"]}


# ---------------------------------------------------------------- integrity / safety
def test_original_archive_hashes_verify():
    assert len(verify_original(ARCHIVE_DIR)) == 16


def test_tampered_original_aborts(tmp_path):
    copy = tmp_path / "orig"
    shutil.copytree(ARCHIVE_DIR, copy)
    with (copy / "01_FINAL_question_bank.csv").open("ab") as fh:
        fh.write(b"x")
    with pytest.raises(OriginalIntegrityError):
        verify_original(copy)
    with pytest.raises(OriginalIntegrityError):
        run_repair(tmp_path / "out", archive_dir=copy)
    assert not (tmp_path / "out").exists()


def test_refuses_to_overwrite_non_empty_output(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.txt").write_text("x", encoding="utf-8")
    with pytest.raises(OutputExistsError):
        run_repair(out)
    assert (out / "keep.txt").read_text(encoding="utf-8") == "x"


def test_archive_is_not_modified_by_a_run(full):
    assert len(verify_original(ARCHIVE_DIR)) == 16


# ---------------------------------------------------------------- accounting and content
def test_accounting_invariant_on_real_archive(full):
    out, result = full
    ea, qa, ic = (read_csv(out / f) for f in ("02_controlled_answers_eligible.csv", "quarantine.csv",
                                              "repaired_ineligible_controls.csv"))
    assert (len(ea), len(qa), len(ic)) == (576, 355, 71)
    ids = list(ea["answer_id"]) + list(qa["answer_id"]) + list(ic["answer_id"])
    assert len(ids) == len(set(ids)) == 1002
    assert set(ids) == set(_orig()["a"]["answer_id"])
    assert dict(qa["quarantine_reason"].value_counts()) == {"unrecoverable_nan": 252, "unsupported_flat_mark": 103}
    assert result["manifest"]["accounting"]["replacement_block_A"]["quarantined"] == 315


def test_no_nan_in_eligible_tables(full):
    out, _ = full
    for name in ("02_controlled_answers_eligible.csv", "01_question_bank.csv", "03_rubric_criteria.csv"):
        df = read_csv(out / name)
        bad = [(c, v[:40]) for c in df.columns for v in df[c] if null_cell_problems(v)]
        assert bad == [], name


def test_splits_and_order_unchanged_versus_original(full):
    out, _ = full
    o = _orig()
    ea = read_csv(out / "02_controlled_answers_eligible.csv")
    canon = set(o["q"][o["q"]["is_replacement"] != "True"]["question_id"])
    expected = o["a"][o["a"]["question_id"].isin(canon)]
    assert list(ea["answer_id"]) == list(expected["answer_id"])
    assert list(ea["split"]) == list(expected["split"])
    assert list(ea["answer_quality"]) == list(expected["answer_quality"])
    assert dict(ea["split"].value_counts()) == {"train": 420, "validation": 66, "test": 90}
    for split, n_q in (("train", 70), ("validation", 11), ("test", 15)):
        qs = read_csv(out / f"question_bank_{split}.csv")
        assert len(qs) == n_q and set(qs["split"]) == {split}
        answers = read_csv(out / f"controlled_answers_{split}.csv")
        assert list(answers["answer_id"]) == list(expected[expected["split"] == split]["answer_id"])


def test_original_columns_preserved_and_new_columns_appended(full):
    out, _ = full
    o = _orig()
    ea = read_csv(out / "02_controlled_answers_eligible.csv")
    assert list(ea.columns[:31]) == list(o["a"].columns)
    assert {"max_marks", "template_negative_control", "placeholder_concepts_flag", "review_status",
            "source_dataset_version", "repair_status"} <= set(ea.columns[31:])
    q = read_csv(out / "01_question_bank.csv")
    assert list(q.columns[:22]) == list(o["q"].columns)
    assert len(q) == 167 and {"eligibility_status", "eligibility_reason", "scope_review"} <= set(q.columns[22:])
    base = o["a"].set_index("answer_id")
    assert all(base.loc[a, "marks"] == m for a, m in zip(ea["answer_id"], ea["marks"], strict=True))
    assert set(ea["dataset_version"]) == {"C3-Phase3-v5-REPAIRED-r2"} and set(ea["source_dataset_version"]) == {
        "C3-Phase3-v5-FINAL"}


def test_irrelevant_replacement_answers_repaired_to_zero_and_ineligible(full):
    out, _ = full
    ic = read_csv(out / "repaired_ineligible_controls.csv")
    assert len(ic) == 71 and set(ic["answer_quality"]) == {"IRRELEVANT"}
    assert set(ic["expected_mark"]) == {"0.0"} and set(ic["marks"]) == {"0.0"}
    assert set(ic["criterion_marks"]) == {"0,0"}
    assert set(ic["original_expected_mark"]) == {"10.0"} and set(ic["original_criterion_marks"]) == {"5,5"}
    assert set(ic["eligibility_reason"]) == {"question_has_only_one_valid_variant"}
    q = read_csv(out / "01_question_bank.csv")
    ineligible = q[q["eligibility_status"] == "ineligible"]
    assert len(ineligible) == 71 and set(ineligible["question_id"]) == set(ic["question_id"])
    assert set(q[q["eligibility_status"] == "eligible"]["repair_group"]) == {"canonical"}


def test_quarantine_keeps_original_values_and_reason(full):
    out, _ = full
    o = _orig()["a"].set_index("answer_id")
    qa = read_csv(out / "quarantine.csv")
    assert (qa["quarantine_reason"] != "").all()
    for r in qa.to_dict("records"):
        for col in o.columns:
            assert r[col] == o.loc[r["answer_id"], col], (r["answer_id"], col)


def test_rubric_rekey_for_eight_rows(full):
    out, result = full
    o = _orig()
    ru = read_csv(out / "03_rubric_criteria.csv")
    rm = read_csv(out / "repair_manifest.csv")
    assert len(ru) == 230 == len(o["r"])
    moved = rm[rm["issue_category"] == "rubric_id_mismatch"]
    assert len(moved) == 8 and set(moved["field"]) == {"question_id"}
    qb = read_csv(out / "01_question_bank.csv").set_index("question_id")
    original_keys = set(o["r"]["question_id"])
    for r in moved.to_dict("records"):
        assert r["original_value"] in original_keys and r["original_value"] not in qb.index
        new_id = r["repaired_value"]
        assert new_id == f"SYN-REPL-{r['original_value']}"
        assert qb.loc[new_id, "source_replaced_question_id"] == r["original_value"]
        row = ru[ru["criterion_id"] == r["record_id"]].iloc[0]
        assert row["question_id"] == new_id and row["repair_status"] == "repaired"
    assert set(ru["question_id"]) <= set(qb.index)
    assert result["manifest"]["counts"]["repaired"]["rubric_rows_rekeyed"] == 8


def test_flags_review_queue_scope_and_lists(full):
    out, result = full
    ea = read_csv(out / "02_controlled_answers_eligible.csv")
    assert len(read_csv(out / "review_queue.csv")) == 4
    assert set(ea[ea["review_status"] == "needs_review"]["answer_id"]) == set(read_csv(out / "review_queue.csv")["answer_id"])
    assert (ea[ea["template_negative_control"] == "True"]["answer_quality"] == "IRRELEVANT").all()
    assert (ea["template_negative_control"] == "True").sum() == 96
    q = read_csv(out / "01_question_bank.csv")
    assert set(q[q["scope_review"] == "True"]["question_id"]) == {"PP-SE3040-001", "PP-SE3040-002"}
    assert not any('"nan"' in v for v in ea["expected_relationships"])
    assert result["manifest"]["ledger"]["by_category"]["nan_list_element"] == 29
    assert {"repaired", "quarantined", "needs_review", "flagged"} <= set(result["manifest"]["ledger"]["by_status"])


def test_criterion_id_map_never_invents_rubric_ids(full):
    out, _ = full
    cm = read_csv(out / "criterion_id_map.csv")
    ru = read_csv(out / "03_rubric_criteria.csv")
    resolved = cm[cm["mapping_status"] == "RESOLVED"]
    assert set(resolved["rubric_criterion_id"]) <= set(ru["criterion_id"])
    assert (cm[cm["mapping_status"] == "UNRESOLVED"]["rubric_criterion_id"] == "").all()
    assert len(cm) == len(resolved) + (cm["mapping_status"] == "UNRESOLVED").sum()


def test_repair_manifest_has_required_columns_and_truncation(full):
    out, _ = full
    rm = read_csv(out / "repair_manifest.csv")
    assert list(rm.columns) == ["record_id", "record_type", "question_id", "original_file", "split", "issue_category",
                                "field", "original_value", "repaired_value", "reason", "evidence", "repair_status",
                                "validation_result"]
    assert (rm["original_value"].str.len() <= 300 + 100).all()
    assert truncate_value("a" * 301).startswith("a" * 300 + "...[sha256:")
    assert truncate_value("short") == "short"
    assert set(rm[rm["repair_status"] == "quarantined"]["record_id"]) == set(read_csv(out / "quarantine.csv")["answer_id"])


def test_repair_is_deterministic_and_idempotent(full, tmp_path):
    out, _ = full
    other = tmp_path / "again"
    run_repair(other, allow_nonempty=True)
    names = sorted(p.name for p in out.iterdir())
    assert names == sorted(p.name for p in other.iterdir())
    for n in names:
        assert (out / n).read_bytes() == (other / n).read_bytes(), n


# ---------------------------------------------------------------- sample mode
def test_sample_selection_and_accounting(sample):
    out, result = sample
    ids = result["manifest"]["scope_question_ids"]
    assert len(ids) == 6
    q = read_csv(out / "01_question_bank.csv")
    assert dict(q["repair_group"].value_counts()) == {"canonical": 3, "replacement_block_A": 2, "replacement_block_B": 1}
    assert set(q[q["repair_group"] == "canonical"]["split"]) == {"train", "validation", "test"}
    acc = result["manifest"]["accounting"]
    assert sum(g["original_answers"] for g in acc.values()) == 36
    assert len(result["diff"]) == 36


# ---------------------------------------------------------------- validator
def test_validator_report_on_real_output_is_honest(full):
    out, result = full
    checks = _checks(result["validation"])
    rc = checks["ratio_concentration"]
    assert rc["details"]["threshold"] == 0.45
    assert rc["details"]["value"] > 0.45 and rc["status"] == "fail" and rc["hard"]
    assert result["validation"]["overall"] == "FAIL"
    assert result["validation"]["hard_failures"] == ["ratio_concentration"]
    assert checks["counts_reconcile"]["status"] == "pass"
    assert checks["per_question_coverage"]["status"] == "pass"
    assert validate_main([str(out)]) == 1


def test_validator_json_report_written_and_manifest_qa_is_real(full):
    out, _ = full
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["qa"]["status"] == "FAIL" and manifest["qa"]["hard_checks_failed"] == ["ratio_concentration"]
    assert (out / "validation_report.json").exists() and (out / "DATASET_CARD.md").exists()
    assert manifest["files"]["02_controlled_answers_eligible.csv"]


def _copy(sample_dir, tmp_path):
    dst = tmp_path / "defect"
    shutil.copytree(sample_dir, dst)
    return dst


def _edit(path, fn):
    df = read_csv(path)
    fn(df)
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def test_validator_clean_sample_has_only_the_expected_failure(sample):
    out, _ = sample
    report = validate_dir(out)
    assert report["hard_failures"] == ["ratio_concentration"]  # 12 inner labels on <=7 ratios: honest, not hidden


def test_validator_catches_injected_nan(sample, tmp_path):
    d = _copy(sample[0], tmp_path)
    _edit(d / "02_controlled_answers_eligible.csv", lambda df: df.__setitem__("student_answer", ["nan"] + list(df["student_answer"][1:])))
    assert _checks(validate_dir(d))["no_literal_nan_none"]["status"] == "fail"


def test_validator_catches_mark_above_max(sample, tmp_path):
    d = _copy(sample[0], tmp_path)
    _edit(d / "02_controlled_answers_eligible.csv", lambda df: df.__setitem__("expected_mark", ["9999.0"] + list(df["expected_mark"][1:])))
    checks = _checks(validate_dir(d))
    assert checks["score_ranges"]["status"] == "fail"
    assert checks["criterion_marks_sum_equals_expected_mark"]["status"] == "fail"


def test_validator_catches_split_leakage(sample, tmp_path):
    d = _copy(sample[0], tmp_path)

    def flip(df):
        other = {"train": "test", "test": "validation", "validation": "train"}
        df.loc[0, "split"] = other[df.loc[0, "split"]]

    _edit(d / "02_controlled_answers_eligible.csv", flip)
    checks = _checks(validate_dir(d))
    assert checks["answer_split_matches_question"]["status"] == "fail"
    assert checks["split_files_consistent"]["status"] == "fail"


def test_validator_catches_question_in_two_splits(sample, tmp_path):
    d = _copy(sample[0], tmp_path)
    q = read_csv(d / "01_question_bank.csv")
    first = q[q["eligibility_status"] == "eligible"].iloc[0].copy()
    dup = first.copy()
    dup["question_id"] = first["question_id"]  # same id again, other split
    dup["split"] = "train" if first["split"] != "train" else "test"
    pd.concat([q, dup.to_frame().T]).to_csv(d / "01_question_bank.csv", index=False, encoding="utf-8", lineterminator="\n")
    report = validate_dir(d)
    assert _checks(report)["id_uniqueness"]["status"] == "fail"


def test_validator_catches_missing_rubric(sample, tmp_path):
    d = _copy(sample[0], tmp_path)
    ru = read_csv(d / "03_rubric_criteria.csv")
    q = read_csv(d / "01_question_bank.csv")
    victim = q[q["eligibility_status"] == "eligible"]["question_id"].iloc[0]
    ru[ru["question_id"] != victim].to_csv(d / "03_rubric_criteria.csv", index=False, encoding="utf-8", lineterminator="\n")
    assert _checks(validate_dir(d))["rubric_association"]["status"] == "fail"


def test_validator_catches_count_mismatch(sample, tmp_path):
    d = _copy(sample[0], tmp_path)
    qa = read_csv(d / "quarantine.csv")
    qa.iloc[1:].to_csv(d / "quarantine.csv", index=False, encoding="utf-8", lineterminator="\n")
    assert _checks(validate_dir(d))["counts_reconcile"]["status"] == "fail"


def test_validator_catches_unflagged_duplicate_and_bad_label(sample, tmp_path):
    d = _copy(sample[0], tmp_path)

    def dup(df):
        mask = df["question_id"] == df["question_id"].iloc[0]
        idx = list(df[mask].index)
        df.loc[idx[1], "student_answer"] = df.loc[idx[0], "student_answer"]
        df.loc[idx[2], "answer_quality"] = "GREAT"

    _edit(d / "02_controlled_answers_eligible.csv", dup)
    checks = _checks(validate_dir(d))
    assert checks["duplicates_within_question"]["status"] == "fail"
    assert checks["label_values"]["status"] == "fail"
    assert checks["per_question_coverage"]["status"] == "fail"


def test_validator_missing_file_is_a_hard_failure(sample, tmp_path):
    d = _copy(sample[0], tmp_path)
    (d / "review_queue.csv").unlink()
    report = validate_dir(d)
    assert report["hard_failures"] == ["files_present"]


# ---------------------------------------------------------------- helpers and metrics
def test_helper_functions():
    assert drop_null_elements('["a", "nan", "b"]') == ('["a", "b"]', 1)
    assert drop_null_elements('["a", "b"]') == ('["a", "b"]', 0)
    assert drop_null_elements("plain text") == ("plain text", 0)
    assert criterion_sum('[{"criterion_id": "x", "mark": 2.5}, {"criterion_id": "y", "mark": 1.5}]') == 4.0
    assert criterion_sum("5,5") == 10.0 and criterion_sum("0,0") == 0.0
    assert null_cell_problems("nan") and null_cell_problems('["a", "nan"]') and null_cell_problems("see nan here")
    assert not null_cell_problems("The Nandi hills") and not null_cell_problems("None of the above is a plain sentence")


def test_metrics_function_and_lexical_baseline():
    m = metrics([1.0, 2.0, 3.0], [1.0, 2.0, 5.0], [10.0, 10.0, 10.0], ["a", "a", "b"])
    assert m["n"] == 3 and abs(m["mae"] - 2 / 3) < 1e-9 and m["within_2_marks_n"] == 3
    assert m["within_10pct_of_max_n"] == 2 and m["pearson_r"] is not None
    assert metrics([1.0, 1.0], [1.0, 2.0], [5.0, 5.0], ["a", "b"])["pearson_r"] is None
    assert metrics([], [], [], [])["n"] == 0
    assert lexical_baseline("alpha beta", "alpha beta gamma delta", 8.0) == 4.0
    assert lexical_baseline("", "alpha", 8.0) == 0.0
    rubric, source = build_legacy_rubric("Q", 10.0, [], [], allow_fallback=False)
    assert rubric is None and source == "no_rubric_rows"


def test_evaluate_repaired_runs_offline(full):
    out, _ = full
    report = evaluate(out)
    test = report["sets"]["repaired eligible test"]
    assert test["n_total"] == 90 and test["condition_e"]["overall"]["n"] == 90
    assert report["bootstrap"]["seed"] == 20261021
    assert report["not_evaluable"]["repaired eligible test"] == []
    original = [k for k in report["sets"] if k.startswith("original test")]
    assert len(original) == 2 and all(report["sets"][k]["n_total"] == 150 for k in original)
    assert "reported by documentation" in report["table_md"]
