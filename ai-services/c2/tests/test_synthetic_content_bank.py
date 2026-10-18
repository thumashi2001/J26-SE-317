
"""Tests for M11.3.2B evidence-based synthetic content bank."""

from copy import deepcopy

import pytest

from services.synthetic_content_bank import (
    SyntheticContentBank,
)


def service():
    return SyntheticContentBank()


def test_bank_loads():
    assert service().load()["schema_version"] == "1.0"


def test_all_eight_modules_present():
    assert service().coverage_report()["module_count"] == 8


def test_sixteen_topic_specifications():
    assert service().coverage_report()["topic_count"] == 16


def test_thirty_two_scenarios():
    assert service().coverage_report()["scenario_count"] == 32


def test_thirty_two_authored_tasks():
    assert service().coverage_report()["authored_task_count"] == 32


def test_possible_scenario_task_pairs():
    assert (
        service().coverage_report()[
            "possible_scenario_task_pairs"
        ] == 64
    )


def test_all_modules_have_content():
    report = service().coverage_report()

    assert all(
        m["topic_count"] >= 2
        and m["scenario_count"] >= 4
        and m["authored_task_count"] >= 4
        for m in report["modules"]
    )


def test_dataset_not_academically_approved():
    report = service().coverage_report()

    assert report["academic_review_status"] == "pending"
    assert report["ready_for_generation"] is False

    assert all(
        not m["academically_verified"]
        for m in report["modules"]
    )


def test_duplicate_scenario_rejected():
    bank = deepcopy(service().load())

    duplicate = bank["modules"][0]["topics"][0][
        "scenarios"
    ][0]

    bank["modules"][1]["topics"][0][
        "scenarios"
    ][0] = duplicate

    with pytest.raises(ValueError, match="Duplicate scenarios"):
        service().validate(bank)


def test_duplicate_task_rejected():
    bank = deepcopy(service().load())

    duplicate = bank["modules"][0]["topics"][0][
        "tasks"
    ][0]

    bank["modules"][1]["topics"][0][
        "tasks"
    ][0] = duplicate

    with pytest.raises(ValueError, match="Duplicate tasks"):
        service().validate(bank)


def test_unverified_status_cannot_be_changed():
    bank = deepcopy(service().load())
    bank["verification_status"] = "verified"

    with pytest.raises(ValueError, match="unverified"):
        service().validate(bank)


def test_missing_module_rejected():
    bank = deepcopy(service().load())
    bank["modules"].pop()

    with pytest.raises(ValueError, match="planned modules"):
        service().validate(bank)
