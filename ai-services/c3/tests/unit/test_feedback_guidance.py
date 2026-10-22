"""Regression tests for criterion-specific improvement guidance (feedback quality only; marks must not change)."""
from app.schemas.assessment import AssessmentRequest
from services.assessment.orchestrator import assess_answer
from services.feedback.explanation_builder import LEXICAL_NOTE, build_contextual_improvements


def _arch_rubric() -> dict:
    concepts = ["high-level structure", "components", "relationships"]
    return {
        "rubric_id": "R-ARCH",
        "title": "Architecture",
        "criteria": [{
            "criterion_id": "C1",
            "description": "Demonstrate understanding of architectural structure and components.",
            "max_marks": 4,
            "required_concepts": concepts,
            "scoring_levels": [
                {"level_id": "L0", "label": "Unsatisfactory", "mark": 0, "descriptor": "Nothing relevant demonstrated."},
                {"level_id": "L2", "label": "Developing", "mark": 2, "descriptor": "At least one concept demonstrated.",
                 "required_concepts": concepts, "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 1}},
                {"level_id": "L4", "label": "Proficient", "mark": 4, "descriptor": "All three concepts demonstrated.",
                 "required_concepts": concepts, "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 3}},
            ],
        }],
    }


def _biology_rubric() -> dict:
    concepts = ["photosynthesis", "chlorophyll", "glucose"]
    return {
        "rubric_id": "R-BIO",
        "title": "Photosynthesis",
        "criteria": [{
            "criterion_id": "B1",
            "description": "Explain how plants make food.",
            "max_marks": 4,
            "required_concepts": concepts,
            "scoring_levels": [
                {"level_id": "L0", "label": "None", "mark": 0, "descriptor": "Nothing relevant."},
                {"level_id": "L2", "label": "Partial", "mark": 2, "descriptor": "Some ideas.", "required_concepts": concepts,
                 "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 1}},
                {"level_id": "L4", "label": "Full", "mark": 4, "descriptor": "All ideas.", "required_concepts": concepts,
                 "evidence_rule": {"type": "required_concept_count", "minimum_demonstrated": 3}},
            ],
        }],
    }


def _assess(question: str, answer: str, rubric: dict, concepts: list[str]):
    return assess_answer(AssessmentRequest(
        question_id="Q", question_text=question, student_answer=answer, rubric=rubric,
        expected_concepts=concepts, answer_type="short", max_marks=4,
    ))


ARCH_Q = "Explain the concept of software architecture and how its key elements organize a system."
ARCH_CONCEPTS = ["high-level structure", "components", "relationships"]
GENERIC_OLD = "Provide answer evidence that can be traced to the rubric requirements."


def _suggestions(result) -> list[str]:
    return result.feedback.criteria_feedback[0].improvement_suggestions


def test_zero_mark_without_evidence_is_specific_honest_and_not_the_old_generic_sentence():
    r = _assess(ARCH_Q, "I enjoy football and pizza at the weekend.", _arch_rubric(), ARCH_CONCEPTS)
    assert r.total_awarded_marks == 0
    text = " ".join(_suggestions(r))
    assert GENERIC_OLD not in text
    assert "No sentence in your answer matched" in text and "cannot tell what you did or did not understand" in text
    for concept in ARCH_CONCEPTS:
        assert f"'{concept}'" in text
    assert "0/4" in text and "'Developing' (2/4)" in text           # grounded in the real mark and next level
    assert "overall structure" in text and "responsible for" in text and "communicate with or depend" in text
    assert "concrete example" in text
    assert LEXICAL_NOTE in text                                        # lexical matching is not verified understanding
    assert "football" not in text                                      # never quotes the student's answer
    assert "misunderstood" not in text.replace("did or did not understand", "")


def test_partial_answer_names_what_was_found_and_what_is_still_needed_without_contradicting_the_mark():
    r = _assess(ARCH_Q, "The system is made of components.", _arch_rubric(), ARCH_CONCEPTS)
    assert r.total_awarded_marks == 2
    text = " ".join(_suggestions(r))
    assert "matched 'components'" in text and "2/4" in text and "'Proficient' (4/4)" in text
    assert "'high-level structure'" in text and "'relationships'" in text
    assert "No sentence in your answer matched" not in text
    assert "top rubric level" not in text


def test_high_scoring_answer_gets_advanced_guidance_and_no_missing_concept_claims():
    answer = "Software architecture defines the high-level structure of a system. It is made of components and the relationships between them."
    r = _assess(ARCH_Q, answer, _arch_rubric(), ARCH_CONCEPTS)
    assert r.total_awarded_marks == 4
    text = " ".join(_suggestions(r))
    assert "top rubric level (4/4)" in text and "trade-off" in text
    assert "to reach" not in text and "not demonstrated" not in text and "No sentence" not in text


def test_non_architecture_question_gets_no_architecture_advice():
    r = _assess("Explain how plants make their own food.", "Cats are nice animals.", _biology_rubric(), ["photosynthesis", "chlorophyll", "glucose"])
    assert r.total_awarded_marks == 0
    text = " ".join(_suggestions(r))
    for word in ("architecture", "component", "system structure", "user interface", "service layer"):
        assert word not in text.casefold(), word
    for concept in ("photosynthesis", "chlorophyll", "glucose"):
        assert f"'{concept}'" in text
    assert "explain it in your own words" in text and "0/4" in text and "'Partial' (2/4)" in text


def test_marks_are_unchanged_by_the_guidance_and_consistent_across_feedback_and_marking():
    for answer in ("", "x", "The system is made of components.", "Software architecture defines the high-level structure and components and the relationships between them."):
        if not answer:
            continue
        r = _assess(ARCH_Q, answer, _arch_rubric(), ARCH_CONCEPTS)
        assert r.feedback.overall_feedback.total_mark == r.total_awarded_marks == r.marking.total_awarded_marks
        assert r.feedback.criteria_feedback[0].awarded_mark == r.marking.criteria_results[0].awarded_mark


class _Lvl:
    def __init__(self, label, mark, concepts=()):
        self.label, self.mark, self.required_concepts = label, mark, list(concepts)


class _Crit:
    def __init__(self, description, levels, concepts=()):
        self.description, self.scoring_levels, self.required_concepts = description, levels, list(concepts)


class _Res:
    def __init__(self, awarded, maximum, evidence):
        self.awarded_mark, self.max_marks, self.evidence_sentence_ids = awarded, maximum, evidence


def test_incomplete_rubric_metadata_is_stated_not_invented():
    crit = _Crit("Discuss the topic.", [_Lvl("None", 0), _Lvl("Some", 2)])
    out = build_contextual_improvements(criterion=crit, result=_Res(0, 4, []), demonstrated=[], partial=[], missing=[], next_level=[], question_text="Discuss it.")
    assert len(out) == 1 and "lists no expected concepts" in out[0] and "cannot be generated" in out[0]
    top = build_contextual_improvements(criterion=_Crit("Discuss the topic.", [_Lvl("Full", 4)]), result=_Res(4, 4, [1]), demonstrated=[], partial=[], missing=[], next_level=[])
    assert len(top) == 1 and "top rubric level (4/4)" in top[0]


def test_legacy_helper_behaviour_is_unchanged():
    from services.feedback.explanation_builder import build_improvement_suggestions
    assert build_improvement_suggestions([], [], has_evidence=False) == [GENERIC_OLD]
