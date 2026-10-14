from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_still_works() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_analysis_endpoint_returns_structured_baseline() -> None:
    response = client.post(
        "/analysis/answer",
        json={
            "question_id": "SE3010-Q01",
            "question_text": "Explain software architecture.",
            "student_answer": (
                "Software architecture describes the high-level structure "
                "of a software system."
            ),
            "reference_answer": (
                "Software architecture defines the high-level structure "
                "of a software system."
            ),
            "expected_concepts": [
                "high-level structure",
                "components",
                "relationships",
            ],
            "answer_type": "short",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["question_id"] == "SE3010-Q01"
    assert body["sentence_count"] == 1
    assert body["token_count"] > 0
    assert body["reference_similarity"] > 0.8
    assert body["analysis_version"] == "baseline-v1"
    assert body["concept_matches"][0]["status"] == "demonstrated"
    assert body["concept_matches"][0]["evidence_sentence_ids"] == [1]


def test_analysis_endpoint_handles_empty_and_missing_optional_inputs() -> None:
    response = client.post(
        "/analysis/answer",
        json={
            "question_id": "SE3010-Q02",
            "question_text": "Explain the concept.",
            "student_answer": "   ",
            "answer_type": "essay",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["normalized_answer"] == ""
    assert body["reference_similarity"] == 0.0
    assert body["concept_matches"] == []
    assert len(body["warnings"]) == 3


def test_analysis_endpoint_rejects_invalid_answer_type() -> None:
    response = client.post(
        "/analysis/answer",
        json={
            "question_id": "SE3010-Q03",
            "question_text": "Explain the concept.",
            "student_answer": "An answer.",
            "answer_type": "multiple-choice",
        },
    )
    assert response.status_code == 422


def test_analysis_endpoint_rejects_blank_expected_concepts() -> None:
    response = client.post(
        "/analysis/answer",
        json={
            "question_id": "SE3010-Q04",
            "question_text": "Explain the concept.",
            "student_answer": "An answer.",
            "expected_concepts": [""],
            "answer_type": "short",
        },
    )
    assert response.status_code == 422
