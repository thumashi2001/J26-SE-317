"""Use the trained model: chance that a student answers the next question on a topic correctly.

    from predict import next_answer_probability
    p = next_answer_probability({...features from features.py...})

The feature names are listed in features.FEATURES (plus topic_prior, looked up here from the training data).
"""
import os
import joblib
import numpy as np
import pandas as pd

_BUNDLE = None


def _load():
    global _BUNDLE
    if _BUNDLE is None:
        _BUNDLE = joblib.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "gbm_next_answer.joblib"))
    return _BUNDLE


def next_answer_probability(feat: dict, topic: str | None = None) -> float:
    b = _load()
    row = dict(feat)
    if "topic_prior" not in row:
        row["topic_prior"] = b["topic_prior"].get(topic, float(np.mean(list(b["topic_prior"].values()))))
    x = pd.DataFrame([[row[c] for c in b["features"]]], columns=b["features"], dtype=float)
    return float(b["model"].predict_proba(x)[0, 1])


if __name__ == "__main__":
    demo = dict(n_prev=6, succ=4, fail=2, ema=0.7, last_correct=1, has_prev=1, days_since=3.0, n_sessions=1, stu_n=60, stu_acc=0.62,
                stu_acc10=0.7, stu_time_ratio=0.0, stu_fast=0.05, stu_hint=0.1, stu_leave=0.1, mod_acc=0.6, sess_acc=-1.0,
                q_in_session=0, is_multi=0, is_diag=0, twin_score=62.0, twin_p=0.62)
    print("chance of a correct answer:", round(next_answer_probability(demo), 3))
