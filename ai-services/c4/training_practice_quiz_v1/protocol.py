"""Contract for a future this-quiz score and pass model. Not served to students."""

PROTOCOL = "c4-practice-quiz-pass-v1"
BLUEPRINT_STRATEGY = "weak_topic_round_robin_v1"
PRODUCT_SCORE_TARGET = 0.6
PRODUCT_SCORE_TARGET_NOTE = (
    "Product rule for this practice-bank quiz. Not an institutional pass mark."
)
FEATURE_CUTOFF = "history_strictly_before_quiz_created_at"
INCOMPATIBLE_ARTIFACT = "se-supervised-sim-v1"
INCOMPATIBLE_REASON = (
    "se-supervised-sim-v1 predicts a synthetic overall exam score from 98 catalogue "
    "columns and labels pass at 0.55. It is not trained on this practice-bank blueprint, "
    "so it must not be shown as P(pass) for the current quiz."
)

# Implementation hold, not a clause copied from a verified proposal PDF.
# The proposal PDF is not in this workspace (see docs/SE_PATH_SIM_V0.md).
# SE_MODEL_TRAINING_SPEC.md §G says a pass probability needs outcome labels and a
# signed feature catalogue. Until that decision is made, synthetic runs stay inactive.
ACTIVATION_BLOCKER = "real_student_learner_disjoint_validation_required"

FEATURE_NAMES = (
    "question_count",
    "topic_count",
    "mean_prior_accuracy",
    "fraction_observed_priors",
    "min_prior_accuracy",
    "cold_start",
    "semester_y3s1",
)

FORBIDDEN_FEATURE_NAMES = (
    "y_score",
    "y_pass",
    "latent_ability",
    "correct_indexes",
    "quiz_outcome",
    "answer",
)
