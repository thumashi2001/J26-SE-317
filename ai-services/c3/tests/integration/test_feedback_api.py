from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def feedback_payload() -> dict:
    concepts = ["security", "performance benefits"]
    return {
        "marking_request": {
            "question_id": "Q-F3-01",
            "question_text": "Explain two benefits.",
            "student_answer": "Security matters. Performance improves.",
            "expected_concepts": concepts,
            "answer_type": "short",
            "rubric": {
                "rubric_id": "R-F3-01",
                "title": "Evidence rubric",
                "criteria": [
                    {
                        "criterion_id": "C1",
                        "description": "Explain two benefits.",
                        "max_marks": 4,
                        "scoring_levels": [
                            {
                                "level_id": "L0",
                                "label": "None",
                                "mark": 0,
                                "descriptor": "No evidence.",
                            },
                            {
                                "level_id": "L2",
                                "label": "Partial",
                                "mark": 2,
                                "descriptor": "One concept demonstrated.",
                                "required_concepts": concepts,
                                "evidence_rule": {
                                    "type": "required_concept_count",
                                    "minimum_demonstrated": 1,
                                },
                            },
                            {
                                "level_id": "L4",
                                "label": "Full",
                                "mark": 4,
                                "descriptor": "Two concepts demonstrated.",
                                "required_concepts": concepts,
                                "evidence_rule": {
                                    "type": "required_concept_count",
                                    "minimum_demonstrated": 2,
                                },
                            },
                        ],
                    }
                ],
            },
        }
    }


def test_feedback_endpoint_returns_traceable_feedback() -> None:
    response = client.post("/feedback/generate", json=feedback_payload())
    assert response.status_code == 200
    body = response.json()
    criterion = body["criteria_feedback"][0]
    assert body["overall_feedback"]["total_mark"] == 2
    assert criterion["awarded_mark"] == 2
    assert criterion["evidence_sentence_ids"] == [1]
    assert criterion["demonstrated_concepts"] == ["security"]
    assert criterion["partial_concepts"] == ["performance benefits"]
    assert body["feedback_version"] == "baseline-v1"


def test_feedback_endpoint_rejects_invalid_request() -> None:
    response = client.post("/feedback/generate", json={"marking_request": {}})
    assert response.status_code == 422


def test_existing_endpoints_remain_available() -> None:
    assert client.get("/health").status_code == 200
    assert client.post(
        "/analysis/answer",
        json={
            "question_id": "Q1",
            "question_text": "Explain.",
            "student_answer": "An answer.",
            "answer_type": "short",
        },
    ).status_code == 200
