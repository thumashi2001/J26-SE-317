
"""Tests for M11.3.1 dataset diversity planning."""

from copy import deepcopy

import pytest

from services.synthetic_diversity_planner import (
    SyntheticDiversityPlanner,
)


def planner():
    return SyntheticDiversityPlanner()


def test_plan_loads():
    plan = planner().load_plan()

    assert plan["schema_version"] == "1.0"


def test_eight_modules_present():
    plan = planner().load_plan()

    assert len(plan["modules"]) == 8


def test_total_papers_is_160():
    report = planner().build_report()

    assert report["target_total_papers"] == 160


def test_each_module_targets_20_papers():
    report = planner().build_report()

    assert all(
        module["target_papers"] == 20
        for module in report["modules"]
    )


def test_unknown_exam_structures_not_assumed():
    report = planner().build_report()

    assert report["all_structures_known"] is False

    assert all(
        module["required_unique_questions"] is None
        for module in report["modules"]
    )


def test_database_fixture_question_requirements():
    report = planner().build_report({
        "database_systems": 12,
    })

    database = next(
        module for module in report["modules"]
        if module["module_key"] == "database_systems"
    )

    assert database["required_unique_questions"] == 240
    assert report["known_total_question_slots"] == 240


def test_duplicate_module_rejected():
    plan = deepcopy(planner().load_plan())

    plan["modules"][1]["module_key"] = (
        plan["modules"][0]["module_key"]
    )

    with pytest.raises(ValueError, match="Duplicate"):
        planner().validate_plan(plan)


def test_wrong_total_rejected():
    plan = deepcopy(planner().load_plan())
    plan["target_total_papers"] = 159

    with pytest.raises(ValueError, match="Target total"):
        planner().validate_plan(plan)


def test_production_enabled_rejected():
    plan = deepcopy(planner().load_plan())
    plan["production_generation_enabled"] = True

    with pytest.raises(ValueError, match="Production"):
        planner().validate_plan(plan)


def test_academic_review_cannot_be_disabled():
    plan = deepcopy(planner().load_plan())
    plan["academic_review_required"] = False

    with pytest.raises(ValueError, match="Academic review"):
        planner().validate_plan(plan)


def test_repeated_questions_cannot_be_enabled():
    plan = deepcopy(planner().load_plan())
    plan["diversity_policy"][
        "allow_repeated_question_text"
    ] = True

    with pytest.raises(ValueError, match="Repeated"):
        planner().validate_plan(plan)


def test_invalid_subquestion_count_rejected():
    with pytest.raises(ValueError, match="Invalid"):
        planner().build_report({
            "database_systems": 0,
        })


def test_all_modules_remain_unverified():
    report = planner().build_report()

    assert all(
        module["ready_for_generation"] is False
        for module in report["modules"]
    )
