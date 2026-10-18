
"""M11.3.3B - Diversity capacity and uniqueness tests."""

from copy import deepcopy

import pytest

from services.synthetic_content_adapter import (
    SyntheticContentAdapter,
)
from services.synthetic_diversity_guard import (
    SyntheticDiversityGuard,
)
from tests.test_synthetic_content_adapter import (
    fixture_structure,
)


def guard():
    return SyntheticDiversityGuard()


def sample_paper():
    return SyntheticContentAdapter().build_paper(
        fixture_structure(),
        seed=42,
    )["paper"]


def four_scenario_paper():
    """Keep one question per scenario for audit testing."""
    paper = deepcopy(sample_paper())
    seen = set()
    selected = []

    for main in paper["questions"]:
        for sub in main["subquestions"]:
            provenance = sub["question"][
                "generation_provenance"
            ]
            key = (
                provenance["topic_index"],
                provenance["scenario_index"],
            )

            if key not in seen:
                seen.add(key)
                selected.append(deepcopy(sub))

    assert len(selected) == 4

    # This is an audit fixture, not a new 100-mark paper.
    paper["questions"] = [
        {
            "number": index,
            "total_marks": sub["marks"],
            "subquestions": [sub],
        }
        for index, sub in enumerate(selected, start=1)
    ]

    paper["main_question_count"] = 4
    paper["total_marks"] = sum(
        sub["marks"] for sub in selected
    )

    return paper


def test_database_systems_capacity():
    report = guard().capacity_report("database_systems")

    assert report["topic_count"] == 2
    assert report["scenario_count"] == 4
    assert report["authored_task_count"] == 4
    assert report["distinct_pair_capacity"] == 8


def test_all_modules_have_capacity():
    keys = [
        "database_systems",
        "case_studies_software_engineering",
        "software_project_management",
        "user_experience_engineering",
        "application_frameworks",
        "distributed_systems",
        "software_architecture",
        "software_engineering_process_quality_management",
    ]

    for key in keys:
        report = guard().capacity_report(key)
        assert report["scenario_count"] == 4
        assert report["distinct_pair_capacity"] == 8
        assert report["production_ready"] is False


def test_eight_question_preflight_fails_scenario_diversity():
    report = guard().preflight("database_systems", 8)

    assert report["enough_distinct_pairs"] is True
    assert report["enough_distinct_scenarios"] is False
    assert report["ready_for_unique_scenario_paper"] is False


def test_four_question_preflight_passes_capacity():
    report = guard().preflight("database_systems", 4)

    assert report["enough_distinct_pairs"] is True
    assert report["enough_distinct_scenarios"] is True


def test_existing_eight_question_paper_detects_reuse():
    report = guard().audit_paper(sample_paper())

    assert report["question_count"] == 8
    assert report["unique_pair_count"] == 8
    assert report["unique_scenario_count"] == 4
    assert report["valid"] is False
    assert "Repeated scenario within paper" in report["errors"]


def test_four_unique_scenarios_pass_audit():
    report = guard().audit_paper(four_scenario_paper())

    assert report["valid"] is True
    assert report["question_count"] == 4
    assert report["unique_scenario_count"] == 4
    assert report["unique_pair_count"] == 4


def test_tampered_question_text_rejected():
    paper = four_scenario_paper()

    paper["questions"][0]["subquestions"][0][
        "question"
    ]["question_text"] = "An unrelated question"

    with pytest.raises(
        ValueError,
        match="does not match bank provenance",
    ):
        guard().audit_paper(paper)


def test_invalid_provenance_rejected():
    paper = four_scenario_paper()

    paper["questions"][0]["subquestions"][0][
        "question"
    ]["generation_provenance"]["scenario_index"] = 99

    with pytest.raises(
        ValueError,
        match="Invalid scenario index",
    ):
        guard().audit_paper(paper)


def test_repeated_pairs_across_batch_detected():
    first = four_scenario_paper()
    second = deepcopy(first)
    second["paper_id"] = "SYN-PAPER-SECOND"

    report = guard().audit_batch([first, second])

    assert report["valid"] is False
    assert any(
        "repeated pair across batch" in error
        for error in report["errors"]
    )


def test_unique_single_paper_batch_passes():
    report = guard().audit_batch([
        four_scenario_paper()
    ])

    assert report["valid"] is True
    assert report["paper_count"] == 1
    assert report["unique_pair_count"] == 4


def test_duplicate_paper_ids_rejected():
    paper = four_scenario_paper()

    report = guard().audit_batch([
        paper,
        deepcopy(paper),
    ])

    assert report["valid"] is False
    assert any(
        "duplicate paper ID" in error
        for error in report["errors"]
    )


def test_invalid_requested_question_count_rejected():
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        guard().preflight("database_systems", 0)


def test_unknown_module_rejected():
    with pytest.raises(
        ValueError,
        match="Unknown content bank module",
    ):
        guard().capacity_report("unknown_module")
