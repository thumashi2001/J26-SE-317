from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def rubric(criteria=None):
    return {
        "rubric_id": "R1",
        "title": "Benefits rubric",
        "criteria": criteria or [
            {
                "criterion_id": "C1",
                "description": "Identify security benefits.",
                "max_marks": 2,
                "scoring_levels": [
                    {"level_id": "L0", "label": "None", "mark": 0, "descriptor": "No evidence."},
                    {"level_id": "L2", "label": "Supported", "mark": 2, "descriptor": "Security benefit supported.", "required_concepts": ["security"]},
                ],
            }
        ],
    }


def payload(rubric_value=None):
    return {
        "question_id": "Q1",
        "question_text": "Explain a benefit.",
        "student_answer": "Security improves protection.",
        "reference_answer": "Security is a benefit.",
        "expected_concepts": ["security"],
        "answer_type": "short",
        "rubric": rubric_value or rubric(),
    }


def test_marking_endpoint_success() -> None:
    response = client.post("/marking/evaluate", json=payload())
    assert response.status_code == 200
    body = response.json()
    assert body["question_id"] == "Q1"
    assert body["criteria_results"][0]["selected_level_id"] == "L2"
    assert body["total_awarded_marks"] == 2
    assert body["total_possible_marks"] == 2
    assert body["percentage"] == 100.0
    assert body["marking_version"] == "baseline-v1"


def test_marking_endpoint_rejects_invalid_request() -> None:
    response = client.post("/marking/evaluate", json={"question_id": "Q1"})
    assert response.status_code == 422


def test_marking_endpoint_rejects_invalid_rubric() -> None:
    invalid = rubric([{
        "criterion_id": "C1",
        "description": "Invalid",
        "max_marks": 1,
        "scoring_levels": [
            {"level_id": "L2", "label": "Too high", "mark": 2, "descriptor": "Invalid"}
        ],
    }])
    response = client.post("/marking/evaluate", json=payload(invalid))
    assert response.status_code == 422


def test_marking_endpoint_supports_multiple_criteria() -> None:
    criteria = [
        {
            "criterion_id": "C1",
            "description": "Security",
            "max_marks": 2,
            "scoring_levels": [{"level_id": "L2", "label": "Supported", "mark": 2, "descriptor": "Supported", "required_concepts": ["security"]}],
        },
        {
            "criterion_id": "C2",
            "description": "Protection",
            "max_marks": 1,
            "scoring_levels": [{"level_id": "L1", "label": "Supported", "mark": 1, "descriptor": "Supported", "required_concepts": ["protection"]}],
        },
    ]
    response = client.post("/marking/evaluate", json=payload(rubric(criteria)))
    assert response.status_code == 200
    body = response.json()
    assert body["total_awarded_marks"] == 3
    assert body["total_possible_marks"] == 3


def test_existing_endpoints_still_work() -> None:
    health = client.get("/health")
    analysis = client.post(
        "/analysis/answer",
        json={
            "question_id": "Q1",
            "question_text": "Explain.",
            "student_answer": "A short answer.",
            "answer_type": "short",
        },
    )
    assert health.status_code == 200
    assert analysis.status_code == 200
