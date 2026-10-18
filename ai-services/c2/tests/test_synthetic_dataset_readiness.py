
"""Tests for M11.2.1 synthetic dataset readiness."""

import json

from services.synthetic_dataset_readiness import (
    SyntheticDatasetReadiness,
)


class FakeRegistry:
    def get_all(self):
        return [
            {
                "module_key": "application_frameworks",
                "module_name": "Application Frameworks",
                "module_code": "SE3040",
                "topics": [],
                "exam_structure": None,
            },
            {
                "module_key": "database_systems",
                "module_name": "Database Systems",
                "module_code": "IT3020",
                "topics": [],
                "exam_structure": None,
            },
        ]


class FakeRules:
    rules = {
        "generation_defaults": {
            "target_papers_per_module": None,
            "difficulty_distribution": None,
            "blooms_taxonomy_distribution": None,
            "question_type_distribution": None,
        },
        "generation_policy": {
            "require_human_review_before_release": True,
        },
        "quality_rules": {
            "require_human_review_before_release": True,
        },
    }


class FakeReviews:
    def list_reviews(self):
        return [
            {
                "module_key": "application_frameworks",
                "review_decision": "approved",
            },
            {
                "module_key": "application_frameworks",
                "review_decision": "rejected",
            },
        ]


class FakeTaxonomy:
    def get_module_taxonomy(self, module_key):
        return {
            "module_key": module_key,
            "verification_status": "unverified",
            "topics": [],
        }


def build_service(tmp_path):
    """
    Create an isolated readiness service using test data.

    No real project configuration or lecturer review
    decisions are modified.
    """
    exam_path = tmp_path / "exam_structures.json"

    exam_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "structures": [
                {
                    "module_key": "application_frameworks",
                    "verification_status": "unverified",
                    "structure": None,
                },
                {
                    "module_key": "database_systems",
                    "verification_status": "partially_verified",
                    "structure": {
                        "total_marks": 100,
                        "question_count": 4,
                    },
                },
            ],
        }),
        encoding="utf-8",
    )

    return SyntheticDatasetReadiness(
        registry=FakeRegistry(),
        rules=FakeRules(),
        review_repository=FakeReviews(),
        taxonomy=FakeTaxonomy(),
        exam_structures_path=exam_path,
    )


def test_all_modules_are_reported(tmp_path):
    result = build_service(tmp_path).report()

    assert result["total_modules"] == 2
    assert len(result["modules"]) == 2


def test_approved_candidate_does_not_imply_readiness(tmp_path):
    result = build_service(tmp_path).report()

    module = result["modules"][0]

    assert module["approved_syllabus_candidates"] == 1
    assert module["ready_for_generation"] is False
    assert "verified_module_topics" in (
        module["missing_requirements"]
    )


def test_unconfigured_generation_target_is_reported(tmp_path):
    result = build_service(tmp_path).report()

    for module in result["modules"]:
        assert "target_papers_per_module" in (
            module["missing_requirements"]
        )


def test_saved_decisions_are_counted(tmp_path):
    result = build_service(tmp_path).report()

    assert result["saved_review_decisions"] == 2
    assert result["approved_review_decisions"] == 1
    assert result["rejected_review_decisions"] == 1


def test_human_review_is_required(tmp_path):
    result = build_service(tmp_path).report()

    assert all(
        module["human_review_required_before_release"]
        for module in result["modules"]
    )


def test_partially_verified_structure_is_not_ready(tmp_path):
    result = build_service(tmp_path).report()

    database_module = next(
        module for module in result["modules"]
        if module["module_key"] == "database_systems"
    )

    assert (
        database_module["exam_structure_verification_status"]
        == "partially_verified"
    )

    assert "verified_exam_structure" in (
        database_module["missing_requirements"]
    )

    assert database_module["ready_for_generation"] is False
