"""Synthetic student dataset for Component 1 (Cognitive Digital Twin).

Why synthetic: real learning logs are not available yet and must be anonymised before use.
The simulator below invents students (S0001, S0002, ...) and plays them through the same flow as the real app:
  day 0   : diagnostic test, one question for every topic of the semester
  day 1.. : practice quizzes of 7 questions on one topic, 50/50 hint, timing, tab leaves
Every student has hidden traits and every topic has a hidden difficulty. The hidden knowledge level of each
student and topic is stored in a separate ground-truth file so models can be checked against the truth.

IMPORTANT: the simulator is a different mathematical form from every model we compare (it uses a power-law
forgetting curve, cross-topic transfer inside a module and student-specific rates), so no model gets a free win.

Run:  python generate_synthetic.py            (writes data/*.csv)
"""
import csv
import os
import numpy as np
import pandas as pd

SEED = 2026
N_STUDENTS = 600
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FLOOR = 0.30          # knowledge never fades fully
QUESTIONS_PER_QUIZ = 7
EXAM_GAP_DAYS = 7     # the exam happens this many days after the last simulated day


def retention(gap_days, stability):
    """Power-law forgetting: fast at first, then slow."""
    return FLOOR + (1 - FLOOR) * (1 + gap_days / stability) ** -0.8


def main():
    rng = np.random.default_rng(SEED)
    topics = pd.read_csv(os.path.join(DATA, "topics.csv"))
    by_sem = {s: g.reset_index(drop=True) for s, g in topics.groupby("semester")}
    diff = {t: rng.normal(0, 0.6) for t in topics.topic}
    mod_eff = {m: rng.normal(0, 0.4) for m in topics.module.unique()}

    events, truth, exam_rows, students = [], [], [], []
    ev_id = 0

    for si in range(N_STUDENTS):
        sid = f"S{si + 1:04d}"
        sem = "Y3S1" if rng.random() < 0.6 else "Y3S2"
        tp = by_sem[sem]
        names = list(tp.topic)
        module_of = dict(zip(tp.topic, tp.module))
        theta = rng.normal(0, 0.9)
        alpha = float(np.clip(rng.lognormal(np.log(0.22), 0.35), 0.06, 0.6))
        stab_mult = float(rng.lognormal(0, 0.4))
        rush = float(rng.beta(1.5, 6))
        slip = float(rng.uniform(0.02, 0.12))
        engage = float(rng.beta(2, 3))
        picks_weak = float(rng.uniform(0, 1))
        horizon = int(rng.integers(21, 61))
        students.append(dict(student_id=sid, semester=sem, theta=round(theta, 3), learn_rate=round(alpha, 3),
                             stability_mult=round(stab_mult, 3), rush=round(rush, 3), slip=round(slip, 3),
                             engagement=round(engage, 3), horizon_days=horizon))

        # hidden knowledge, last practice day and number of sessions for each topic
        k = {t: float(np.clip(1 / (1 + np.exp(-(1.2 * theta - diff[t] - mod_eff[module_of[t]] * 0.5 - 0.6 + rng.normal(0, 0.6)))), 0.02, 0.97)) for t in names}
        last_day = {t: 0.0 for t in names}
        nsess = {t: 0 for t in names}
        seen_acc = {t: [0, 0] for t in names}  # what the student could see: correct, answered

        def k_now(t, day):
            stab = 6.0 * stab_mult * (1 + 0.4 * nsess[t] ** 0.7)
            return k[t] * retention(max(day - last_day[t], 0.0), stab)

        def play(t, day, source, session, pos):
            nonlocal ev_id
            kn = k_now(t, day)
            multi = source == "quiz" and rng.random() < 0.4
            guess = 0.10 if multi else 0.25
            rushed = rng.random() < rush * (1.4 - kn)
            leaves = int(rng.poisson(0.12 + (1 - kn) * 0.3))
            hint = (not multi) and source == "quiz" and kn < 0.5 and rng.random() < 0.35
            if rushed:
                p = guess
                t_sec = float(rng.uniform(2, 7.5))
            else:
                g = 0.5 if hint else guess
                p = g + (1 - g - slip) * kn
                if multi:
                    p *= 0.88
                if leaves > 0:
                    p = min(0.97, p + 0.12)
                mean_t = (38 - 16 * kn) * (1.35 if multi else 1.0)
                t_sec = float(np.clip(rng.lognormal(np.log(mean_t), 0.45), 6, 240))
                if leaves > 0:
                    t_sec += float(rng.uniform(5, 40))
            p = float(np.clip(p, 0.02, 0.98))
            correct = int(rng.random() < p)
            events.append(dict(event_id=ev_id, student_id=sid, semester=sem, day=round(day, 4), topic=t, module=module_of[t],
                               source=source, session_id=session, q_in_session=pos, question_type="multi" if multi else "single",
                               correct=correct, time_sec=round(t_sec, 1), hint_used=int(hint), tab_leaves=leaves))
            truth.append(dict(event_id=ev_id, gt_knowledge=round(kn, 4), gt_p_correct=round(p, 4)))
            ev_id += 1
            seen_acc[t][0] += correct
            seen_acc[t][1] += 1
            # learning
            if not rushed:
                factor = (1.0 if correct else 0.45) * (0.5 if hint else 1.0) * (0.5 if leaves > 0 else 1.0)
                new = kn + alpha * factor * (1 - kn)
                k[t] = float(np.clip(new, 0.02, 0.99))
                for o in names:
                    if o != t and module_of[o] == module_of[t]:
                        k[o] = float(np.clip(k[o] + 0.05 * alpha * factor * (1 - k[o]), 0.02, 0.99))
            else:
                k[t] = kn
            last_day[t] = day

        # diagnostic: day 0, one question per topic
        order = list(rng.permutation(names))
        for pos, t in enumerate(order):
            play(t, 0.0 + pos * 0.0004, "diagnostic", f"{sid}-D", pos)
        for t in names:
            nsess[t] = 0

        # practice days
        sess_no = 0
        for day in range(1, horizon + 1):
            if rng.random() > engage * 0.9:
                continue
            if rng.random() < picks_weak:
                est = sorted(names, key=lambda x: (seen_acc[x][0] + 0.8) / (seen_acc[x][1] + 2))
                t = est[int(rng.integers(0, min(3, len(est))))]
            else:
                t = names[int(rng.integers(0, len(names)))]
            sess_no += 1
            start = day + float(rng.uniform(0.2, 0.8))
            sid_s = f"{sid}-Q{sess_no}"
            for q in range(QUESTIONS_PER_QUIZ):
                play(t, start + q * 0.002, "quiz", sid_s, q)
            nsess[t] += 1

        # exam day: hidden truth for every topic, used to test "predict exam performance"
        exam_day = horizon + EXAM_GAP_DAYS
        total = 0.0
        for t in names:
            kn = k_now(t, exam_day)
            p = float(np.clip(0.25 + (0.75 - slip) * kn, 0.02, 0.98))
            exam_rows.append(dict(student_id=sid, topic=t, day=exam_day, gt_knowledge=round(kn, 4), gt_p_correct=round(p, 4)))
            total += p
        students[-1]["exam_true_score"] = round(100 * total / len(names), 2)

    pd.DataFrame(events).to_csv(os.path.join(DATA, "synthetic_events.csv"), index=False)
    pd.DataFrame(truth).to_csv(os.path.join(DATA, "synthetic_ground_truth.csv"), index=False)
    pd.DataFrame(students).to_csv(os.path.join(DATA, "synthetic_students.csv"), index=False)
    pd.DataFrame(exam_rows).to_csv(os.path.join(DATA, "synthetic_exam_truth.csv"), index=False)
    ev = pd.DataFrame(events)
    print(f"students {ev.student_id.nunique()}, events {len(ev)}, quiz sessions {ev[ev.source == 'quiz'].session_id.nunique()}")
    print(f"overall accuracy {ev.correct.mean():.3f}, diagnostic {ev[ev.source == 'diagnostic'].correct.mean():.3f}, quiz {ev[ev.source == 'quiz'].correct.mean():.3f}")


if __name__ == "__main__":
    main()
