"""Data-leakage and split isolation checks (fixture data only)."""

from __future__ import annotations

import sys
from pathlib import Path

C4_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C4_ROOT))

from training.dataset_assistments import normalise_interactions, parse_skill_tokens
from training.features import assert_no_current_outcome_leakage, build_historical_features
from training.fixtures import FIXTURE_BANNER, build_fixture_dataframe
from training.splits import split_learners


def test_multi_skill_tokens_preserved():
    assert parse_skill_tokens("1_27_33") == ["1", "27", "33"]
    assert parse_skill_tokens("Box_and_Whisker") == ["Box_and_Whisker"]


def test_fixture_banner_present():
    df = build_fixture_dataframe()
    assert set(df["fixture_banner"]) == {FIXTURE_BANNER}


def test_no_current_outcome_in_feature_columns():
    raw = build_fixture_dataframe()
    norm = normalise_interactions(raw)
    feats = build_historical_features(norm)
    assert_no_current_outcome_leakage(feats)
    # Historical accuracy must not equal always using current label as feature.
    # For first step of each learner, skill_prior_attempts == 0.
    first = feats.groupby("user_id").head(1)
    assert (first["skill_prior_attempts"] == 0).all()


def test_features_do_not_use_future_correctness():
    raw = build_fixture_dataframe(n_learners=3, steps=5, seed=1)
    norm = normalise_interactions(raw)
    feats = build_historical_features(norm)
    # Manually reconstruct: after first interaction, next row attempts should be 1.
    g = feats[feats["user_id"] == feats["user_id"].iloc[0]].reset_index(drop=True)
    assert g.loc[0, "skill_prior_attempts"] == 0
    # If same primary skill repeats, second row should see prior attempts >= 1 when skill matches.
    # Not always true if multi-skill primary differs; check monotonic global attempts.
    assert list(g["global_prior_attempts"]) == list(range(len(g)))


def test_learner_split_no_overlap():
    raw = build_fixture_dataframe()
    norm = normalise_interactions(raw)
    splits = split_learners(norm)
    ids = {k: set(v["user_id"]) for k, v in splits.items() if k != "_meta"}
    assert ids["train"].isdisjoint(ids["validation"])
    assert ids["train"].isdisjoint(ids["test"])
    assert ids["validation"].isdisjoint(ids["test"])
