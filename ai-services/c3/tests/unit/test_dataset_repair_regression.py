"""
Regression tests for C3 synthetic dataset repair and integrity invariants.
Validates that all historical defects (literal 'nan', flat 10.0 marks, duplicate variants)
remain completely resolved.
"""

import csv
import re
from pathlib import Path

C3_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTH_DIR = C3_ROOT / "datasets" / "synthetic"
BACKUP_DIR = C3_ROOT / "datasets" / "backup_original_synthetic_20261020_2145"
MANIFEST_PATH = C3_ROOT / "datasets" / "dataset_repair_manifest.csv"
INVENTORY_PATH = C3_ROOT / "datasets" / "dataset_inventory.json"


def load_csv(filename: str):
    path = SYNTH_DIR / filename
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def test_backup_directory_preserved():
    """Verify timestamped original backup directory is intact with all 16 files."""
    assert BACKUP_DIR.exists()
    assert BACKUP_DIR.is_dir()
    backup_files = list(BACKUP_DIR.glob("*"))
    assert len(backup_files) >= 16, f"Expected at least 16 backup files, found {len(backup_files)}"


def test_zero_literal_nan_in_student_answers():
    """Verify that no student answer in master or splits contains the literal 'nan' token."""
    for split_file in [
        "02_FINAL_controlled_answers.csv",
        "controlled_answers_train.csv",
        "controlled_answers_validation.csv",
        "controlled_answers_test.csv"
    ]:
        rows = load_csv(split_file)
        for idx, row in enumerate(rows):
            ans = row["student_answer"].strip()
            # Tokenize into words
            tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", ans.lower())
            assert "nan" not in tokens, (
                f"Literal 'nan' found in {split_file} row {idx} ({row.get('answer_id')}): {ans[:80]}"
            )


def test_zero_literal_nan_in_metadata_and_relationships():
    """Verify no literal 'nan' exists in question texts, references, or relationship lists."""
    for qb_file in [
        "01_FINAL_question_bank.csv",
        "question_bank_train.csv",
        "question_bank_validation.csv",
        "question_bank_test.csv"
    ]:
        rows = load_csv(qb_file)
        for idx, row in enumerate(rows):
            q_text = row["question_text"]
            ref_text = row["reference_answer"]
            rel_text = row.get("expected_relationships", "")

            tokens_q = re.findall(r"\b[a-zA-Z0-9_-]+\b", q_text.lower())
            tokens_ref = re.findall(r"\b[a-zA-Z0-9_-]+\b", ref_text.lower())
            tokens_rel = re.findall(r"\b[a-zA-Z0-9_-]+\b", rel_text.lower())

            assert "nan" not in tokens_q, f"Literal 'nan' in question_text of {row.get('question_id')}"
            assert "nan" not in tokens_ref, f"Literal 'nan' in reference_answer of {row.get('question_id')}"
            assert "nan" not in tokens_rel, f"Literal 'nan' in expected_relationships of {row.get('question_id')}"


def test_replacement_questions_differentiated_marks():
    """
    Verify that all replacement questions have differentiated ground-truth marks across tiers
    and that no replacement question has flat 10.0 marks for all variants.
    """
    answers = load_csv("02_FINAL_controlled_answers.csv")
    by_q = {}
    for a in answers:
        qid = a["question_id"]
        if qid not in by_q:
            by_q[qid] = {}
        by_q[qid][a["answer_quality"].upper()] = float(a["expected_mark"])

    replacement_qids = [qid for qid in by_q if qid.startswith("SYN-REPL-")]
    assert len(replacement_qids) >= 63, f"Expected at least 63 replacement questions, found {len(replacement_qids)}"

    for qid in replacement_qids:
        q_marks = by_q[qid]
        # Must have all 6 variants
        assert len(q_marks) == 6, f"Replacement question {qid} missing some quality variants: {q_marks.keys()}"

        full_mark = q_marks["FULL"]
        mostly_mark = q_marks["MOSTLY_CORRECT"]
        partial_mark = q_marks["PARTIAL"]
        missing_mark = q_marks["MISSING_CONCEPT"]
        miscon_mark = q_marks["MISCONCEPTION"]
        irrel_mark = q_marks["IRRELEVANT"]

        # Assert no flat 10.0 marks across all 6
        assert not (full_mark == mostly_mark == partial_mark == missing_mark == miscon_mark == irrel_mark), (
            f"Question {qid} has flat identical marks across all variants: {full_mark}"
        )

        # Assert correct tiered progression
        assert full_mark > mostly_mark, f"{qid}: FULL ({full_mark}) not > MOSTLY_CORRECT ({mostly_mark})"
        assert mostly_mark >= partial_mark, f"{qid}: MOSTLY_CORRECT ({mostly_mark}) not >= PARTIAL ({partial_mark})"
        assert partial_mark >= miscon_mark, f"{qid}: PARTIAL ({partial_mark}) not >= MISCONCEPTION ({miscon_mark})"
        assert miscon_mark > irrel_mark, f"{qid}: MISCONCEPTION ({miscon_mark}) not > IRRELEVANT ({irrel_mark})"
        assert irrel_mark == 0.0, f"{qid}: IRRELEVANT ({irrel_mark}) must be 0.0"


def test_all_irrelevant_controls_have_zero_mark():
    """Verify that 100% of IRRELEVANT variants receive 0.0 credit."""
    answers = load_csv("02_FINAL_controlled_answers.csv")
    irrel = [a for a in answers if a["answer_quality"].upper() == "IRRELEVANT"]
    assert len(irrel) == 167, f"Expected exactly 167 IRRELEVANT variants, found {len(irrel)}"
    for a in irrel:
        mark = float(a["expected_mark"])
        assert mark == 0.0, f"IRRELEVANT answer {a['answer_id']} has non-zero mark: {mark}"


def test_variant_distinguishability_within_each_question():
    """Verify that within any question, all 6 variants have distinct text."""
    answers = load_csv("02_FINAL_controlled_answers.csv")
    by_q = {}
    for a in answers:
        qid = a["question_id"]
        if qid not in by_q:
            by_q[qid] = []
        by_q[qid].append(a["student_answer"].strip().lower())

    for qid, texts in by_q.items():
        assert len(texts) == len(set(texts)), (
            f"Question {qid} has duplicate variants ({len(texts)} total, {len(set(texts))} unique)"
        )


def test_split_disjointness_and_zero_leakage():
    """Verify that train, validation, and test splits are 100% question-ID disjoint."""
    train_qb = load_csv("question_bank_train.csv")
    val_qb = load_csv("question_bank_validation.csv")
    test_qb = load_csv("question_bank_test.csv")

    tr_ids = set(q["question_id"] for q in train_qb)
    val_ids = set(q["question_id"] for q in val_qb)
    te_ids = set(q["question_id"] for q in test_qb)

    assert len(tr_ids) == 117
    assert len(val_ids) == 25
    assert len(te_ids) == 25
    assert len(tr_ids & val_ids) == 0, f"Train/Val overlap: {tr_ids & val_ids}"
    assert len(tr_ids & te_ids) == 0, f"Train/Test overlap: {tr_ids & te_ids}"
    assert len(val_ids & te_ids) == 0, f"Val/Test overlap: {val_ids & te_ids}"


def test_repair_manifest_provenance():
    """Verify that dataset_repair_manifest.csv exists, is non-empty, and has valid structure."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        manifest = list(reader)

    assert len(manifest) >= 426, f"Expected at least 426 repair manifest entries, found {len(manifest)}"
    required_fields = {
        "question_id", "answer_id", "split", "answer_quality",
        "original_expected_mark", "repaired_expected_mark",
        "repair_action", "repair_rationale"
    }
    sample = manifest[0]
    for field in required_fields:
        assert field in sample, f"Manifest missing field: {field}"


def test_dataset_inventory_json_validity():
    """Verify that dataset_inventory.json exists and reports consistent totals."""
    import json
    assert INVENTORY_PATH.exists()
    with open(INVENTORY_PATH, encoding="utf-8") as f:
        inv = json.load(f)

    assert inv["counts"]["total_questions_qb"] == 167
    assert inv["counts"]["total_answers_master"] == 1002
    assert inv["partition_integrity"]["is_question_disjoint"] is True
    assert inv["counts"]["splits"]["total_splits_sum"]["literal_nan_answers"] == 0
