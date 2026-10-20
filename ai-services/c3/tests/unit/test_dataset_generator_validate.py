"""Validator tests: each known legacy defect class must be caught; a clean tiny release must pass.

The clean release is produced by the real pipeline over a deterministic FakeProvider (pipeline logic only, not data).
"""

from __future__ import annotations

import copy
import json
import random
from pathlib import Path

import pytest
from test_dataset_generator import VOCAB, make_questions, make_tasks

from datasets.generator import DATASET_VERSION, load_tier_spec
from datasets.generator.pipeline import Pipeline
from datasets.generator.writer import write_release
from datasets.validate_dataset import ALL_CODES, main, validate_release

SPEC = load_tier_spec()


@pytest.fixture(scope="module")
def clean_data():
    pipe = Pipeline(make_tasks(), SPEC, 20261021, 2, "fake-gen", "fake-ver")
    data, failures = pipe.run(make_questions(12))
    assert not failures and data is not None
    return data


def write(tmp_path: Path, data) -> Path:
    out = tmp_path / "rel"
    write_release(out, data, SPEC, 1)
    return out


def codes(path: Path) -> set[str]:
    return {v.code for v in validate_release(path)}


def patch_csv(path: Path, name: str, old: str, new: str) -> None:
    f = path / name
    text = f.read_text(encoding="utf-8")
    assert old in text
    f.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_clean_tiny_release_passes(tmp_path, clean_data, capsys):
    out = write(tmp_path, clean_data)
    assert validate_release(out) == []
    assert main([str(out)]) == 0
    assert "All checks passed" in capsys.readouterr().out


def test_missing_files_reported_and_exit_code(tmp_path, clean_data, capsys):
    assert len(ALL_CODES) == len(set(ALL_CODES))
    out = write(tmp_path, clean_data)
    (out / "answers.csv").unlink()
    assert main([str(out)]) == 1
    assert "FILE_MISSING" in capsys.readouterr().out


def test_catches_misordered_tiers(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    qid = d.questions[0]["question_id"]
    for a in d.answers:
        if a["question_id"] == qid and a["tier"] == "PARTIAL":
            a["expected_mark"] = a["max_marks"] * 0.99
            a["normalized_mark"] = 0.99
    assert "TIER_ORDER" in codes(write(tmp_path, d))


def test_catches_nan_and_blank_text_cells(tmp_path, clean_data):
    out = write(tmp_path, clean_data)
    patch_csv(out, "answers.csv", clean_data.answers[0]["student_answer"], "nan")
    patch_csv(out, "questions.csv", clean_data.questions[0]["reference_answer"], "")
    found = codes(out)
    assert "NAN_VALUE" in found and "MANIFEST_HASH" in found
    assert len([v for v in validate_release(out) if v.code == "NAN_VALUE"]) >= 2


def test_catches_rubric_and_mark_defects(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    d.rubrics[0]["scoring_levels"] = d.rubrics[0]["scoring_levels"][1:]  # no explicit mark-0 level
    last_q = d.rubrics[-1]["question_id"]
    next(r for r in d.rubrics if r["question_id"] == last_q)["max_marks"] += 1.0  # criteria no longer sum to marks
    d.answers[3]["criterion_marks"][0]["criterion_id"] = "NOT-IN-RUBRIC"
    d.answers[4]["expected_mark"] = d.answers[4]["expected_mark"] * 0.5 + 0.01
    d.answers[5]["normalized_mark"] = 1.5
    d.answers[1]["expected_mark"] = d.answers[1]["max_marks"] + 1
    found = codes(write(tmp_path, d))
    expected = {
        "RUBRIC_NO_ZERO_LEVEL", "LEVEL_MISMATCH", "RUBRIC_SUM", "CRITERION_UNKNOWN", "CRITERION_SUM",
        "NORMALIZED_MISMATCH", "MARK_RANGE",
    }  # fmt: skip
    assert expected <= found


def test_catches_length_correlated_labels(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    rng = random.Random(1)
    for a in d.answers:
        if a["tier"] in ("EMPTY", "TOO_SHORT"):
            continue
        n = 10 + int(200 * a["normalized_mark"])
        a["student_answer"] = " ".join(rng.choice(VOCAB) for _ in range(n)) + "."
    found = codes(write(tmp_path, d))
    assert "LENGTH_CORR_OVERALL" in found and "LENGTH_CORR_WITHIN" in found


def test_catches_cross_split_duplicates_shared_irrelevant_and_banned_phrases(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    train = next(a for a in d.answers if a["split"] == "train" and a["tier"] == "FULL")
    test = next(a for a in d.answers if a["split"] == "test" and a["tier"] == "FULL")
    test["student_answer"] = train["student_answer"]
    irr = [a for a in d.answers if a["tier"] == "IRRELEVANT" and a["split"] == "train"]
    other = next(a for a in irr if a["question_id"] != irr[0]["question_id"])
    other["student_answer"] = irr[0]["student_answer"]
    victim = next(a for a in irr if a is not irr[0] and a is not other)
    victim["student_answer"] += " The answer does not cover the topic."
    found = codes(write(tmp_path, d))
    assert {"SPLIT_DUP_ANSWER", "IRRELEVANT_SHARED", "BANNED_PHRASE"} <= found


def test_catches_bad_manifest_hash_and_counts(tmp_path, clean_data):
    out = write(tmp_path, clean_data)
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    m["files"]["questions.csv"]["sha256"] = "0" * 64
    m["counts"]["answers"] += 1
    (out / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    found = codes(out)
    assert "MANIFEST_HASH" in found and "MANIFEST_COUNTS" in found


def test_catches_version_drift_placeholders_status_and_annotation_defects(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    d.answers[0]["dataset_version"] = "C3-v5.9.9"
    d.questions[0]["expected_concepts"][0] = "conceptual understanding"
    d.questions[1]["rubric_status"] = "pending"
    full = [a for a in d.answers if a["tier"] == "FULL"]
    k = next(iter(full[0]["evidence_spans"]))
    full[0]["evidence_spans"][k] = [99]
    full[1]["evidence_spans"] = {c: [0] for c in full[1]["concept_status"]}
    full[2]["gold_mindmap"]["edges"].append({"source": "ghost", "target": "n0", "type": "part_of"})
    found = codes(write(tmp_path, d))
    expected = {
        "VERSION_MISMATCH", "PLACEHOLDER_CONCEPT", "STATUS_UNSET", "EVIDENCE_SPAN_RANGE", "EVIDENCE_STALE",
        "MINDMAP_EDGE",
    }  # fmt: skip
    assert DATASET_VERSION != "C3-v5.9.9" and expected <= found


def test_catches_low_sentence_diversity(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    for a in d.answers:
        if a["tier"] not in ("EMPTY", "TOO_SHORT"):
            a["student_answer"] = "This is the same boilerplate sentence. " + a["student_answer"].split(".")[0] + "."
    assert "LOW_SENTENCE_DIVERSITY" in codes(write(tmp_path, d))


def test_catches_missing_edge_tier(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    d.answers = [a for a in d.answers if not (a["split"] == "test" and a["tier"] == "TYPO_FULL")]
    assert "EDGE_TIER_MISSING" in codes(write(tmp_path, d))


def test_catches_module_missing_from_a_split(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    mod = d.questions[0]["module_code"]
    ids = set()
    for q in d.questions:
        if q["module_code"] == mod:
            q["split"] = "train"
            ids.add(q["question_id"])
    for a in d.answers:
        if a["question_id"] in ids:
            a["split"] = "train"
    assert "MODULE_SPLIT_COVERAGE" in codes(write(tmp_path, d))


def test_catches_question_similarity_across_splits(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    tr = next(q for q in d.questions if q["split"] == "train")
    te = next(q for q in d.questions if q["split"] == "test")
    te["question_text"] = tr["question_text"]
    te["expected_concepts"] = list(tr["expected_concepts"])
    assert "SPLIT_QUESTION_SIMILARITY" in codes(write(tmp_path, d))


def test_catches_excluded_without_reason_and_excluded_but_kept(tmp_path, clean_data):
    d = copy.deepcopy(clean_data)
    d.excluded[0]["reason"] = "placeholder"
    d.excluded.append({**d.excluded[0], "question_id": d.questions[0]["parent_question_id"], "reason": "kept anyway"})
    out = write(tmp_path, d)  # the writer itself refuses blank reasons, so blank one after a valid write
    patch_csv(out, "excluded_questions.csv", "placeholder", " ")
    found = codes(out)
    assert "EXCLUDED_NO_REASON" in found and "EXCLUDED_ALSO_KEPT" in found
