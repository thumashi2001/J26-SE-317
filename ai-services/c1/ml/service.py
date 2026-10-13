"""Serves the trained gradient boosting model to the app.

The backend sends one student's answer history. This builds the same 22 features the model was trained on
(features.build) and asks the model: "if this student were asked a question on each topic NOW, what is the
chance they get it right?"  Topics the student has never answered are left out (no history, no honest prediction).
"""
import os
import joblib
import numpy as np
import pandas as pd

from .features import build

_BUNDLE = None
_COLUMNS = ["day", "topic", "module", "source", "session_id", "q_in_session", "question_type",
            "correct", "time_sec", "hint_used", "tab_leaves"]


def _bundle():
    global _BUNDLE
    if _BUNDLE is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "gbm_next_answer.joblib")
        _BUNDLE = joblib.load(path)
    return _BUNDLE


def predict_correct(events: list, as_of_day: float) -> dict:
    """events: list of dicts with the keys in _COLUMNS (day counted from the student's first answer).
    Returns {topic: {"p": chance 0-1, "answers": number of answers on that topic}}."""
    if not events:
        return {}
    df = pd.DataFrame(events)
    for c in _COLUMNS:
        if c not in df.columns:
            raise ValueError(f"event field missing: {c}")
    df = df.sort_values("day", kind="stable").reset_index(drop=True)
    df["event_id"] = np.arange(len(df))
    df["student_id"] = "me"
    for c in ("correct", "hint_used", "tab_leaves"):
        df[c] = df[c].astype(int)
    day_now = max(float(as_of_day), float(df.day.max()))

    rows = build(df, {"me": day_now})
    q = rows[rows.is_query == 1]
    b = _bundle()
    prior = b["topic_prior"]
    fallback = float(np.mean(list(prior.values())))
    q = q.assign(topic_prior=q.topic.map(lambda t: prior.get(t, fallback)))
    p = b["model"].predict_proba(q[b["features"]].astype(float))[:, 1]
    counts = df.groupby("topic").size().to_dict()
    return {t: {"p": float(x), "answers": int(counts.get(t, 0))} for t, x in zip(q.topic, p)}
