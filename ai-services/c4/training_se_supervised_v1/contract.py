"""Frozen synthetic generation and evaluation contract (declared before fitting).

Do not retune these values after seeing model metrics to chase attractive numbers.
All declared scenarios must be reported; do not select a generator based on wins.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from .catalogue import (
    N_TOPICS,
    ORDERED_TOPICS,
    TOPIC_MODULE,
    TOPIC_SEMESTER,
    Y3S1_TOPICS,
    Y3S2_TOPICS,
    catalogue_hash,
)
from .protocol import DOMAIN_MARKERS, GENERATOR_VERSION, NON_CLAIMS, PROTOCOL_VERSION

# ---------------------------------------------------------------------------
# Declared BEFORE any fitting. Pass uses exam fraction-correct scale [0, 1].
# ---------------------------------------------------------------------------
PASS_THRESHOLD: float = 0.55
PASS_THRESHOLD_NOTE = (
    "Pass label = 1[y_exam_score >= 0.55] on the synthetic exam fraction-correct scale. "
    "This is a declared synthetic exam-score cutoff only — not an institutional rule."
)
# Separate from PASS_THRESHOLD: used only when converting probabilities → hard class
# for accuracy reporting. Do not conflate with the score cutoff that defines y_pass.
CLASSIFICATION_PROB_THRESHOLD: float = 0.5
CLASSIFICATION_PROB_THRESHOLD_NOTE = (
    "Hard-class threshold on predicted P(y=1) for accuracy only. "
    "Independent of PASS_THRESHOLD on the exam-score scale."
)

# Minimum train positives AND negatives required to enable optional pass models.
PASS_MIN_CLASS_COUNT: int = 8

# Random stream offsets (separate streams; never reuse across roles).
STREAM_LEARNER = 0
STREAM_QUESTIONS = 100_003
STREAM_PRACTICE = 1_000_003
STREAM_EXAM = 2_000_003
STREAM_SPLIT = 3_000_003

PRIMARY_SCENARIO = "baseline"


@dataclass(frozen=True)
class SizeConfig:
    n_learners: int
    n_questions_per_topic: int
    practice_attempts_min: int
    practice_attempts_max: int
    exam_items_per_topic: int
    # Max practice attempts used as response-prediction rows per learner (cap for smoke speed).
    max_response_rows_per_learner: int


SMOKE_SIZES = SizeConfig(
    n_learners=60,
    n_questions_per_topic=8,
    practice_attempts_min=12,
    practice_attempts_max=36,
    exam_items_per_topic=2,
    max_response_rows_per_learner=24,
)

FULL_SIZES = SizeConfig(
    n_learners=2000,
    n_questions_per_topic=20,
    practice_attempts_min=20,
    practice_attempts_max=80,
    exam_items_per_topic=3,
    max_response_rows_per_learner=60,
)


@dataclass(frozen=True)
class ScenarioParams:
    """Assumed generator parameters — NOT empirically fitted."""

    name: str
    description: str
    ability_mean: float
    ability_sd: float
    topic_affinity_sd: float
    difficulty_mean: float
    difficulty_sd: float
    response_logit_noise_sd: float
    practice_gain_per_correct: float
    practice_gain_per_incorrect: float
    # Stochastic topic choice: preference for weaker topics (higher = more remedial).
    weak_topic_bias: float


# Predeclared scenarios. Report ALL; do not drop after seeing results.
SCENARIOS: dict[str, ScenarioParams] = {
    "baseline": ScenarioParams(
        name="baseline",
        description="Default learner heterogeneity and question difficulty.",
        ability_mean=0.0,
        ability_sd=0.85,
        topic_affinity_sd=0.35,
        difficulty_mean=0.0,
        difficulty_sd=0.70,
        response_logit_noise_sd=0.45,
        practice_gain_per_correct=0.08,
        practice_gain_per_incorrect=0.02,
        weak_topic_bias=0.55,
    ),
    "high_noise": ScenarioParams(
        name="high_noise",
        description="Higher stochastic response noise; same ability/difficulty margins.",
        ability_mean=0.0,
        ability_sd=0.85,
        topic_affinity_sd=0.35,
        difficulty_mean=0.0,
        difficulty_sd=0.70,
        response_logit_noise_sd=1.10,
        practice_gain_per_correct=0.08,
        practice_gain_per_incorrect=0.02,
        weak_topic_bias=0.55,
    ),
    "easy_bank": ScenarioParams(
        name="easy_bank",
        description="Easier question bank (lower mean difficulty); other knobs unchanged.",
        ability_mean=0.0,
        ability_sd=0.85,
        topic_affinity_sd=0.35,
        difficulty_mean=-0.75,
        difficulty_sd=0.55,
        response_logit_noise_sd=0.45,
        practice_gain_per_correct=0.08,
        practice_gain_per_incorrect=0.02,
        weak_topic_bias=0.55,
    ),
}


@dataclass(frozen=True)
class SplitFractions:
    train: float = 0.70
    validation: float = 0.15
    test: float = 0.15


@dataclass(frozen=True)
class SelectionMetrics:
    response_primary: str = "log_loss"  # lower better
    exam_score_primary: str = "mae"  # lower better
    pass_primary: str = "log_loss"  # lower better; only if pass models enabled


@dataclass(frozen=True)
class FrozenContract:
    protocol: str = PROTOCOL_VERSION
    generator_version: str = GENERATOR_VERSION
    master_seed: int = 42
    pass_threshold: float = PASS_THRESHOLD
    pass_threshold_note: str = PASS_THRESHOLD_NOTE
    classification_prob_threshold: float = CLASSIFICATION_PROB_THRESHOLD
    classification_prob_threshold_note: str = CLASSIFICATION_PROB_THRESHOLD_NOTE
    pass_min_class_count: int = PASS_MIN_CLASS_COUNT
    primary_scenario: str = PRIMARY_SCENARIO
    split: SplitFractions = field(default_factory=SplitFractions)
    selection: SelectionMetrics = field(default_factory=SelectionMetrics)
    n_topics: int = N_TOPICS
    topics: tuple[str, ...] = ORDERED_TOPICS
    exam_coverage: str = (
        "Mock exam items cover only the learner's semester-eligible topics "
        f"(Y3S1={len(Y3S1_TOPICS)} topics, Y3S2={len(Y3S2_TOPICS)} topics). "
        "Practice topic choice is likewise semester-restricted."
    )
    prediction_horizon: str = (
        "response: next practice attempt correctness at time t "
        "(features use only events with timestamp < t). "
        "exam_score/pass: predict at end of practice window; mock exam starts after cutoff."
    )
    feature_cutoff_rule: str = (
        "Strict: response features exclude target row correctness and any aggregate "
        "that includes it. Exam features use only practice before exam_start_ts; "
        "exclude exam answers/score, future mastery, latents, and true P(correct)."
    )
    latent_audit_only: tuple[str, ...] = (
        "latent_ability",
        "topic_affinity",
        "true_p_correct",
        "exam_true_p",
        "generator_noise",
    )
    excluded_from_features: tuple[str, ...] = (
        "learner_id",  # identifiers never used as predictors
        "user_id",
        "correct",  # target for response
        "y_correct",
        "exam_score",
        "y_exam_score",
        "y_pass",
        "exam_n_correct",
        *latent_audit_only,
    )


def sizes_for_mode(mode: str) -> SizeConfig:
    if mode == "smoke":
        return SMOKE_SIZES
    if mode == "full":
        return FULL_SIZES
    raise ValueError(f"mode must be 'smoke' or 'full', got {mode!r}")


def frozen_contract_dict(*, mode: str, master_seed: int = 42) -> dict[str, Any]:
    """Serializable contract snapshot saved before fitting."""
    sizes = sizes_for_mode(mode)
    contract = FrozenContract(master_seed=master_seed)
    payload = {
        **DOMAIN_MARKERS,
        "contract": {
            "protocol": contract.protocol,
            "generator_version": contract.generator_version,
            "master_seed": contract.master_seed,
            "pass_threshold": contract.pass_threshold,
            "pass_threshold_note": contract.pass_threshold_note,
            "classification_prob_threshold": contract.classification_prob_threshold,
            "classification_prob_threshold_note": contract.classification_prob_threshold_note,
            "pass_min_class_count": contract.pass_min_class_count,
            "primary_scenario": contract.primary_scenario,
            "split": asdict(contract.split),
            "selection": asdict(contract.selection),
            "n_topics": contract.n_topics,
            "topics": list(contract.topics),
            "topic_modules": dict(TOPIC_MODULE),
            "topic_semesters": dict(TOPIC_SEMESTER),
            "exam_coverage": contract.exam_coverage,
            "exam_n_items_y3s1": sizes.exam_items_per_topic * len(Y3S1_TOPICS),
            "exam_n_items_y3s2": sizes.exam_items_per_topic * len(Y3S2_TOPICS),
            "catalogue_sha256": catalogue_hash(),
            "prediction_horizon": contract.prediction_horizon,
            "feature_cutoff_rule": contract.feature_cutoff_rule,
            "latent_audit_only": list(contract.latent_audit_only),
            "excluded_from_features": list(contract.excluded_from_features),
            "stream_offsets": {
                "learner": STREAM_LEARNER,
                "questions": STREAM_QUESTIONS,
                "practice": STREAM_PRACTICE,
                "exam": STREAM_EXAM,
                "split": STREAM_SPLIT,
            },
            "mode": mode,
            "sizes": asdict(sizes),
            "exam_n_items_note": (
                "Per-learner exam length = exam_items_per_topic * n_semester_topics "
                "(not full 46)."
            ),
            "scenarios": {k: asdict(v) for k, v in SCENARIOS.items()},
            "scenario_reporting_rule": (
                "All predeclared scenarios are generated and reported. "
                "Model selection uses primary_scenario validation only. "
                "Do not choose a generator scenario based on model wins."
            ),
            "targets": {
                "A": {
                    "name": "next_attempt_correctness",
                    "type": "binary",
                    "label": "y_correct",
                    "candidates": [
                        "constant_train_prevalence",
                        "logistic_regression",
                        "hist_gradient_boosting_classifier",
                    ],
                },
                "B": {
                    "name": "mock_exam_score",
                    "type": "regression",
                    "label": "y_exam_score",
                    "scale": "fraction_correct_[0,1]",
                    "candidates": [
                        "train_mean",
                        "ridge_regression",
                        "hist_gradient_boosting_regressor",
                    ],
                },
                "B_optional_pass": {
                    "name": "mock_exam_pass",
                    "type": "binary",
                    "label": "y_pass",
                    "enabled_if": (
                        f"train has >= {PASS_MIN_CLASS_COUNT} examples in each class "
                        f"at pass_threshold={PASS_THRESHOLD}"
                    ),
                    "candidates": [
                        "constant_train_prevalence",
                        "logistic_regression",
                        "hist_gradient_boosting_classifier",
                    ],
                },
            },
            "non_claims": list(NON_CLAIMS),
            "note": (
                "All ScenarioParams and SizeConfig values are assumed for synthesis. "
                "They are not fitted from real SE logs."
            ),
        },
    }
    return deepcopy(payload)
