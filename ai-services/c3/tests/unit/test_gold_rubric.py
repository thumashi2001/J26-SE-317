"""The gold-rubric template and checker: compatible with the marking engine, strict about provenance, honest about limits.

The rubrics built here are test fixtures with invented wording; they are not lecturer-approved and say nothing about any real
question. Nothing is written to the repository.
"""

import copy
import csv
import json
from pathlib import Path

import pytest

from app.schemas.marking import Rubric
from datasets.gold import rubric_check
from datasets.gold.rubric_check import check_document, load_question, usable_as_gold
from services.marking.rubric_validator import validate_rubric

GOLD_DIR = Path(__file__).resolve().parents[2] / "datasets" / "gold"
V2_DIR = Path(__file__).resolve().parents[2] / "datasets" / "c3_phase3_v5_repaired_v2"
TEMPLATE = GOLD_DIR / "rubric_template.json"


def _level(level_id, label, mark, descriptor, concepts=(), minimum=None):
    level = {"level_id": level_id, "label": label, "mark": mark, "descriptor": descriptor}
    if concepts:
        level["required_concepts"] = list(concepts)
    if minimum:
        level["evidence_rule"] = {"type": "required_concept_count", "minimum_demonstrated": minimum}
    return level


def _criterion(cid, max_marks, concepts):
    half = max_marks / 2
    return {
        "criterion_id": cid, "description": f"Criterion {cid} of the test rubric", "max_marks": max_marks,
        "required_concepts": list(concepts),
        "scoring_levels": [
            _level("L0", "No credit", 0, f"The answer shows none of the concepts for {cid}."),
            _level("L1", "Partial", half, f"The answer shows some of the concepts for {cid} but not all.", minimum=1),
            _level("L2", "Full", max_marks, f"The answer shows every concept for {cid} correctly.", minimum=len(concepts)),
        ],
    }


def good_doc(status="ai_drafted"):
    prov = {"status": status, "drafted_by": "test-drafter-v1", "drafted_on": "2026-10-01", "validated_by": "", "validated_on": "",
            "validation_notes": ""}
    if status == "lecturer_validated":
        prov.update(validated_by="Test Lecturer", validated_on="2026-10-05")
    return {"format": "c3-gold-rubric/1", "question_id": "Q-TEST-1", "provenance": prov,
            "rubric": {"rubric_id": "R-TEST-1", "title": "Test rubric", "criteria": [
                _criterion("C1", 4, ["alpha", "beta"]), _criterion("C2", 6, ["gamma", "delta", "epsilon"])]}}


def with_(doc, edit):
    doc = copy.deepcopy(doc)
    edit(doc)
    return doc


def problems_with(edit, status="ai_drafted"):
    return check_document(with_(good_doc(status), edit))


# --------------------------------------------------------------------------------------------- template
def test_template_is_compatible_with_the_engine_schema():
    doc = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    validate_rubric(Rubric.model_validate(doc["rubric"]))  # the engine's own schema and cross-field checks accept its shape
    assert doc["format"] == rubric_check.FORMAT
    assert doc["provenance"]["status"] == "template"


def test_unfilled_template_is_always_rejected():
    doc = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    problems = check_document(doc)
    assert any("unfilled template" in p for p in problems)
    assert any("placeholder" in p for p in problems)
    assert not usable_as_gold(doc, problems)


def test_template_with_only_its_status_changed_is_still_rejected():
    doc = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    doc["provenance"].update(status="lecturer_validated", drafted_by="a", drafted_on="2026-10-01",
                             validated_by="b", validated_on="2026-10-02")
    problems = check_document(doc)
    assert problems and not usable_as_gold(doc, problems)  # placeholders and the question id still block it


# --------------------------------------------------------------------------------------------- accepted
def test_complete_ai_drafted_rubric_passes_but_is_not_usable_as_gold():
    doc = good_doc("ai_drafted")
    problems = check_document(doc)
    assert problems == [] and not usable_as_gold(doc, problems)


def test_complete_lecturer_validated_rubric_is_usable_as_gold():
    doc = good_doc("lecturer_validated")
    problems = check_document(doc)
    assert problems == [] and usable_as_gold(doc, problems)


# --------------------------------------------------------------------------------------- provenance rules
@pytest.mark.parametrize("edit, fragment", [
    (lambda d: d.pop("provenance"), "provenance: missing"),
    (lambda d: d["provenance"].update(status="approved"), "is not one of"),
    (lambda d: d["provenance"].update(drafted_by=""), "drafted_by is required"),
    (lambda d: d["provenance"].update(drafted_on="01/10/2026"), "drafted_on must be an ISO date"),
    (lambda d: d["provenance"].update(validated_by="Someone"), "must not carry validated_by"),
])
def test_ai_drafted_provenance_is_checked(edit, fragment):
    assert any(fragment in p for p in problems_with(edit))


@pytest.mark.parametrize("edit, fragment", [
    (lambda d: d["provenance"].update(validated_by=""), "validated_by is required"),
    (lambda d: d["provenance"].update(validated_by="test-drafter-v1"), "different person"),
    (lambda d: d["provenance"].update(validated_by="TEST-DRAFTER-V1"), "different person"),
    (lambda d: d["provenance"].update(validated_on=""), "validated_on must be an ISO date"),
    (lambda d: d["provenance"].update(validated_on="2026-09-01"), "earlier than drafted_on"),
])
def test_lecturer_validation_record_must_be_complete_and_independent(edit, fragment):
    assert any(fragment in p for p in problems_with(edit, "lecturer_validated"))


def test_wrong_format_and_missing_question_are_reported():
    assert any("format must be" in p for p in problems_with(lambda d: d.update(format="other")))
    assert any("question_id is required" in p for p in problems_with(lambda d: d.update(question_id=" ")))
    assert check_document([]) == ["document must be a JSON object"]


# ---------------------------------------------------------------------------- engine rules are reused
def test_engine_schema_errors_are_reported():
    problems = problems_with(lambda d: d["rubric"]["criteria"][0]["scoring_levels"][0].pop("descriptor"))
    assert any(p.startswith("rubric.criteria.0.scoring_levels.0.descriptor") for p in problems)
    assert any(p.startswith("rubric.title") for p in problems_with(lambda d: d["rubric"].pop("title")))


def test_engine_cross_field_errors_are_reported():
    assert any("exceeds criterion" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][2].update(mark=9)))
    assert any("duplicate criterion_id" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][1].update(criterion_id="C1")))
    assert any("minimum_demonstrated exceeds required concepts" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][2]["evidence_rule"].update(minimum_demonstrated=5)))


# ----------------------------------------------------------------------------------- gold-specific rules
def test_criterion_needs_several_levels_a_zero_level_and_a_full_level():
    assert any("at least 3 levels" in p for p in problems_with(lambda d: d["rubric"]["criteria"][0]["scoring_levels"].pop(1)))
    assert any("worth 0 marks" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][0].update(mark=1)))
    assert any("worth the criterion's max_marks" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][2].update(mark=3)))
    assert any("marks must be distinct" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][1].update(mark=4)))


def test_descriptors_must_be_real_and_distinct():
    assert any("shorter than" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][1].update(descriptor="Some credit.")))
    assert any("descriptors must be distinct" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][1].update(
            descriptor=d["rubric"]["criteria"][0]["scoring_levels"][2]["descriptor"])))
    assert any("labels must be distinct" in p for p in problems_with(
        lambda d: d["rubric"]["criteria"][0]["scoring_levels"][1].update(label="Full")))
    for text in ("TODO write this descriptor later", "<FILL IN: what the answer shows>", "placeholder descriptor for level"):
        assert any("placeholder" in p for p in problems_with(
            lambda d, t=text: d["rubric"]["criteria"][0]["scoring_levels"][1].update(descriptor=t)))


def test_positive_levels_need_concepts():
    def edit(d):
        d["rubric"]["criteria"][0]["required_concepts"] = []
        for lv in d["rubric"]["criteria"][0]["scoring_levels"]:
            lv.pop("evidence_rule", None)

    assert any("needs required_concepts" in p for p in problems_with(edit))


# ------------------------------------------------------------------------------ dataset cross-checks
def _bank(tmp_path, rows):
    with open(tmp_path / "01_question_bank.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["question_id", "marks", "eligibility_status"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return tmp_path


def test_marks_must_match_the_question(tmp_path):
    bank = _bank(tmp_path, [{"question_id": "Q-TEST-1", "marks": "10", "eligibility_status": "eligible"},
                            {"question_id": "Q-TEST-2", "marks": "10", "eligibility_status": "quarantined_v2"}])
    q = load_question(bank, "Q-TEST-1")
    assert check_document(good_doc(), q) == []
    assert any("question is worth 12" in p for p in check_document(good_doc(), {**q, "marks": "12"}))
    assert any("does not match the question" in p for p in check_document(good_doc(), {**q, "question_id": "Q-OTHER"}))
    assert load_question(bank, "Q-TEST-2") is None  # a question that is not eligible cannot be used
    assert load_question(bank, "Q-MISSING") is None


def test_check_file_reports_an_unknown_question(tmp_path):
    bank = _bank(tmp_path, [{"question_id": "Q-OTHER", "marks": "10", "eligibility_status": "eligible"}])
    path = tmp_path / "rubric.json"
    path.write_text(json.dumps(good_doc()), encoding="utf-8")
    _, problems = rubric_check.check_file(path, bank)
    assert any("not an eligible question" in p for p in problems)


@pytest.mark.skipif(not (V2_DIR / "01_question_bank.csv").exists(), reason="v2 dataset not present")
def test_a_rubric_for_a_real_v2_question_is_accepted_when_its_marks_match():
    with open(V2_DIR / "01_question_bank.csv", encoding="utf-8", newline="") as f:
        row = next(r for r in csv.DictReader(f) if r["eligibility_status"] == "eligible")
    marks = float(row["marks"])
    doc = with_(good_doc(), lambda d: d.update(question_id=row["question_id"]))
    doc["rubric"]["criteria"] = [_criterion("C1", marks / 2, ["alpha", "beta"]), _criterion("C2", marks / 2, ["gamma", "delta"])]
    assert check_document(doc, load_question(V2_DIR, row["question_id"])) == []
    assert load_question(V2_DIR, row["question_id"])["marks"] == row["marks"]


# --------------------------------------------------------------------------------------------------- CLI
def _run(tmp_path, doc, *extra, capsys):
    path = tmp_path / "rubric.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    code = rubric_check.main([str(path), *extra])
    return code, capsys.readouterr().out


def test_cli_exit_codes_and_wording(tmp_path, capsys):
    code, out = _run(tmp_path, good_doc("ai_drafted"), capsys=capsys)
    assert code == 0 and "usable as gold: no" in out
    code, _ = _run(tmp_path, good_doc("ai_drafted"), "--require-gold", capsys=capsys)
    assert code == 1  # a structurally fine AI draft is still not gold
    code, out = _run(tmp_path, good_doc("lecturer_validated"), "--require-gold", capsys=capsys)
    assert code == 0 and "usable as gold: yes" in out
    code, out = _run(tmp_path, with_(good_doc(), lambda d: d.update(format="x")), capsys=capsys)
    assert code == 1 and "PROBLEM" in out


def test_cli_reports_an_unreadable_file(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert rubric_check.main([str(path)]) == 1
    assert "cannot read" in capsys.readouterr().out


# ------------------------------------------------------------------------------------------- protocol
def test_protocol_covers_the_required_topics_and_states_its_status():
    text = (GOLD_DIR / "GOLD_PROTOCOL.md").read_text(encoding="utf-8")
    for heading in ("Status and limits", "Roles", "Evaluation subset", "Rubrics", "Blind marking", "Scoring",
                    "Agreement", "Adjudication", "Sealing", "Ethics and provenance", "AI-drafted and lecturer-validated",
                    "Open decisions"):
        assert f"\n## {heading}\n" in text, heading
    lowered = text.lower()
    assert "not been operationally validated" in lowered
    assert "no human marks" in lowered
    assert "lecturer_validated" in text and "ai_drafted" in text
