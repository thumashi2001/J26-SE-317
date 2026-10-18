
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


def build_service():
    return SyntheticDatasetReadiness(
        registry=FakeRegistry(),
        rules=FakeRules(),
        review_repository=FakeReviews(),
    )


def test_all_modules_are_reported():
    result = build_service().report()

    assert result["total_modules"] == 2
    assert len(result["modules"]) == 2


def test_approved_candidate_does_not_imply_readiness():
    result = build_service().report()

    module = result["modules"][0]

    assert module["approved_syllabus_candidates"] == 1
    assert module["ready_for_generation"] is False
    assert "verified_module_topics" in module[
        "missing_requirements"
    ]


def test_unconfigured_generation_target_is_reported():
    result = build_service().report()

    for module in result["modules"]:
        assert "target_papers_per_module" in module[
            "missing_requirements"
        ]


def test_saved_decisions_are_counted():
    result = build_service().report()

    assert result["saved_review_decisions"] == 2
    assert result["approved_review_decisions"] == 1
    assert result["rejected_review_decisions"] == 1


def test_human_review_is_required():
    result = build_service().report()

    assert all(
        module["human_review_required_before_release"]
        for module in result["modules"]
    )
