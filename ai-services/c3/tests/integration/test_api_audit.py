"""API-level tests: service endpoints, cross-field rubric failures and empty/whitespace answers."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

# raise_server_exceptions=False so an unhandled server error is observed as HTTP 500 instead of re-raised.
client = TestClient(app, raise_server_exceptions=False)


def base_payload(answer: str = "Security matters.") -> dict:
    return {
        "question_id": "Q-1",
        "question_text": "Explain security.",
        "student_answer": answer,
        "answer_type": "short",
    }


def valid_rubric() -> dict:
    return {
        "rubric_id": "R1",
        "title": "T",
        "criteria": [
            {
                "criterion_id": "C1",
                "description": "Security",
                "max_marks": 2.0,
                "scoring_levels": [
                    {"level_id": "L0", "label": "None", "mark": 0.0, "descriptor": "None"},
                    {
                        "level_id": "L2",
                        "label": "Full",
                        "mark": 2.0,
                        "descriptor": "Security shown",
                        "required_concepts": ["security"],
                    },
                ],
            }
        ],
    }


def cross_field_invalid_rubric() -> dict:
    """Passes Pydantic but fails validate_rubric: level mark (5) exceeds criterion max_marks (2)."""
    rubric = valid_rubric()
    rubric["criteria"][0]["scoring_levels"][1]["mark"] = 5.0
    return rubric


# ---------------------------------------------------------------- service endpoints
def test_health_reports_service_status_and_version() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "component-3-ai-service"
    assert body["status"] == "running"
    assert body["version"] == "0.1.0"


def test_provider_status_has_expected_sections() -> None:
    response = client.get("/api/v1/provider/status")
    assert response.status_code == 200
    body = response.json()
    for key in ("active_llm_provider", "vector_store", "knowledge_graph", "safe_config"):
        assert key in body


# ---------------------------------------------------------------- cross-field rubric failures
def test_marking_endpoint_rejects_cross_field_invalid_rubric_with_422() -> None:
    response = client.post("/marking/evaluate", json={**base_payload(), "rubric": cross_field_invalid_rubric()})
    assert response.status_code == 422
    assert any("exceeds" in message for message in response.json()["detail"])


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-A1: /c3/assess with a rubric whose level mark (5) exceeds criterion max_marks (2) raises an "
    "unhandled RubricValidationError -> HTTP 500 (app/routes/assessment.py:13 has no try/except, unlike "
    "app/routes/marking.py:14-17); expected 422",
)
def test_assess_cross_field_invalid_rubric_returns_422() -> None:
    response = client.post("/c3/assess", json={**base_payload(), "rubric": cross_field_invalid_rubric()})
    assert response.status_code == 422


@pytest.mark.xfail(
    strict=True,
    reason="AUDIT-A1: /feedback/generate with a rubric whose level mark exceeds criterion max_marks raises an "
    "unhandled RubricValidationError -> HTTP 500 (app/routes/feedback.py:12 has no try/except); expected 422",
)
def test_feedback_cross_field_invalid_rubric_returns_422() -> None:
    payload = {"marking_request": {**base_payload(), "rubric": cross_field_invalid_rubric()}}
    response = client.post("/feedback/generate", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------- empty / whitespace answers
@pytest.mark.parametrize("answer", ["", "   \n\t "])
def test_analysis_endpoint_empty_answer(answer) -> None:
    response = client.post("/analysis/answer", json={**base_payload(answer), "expected_concepts": ["security"]})
    assert response.status_code == 200
    body = response.json()
    assert body["sentence_count"] == 0 and body["token_count"] == 0
    assert body["concept_matches"][0]["status"] == "not_demonstrated"
    assert any("empty" in w for w in body["warnings"])


@pytest.mark.parametrize("answer", ["", "   \n\t "])
def test_marking_endpoint_empty_answer_gets_zero(answer) -> None:
    response = client.post("/marking/evaluate", json={**base_payload(answer), "rubric": valid_rubric()})
    assert response.status_code == 200
    body = response.json()
    assert body["total_awarded_marks"] == 0.0
    assert body["criteria_results"][0]["selected_level_id"] == "L0"


@pytest.mark.parametrize("answer", ["", "   \n\t "])
def test_assess_endpoint_empty_answer_gets_zero(answer) -> None:
    response = client.post("/c3/assess", json={**base_payload(answer), "rubric": valid_rubric()})
    assert response.status_code == 200
    body = response.json()
    assert body["total_awarded_marks"] == 0.0
    assert body["percentage"] == 0.0
    assert body["marking"]["total_awarded_marks"] == 0.0
    assert body["mindmap"]["summary"]["demonstrated_count"] == 0


@pytest.mark.parametrize("answer", ["", "   \n\t "])
def test_mindmap_endpoint_empty_answer(answer) -> None:
    payload = {"analysis_request": {**base_payload(answer), "expected_concepts": ["security"]}}
    response = client.post("/mindmap/generate", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["demonstrated_count"] == 0
    assert body["summary"]["missing_count"] == 1


@pytest.mark.parametrize("answer", ["", "   \n\t "])
def test_mindmap_endpoint_empty_answer_without_concepts(answer) -> None:
    response = client.post("/mindmap/generate", json={"analysis_request": base_payload(answer)})
    assert response.status_code == 200
    assert response.json()["summary"]["total_nodes"] >= 1
