"""Forgetting-curve decay (Ebbinghaus-style exponential) for Component 1."""
import math

FLOOR = 0.35            # knowledge never fades fully to zero
BASE_STABILITY = 14.0   # days; how slowly memory fades with no extra practice
STABILITY_GAIN = 0.6    # each practice session makes the memory last longer


def apply_decay(score, days_since_practice, practice_sessions=0):
    """Return the score after forgetting. score is 0-100."""
    stability = BASE_STABILITY * (1 + STABILITY_GAIN * practice_sessions)
    retention = math.exp(-max(days_since_practice, 0) / stability)
    return round(score * (FLOOR + (1 - FLOOR) * retention), 1)