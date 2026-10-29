"""The live pipeline behind POST /c3/assess: one function, assess_answer(), that runs all four C3 steps in order.

READ THIS FIRST (viva summary)
    Student answer
      -> F1  analyze_answer          word-overlap evidence for each concept           (services/semantic/analyzer.py)
      -> F2  evaluate_criterion      rubric level lookup => the awarded marks
          (services/marking/criterion_evaluator.py)
      -> F3  build_feedback_from_results  explanations + "how to improve" text         (services/feedback/*)
      -> F4  build_mindmap_from_analysis  root + concept nodes                          (services/mindmap/*)
    The marks are deterministic and rule based (F2). No LLM, vector search or Neo4j query is used here. OPTIONALLY (only
    when C3_ML_MODEL_DIR points at a saved checkpoint) a fine-tuned transformer adds an ADVISORY "ai_estimate" next to
    the rubric mark (services/ml/scorer.py); it never changes a mark. A rule-based "review" flag
    (services/assessment/review_rules.py) says when a lecturer should look at the result. The feedback, the mind map
    and the review flag can never change the marks: the marks are fixed in step F2.
"""
from app.schemas.analysis import AnswerAnalysisRequest, AnswerAnalysisResponse
from app.schemas.assessment import AIScoreEstimate, AssessmentRequest, AssessmentResponse
from app.schemas.marking import (
    CriterionMarkingResult,
    MarkingResponse,
)
from services.assessment.review_rules import review_assessment
from services.feedback.generator import build_feedback_from_results
from services.marking.criterion_evaluator import evaluate_criterion
from services.marking.rubric_validator import validate_rubric
from services.mindmap.generator import build_mindmap_from_analysis
from services.ml.scorer import get_scorer
from services.semantic.analyzer import analyze_answer

PIPELINE_VERSION = "integrated-v1"
MARKING_VERSION = "baseline-v1"
# The AI estimate is flagged for review when it differs from the rubric mark by more than this share of the maximum.
AI_REVIEW_THRESHOLD = 0.25


def _analysis_request(request: AssessmentRequest) -> AnswerAnalysisRequest:
    """Collect all expected and rubric-required concepts for unified analysis."""
    # The analyzer reports only on concepts it is told about, so merge the question's concepts with every concept
    # named anywhere in the rubric (criteria and levels), removing duplicates regardless of letter case.
    concepts: list[str] = list(request.expected_concepts or [])
    seen: set[str] = {c.casefold() for c in concepts}
    for criterion in request.rubric.criteria:
        for concept in (criterion.required_concepts or []):
            if concept.casefold() not in seen:
                concepts.append(concept)
                seen.add(concept.casefold())
        for level in criterion.scoring_levels:
            for concept in (level.required_concepts or []):
                if concept.casefold() not in seen:
                    concepts.append(concept)
                    seen.add(concept.casefold())

    dump = request.model_dump(exclude={"rubric", "expected_concepts"})
    dump["expected_concepts"] = concepts if concepts else None
    return AnswerAnalysisRequest.model_validate(dump)


def _overall_explanation(results: list[CriterionMarkingResult]) -> str:
    """One sentence listing each criterion's mark, e.g. 'C1=2/4; C2=3/3'."""
    # Sentence such as "C1=2/4; C2=3/3" explaining how the total was formed.
    details = "; ".join(
        f"{result.criterion_id}={result.awarded_mark:g}/{result.max_marks:g}"
        for result in results
    )
    return (
        "The overall proposed mark is derived by summing the rubric-defined "
        f"criterion marks: {details}. It is a deterministic baseline proposal, "
        "not a claim of factual correctness or final lecturer judgment."
    )


def _ai_estimate(request: AssessmentRequest, awarded: float, possible: float) -> AIScoreEstimate | None:
    """Advisory transformer estimate, or None when the scorer is off/unavailable. Never raises, never alters marks."""
    if not request.reference_answer:
        return None
    scorer = get_scorer()
    ratio = scorer.estimate_ratio(request.reference_answer, request.student_answer)
    if ratio is None:
        return None
    rubric_ratio = min(1.0, max(0.0, awarded / possible))
    diff = ratio - rubric_ratio
    return AIScoreEstimate(estimated_ratio=ratio, estimated_marks=round(ratio * possible, 2), rubric_ratio=rubric_ratio,
                           difference=round(diff, 4), needs_review=abs(diff) > AI_REVIEW_THRESHOLD,
                           model=scorer.model_name)


def _mark(request: AssessmentRequest, analysis: AnswerAnalysisResponse) -> MarkingResponse:
    """Function 2: choose one rubric level per criterion and total the fixed marks (the only place marks are set)."""
    criteria_results = [evaluate_criterion(criterion, analysis) for criterion in request.rubric.criteria]
    total_awarded_marks = sum(result.awarded_mark for result in criteria_results)
    total_possible_marks = sum(result.max_marks for result in criteria_results)
    marking_warnings = list(analysis.warnings)
    marking_warnings.extend(warning for result in criteria_results for warning in result.warnings)
    return MarkingResponse(
        question_id=request.question_id,
        criteria_results=criteria_results,
        total_awarded_marks=total_awarded_marks,
        total_possible_marks=total_possible_marks,
        percentage=round(total_awarded_marks / total_possible_marks * 100, 2),
        overall_explanation=_overall_explanation(criteria_results),
        warnings=marking_warnings,
        marking_version=MARKING_VERSION,
    )


def assess_answer(request: AssessmentRequest) -> AssessmentResponse:
    """Execute the end-to-end C3 assessment pipeline:

    Student Answer
        ↓
    F1 Answer Processing / Semantic Analysis
        ↓
    F2 Rubric-Aware Marking Engine
        ↓
    F3 Explainable Feedback Generation
        ↓
    F4 Concept-Based Mind Map Generator
        ↓
    Integrated Assessment Result
    """
    # Step 0: Validate rubric structure
    # (a contradictory rubric raises RubricValidationError before any marking happens)
    validate_rubric(request.rubric)

    # Step 1: Function 1 — Answer Processing & Semantic Analysis
    # (despite the name, this is lexical word matching; see services/semantic/analyzer.py)
    analysis_req = _analysis_request(request)
    analysis = analyze_answer(analysis_req)

    # Step 2: Function 2 — Rubric-Aware Marking Engine
    # THE MARKS ARE DECIDED HERE: one rubric level is selected per criterion and its fixed mark is awarded.
    marking = _mark(request, analysis)

    # Step 3: Function 3 — Explainable Feedback Generation
    # Text only: built FROM the finished marking and analysis, so it cannot alter a mark.
    feedback = build_feedback_from_results(
        marking=marking,
        analysis=analysis,
        rubric=request.rubric,
        question_text=request.question_text,
    )

    # Step 4: Function 4 — Concept-Based Mind Map Generator
    # One root node (the question) plus one node per concept, coloured by the concept status from step 1.
    expected_concepts = analysis_req.expected_concepts or []
    mindmap = build_mindmap_from_analysis(
        question_id=request.question_id,
        question_text=request.question_text,
        analysis=analysis,
        expected_concepts=expected_concepts,
    )

    # Step 5 (optional): advisory AI score estimate. It is computed from the finished marks and cannot change them.
    ai_estimate = _ai_estimate(request, marking.total_awarded_marks, marking.total_possible_marks)

    # Step 6: Aggregate warnings
    # (merge and de-duplicate the warnings produced by the steps above)
    all_warnings = list(dict.fromkeys(
        marking.warnings + feedback.warnings + mindmap.warnings
    ))
    if ai_estimate is not None and ai_estimate.needs_review:
        all_warnings.append(
            "The AI score estimate differs noticeably from the rubric mark; lecturer review is recommended."
        )

    # The single object returned to Node, which stores it in MongoDB (c3_results.ai_evaluation).
    return AssessmentResponse(
        question_id=request.question_id,
        total_awarded_marks=marking.total_awarded_marks,
        total_possible_marks=marking.total_possible_marks,
        percentage=marking.percentage,
        marking=marking,
        analysis=analysis,
        feedback=feedback,
        mindmap=mindmap,
        warnings=all_warnings,
        pipeline_version=PIPELINE_VERSION,
        ai_estimate=ai_estimate,
        review=review_assessment(analysis, marking, ai_estimate),
    )
