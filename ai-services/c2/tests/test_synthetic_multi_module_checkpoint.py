
"""M11.3.3C.3 - Eight-module checkpoint tests."""

import pytest

from services.synthetic_multi_module_checkpoint import (
    SyntheticMultiModuleCheckpoint,
)


def checkpoint():
    return SyntheticMultiModuleCheckpoint()


def test_all_eight_modules_generate():
    report = checkpoint().run()

    assert report["module_count"] == 8
    assert report["generated_paper_count"] == 8
    assert report["passed_count"] == 8
    assert report["failed_count"] == 0
    assert report["all_passed"] is True


def test_all_papers_have_correct_structure():
    report = checkpoint().run()

    for paper in report["papers"]:
        assert paper["total_marks"] == 100
        assert paper["main_question_count"] == 4
        assert len(paper["questions"]) == 4


def test_all_papers_have_twelve_subquestions():
    report = checkpoint().run()

    for paper in report["papers"]:
        count = sum(
            len(main["subquestions"])
            for main in paper["questions"]
        )
        assert count == 12


def test_all_papers_have_unique_scenarios():
    report = checkpoint().run()

    for item in report["reports"]:
        assert item["unique_scenarios"] == 12
        assert item["diversity_valid"] is True


def test_every_module_has_distinct_paper_id():
    report = checkpoint().run()

    paper_ids = [
        paper["paper_id"]
        for paper in report["papers"]
    ]

    assert len(paper_ids) == len(set(paper_ids))


def test_deterministic_output():
    first = checkpoint().run(seed=42)
    second = checkpoint().run(seed=42)

    assert first == second


def test_different_seed_changes_output():
    first = checkpoint().run(seed=42)
    second = checkpoint().run(seed=43)

    assert [
        paper["paper_id"] for paper in first["papers"]
    ] != [
        paper["paper_id"] for paper in second["papers"]
    ]


def test_no_paper_is_approved():
    report = checkpoint().run()

    assert report["production_ready"] is False
    assert report["academic_review_status"] == "pending"

    for paper in report["papers"]:
        assert paper["release_status"] == "not_approved"


def test_production_mode_blocked():
    with pytest.raises(
        ValueError,
        match="development-only",
    ):
        checkpoint().run(mode="production")


def test_invalid_seed_blocked():
    with pytest.raises(
        ValueError,
        match="seed",
    ):
        checkpoint().run(seed=True)
