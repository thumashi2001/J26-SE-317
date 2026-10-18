
"""M11.3.3C.2 - Diversity-enforced generation tests."""

from copy import deepcopy

import pytest

from services.synthetic_diverse_paper_generator import (
    SyntheticDiversePaperGenerator,
)
from services.synthetic_dataset_exporter import (
    SyntheticDatasetExporter,
)


def structure():
    return {
        "module_key": "database_systems",
        "module_name": "Database Systems",
        "total_marks": 100,
        "questions": [
            {
                "number": number,
                "total_marks": 25,
                "subquestion_marks": [5, 10, 10],
            }
            for number in range(1, 5)
        ],
    }


def generate(seed=42):
    return SyntheticDiversePaperGenerator().generate(
        structure(), seed=seed
    )


def questions(paper):
    return [
        sub["question"]
        for main in paper["questions"]
        for sub in main["subquestions"]
    ]


def test_generates_valid_100_mark_paper():
    result = generate()
    paper = result["paper"]

    assert paper["total_marks"] == 100
    assert paper["main_question_count"] == 4
    assert result["validation"]["valid"] is True


def test_generates_twelve_subquestions():
    result = generate()

    assert result["generated_question_count"] == 12
    assert len(questions(result["paper"])) == 12


def test_all_scenarios_are_unique():
    result = generate()
    diversity = result["diversity"]

    assert diversity["valid"] is True
    assert diversity["unique_scenario_count"] == 12
    assert diversity["duplicate_scenario_count"] == 0


def test_all_pairs_are_unique():
    result = generate()
    diversity = result["diversity"]

    assert diversity["unique_pair_count"] == 12
    assert diversity["duplicate_pair_count"] == 0


def test_expanded_scenarios_are_used():
    result = generate()

    assert result["available_scenario_count"] == 12

    provenance = [
        q["generation_provenance"]
        for q in questions(result["paper"])
    ]

    assert all(
        p["expansion_id"] == "c2_scenario_expansion_v1"
        for p in provenance
    )


def test_deterministic_same_seed():
    assert generate(42)["paper"] == generate(42)["paper"]


def test_marks_structure_preserved():
    paper = generate()["paper"]

    for main in paper["questions"]:
        assert main["total_marks"] == 25
        assert [
            sub["marks"]
            for sub in main["subquestions"]
        ] == [5, 10, 10]


def test_exporter_validation_passes():
    paper = generate()["paper"]

    assert SyntheticDatasetExporter().validate(
        paper
    )["valid"] is True


def test_all_questions_pending_review():
    paper = generate()["paper"]

    assert paper["release_status"] == "not_approved"

    for q in questions(paper):
        assert q["source_type"] == "synthetic"
        assert q["verification_status"] == "unverified"
        assert q["human_review_status"] == "pending"


def test_production_generation_blocked():
    with pytest.raises(
        ValueError, match="development-only"
    ):
        SyntheticDiversePaperGenerator().generate(
            structure(), mode="production"
        )


def test_invalid_seed_rejected():
    with pytest.raises(ValueError, match="seed"):
        SyntheticDiversePaperGenerator().generate(
            structure(), seed=True
        )


def test_insufficient_scenarios_rejected():
    modified = deepcopy(structure())

    # 16 subquestions, still 100 total marks.
    modified["questions"] = [
        {
            "number": number,
            "total_marks": 25,
            "subquestion_marks": [5, 5, 5, 10],
        }
        for number in range(1, 5)
    ]

    with pytest.raises(
        ValueError, match="Insufficient unique scenarios"
    ):
        SyntheticDiversePaperGenerator().generate(modified)


def test_unknown_module_rejected():
    modified = deepcopy(structure())
    modified["module_key"] = "unknown_module"

    with pytest.raises(
        ValueError, match="No expanded content"
    ):
        SyntheticDiversePaperGenerator().generate(modified)
