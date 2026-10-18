
"""M11.2.6.2 scenario enrichment tests."""

from copy import deepcopy

import pytest

from services.synthetic_scenario_enricher import (
    SyntheticScenarioEnricher,
)
from tests.test_synthetic_generation_adapter import (
    adapter,
    pool_configs,
)
from tests.test_synthetic_paper_builder import (
    fixture_structure,
)


def source_paper():
    return adapter().build_paper(
        fixture_structure(),
        pool_configs(),
        seed=42,
    )["paper"]


def all_questions(paper):
    return [
        sub["question"]
        for main in paper["questions"]
        for sub in main["subquestions"]
    ]


def test_enriches_all_questions():
    result = SyntheticScenarioEnricher().enrich(
        source_paper()
    )

    assert result["enriched_question_count"] == 12
    assert result["validation"]["valid"] is True


def test_questions_contain_scenarios():
    paper = SyntheticScenarioEnricher().enrich(
        source_paper()
    )["paper"]

    for question in all_questions(paper):
        assert question["question_text"].startswith(
            "Case study:"
        )
        assert "\nTask:" in question["question_text"]
        assert question["scenario_id"]


def test_scenario_ids_are_unique():
    paper = SyntheticScenarioEnricher().enrich(
        source_paper()
    )["paper"]

    ids = [
        question["scenario_id"]
        for question in all_questions(paper)
    ]

    assert len(ids) == len(set(ids))


def test_preserves_marks_and_review_status():
    original = source_paper()

    enriched = SyntheticScenarioEnricher().enrich(
        original
    )["paper"]

    assert enriched["total_marks"] == 100
    assert enriched["human_review_status"] == "pending"
    assert enriched["release_status"] == "not_approved"

    original_marks = [
        sub["marks"]
        for main in original["questions"]
        for sub in main["subquestions"]
    ]

    enriched_marks = [
        sub["marks"]
        for main in enriched["questions"]
        for sub in main["subquestions"]
    ]

    assert original_marks == enriched_marks


def test_does_not_mutate_original():
    original = source_paper()
    snapshot = deepcopy(original)

    SyntheticScenarioEnricher().enrich(original)

    assert original == snapshot


def test_reproducible_enrichment():
    original = source_paper()
    enricher = SyntheticScenarioEnricher()

    assert enricher.enrich(original) == enricher.enrich(
        original
    )


def test_enriched_paper_has_new_id():
    original = source_paper()

    enriched = SyntheticScenarioEnricher().enrich(
        original
    )["paper"]

    assert enriched["paper_id"] != original["paper_id"]


def test_production_paper_blocked():
    original = source_paper()
    original["generation_mode"] = "production"

    with pytest.raises(
        ValueError,
        match="development",
    ):
        SyntheticScenarioEnricher().enrich(original)


def test_missing_module_scenarios_blocked():
    with pytest.raises(
        ValueError,
        match="No development scenarios",
    ):
        SyntheticScenarioEnricher(
            scenarios={}
        ).enrich(source_paper())


def test_insufficient_scenarios_blocked():
    scenarios = {
        "database_systems": {
            "SQL Queries": [
                "A database contains multiple tables "
                "requiring SQL query processing."
            ]
        }
    }

    with pytest.raises(
        ValueError,
        match="Insufficient unique scenarios|No scenarios configured",
    ):
        SyntheticScenarioEnricher(
            scenarios=scenarios
        ).enrich(source_paper())
