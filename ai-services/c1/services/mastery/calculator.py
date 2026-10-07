"""Mastery scoring for Component 1: diagnostic scoring and per-event updates."""
from collections import defaultdict

PRIOR_STRENGTH = 2      # pseudo-answers that pull small samples towards the prior
PRIOR_ACCURACY = 0.4    # a student with no evidence starts a little below the middle
LEARN_RATE = 0.25       # how much one new answer moves the score (recent answers count more)
HINT_WEIGHT = 0.5       # a correct answer given with a hint counts half as much


def score_diagnostic(answers):
    """
    answers: list of dicts with keys: topic, correct (bool)
    returns: {topic: {"score": 0-100, "answered": n, "correct": c}}
    """
    tally = defaultdict(lambda: [0, 0])  # topic -> [correct, total]
    for a in answers:
        tally[a["topic"]][1] += 1
        if a["correct"]:
            tally[a["topic"]][0] += 1
    result = {}
    for topic, (c, n) in tally.items():
        acc = (c + PRIOR_STRENGTH * PRIOR_ACCURACY) / (n + PRIOR_STRENGTH)
        result[topic] = {"score": round(acc * 100, 1), "answered": n, "correct": c}
    return result


def update_score(current_score, correct, hint_used=False):
    """Move a topic score towards 100 (correct) or 0 (wrong). Recent answers count most."""
    target = 100.0 if correct else 0.0
    rate = LEARN_RATE * (HINT_WEIGHT if (hint_used and correct) else 1.0)
    return round(current_score + rate * (target - current_score), 1)