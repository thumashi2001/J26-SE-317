"""What-if forecast for one topic (Component 1).

Two futures are simulated day by day with the same forgetting and update rules the twin
already uses, so the forecast and the real twin can never disagree:
  - "nothing":  the student stops practising, the score only fades.
  - "plan":     the student practises a fixed number of times per week.

A practice session is one answered question. We cannot know in advance whether it will be right,
so the score moves by its EXPECTED value:
    new = faded + LEARN_RATE * (accuracy * 100 - faded)
This is exactly the average of the "correct" and "wrong" updates, weighted by accuracy.
"""
from services.forgetting.decay import apply_decay

LEARN_RATE = 0.25     # must match services/mastery/calculator.py
MIN_ACCURACY = 0.6    # a student who practises is assumed to get at least 60% right
WEAK_BELOW = 30
MAX_DAYS = 120


def assumed_accuracy(correct, answered):
    """The student's own accuracy so far, smoothed, and never below MIN_ACCURACY."""
    smoothed = (correct + 0.8) / (answered + 2)
    return round(max(MIN_ACCURACY, smoothed), 2)


def _practice_days(days_ahead, per_week):
    """Evenly spaced practice days from tomorrow to the exam day."""
    if per_week <= 0:
        return []
    gap = 7.0 / per_week
    days, d = [], gap
    while d <= days_ahead + 1e-9:
        days.append(int(round(d)))
        d += gap
    return sorted(set(x for x in days if 1 <= x <= days_ahead))


def _run(score, days_since_last, sessions, practice_days, days_ahead, accuracy):
    """Score on each day 0..days_ahead. Day 0 is today."""
    last_day = -days_since_last          # the stored score belongs to the day it was last practised
    stored = score
    n = sessions
    series = []
    pset = set(practice_days)
    for day in range(0, days_ahead + 1):
        if day in pset:
            faded = apply_decay(stored, day - last_day, n)
            stored = round(faded + LEARN_RATE * (accuracy * 100 - faded), 1)
            n += 1
            last_day = day
        series.append(apply_decay(stored, day - last_day, n))
    return series


def forecast(score, days_since_last, sessions, correct, answered, days_ahead, per_week):
    days_ahead = max(1, min(int(days_ahead), MAX_DAYS))
    per_week = max(0, min(int(per_week), 14))
    accuracy = assumed_accuracy(correct, answered)
    plan_days = _practice_days(days_ahead, per_week)

    nothing = _run(score, days_since_last, sessions, [], days_ahead, accuracy)
    plan = _run(score, days_since_last, sessions, plan_days, days_ahead, accuracy)

    def below_weak(series):
        for d, v in enumerate(series):
            if v < WEAK_BELOW:
                return d
        return None

    return {
        "days_ahead": days_ahead,
        "sessions_per_week": per_week,
        "assumed_accuracy": accuracy,
        "today": nothing[0],
        "practice_days": plan_days,
        "nothing": {"series": nothing, "exam_day": nothing[-1], "first_weak_day": below_weak(nothing)},
        "plan": {"series": plan, "exam_day": plan[-1], "first_weak_day": below_weak(plan)},
        "gain": round(plan[-1] - nothing[-1], 1),
    }
