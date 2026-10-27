"""C2 -> C3 input contract: the documented payload is accepted, bad inputs are rejected, nothing is invented.

C2 has no HTTP endpoint in this repository. The real C2 function is loaded from its file, so these tests fail if its record
shape changes; they do not prove that a C2 service exists.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.assessment import AssessmentResponse
from services.integration.c2_adapter import (
    C2RecordError,
    build_assessment_request,
    question_context_from_c2,
)

ROOT = Path(__file__).resolve().parents[4]
README = ROOT / "backend" / "src" / "integration" / "c2-c3" / "README.md"
C2_REPOSITORY = ROOT / "ai-services" / "c2" / "services" / "question_repository.py"
client = TestClient(app)


def _readme_json_blocks():
    return [json.loads(b) for b in re.findall(r"```json\n(.*?)```", README.read_text(encoding="utf-8"), re.S)]


def _real_c2_records():
    spec = importlib.util.spec_from_file_location("c2_question_repository_under_test", C2_REPOSITORY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paper = {"metadata": {"module_code": "IT3020", "module_name": "Distributed Systems", "calendar_year": 2023},
             "source": {"filename": "paper.pdf", "source_type": "pdf"},
             "questions": [{"question_number": 1, "subquestions": [
                 {"id": "(a)", "text": "Explain the ACID properties.", "context": "A banking database.", "marks": 10,
                  "marks_status": "extracted"},
                 {"id": "(b)", "text": "Define durability.", "marks": None, "marks_status": "missing"}]}]}
    return module.build_question_repository(paper)["questions"]


# ----------------------------------------------------- documented payload

def test_documented_c2_request_is_accepted_and_marked_from_the_rubric():
    request = _readme_json_blocks()[0]
    response = client.post("/c3/assess", json=request)
    assert response.status_code == 200
    body = response.json()
    assert body["total_possible_marks"] == request["max_marks"] == 10.0  # C2 total and rubric total agree
    assert body["total_awarded_marks"] == 5.0  # only atomicity+consistency are in the answer


def test_documented_response_example_matches_the_real_response_shape():
    AssessmentResponse.model_validate(_readme_json_blocks()[1])


@pytest.mark.parametrize("mutate", [
    lambda r: r.pop("rubric"),
    lambda r: r.update(question_text=""),
    lambda r: r.update(expected_concepts=[""]),
    lambda r: r.update(answer_type="mcq"),
    lambda r: r.update(max_marks="ten"),
    lambda r: r.update(max_marks=7.0),     # disagrees with the rubric total of 10
    lambda r: r.update(max_marks=-1),
])
def test_invalid_or_inconsistent_inputs_are_rejected_with_422(mutate):
    request = _readme_json_blocks()[0]
    mutate(request)
    assert client.post("/c3/assess", json=request).status_code == 422


def test_max_marks_is_optional_and_never_used_to_compute_a_mark():
    request = _readme_json_blocks()[0]
    request.pop("max_marks")
    assert client.post("/c3/assess", json=request).json()["total_possible_marks"] == 10.0


# ------------------------------------------------------------------ adapter

def test_adapter_keeps_only_what_c2_really_provides():
    records = _real_c2_records()
    context = question_context_from_c2(records[0])
    assert context["question_id"].endswith("(a)") and context["question_text"] == "Explain the ACID properties."
    assert context["max_marks"] == 10.0 and context["context"] == "A banking database."
    assert context["lecturer_must_supply"] == ["rubric", "reference_answer", "expected_concepts"]
    assert context["metadata"]["module_code"] == "IT3020"


def test_untrusted_c2_marks_are_not_used():
    context = question_context_from_c2(_real_c2_records()[1])
    assert context["max_marks"] is None and "missing" in context["max_marks_note"]


@pytest.mark.parametrize("record", [None, {}, {"question_id": "Q"}, {"question_id": " ", "question_text": "x"},
                                    {"question_id": "Q", "question_text": "   "}])
def test_unusable_c2_records_are_refused(record):
    with pytest.raises(C2RecordError):
        question_context_from_c2(record)


def test_adapter_never_invents_a_rubric_and_checks_marks_against_the_one_supplied():
    documented = _readme_json_blocks()[0]
    context = question_context_from_c2({"question_id": "Q1", "question_text": "Explain ACID.", "marks": 10,
                                        "marks_status": "calculated"})
    with pytest.raises(C2RecordError):
        build_assessment_request(context, "answer", rubric={})
    request = build_assessment_request(context, documented["student_answer"], documented["rubric"],
                                       reference_answer=documented["reference_answer"],
                                       expected_concepts=documented["expected_concepts"])
    assert request.max_marks == 10.0
    context["max_marks"] = 12.0
    with pytest.raises(ValueError):
        build_assessment_request(context, "answer", documented["rubric"])
