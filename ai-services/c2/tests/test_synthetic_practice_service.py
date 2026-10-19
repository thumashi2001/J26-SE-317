"""Tests for SyntheticPracticeService and /mock-exams/synthetic API."""

import os
import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.synthetic_practice_service import (
    MODULE_NAMES,
    VALID_MODULE_KEYS,
    SyntheticPracticeService,
)

client = TestClient(app)
INTERNAL_TOKEN = os.environ.get("C2_INTERNAL_TOKEN", "local-c2-dev-token-change-before-deployment")


@pytest.fixture
def service():
    return SyntheticPracticeService()


def test_valid_module_keys_count():
    assert len(VALID_MODULE_KEYS) == 8


def test_load_all_eight_modules(service):
    for module_key in VALID_MODULE_KEYS:
        questions = service.load_module_questions(module_key)
        assert isinstance(questions, list)
        assert len(questions) == 100, f"Module {module_key} should have 100 M16 questions"


def test_generate_paper_all_eight_modules(service):
    for module_key in VALID_MODULE_KEYS:
        paper = service.generate_practice_paper(module_key, question_count=5, seed=42)
        assert paper["module_key"] == module_key
        assert paper["question_count"] == 5
        assert len(paper["questions"]) == 5
        assert paper["source_type"] == "synthetic"
        assert paper["practice_mode"] == "synthetic_experimental"
        assert paper["verification_status"] == "unverified"
        assert paper["total_marks"] is None
        assert paper["has_unassessed_marks"] is True
        for q in paper["questions"]:
            assert q["marks"] is None
            assert q["marks_status"] == "unassessed"
            assert q["source_type"] == "synthetic"
            assert q["verification_status"] == "unverified"
            assert q["difficulty"] == "unassessed"


def test_determinism_with_seed(service):
    paper1 = service.generate_practice_paper("software_architecture", question_count=7, seed=99)
    paper2 = service.generate_practice_paper("software_architecture", question_count=7, seed=99)
    paper3 = service.generate_practice_paper("software_architecture", question_count=7, seed=100)

    q_ids_1 = [q["question_id"] for q in paper1["questions"]]
    q_ids_2 = [q["question_id"] for q in paper2["questions"]]
    q_ids_3 = [q["question_id"] for q in paper3["questions"]]

    assert q_ids_1 == q_ids_2
    assert q_ids_1 != q_ids_3


def test_reject_invalid_module(service):
    with pytest.raises(ValueError, match="Unsupported module key"):
        service.generate_practice_paper("invalid_module")


def test_reject_invalid_question_count(service):
    with pytest.raises(ValueError, match="question_count"):
        service.generate_practice_paper("database_systems", question_count=0)
    with pytest.raises(ValueError, match="question_count"):
        service.generate_practice_paper("database_systems", question_count=25)


def test_api_synthetic_practice_endpoint():
    response = client.post(
        "/mock-exams/synthetic",
        headers={"X-C2-Internal-Token": INTERNAL_TOKEN},
        json={"module_key": "software_architecture", "question_count": 5, "seed": 42},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["module_key"] == "software_architecture"
    assert data["question_count"] == 5
    assert data["source_type"] == "synthetic"
    assert data["verification_status"] == "unverified"
    assert data["total_marks"] is None
    assert data["has_unassessed_marks"] is True
    assert len(data["questions"]) == 5


def test_api_synthetic_practice_rejects_unauthorized():
    response = client.post(
        "/mock-exams/synthetic",
        json={"module_key": "software_architecture", "question_count": 5},
    )
    assert response.status_code == 401


def test_api_synthetic_practice_rejects_invalid_module():
    response = client.post(
        "/mock-exams/synthetic",
        headers={"X-C2-Internal-Token": INTERNAL_TOKEN},
        json={"module_key": "nonexistent_module", "question_count": 5},
    )
    assert response.status_code == 400
