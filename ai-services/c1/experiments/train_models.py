"""
Train and evaluate Component 1 models on the synthetic data.

Task A  Knowledge tracing: predict whether the student answers the NEXT question correctly.
Task B  Risk prediction: from the first 6 weeks of activity, predict who fails the final exam.

Splits are by STUDENT (never by row) so no student appears in both train and test.
Run from the repo root:
    python ai-services/c1/experiments/train_models.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets" / "raw"
MODELS = ROOT / "models"
MODELS.mkdir(exist_ok=True)
MID_DAY = 42
TAU = 14.0
FLOOR = 0.35


def split_ids(ids, seed=0):
    ids = np.array(sorted(ids))
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    cut = int(len(ids) * 0.8)
    return set(ids[:cut]), set(ids[cut:])


# ---------------------------------------------------------------- Task A
def bkt_predictions(df, p_init=0.3, p_learn=0.15, slip=0.1, guess=0.2):
    """Plain Bayesian Knowledge Tracing with fixed textbook-style parameters (the baseline)."""
    preds = np.zeros(len(df))
    for _, idx in df.groupby(["student_id", "topic"], sort=False).indices.items():
        p = p_init
        for j in idx:
            preds[j] = p * (1 - slip) + (1 - p) * guess
            c = df.correct.values[j]
            post = (p * (1 - slip) / preds[j]) if c else (p * slip / (1 - preds[j]))
            p = post + (1 - post) * p_learn
    return preds


def kt_features(ans):
    ans = ans.sort_values(["student_id", "day", "session_id"]).reset_index(drop=True)
    g = ans.groupby(["student_id", "topic"])
    ans["n_prev"] = g.cumcount()
    cs = g.correct.cumsum() - ans.correct
    ans["acc_prev"] = (cs + 1) / (ans.n_prev + 2)
    ans["last3"] = g.correct.transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean()).fillna(0.4)
    last_day = g.day.shift(1)
    ans["days_since"] = (ans.day - last_day).fillna(30)
    gs = ans.groupby("student_id")
    ans["stu_acc_prev"] = ((gs.correct.cumsum() - ans.correct) + 1) / (gs.cumcount() + 2)
    ans["stu_hint_prev"] = ((gs.hint_used.cumsum() - ans.hint_used) + 0.3) / (gs.cumcount() + 2)
    return ans


def task_a(ans):
    ans = kt_features(ans)
    tr_ids, te_ids = split_ids(ans.student_id.unique())
    tr, te = ans[ans.student_id.isin(tr_ids)], ans[ans.student_id.isin(te_ids)]
    y_te = te.correct.values
    results = {}

    topic_mean = tr.groupby("topic").correct.mean()
    results["Baseline: topic average"] = roc_auc_score(y_te, te.topic.map(topic_mean).fillna(0.5))

    te_bkt = ans[ans.student_id.isin(te_ids)].reset_index(drop=True)
    results["Baseline: plain BKT"] = roc_auc_score(te_bkt.correct, bkt_predictions(te_bkt))

    base = ["n_prev", "acc_prev", "last3", "stu_acc_prev", "stu_hint_prev", "hint_used"]
    full = base + ["days_since"]
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)).fit(tr[base], tr.correct)
    results["Logistic regression (no time features)"] = roc_auc_score(y_te, lr.predict_proba(te[base])[:, 1])
    gb = HistGradientBoostingClassifier(random_state=0).fit(tr[full], tr.correct)
    results["Gradient boosting + forgetting features"] = roc_auc_score(y_te, gb.predict_proba(te[full])[:, 1])
    joblib.dump({"model": gb, "features": full}, MODELS / "kt_model.joblib")
    return results


# ---------------------------------------------------------------- Task B
def risk_features(ans, students):
    a = ans[ans.day <= MID_DAY]
    rows = []
    for sid, d in a.groupby("student_id"):
        h1, h2 = d[d.day <= 21], d[d.day > 21]
        acc = d.correct.mean()
        trend = (h2.correct.mean() if len(h2) else acc) - (h1.correct.mean() if len(h1) else acc)
        est = []
        for _, t in d.groupby("topic"):
            gap = MID_DAY - t.day.max()
            est.append(((t.correct.sum() + 1) / (len(t) + 2)) * (FLOOR + (1 - FLOOR) * np.exp(-gap / TAU)))
        rows.append(dict(student_id=sid, acc_overall=acc, n_answers=len(d), hint_rate=d.hint_used.mean(),
                         mean_time=d.time_sec.mean(), trend=trend,
                         days_since_active=MID_DAY - d.day.max(), active_days=d.day.nunique(),
                         topics_covered=d.topic.nunique(), decayed_mastery=np.mean(est)))
    f = pd.DataFrame(rows)
    return f.merge(students[["student_id", "at_risk"]], on="student_id", how="right").fillna(
        {"acc_overall": 0, "n_answers": 0, "hint_rate": 0, "mean_time": 0, "trend": 0,
         "days_since_active": MID_DAY, "active_days": 0, "topics_covered": 0, "decayed_mastery": 0})


def task_b(ans, students):
    f = risk_features(ans, students)
    tr_ids, te_ids = split_ids(f.student_id)
    tr, te = f[f.student_id.isin(tr_ids)], f[f.student_id.isin(te_ids)]
    y_te = te.at_risk.values
    base = ["acc_overall", "n_answers", "hint_rate", "mean_time"]
    twin = base + ["trend", "days_since_active", "active_days", "topics_covered", "decayed_mastery"]
    results = {}
    results["Baseline: rule (low accuracy = at risk)"] = roc_auc_score(y_te, 1 - te.acc_overall)
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)).fit(tr[base], tr.at_risk)
    results["Logistic regression (basic features)"] = roc_auc_score(y_te, lr.predict_proba(te[base])[:, 1])
    gb0 = HistGradientBoostingClassifier(random_state=0).fit(tr[base], tr.at_risk)
    results["Gradient boosting (basic features)"] = roc_auc_score(y_te, gb0.predict_proba(te[base])[:, 1])
    gb = HistGradientBoostingClassifier(random_state=0).fit(tr[twin], tr.at_risk)
    prob = gb.predict_proba(te[twin])[:, 1]
    results["Gradient boosting + twin features"] = roc_auc_score(y_te, prob)
    extra = {"precision_at_0.5": float(precision_score(y_te, prob > 0.5)),
             "recall_at_0.5": float(recall_score(y_te, prob > 0.5))}
    joblib.dump({"model": gb, "features": twin}, MODELS / "risk_model.joblib")
    return results, extra


if __name__ == "__main__":
    ans = pd.read_csv(RAW / "synthetic_answers.csv")
    students = pd.read_csv(RAW / "synthetic_students.csv")
    a = task_a(ans)
    b, extra = task_b(ans, students)
    print("\nTask A: next-answer prediction (AUC, test students only)")
    for k, v in a.items():
        print(f"  {v:.3f}  {k}")
    print("\nTask B: at-risk prediction from first 6 weeks (AUC, test students only)")
    for k, v in b.items():
        print(f"  {v:.3f}  {k}")
    print("  ", extra)
    (MODELS / "metrics.json").write_text(json.dumps({"task_a_auc": a, "task_b_auc": b, "task_b_extra": extra}, indent=2))
    print(f"\nModels and metrics saved to {MODELS}")