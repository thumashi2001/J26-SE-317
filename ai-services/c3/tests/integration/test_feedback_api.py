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


def test_feedback_endpoint_supports_criterion_level_required_concepts() -> None:
    payload = {
        "marking_request": {
            "question_id": "TEST-SE-NORM-001",
            "question_text": "Explain 1NF in database normalization.",
            "student_answer": "1NF requires each attribute to have single atomic values with no repeating groups.",
            "reference_answer": "1NF requires atomic values.",
            "answer_type": "short",
            "rubric": {
                "rubric_id": "RUBRIC-NORM-001",
                "title": "Database Normalization Rubric",
                "criteria": [
                    {
                        "criterion_id": "C1",
                        "description": "Explains 1NF and atomic values.",
                        "max_marks": 2,
                        "required_concepts": ["1NF", "Atomic values"],
                        "scoring_levels": [
                            {
                                "level_id": "L0",
                                "label": "Not Demonstrated",
                                "descriptor": "Does not explain 1NF.",
                                "mark": 0,
                            },
                            {
                                "level_id": "L1",
                                "label": "Partial",
                                "descriptor": "Partially explains 1NF.",
                                "mark": 1,
                            },
                            {
                                "level_id": "L2",
                                "label": "Fully Demonstrated",
                                "descriptor": "Correctly explains 1NF and atomic values.",
                                "mark": 2,
                            },
                        ],
                    }
                ],
            },
        }
    }
    response = client.post("/feedback/generate", json=payload)
    assert response.status_code == 200
    body = response.json()
    criterion = body["criteria_feedback"][0]
    assert criterion["awarded_mark"] == 2.0
    assert criterion["selected_level_id"] == "L2"
    assert len(criterion["evidence_sentence_ids"]) > 0
    assert "1NF" in criterion["demonstrated_concepts"]
    assert "Atomic values" in criterion["demonstrated_concepts"]
    assert len(criterion["strengths"]) > 0


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
    assert client.post(
        "/marking/evaluate",
        json={
            "question_id": "Q1",
            "question_text": "Explain.",
            "student_answer": "An answer.",
            "answer_type": "short",
            "rubric": {
                "rubric_id": "R1",
                "title": "Rubric",
                "criteria": [
                    {
                        "criterion_id": "C1",
                        "description": "Criterion 1",
                        "max_marks": 1,
                        "scoring_levels": [
                            {
                                "level_id": "L0",
                                "label": "None",
                                "mark": 0,
                                "descriptor": "None.",
                            }
                        ],
                    }
                ],
            },
        },
    ).status_code == 200
