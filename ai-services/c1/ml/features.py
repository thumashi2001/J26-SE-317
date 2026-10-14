"""Turns the event log into one row per answer, using ONLY what was known before that answer.

The same code also builds "exam queries": a pretend question on every topic on exam day, so every model can
be asked "how likely is this student to get a question on this topic right on exam day?".
"""
import math
import numpy as np
import pandas as pd

# ---- the current rule-based twin (same rules as the app: see services/forgetting/decay.py and the mastery update)
FLOOR, BASE_STAB, STAB_GAIN = 0.35, 14.0, 0.6
LEARN_RATE = 0.25
PRIOR = 40.0
FAST_SEC = 8.0


def twin_decay(score, days, sessions):
    stab = BASE_STAB * (1 + STAB_GAIN * sessions)
    return score * (FLOOR + (1 - FLOOR) * math.exp(-max(days, 0.0) / stab))


FEATURES = [
    "n_prev", "succ", "fail", "ema", "last_correct", "has_prev", "days_since", "n_sessions",
    "stu_n", "stu_acc", "stu_acc10", "stu_time_ratio", "stu_fast", "stu_hint", "stu_leave",
    "mod_acc", "sess_acc", "q_in_session", "is_multi", "is_diag", "twin_score", "twin_p",
]
FORGET_FEATURES = ["days_since", "twin_score", "twin_p", "n_sessions"]
BEHAVIOUR_FEATURES = ["stu_time_ratio", "stu_fast", "stu_hint", "stu_leave"]


def build(events: pd.DataFrame, exam_days: dict) -> pd.DataFrame:
    """events: sorted log. exam_days: {student_id: exam day}. Returns rows for events and exam queries."""
    rows = []
    for sid, g in events.sort_values(["student_id", "day", "event_id"]).groupby("student_id", sort=False):
        topics_here = list(dict.fromkeys(g.topic))
        mod_of = dict(zip(g.topic, g.module))
        st = {t: dict(n=0, s=0, f=0, ema=0.5, lastc=-1, last_day=None, sess=0, last_sess=None, twin=PRIOR, tn=0) for t in topics_here}
        hist_c, hist_t, hist_fast, hist_hint, hist_leave = [], [], [], [], []
        sess_c = {}

        def emit(t, day, source, multi, qpos, sess_id, real_row):
            s = st[t]
            gap = None if s["last_day"] is None else day - s["last_day"]
            twin_now = twin_decay(s["twin"], gap if gap is not None else 0.0, s["tn"]) if s["last_day"] is not None else PRIOR
            tp = min(0.97, max(0.03, twin_now / 100.0))
            mods = [x for x in topics_here if x != t and mod_of[x] == mod_of[t]]
            mc = sum(st[x]["s"] for x in mods)
            mn = sum(st[x]["n"] for x in mods)
            sc = sess_c.get(sess_id, [0, 0])
            last10 = hist_c[-10:]
            ratio = float(np.mean([math.log(max(x, 1.0) / 32.0) for x in hist_t[-20:]])) if hist_t else 0.0
            n_all = len(hist_c)
            row = dict(
                n_prev=s["n"], succ=s["s"], fail=s["f"], ema=s["ema"], last_correct=s["lastc"], has_prev=int(s["n"] > 0),
                days_since=(gap if gap is not None else 60.0), n_sessions=s["sess"],
                stu_n=n_all, stu_acc=(sum(hist_c) + 1) / (n_all + 2),
                stu_acc10=(sum(last10) + 1) / (len(last10) + 2),
                stu_time_ratio=ratio,
                stu_fast=float(np.mean(hist_fast[-20:])) if hist_fast else 0.0,
                stu_hint=float(np.mean(hist_hint[-20:])) if hist_hint else 0.0,
                stu_leave=float(np.mean(hist_leave[-20:])) if hist_leave else 0.0,
                mod_acc=(mc + 1) / (mn + 2), sess_acc=((sc[0] + 1) / (sc[1] + 2)) if sc[1] else -1.0,
                q_in_session=qpos, is_multi=int(multi), is_diag=int(source == "diagnostic"),
                twin_score=twin_now, twin_p=tp,
                student_id=sid, topic=t, module=mod_of[t], day=day, source=source,
            )
            if real_row is not None:
                row.update(event_id=int(real_row.event_id), correct=int(real_row.correct), session_id=sess_id, is_query=0,
                           time_sec=real_row.time_sec, hint_used=int(real_row.hint_used), tab_leaves=int(real_row.tab_leaves))
            else:
                row.update(event_id=-1, correct=-1, session_id="", is_query=1, time_sec=np.nan, hint_used=0, tab_leaves=0)
            rows.append(row)

        for r in g.itertuples(index=False):
            t = r.topic
            s = st[t]
            multi = r.question_type == "multi"
            emit(t, r.day, r.source, multi, r.q_in_session, r.session_id, r)
            # ---- update with the outcome (after the row was emitted)
            if r.source == "diagnostic":
                s["twin"] = (r.correct + 0.8) / 3.0 * 100.0
            else:
                faded = twin_decay(s["twin"], r.day - s["last_day"], s["tn"]) if s["last_day"] is not None else s["twin"]
                if r.correct:
                    w = (0.5 if r.tab_leaves > 0 else 1.0) * (0.6 if r.time_sec < FAST_SEC else 1.0) * (0.5 if r.hint_used else 1.0)
                    s["twin"] = faded + LEARN_RATE * w * (100 - faded)
                else:
                    s["twin"] = faded * (1 - LEARN_RATE)
            if r.source == "quiz" and s["last_sess"] != r.session_id:
                s["sess"] += 1
                s["tn"] = s["sess"]
                s["last_sess"] = r.session_id
            s["n"] += 1
            s["s"] += int(r.correct)
            s["f"] += 1 - int(r.correct)
            s["ema"] = 0.5 * s["ema"] + 0.5 * r.correct
            s["lastc"] = int(r.correct)
            s["last_day"] = r.day
            hist_c.append(int(r.correct))
            hist_t.append(float(r.time_sec))
            hist_fast.append(int(r.time_sec < FAST_SEC))
            hist_hint.append(int(r.hint_used))
            hist_leave.append(int(r.tab_leaves > 0))
            sc = sess_c.setdefault(r.session_id, [0, 0])
            sc[0] += int(r.correct)
            sc[1] += 1

        ed = exam_days[sid]
        for t in topics_here:
            emit(t, ed, "query", False, 0, "", None)
    return pd.DataFrame(rows)
