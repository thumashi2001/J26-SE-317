"""Synthetic learners aligned with the practice-bank quiz. Latent ability is not a feature."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from training_practice_quiz_v1.blueprint import QUESTIONS_PER_TOPIC, topics_for
from training_practice_quiz_v1.protocol import (
    FEATURE_NAMES,
    FORBIDDEN_FEATURE_NAMES,
    PRODUCT_SCORE_TARGET,
)


@dataclass(frozen=True)
class QuizRow:
    learner_id: str
    semester: str
    features: dict[str, float]
    y_score: float
    y_pass: int


def _prior(history: dict[str, tuple[int, int]], topic: str) -> tuple[float, bool]:
    attempts, correct = history.get(topic, (0, 0))
    if attempts <= 0:
        return 0.5, False
    return correct / attempts, True


def _blueprint(history: dict[str, tuple[int, int]], topics: tuple[str, ...], count: int) -> list[str]:
    ordered = sorted(topics, key=lambda topic: (_prior(history, topic)[0], topic))
    banks = {topic: QUESTIONS_PER_TOPIC for topic in ordered}
    selected: list[str] = []
    round_index = 0
    while len(selected) < count and any(banks[topic] > round_index for topic in ordered):
        for topic in ordered:
            if len(selected) >= count:
                break
            if banks[topic] > round_index:
                selected.append(topic)
        round_index += 1
    return selected


def features_from_history(semester: str, history: dict[str, tuple[int, int]], questions: list[str]) -> dict[str, float]:
    priors = [_prior(history, topic) for topic in questions]
    observed = [flag for _value, flag in priors]
    values = [value for value, _flag in priors]
    cold = not any(observed)
    return {
        "question_count": float(len(questions)),
        "topic_count": float(len(set(questions))),
        "mean_prior_accuracy": float(np.mean(values)) if values else 0.5,
        "fraction_observed_priors": float(np.mean(observed)) if observed else 0.0,
        "min_prior_accuracy": float(np.min(values)) if values else 0.5,
        "cold_start": 1.0 if cold else 0.0,
        "semester_y3s1": 1.0 if semester == "Y3S1" else 0.0,
    }


def assert_feature_contract(features: dict[str, float]) -> None:
    names = tuple(features)
    if names != FEATURE_NAMES:
        raise ValueError(f"feature order must be {FEATURE_NAMES}")
    leaked = [name for name in FORBIDDEN_FEATURE_NAMES if name in features]
    if leaked:
        raise ValueError(f"leaked fields: {leaked}")


def make_row(rng: np.random.Generator, learner_id: str, semester: str, question_count: int = 8) -> QuizRow:
    topics = topics_for(semester)
    if not topics:
        raise ValueError(f"unknown semester {semester}")
    latent = float(rng.uniform(0.15, 0.9))
    history: dict[str, tuple[int, int]] = {}
    for topic in topics:
        if rng.random() < 0.5:
            attempts = int(rng.integers(1, 8))
            correct = int(rng.binomial(attempts, np.clip(latent, 0.05, 0.95)))
            history[topic] = (attempts, correct)
    questions = _blueprint(history, topics, question_count)
    outcomes = rng.random(len(questions)) < np.clip(latent, 0.05, 0.95)
    y_score = float(np.mean(outcomes)) if len(questions) else 0.0
    features = features_from_history(semester, history, questions)
    assert_feature_contract(features)
    return QuizRow(
        learner_id=learner_id,
        semester=semester,
        features=features,
        y_score=y_score,
        y_pass=int(y_score >= PRODUCT_SCORE_TARGET),
    )


def generate_rows(seed: int, learners: int) -> list[QuizRow]:
    rng = np.random.default_rng(seed)
    rows: list[QuizRow] = []
    for index in range(learners):
        semester = "Y3S1" if index % 2 == 0 else "Y3S2"
        rows.append(make_row(rng, f"syn-{index:04d}", semester))
    return rows
