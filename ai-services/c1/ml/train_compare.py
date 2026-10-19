"""Trains and compares models on the synthetic data. Everything is judged on students the models never saw.

Run:  python generate_synthetic.py && python train_compare.py
Outputs: models/*, reports/results.json, reports/model_comparison.csv  (charts: python make_charts.py)
"""
import json
import os
import time
import joblib
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import bkt
from features import BEHAVIOUR_FEATURES, FEATURES, FORGET_FEATURES, build

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda f: os.path.join(HERE, "data", f)
M = lambda f: os.path.join(HERE, "models", f)
R = lambda f: os.path.join(HERE, "reports", f)
SEED = 7

NAMES = {
    "global_mean": "Global average",
    "topic_mean": "Topic average",
    "rule_twin": "Rule-based twin (current)",
    "twin_cal": "Rule-based twin + calibration",
    "bkt": "BKT",
    "bkt_forget": "BKT with forgetting",
    "pfa": "PFA (logistic)",
    "logreg": "Logistic, rich features",
    "mlp": "Neural network (MLP)",
    "gbm": "Gradient boosting",
}


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    out = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.sum():
            out += m.mean() * abs(y[m].mean() - p[m].mean())
    return out


def metrics(y, p, gt=None):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    out = dict(auc=roc_auc_score(y, p), logloss=log_loss(y, p), brier=brier_score_loss(y, p), acc=accuracy_score(y, p >= 0.5), ece=ece(y, p))
    if gt is not None:
        out["rmse_truth"] = float(np.sqrt(np.mean((p - gt) ** 2)))
    return out


def main():
    ev = pd.read_csv(D("synthetic_events.csv"))
    truth = pd.read_csv(D("synthetic_ground_truth.csv"))
    ex = pd.read_csv(D("synthetic_exam_truth.csv"))
    stu = pd.read_csv(D("synthetic_students.csv"))
    exam_days = ex.groupby("student_id").day.first().to_dict()
    exam_true = stu.set_index("student_id").exam_true_score

    t0 = time.time()
    df = build(ev, exam_days)
    df = df.merge(truth[["event_id", "gt_p_correct"]], on="event_id", how="left")
    print(f"features built: {len(df)} rows in {time.time() - t0:.0f}s")

    rng = np.random.default_rng(SEED)
    ids = np.array(sorted(stu.student_id))
    rng.shuffle(ids)
    n = len(ids)
    split = {"train": set(ids[: int(.6 * n)]), "val": set(ids[int(.6 * n): int(.8 * n)]), "test": set(ids[int(.8 * n):])}
    df["split"] = df.student_id.map(lambda s: "train" if s in split["train"] else "val" if s in split["val"] else "test")
    real = df[df.is_query == 0]
    tr, va, te = (real[real.split == k] for k in ("train", "val", "test"))
    print({k: (len(v), v.student_id.nunique()) for k, v in (("train", tr), ("val", va), ("test", te))})

    prior = tr.groupby("topic").correct.mean()
    df["topic_prior"] = df.topic.map(prior).fillna(tr.correct.mean())
    X_cols = FEATURES + ["topic_prior"]
    real = df[df.is_query == 0]
    tr, va, te = (real[real.split == k] for k in ("train", "val", "test"))
    preds = {}

    preds["global_mean"] = np.full(len(df), tr.correct.mean())
    preds["topic_mean"] = df.topic_prior.values
    preds["rule_twin"] = df.twin_p.values
    cal = LogisticRegression(C=10).fit(tr[["twin_score"]], tr.correct)
    preds["twin_cal"] = cal.predict_proba(df[["twin_score"]])[:, 1]

    # ---- BKT (fit on training students only)
    obs, gap, idx = bkt.make_sequences(df)
    train_rows = set(tr.index)
    in_train = np.array([df.student_id.values[i[0]] in split["train"] for i in idx])
    obs_tr, gap_tr = obs[in_train], gap[in_train]
    for key, forget in (("bkt", False), ("bkt_forget", True)):
        t1 = time.time()
        cache = M(f"{key}_theta.npy")
        if os.path.exists(cache) and not os.environ.get("REFIT"):
            theta = np.load(cache)
        else:
            theta = bkt.fit(obs_tr, gap_tr, forget)
            np.save(cache, theta)
        pm, _ = bkt.run(theta, obs, gap, forget)
        p = np.full(len(df), np.nan)
        mask = idx >= 0
        p[idx[mask]] = pm[mask]
        preds[key] = p
        pr = bkt.unpack(theta, forget)
        json.dump({"params": [None if x is None else float(x) for x in pr], "names": ["p_init", "p_learn", "slip", "guess", "tau_days", "p_floor"]}, open(M(f"{key}_params.json"), "w"), indent=1)
        print(f"{key} fitted in {time.time() - t1:.0f}s", [None if x is None else round(float(x), 3) for x in pr])

    # ---- PFA
    topics = sorted(df.topic.unique())
    def pfa_X(d):
        base = np.column_stack([np.log1p(d.succ), np.log1p(d.fail)])
        oh = pd.get_dummies(d.topic).reindex(columns=topics, fill_value=0).astype(float).values
        return np.hstack([base, oh])
    pfa = LogisticRegression(C=1.0, max_iter=500).fit(pfa_X(tr), tr.correct)
    preds["pfa"] = pfa.predict_proba(pfa_X(df))[:, 1]

    # ---- logistic regression, MLP, gradient boosting on the rich history features
    lr = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=1000)).fit(tr[X_cols], tr.correct)
    preds["logreg"] = lr.predict_proba(df[X_cols])[:, 1]
    mlp = make_pipeline(StandardScaler(), MLPClassifier((64, 32), alpha=1e-3, early_stopping=True, validation_fraction=0.15, max_iter=200, random_state=SEED)).fit(tr[X_cols], tr.correct)
    preds["mlp"] = mlp.predict_proba(df[X_cols])[:, 1]

    best_gbm, best_ll = None, 9
    for lrt in (0.04, 0.08):
        for leaves in (8, 20):
            g = HistGradientBoostingClassifier(learning_rate=lrt, max_leaf_nodes=leaves, max_iter=400, early_stopping=True,
                                               validation_fraction=0.15, n_iter_no_change=25, l2_regularization=1.0, random_state=SEED).fit(tr[X_cols], tr.correct)
            ll = log_loss(va.correct, g.predict_proba(va[X_cols])[:, 1])
            if ll < best_ll:
                best_gbm, best_ll, best_cfg = g, ll, (lrt, leaves)
    gbm = best_gbm
    print("gbm config", best_cfg, "iters", gbm.n_iter_)
    preds["gbm"] = gbm.predict_proba(df[X_cols])[:, 1]

    for k, v in preds.items():
        df["p_" + k] = v

    # ---- 1. next-answer prediction on unseen students
    real = df[df.is_query == 0]
    te = real[real.split == "test"]
    va = real[real.split == "val"]
    results = {}
    for k in NAMES:
        results[k] = metrics(te.correct.values, te["p_" + k].values, te.gt_p_correct.values)
        results[k]["auc_val"] = float(roc_auc_score(va.correct, va["p_" + k]))
    quiz = te[te.source == "quiz"]
    for k in NAMES:
        results[k]["auc_quiz"] = float(roc_auc_score(quiz.correct, quiz["p_" + k]))

    # the best any model could do on this data: it knows the hidden true probability of every answer
    oracle = metrics(te.correct.values, te.gt_p_correct.values, te.gt_p_correct.values)

    # ---- 1b. is a difference real? resample whole students 300 times
    sid_te = te.student_id.values
    uniq = np.unique(sid_te)
    groups = {u: np.where(sid_te == u)[0] for u in uniq}
    brng = np.random.default_rng(SEED)
    boots = {k: [] for k in NAMES}
    y_te = te.correct.values
    for _ in range(300):
        pick = brng.choice(uniq, size=len(uniq), replace=True)
        ix = np.concatenate([groups[u] for u in pick])
        for k in NAMES:
            boots[k].append(roc_auc_score(y_te[ix], te["p_" + k].values[ix]))
    ci = {}
    for k in NAMES:
        a = np.array(boots[k]); d = a - np.array(boots["gbm"])
        ci[k] = dict(auc_lo=float(np.percentile(a, 2.5)), auc_hi=float(np.percentile(a, 97.5)), diff_vs_gbm_lo=float(np.percentile(d, 2.5)), diff_vs_gbm_hi=float(np.percentile(d, 97.5)))
    for k in NAMES:
        results[k].update(ci[k])

    # ---- 2. how much history does a model need?  AUC by number of earlier answers on the same topic
    bins = [(0, 0, "0 (cold start)"), (1, 3, "1 to 3"), (4, 9, "4 to 9"), (10, 999, "10 or more")]
    cold = {}
    for lo, hi, lab in bins:
        s = te[(te.n_prev >= lo) & (te.n_prev <= hi)]
        cold[lab] = {k: float(roc_auc_score(s.correct, s["p_" + k])) if s.correct.nunique() > 1 else None for k in NAMES}
        cold[lab]["n"] = int(len(s))

    # ---- 3. predict the exam-day score of each student (TAF task 5)
    q = df[(df.is_query == 1) & (df.split == "test")]
    exam = {}
    for k in NAMES:
        pred_score = 100 * q.groupby("student_id")["p_" + k].mean()
        tru = exam_true.loc[pred_score.index]
        exam[k] = dict(mae=float(np.mean(np.abs(pred_score - tru))), bias=float(np.mean(pred_score - tru)),
                       pearson=float(pearsonr(pred_score, tru)[0]) if pred_score.std() > 1e-9 else 0.0,
                       spearman=float(spearmanr(pred_score, tru)[0]) if pred_score.std() > 1e-9 else 0.0,
                       auc_at_risk=float(roc_auc_score((tru < 40).astype(int), -pred_score)) if pred_score.std() > 1e-9 else 0.5)
    exam_meta = dict(students=int(q.student_id.nunique()), at_risk_share=float((exam_true.loc[q.student_id.unique()] < 40).mean()))

    # ---- 4. calibration curves (saved for the chart)
    calib = {}
    for k in ("rule_twin", "bkt_forget", "gbm"):
        p = np.clip(te["p_" + k].values, 0, 1)
        b = np.minimum((p * 10).astype(int), 9)
        calib[k] = [[float(p[b == i].mean()), float(te.correct.values[b == i].mean()), int((b == i).sum())] for i in range(10) if (b == i).sum() > 30]

    # ---- 5. which signals matter?  Retrain boosting without a group of features.
    def fit_gbm(cols):
        g = HistGradientBoostingClassifier(learning_rate=best_cfg[0], max_leaf_nodes=best_cfg[1], max_iter=400, early_stopping=True,
                                           validation_fraction=0.15, n_iter_no_change=25, l2_regularization=1.0, random_state=SEED).fit(tr[cols], tr.correct)
        p = g.predict_proba(te[cols])[:, 1]
        return dict(auc=float(roc_auc_score(te.correct, p)), logloss=float(log_loss(te.correct, np.clip(p, 1e-4, 1 - 1e-4))))
    drop = lambda cols: [c for c in X_cols if c not in cols]
    ablation = {
        "All signals": fit_gbm(X_cols),
        "Without forgetting signals": fit_gbm(drop(FORGET_FEATURES)),
        "Without behaviour signals (time, hints, tab leaves)": fit_gbm(drop(BEHAVIOUR_FEATURES)),
        "Without both": fit_gbm(drop(FORGET_FEATURES + BEHAVIOUR_FEATURES)),
        "Without the rule-based twin score": fit_gbm(drop(["twin_score", "twin_p"])),
    }
    samp = te.sample(4000, random_state=SEED)
    pi = permutation_importance(gbm, samp[X_cols], samp.correct, scoring="roc_auc", n_repeats=4, random_state=SEED)
    imp = sorted(zip(X_cols, pi.importances_mean), key=lambda x: -x[1])

    # ---- 6. speed of one prediction
    lat = {}
    one = te[X_cols].iloc[:200]
    for k, mdl in (("gbm", gbm), ("mlp", mlp), ("logreg", lr), ("pfa", None)):
        if mdl is None:
            continue
        t1 = time.time()
        for i in range(200):
            mdl.predict_proba(one.iloc[[i]])
        lat[k] = (time.time() - t1) / 200 * 1000

    # ---- 7. is the data itself believable?
    data_check = dict(
        students=int(stu.shape[0]), events=int(len(ev)), quiz_sessions=int(ev[ev.source == "quiz"].session_id.nunique()),
        topics=int(ev.topic.nunique()), accuracy_diagnostic=float(ev[ev.source == "diagnostic"].correct.mean()),
        accuracy_quiz=float(ev[ev.source == "quiz"].correct.mean()),
        median_time_sec=float(ev.time_sec.median()), hint_share=float(ev.hint_used.mean()),
        tab_leave_share=float((ev.tab_leaves > 0).mean()), train_students=len(split["train"]), val_students=len(split["val"]), test_students=len(split["test"]),
        test_events=int(len(te)),
    )

    out = dict(next_answer=results, by_history=cold, exam=exam, exam_meta=exam_meta, calibration=calib, ablation=ablation,
               importance=[[a, float(b)] for a, b in imp], oracle=oracle, latency_ms=lat, data=data_check, names=NAMES, gbm_config=best_cfg)
    json.dump(out, open(R("results.json"), "w"), indent=1)
    tab = pd.DataFrame({NAMES[k]: results[k] for k in NAMES}).T
    tab["exam_mae"] = [exam[k]["mae"] for k in NAMES]
    tab["exam_bias"] = [exam[k]["bias"] for k in NAMES]
    tab["exam_spearman"] = [exam[k]["spearman"] for k in NAMES]
    tab.round(4).to_csv(R("model_comparison.csv"))
    print(tab.drop(columns=[c for c in tab.columns if c.endswith(('_lo', '_hi'))]).round(3).to_string())
    print({k: (round(results[k]['auc_lo'], 3), round(results[k]['auc_hi'], 3), round(results[k]['diff_vs_gbm_lo'], 3), round(results[k]['diff_vs_gbm_hi'], 3)) for k in NAMES})
    print("\nEXAM", {k: (round(v['mae'], 1), round(v['spearman'], 2), round(v['auc_at_risk'], 2)) for k, v in exam.items()})
    print("\nORACLE", {k: round(v, 3) for k, v in oracle.items()})
    print("\nABLATION", {k: round(v['auc'], 4) for k, v in ablation.items()})
    print("\nIMPORTANCE", [(a, round(b, 4)) for a, b in imp[:8]])
    print("\nLATENCY", {k: round(v, 2) for k, v in lat.items()})
    print("\nHISTORY", {lab: {k: (None if v is None else round(v, 3)) for k, v in d.items()} for lab, d in cold.items()})

    joblib.dump(dict(model=gbm, features=X_cols, topic_prior=prior.to_dict(), config=best_cfg), M("gbm_next_answer.joblib"))


if __name__ == "__main__":
    main()
