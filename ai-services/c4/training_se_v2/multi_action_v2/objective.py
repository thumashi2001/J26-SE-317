"""Frozen se-path-multi-v2 objective. Defined before training.

Primary outcome: synthetic mean mastery change on topics available at episode
start. That is an assumption of the simulator, not a measured student gain.

Reward: the actual post-clip mastery change of the selected topic, for
practice, revision and quiz. There is no correctness bonus and no payment
for an intended gain that clipping removed.

se-path-multi-v1 is unchanged historical evidence. Its quiz term
(correctness minus 0.5) and its revision term (intended 0.04) are not used.
"""

from __future__ import annotations

PROTOCOL = "se-path-multi-v2"
REWARD_DEFINITION_VERSION = "se-path-multi-v2-reward-1"
HISTORICAL_PROTOCOL = "se-path-multi-v1"

PRIMARY_METRIC = "mean_mastery_change"
PRIMARY_DEFINITION = (
    "Mean, over topics available at episode start, of final mastery minus "
    "initial mastery. Synthetic. Not accuracy, not a real-student effect."
)
WEAKEST_TOPIC_DEFINITION = (
    "Mastery change of the available topic with the lowest mastery at episode start."
)
RETURN_DEFINITION = (
    "Sum of actual clipped mastery changes, plus -0.2 for an invalid action. "
    "Not accuracy. Not the se-path-multi-v1 return."
)
NO_PROGRESS_DEFINITION = (
    "Share of valid steps whose clipped mastery change on the selected topic is 0."
)
COMPLETION_DEFINITION = (
    "Valid simulator steps. Not verified student completion and not self-report."
)

# Same action budget as v1. No per-type duration exists, so comparisons are per action.
EPISODE_STEPS = 40
ACTION_DURATION_STEPS = 1
COMPARISON_UNIT = "per_action_equal_step_budget"

FULL_TIMESTEPS = 80_000
FULL_SEEDS = (0, 1, 2)
VAL_EPISODES = 20
TEST_EPISODES = 20
SMOKE_TIMESTEPS = 128
# Corrects single-semester seeds. Does not change the reward or the acceptance thresholds.
TRAINING_REVISION = "se-path-multi-v2-coverage-r2"
TRAINING_SCHEDULE = (
    "Every seed alternates episodes: even index Y3S1, odd index Y3S2. "
    "Separate single-semester seeds are not combined training."
)

# Disjoint from validation (81xxx/82xxx), held-out test (91xxx/92xxx),
# and the retired per-seed streams 51xxx and 71xxx.
def training_semester(episode_index: int) -> str:
    return "Y3S1" if int(episode_index) % 2 == 0 else "Y3S2"


def training_episode_rng_seed(train_seed: int, episode_index: int) -> int:
    return 11_000_000 + int(train_seed) * 100_000 + int(episode_index)


def val_scenario_seed(semester: str, episode: int) -> int:
    """Common bank. The same scenarios are used for every candidate seed."""
    if semester == "Y3S1":
        return 81_000 + int(episode)
    if semester == "Y3S2":
        return 82_000 + int(episode)
    raise ValueError(semester)


def heldout_scenario_seed(semester: str, episode: int) -> int:
    if semester == "Y3S1":
        return 91_000 + int(episode)
    if semester == "Y3S2":
        return 92_000 + int(episode)
    raise ValueError(semester)


VAL_RANDOM_SEED = 83_017
TEST_RANDOM_SEED = 93_017


def coverage_complete(semesters: dict) -> bool:
    for name in ("Y3S1", "Y3S2"):
        block = semesters.get(name) or {}
        if int(block.get("episodes") or 0) < 1 or int(block.get("steps") or 0) < 1:
            return False
    return True


def coverage_balanced(semesters: dict, *, min_share: float = 0.25) -> bool:
    """Full-run check. A single stray episode of the other semester is not enough."""
    if not coverage_complete(semesters):
        return False
    total = sum(int((semesters.get(name) or {}).get("steps") or 0) for name in ("Y3S1", "Y3S2"))
    if total < 10_000:
        return False
    return all(int(semesters[name]["steps"]) / total >= min_share for name in ("Y3S1", "Y3S2"))


SELECTION_RULE = (
    "Highest mean of Y3S1 and Y3S2 validation mean_mastery_change on the common "
    "scenario bank (Y3S1 seeds 81000+episode, Y3S2 seeds 82000+episode), shared "
    "by every candidate. Ties use the lowest seed. The held-out bank is not used."
)
# Floor, not a demand that PPO beat the best rule. random_valid is reported only.
CRITERION_BASELINES = ("weakest_practice", "recent_performance", "weakest_multi")
ACCEPTANCE_RULE = (
    "On validation only, the selected seed must have invalid_action_rate mean 0 "
    "in both semesters, and mean_mastery_change at least the lowest of "
    "weakest_practice, recent_performance and weakest_multi on that same split. "
    "Passing is not real-student validation and does not by itself switch the live app. "
    "Failing leaves activation_allowed false."
)


def criterion_met(validation: dict) -> bool:
    seed = str(validation["selected_seed"])
    for semester in ("Y3S1", "Y3S2"):
        block = validation["by_seed"][seed][semester]
        ppo = block["maskable_ppo"]
        if float(ppo["invalid_action_rate"]["mean"]) != 0.0:
            return False
        floor = min(float(block[name]["mean_mastery_change"]["mean"]) for name in CRITERION_BASELINES)
        if float(ppo["mean_mastery_change"]["mean"]) + 1e-9 < floor:
            return False
    return True
