
"""M11.3.2A historical evidence tests."""

from copy import deepcopy

import pytest

from services.past_paper_evidence_analyzer import (
    PastPaperEvidenceAnalyzer,
)


def test_eight_source_profiles():
    assert (
        PastPaperEvidenceAnalyzer()
        .report()["module_count"]
        == 8
    )


def test_all_papers_have_100_marks():
    modules = PastPaperEvidenceAnalyzer().load()["modules"]

    assert all(
        m["total_marks"] == 100
        for m in modules
    )


def test_case_studies_seen_unseen_structure():
    modules = PastPaperEvidenceAnalyzer().load()["modules"]

    m = next(
        x for x in modules
        if x["module_key"]
        == "case_studies_software_engineering"
    )

    assert m["main_question_count"] == 3
    assert m["main_question_marks"][:2] == [20, 50]
    assert (
        "seen project reflection"
        in m["observed_question_formats"]
    )


def test_application_frameworks_has_five_questions_and_three_hours():
    modules = PastPaperEvidenceAnalyzer().load()["modules"]

    m = next(
        x for x in modules
        if x["module_key"] == "application_frameworks"
    )

    assert m["main_question_count"] == 5
    assert m["duration_minutes"] == 180


def test_unknown_marks_remain_unknown():
    report = PastPaperEvidenceAnalyzer().report()

    assert any(
        m["unknown_question_mark_allocations"] > 0
        for m in report["modules"]
    )

    assert all(
        not m["ready_for_automatic_generation"]
        for m in report["modules"]
    )


def test_duplicate_module_rejected():
    data = deepcopy(
        PastPaperEvidenceAnalyzer().load()
    )

    data["modules"][1]["module_key"] = (
        data["modules"][0]["module_key"]
    )

    with pytest.raises(ValueError, match="duplicate"):
        PastPaperEvidenceAnalyzer.validate(data)


def test_incorrect_marks_rejected():
    data = deepcopy(
        PastPaperEvidenceAnalyzer().load()
    )

    data["modules"][0]["main_question_marks"] = [
        50, 50, 50
    ]

    with pytest.raises(ValueError, match="structure"):
        PastPaperEvidenceAnalyzer.validate(data)


def test_approval_bypass_rejected():
    data = deepcopy(
        PastPaperEvidenceAnalyzer().load()
    )

    data["academic_verification_status"] = "verified"

    with pytest.raises(
        ValueError,
        match="Academic review"
    ):
        PastPaperEvidenceAnalyzer.validate(data)
