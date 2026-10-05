"""Risk prediction for Component 1. Uses the trained model; falls back to a rule if it is missing."""
import math
from pathlib import Path
import joblib
import pandas as pd

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "risk_model.joblib"
FLOOR, TAU = 0.35, 14.0
LOW_BELOW, HIGH_FROM = 0.25, 0.50   # probability cut-offs: tune these when real data exists

try:
    _bundle = joblib.load(MODEL_PATH)
    _model, _features = _bundle["model"], _bundle["features"]
except Exception:
    _model, _features = None, None


def compute_features(events, as_of_day):
    """events: list of dicts with day, topic, correct, hint_used, time_sec."""
    d = pd.DataFrame([e for e in events if e["day"] <= as_of_day])
    if d.empty:
        return {"acc_overall": 0, "n_answers": 0, "hint_rate": 0, "mean_time": 0, "trend": 0,
                "days_since_active": as_of_day, "active_days": 0, "topics_covered": 0,
                "decayed_mastery": 0}
    d["correct"] = d["correct"].astype(int)
    d["hint_used"] = d["hint_used"].astype(int)
    h1, h2 = d[d.day <= 21], d[d.day > 21]
    acc = d.correct.mean()
    trend = (h2.correct.mean() if len(h2) else acc) - (h1.correct.mean() if len(h1) else acc)
    est = []
    for _, t in d.groupby("topic"):
        gap = as_of_day - t.day.max()
        est.append(((t.correct.sum() + 1) / (len(t) + 2)) * (FLOOR + (1 - FLOOR) * math.exp(-gap / TAU)))
    return {"acc_overall": acc, "n_answers": len(d), "hint_rate": d.hint_used.mean(),
            "mean_time": d.time_sec.mean(), "trend": trend,
            "days_since_active": as_of_day - d.day.max(), "active_days": d.day.nunique(),
            "topics_covered": d.topic.nunique(), "decayed_mastery": sum(est) / len(est)}


def predict_risk(events, as_of_day):
    feats = compute_features(events, as_of_day)
    if _model is not None:
        prob = float(_model.predict_proba(pd.DataFrame([feats])[_features])[0, 1])
        source = "gradient_boosting"
    else:
        prob = 1 - feats["acc_overall"]
        source = "rule_fallback"
    level = "Low" if prob < LOW_BELOW else ("High" if prob >= HIGH_FROM else "Medium")
    return {"risk_probability": round(prob, 3), "risk_level": level, "model": source,
            "features": {k: round(float(v), 3) for k, v in feats.items()}}