"""Clearly labelled miniature fixtures for software tests only.

These are NOT research training/evaluation datasets and must never be described as such.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .paths import ensure_dir, fixtures_dir

FIXTURE_FILENAME = "assistments_like_SOFTWARE_TEST_FIXTURE.csv"
FIXTURE_BANNER = "SOFTWARE_TEST_FIXTURE_NOT_FOR_RESEARCH_TRAINING_OR_EVALUATION"


def build_fixture_dataframe(n_learners: int = 12, steps: int = 40, seed: int = 0) -> pd.DataFrame:
    rng = __import__("numpy").random.default_rng(seed)
    skills = ["101", "102", "103", "101_104"]  # includes multi-skill collapse
    rows = []
    order = 1
    for u in range(n_learners):
        user = f"fixture_user_{u}"
        for t in range(steps):
            skill = skills[int(rng.integers(0, len(skills)))]
            correct = int(rng.random() > 0.4)
            rows.append(
                {
                    "order_id": order,
                    "assignment_id": 1,
                    "user_id": user,
                    "assistment_id": 10 + t,
                    "problem_id": 1000 + t,
                    "original": 1,
                    "correct": correct,
                    "attempt_count": 1,
                    "ms_first_response": int(rng.integers(500, 8000)),
                    "tutor_mode": "tutor",
                    "answer_type": "algebra",
                    "sequence_id": 1,
                    "student_class_id": 1,
                    "position": t,
                    "type": "MasterySection",
                    "base_sequence_id": 1,
                    "skill_id": skill,
                    "skill_name": f"FixtureSkill_{skill}",
                    "teacher_id": 1,
                    "school_id": 1,
                    "hint_count": int(rng.integers(0, 3)) if correct == 0 else 0,
                    "hint_total": 3,
                    "overlap_time": 0,
                    "template_id": 1,
                    "answer_id": None,
                    "answer_text": None,
                    "first_action": 0,
                    "bottom_hint": 0,
                    "opportunity": t + 1,
                    "opportunity_original": t + 1,
                    "fixture_banner": FIXTURE_BANNER,
                }
            )
            order += 1
    return pd.DataFrame(rows)


def write_default_fixture(path: Path | str | None = None) -> Path:
    out = Path(path) if path else fixtures_dir() / FIXTURE_FILENAME
    ensure_dir(out.parent)
    df = build_fixture_dataframe()
    df.to_csv(out, index=False)
    readme = out.with_suffix(".README.txt")
    readme.write_text(
        "SOFTWARE TEST FIXTURE ONLY.\n"
        "Not ASSISTments research data.\n"
        "Not for model training claims or evaluation claims.\n",
        encoding="utf-8",
    )
    return out


def load_fixture_csv(path: Path | str | None = None) -> pd.DataFrame:
    p = Path(path) if path else fixtures_dir() / FIXTURE_FILENAME
    if not p.exists():
        write_default_fixture(p)
    df = pd.read_csv(p, low_memory=False)
    if "fixture_banner" in df.columns and FIXTURE_BANNER not in set(df["fixture_banner"].astype(str)):
        raise ValueError("Fixture banner missing; refusing to treat unknown CSV as a test fixture")
    return df
