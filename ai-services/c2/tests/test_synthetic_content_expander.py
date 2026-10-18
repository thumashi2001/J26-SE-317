
"""M11.3.3C.1 - Scenario expansion tests."""

import json
from copy import deepcopy

import pytest

from services.synthetic_content_bank import SyntheticContentBank
from services.synthetic_content_expander import (
    SyntheticContentExpander,
)


def expander():
    return SyntheticContentExpander()


def write_modified_expansion(tmp_path, modify):
    data = expander().load_expansion()
    modify(data)

    path = tmp_path / "modified_expansion.json"
    path.write_text(
        json.dumps(data), encoding="utf-8"
    )

    return SyntheticContentExpander(
        expansion_path=path
    )


def test_expanded_bank_has_eight_modules():
    bank = expander().expanded_bank()
    assert len(bank["modules"]) == 8


def test_each_module_has_twelve_scenarios():
    bank = expander().expanded_bank()

    for module in bank["modules"]:
        count = sum(
            len(topic["scenarios"])
            for topic in module["topics"]
        )
        assert count == 12


def test_total_scenario_count():
    report = expander().coverage_report()
    assert report["total_scenarios"] == 96


def test_possible_pair_capacity():
    report = expander().coverage_report()
    assert report["total_possible_pairs"] == 192


def test_all_modules_support_twelve_scenarios():
    report = expander().coverage_report()

    assert all(
        module["supports_12_unique_scenarios"]
        for module in report["modules"]
    )


def test_original_bank_remains_unchanged():
    before = SyntheticContentBank().load()
    snapshot = deepcopy(before)

    expander().expanded_bank()

    after = SyntheticContentBank().load()
    assert before == snapshot
    assert after == snapshot


def test_expansion_does_not_approve_content():
    report = expander().coverage_report()
    bank = expander().expanded_bank()

    assert report["production_ready"] is False
    assert report["academic_review_status"] == "pending"
    assert (
        bank["expansion_provenance"]["verification_status"]
        == "unverified"
    )


def test_duplicate_scenario_rejected(tmp_path):
    original = SyntheticContentBank().load()
    scenario = original["modules"][0]["topics"][0][
        "scenarios"
    ][0]

    modified = write_modified_expansion(
        tmp_path,
        lambda data: data["modules"][0]["topics"][0][
            "scenarios"
        ].append(scenario),
    )

    with pytest.raises(
        ValueError, match="Duplicate scenario"
    ):
        modified.expanded_bank()


def test_unknown_module_rejected(tmp_path):
    modified = write_modified_expansion(
        tmp_path,
        lambda data: data["modules"][0].update(
            module_key="unknown_module"
        ),
    )

    with pytest.raises(
        ValueError, match="Unknown expansion module"
    ):
        modified.expanded_bank()


def test_unknown_topic_rejected(tmp_path):
    modified = write_modified_expansion(
        tmp_path,
        lambda data: data["modules"][0]["topics"][0].update(
            name="Unknown Topic"
        ),
    )

    with pytest.raises(
        ValueError, match="Unknown expansion topic"
    ):
        modified.expanded_bank()


def test_approved_expansion_rejected(tmp_path):
    modified = write_modified_expansion(
        tmp_path,
        lambda data: data.update(
            academic_review_status="approved"
        ),
    )

    with pytest.raises(
        ValueError, match="unverified"
    ):
        modified.expanded_bank()


def test_duplicate_expansion_module_rejected(tmp_path):
    modified = write_modified_expansion(
        tmp_path,
        lambda data: data["modules"].append(
            deepcopy(data["modules"][0])
        ),
    )

    with pytest.raises(
        ValueError, match="Duplicate expansion module"
    ):
        modified.expanded_bank()
