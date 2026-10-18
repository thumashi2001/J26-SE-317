
"""M11.2.6.1 real generator integration tests."""

from copy import deepcopy

import pytest

from services.synthetic_generation_adapter import (
    SyntheticGenerationAdapter,
)
from services.synthetic_question_generator import (
    SyntheticQuestionGenerator,
)
from tests.test_synthetic_question_generator import (
    fixture_config,
    FakeRules,
    FakeReadiness,
)
from tests.test_synthetic_paper_builder import (
    fixture_structure,
)


def adapter():
    return SyntheticGenerationAdapter(
        question_generator=SyntheticQuestionGenerator(
            rules=FakeRules(),
            readiness=FakeReadiness(),
        )
    )


def pool_configs():
    five_marks = fixture_config()
    ten_marks = fixture_config()

    # The 5-mark pool has five possible combinations.
    # Four are needed.
    five_marks["topics"] = [
        "SQL Queries",
    ]

    # The 10-mark pool has ten possible combinations.
    # Eight are needed.
    ten_marks["topics"] = [
        "Database Normalization",
        "Transaction Management",
    ]

    return {
        5: five_marks,
        10: ten_marks,
    }


def test_real_generator_builds_valid_paper():
    result = adapter().build_paper(
        fixture_structure(),
        pool_configs(),
    )

    assert result["validation"]["valid"] is True
    assert result["paper"]["total_marks"] == 100
    assert result["generated_question_count"] == 12


def test_correct_marks_distribution():
    result = adapter().build_paper(
        fixture_structure(),
        pool_configs(),
    )

    marks = [
        sub["marks"]
        for main in result["paper"]["questions"]
        for sub in main["subquestions"]
    ]

    assert marks.count(5) == 4
    assert marks.count(10) == 8


def test_real_generator_provenance():
    result = adapter().build_paper(
        fixture_structure(),
        pool_configs(),
    )

    for main in result["paper"]["questions"]:
        for sub in main["subquestions"]:
            question = sub["question"]

            assert (
                question["generation_provenance"][
                    "generator"
                ]
                == "c2_template_generator_v1"
            )

            assert (
                question["generation_provenance"]["mode"]
                == "development_fixture"
            )


def test_reproducible_integration():
    service = adapter()

    first = service.build_paper(
        fixture_structure(),
        pool_configs(),
        seed=99,
    )

    second = service.build_paper(
        fixture_structure(),
        pool_configs(),
        seed=99,
    )

    assert first == second


def test_unique_question_texts():
    result = adapter().build_paper(
        fixture_structure(),
        pool_configs(),
    )

    texts = [
        sub["question"]["question_text"]
        for main in result["paper"]["questions"]
        for sub in main["subquestions"]
    ]

    assert len(texts) == len(set(texts))


def test_production_mode_blocked():
    with pytest.raises(
        ValueError,
        match="development-only",
    ):
        adapter().build_paper(
            fixture_structure(),
            pool_configs(),
            mode="production",
        )


def test_module_mismatch_blocked():
    configs = pool_configs()

    configs[5]["module_key"] = (
        "software_architecture"
    )

    with pytest.raises(
        ValueError,
        match="module does not match",
    ):
        adapter().build_paper(
            fixture_structure(),
            configs,
        )


def test_insufficient_unique_combinations():
    configs = pool_configs()

    # Only five possible combinations;
    # eight questions are required.
    configs[10]["topics"] = ["SQL Queries"]

    with pytest.raises(
        ValueError,
        match="exceeds available unique",
    ):
        adapter().build_paper(
            fixture_structure(),
            configs,
        )


def test_duplicate_text_across_pools_blocked():
    configs = pool_configs()

    # Deliberately make the pools overlap.
    configs[10]["topics"] = [
        "SQL Queries",
        "Database Normalization",
    ]

    with pytest.raises(
        ValueError,
        match="Duplicate question text",
    ):
        adapter().build_paper(
            fixture_structure(),
            configs,
        )


def test_inputs_not_modified():
    structure = fixture_structure()
    configs = pool_configs()

    original_structure = deepcopy(structure)
    original_configs = deepcopy(configs)

    adapter().build_paper(
        structure,
        configs,
    )

    assert structure == original_structure
    assert configs == original_configs
