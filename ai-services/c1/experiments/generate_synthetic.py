"""
Synthetic learning-event generator for Component 1 (Cognitive Digital Twin).
Simulates students with HIDDEN knowledge that grows with practice and fades over time.
The app can only observe answers, hints and timing, never the hidden state.
Outputs go to ai-services/c1/datasets/raw/
"""
import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
N_STUDENTS = 600
EXAM_DAY = 90
GUESS, SLIP = 0.25, 0.08
FLOOR = 0.35

TOPICS = {
    "Y3S1": ["sdlc_models", "quality_assurance", "process_metrics",
             "distributed_transactions", "consistency_models", "microservices",
             "architectural_patterns", "quality_attributes", "design_tradeoffs",
             "mvc_architecture", "orm_frameworks", "dependency_injection"],
    "Y3S2": ["usability_heuristics", "user_research_methods", "prototyping",
             "normalization", "indexing", "query_optimization",
             "case_analysis_techniques", "industry_case_studies", "lessons_learned",
             "risk_management", "estimation", "agile_planning"],
}


def knowledge(m, gap_days, stability):
    retention = np.exp(-gap_days / stability)
    return m * (FLOOR + (1 - FLOOR) * retention)


def simulate(n_students=N_STUDENTS, seed=SEED):
    rng = np.random.default_rng(seed)
    answers, students = [], []

    for i in range(n_students):
        sid = f"SYN{i + 1:04d}"
        semester = "Y3S1" if i % 2 == 0 else "Y3S2"
        topics = TOPICS[semester]

        ability = rng.normal(0, 1)
        engagement = rng.beta(2.5, 2)
        hint_tendency = rng.beta(2, 4)
        procrastinator = rng.random() < 0.30

        m = np.clip(0.25 + 0.12 * ability + rng.normal(0, 0.05, len(topics)), 0.02, 0.6)
        n_sessions = np.zeros(len(topics))
        last_day = np.zeros(len(topics))
        base_stability = 6 * np.exp(0.25 * ability)
        learn_rate = 0.10 * np.exp(0.2 * ability)

        session_id = 0
        for day in range(1, EXAM_DAY):
            weekly = 1 + 4 * engagement
            if procrastinator:
                weekly *= 0.3 if day < 63 else 2.5
            if rng.random() > min(0.9, weekly / 7):
                continue

            session_id += 1
            t = int(rng.integers(len(topics)))
            stability = base_stability * (1 + 0.6 * n_sessions[t])
            for _ in range(3):
                k = knowledge(m[t], day - last_day[t], stability)
                hint = rng.random() < hint_tendency * (1 - k)
                p = GUESS + (1 - GUESS - SLIP) * k + (0.15 if hint else 0.0)
                correct = rng.random() < min(p, 0.97)
                time_sec = float(np.clip(rng.lognormal(3.4 - 0.8 * k, 0.4), 5, 300))
                answers.append((sid, semester, day, session_id, topics[t], int(correct), int(hint), round(time_sec, 1)))
                m[t] += learn_rate * (1 - m[t]) * (0.5 if hint else 1.0)
            n_sessions[t] += 1
            last_day[t] = day

        correct_total, total = 0, 0
        for t in range(len(topics)):
            stability = base_stability * (1 + 0.6 * n_sessions[t])
            k = knowledge(m[t], EXAM_DAY - last_day[t], stability)
            p = GUESS + (1 - GUESS - SLIP) * k
            correct_total += rng.binomial(5, p)
            total += 5
        exam = correct_total / total
        students.append((sid, semester, round(exam, 4), int(exam < 0.5)))

    ans = pd.DataFrame(answers, columns=["student_id", "semester", "day", "session_id", "topic",
                                         "correct", "hint_used", "time_sec"])
    stu = pd.DataFrame(students, columns=["student_id", "semester", "exam_score", "at_risk"])
    return ans, stu


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "datasets" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    ans, stu = simulate()
    ans.to_csv(out / "synthetic_answers.csv", index=False)
    stu.to_csv(out / "synthetic_students.csv", index=False)
    print(f"{len(stu)} students, {len(ans)} answer events")
    print(f"at-risk rate: {stu.at_risk.mean():.1%}, mean exam score: {stu.exam_score.mean():.1%}")
    print(f"saved to {out}")