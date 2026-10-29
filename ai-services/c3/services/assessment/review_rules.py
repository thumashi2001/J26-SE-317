"""Rule-based "needs manual review" flag for one finished assessment (FR-C3-079, FR-C3-093).

SIMPLE ENGLISH
    The lexical marking engine has no probability or confidence score, so "low confidence" cannot be measured. Instead
    this module checks a short list of explicit, named situations in which a lecturer should look at the result before
    trusting it, and reports which ones apply. Which rules are active is configurable with C3_REVIEW_RULES (a comma
    separated list of rule names; unset = all rules; an unknown name is rejected). The flag never changes a mark.
"""
import os

from app.schemas.analysis import AnswerAnalysisResponse
from app.schemas.assessment import AIScoreEstimate, ReviewSummary
from app.schemas.marking import MarkingResponse

REVIEW_RULES_VERSION = "review-rules-v1"
VERY_SHORT_TOKENS = 3  # same cut-off as the analyzer's "very short" warning


def _contradiction(analysis, marking, ai):
    """The answer negates, or both affirms and negates, an expected concept."""
    flagged = [m.concept for m in analysis.concept_matches if m.contradicted or m.conflicting]
    return f"possible contradiction about: {', '.join(flagged)}" if flagged else None


def _off_topic(analysis, marking, ai):
    """The answer shares almost no vocabulary with the question's topic."""
    if analysis.relevance is not None and analysis.relevance.status == "off_topic":
        return "answer may be off-topic (very little shared vocabulary with the question)"
    return None


def _no_evidence(analysis, marking, ai):
    """A real-length answer matched none of the expected concepts (a paraphrase or an off-topic text)."""
    if analysis.token_count >= VERY_SHORT_TOKENS and analysis.concept_matches and all(
        m.status == "not_demonstrated" for m in analysis.concept_matches
    ):
        return "no expected concept was found in the answer"
    return None


def _zero_marks(analysis, marking, ai):
    """Every criterion fell to a zero-mark level; check it was not a wording mismatch."""
    if marking.criteria_results and all(r.awarded_mark == 0 for r in marking.criteria_results):
        return "every criterion scored zero"
    return None


def _very_short(analysis, marking, ai):
    """Too little text to judge."""
    if analysis.token_count < VERY_SHORT_TOKENS:
        return "the answer is very short or empty"
    return None


def _ai_disagrees(analysis, marking, ai):
    """The optional advisory AI estimate differs noticeably from the rubric mark."""
    if ai is not None and ai.needs_review:
        return "the AI estimate differs noticeably from the rubric mark"
    return None


RULES = {
    "contradiction": _contradiction,
    "off_topic": _off_topic,
    "no_evidence": _no_evidence,
    "zero_marks": _zero_marks,
    "very_short": _very_short,
    "ai_disagrees": _ai_disagrees,
}


def active_rules() -> list[str]:
    """Names of the rules in force: C3_REVIEW_RULES, or every rule when unset. An unknown name raises ValueError."""
    raw = os.getenv("C3_REVIEW_RULES")
    if raw is None or not raw.strip():
        return list(RULES)
    names = [n.strip() for n in raw.split(",") if n.strip()]
    unknown = [n for n in names if n not in RULES]
    if unknown:
        raise ValueError(f"unknown C3_REVIEW_RULES name(s): {', '.join(unknown)} (valid: {', '.join(RULES)})")
    return names


def review_assessment(
    analysis: AnswerAnalysisResponse, marking: MarkingResponse, ai_estimate: AIScoreEstimate | None
) -> ReviewSummary:
    """Run the active rules; the result lists every reason that fired (empty = no rule asks for a review)."""
    rules = active_rules()
    reasons = []
    for name in rules:
        reason = RULES[name](analysis, marking, ai_estimate)
        if reason:
            reasons.append(f"{name}: {reason}")
    return ReviewSummary(
        needs_review=bool(reasons), reasons=reasons, rules_applied=rules, rules_version=REVIEW_RULES_VERSION
    )
