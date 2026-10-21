"""Local smoke for se-path-sim-v2 observation contract (no full training)."""

from __future__ import annotations

import numpy as np

from training_se_v1.catalogue import N_TOPICS
from training_se_v2.observation import OBS_DIM, PROTOCOL, build_observation, observation_schema


def main() -> None:
    schema = observation_schema()
    assert schema["protocol"] == PROTOCOL
    assert schema["dim"] == OBS_DIM
    assert schema["extras_names"][-1] == "episode_init_mean_mastery"
    assert "prior_strength" not in schema["extras_names"]

    mastery = np.full(N_TOPICS, 0.4, dtype=np.float32)
    available = np.ones(N_TOPICS, dtype=np.float32)
    obs = build_observation(
        mastery,
        available,
        elapsed_env_steps=3,
        max_episode_steps=40,
        episode_init_mean_mastery=0.42,
        mastery_threshold=0.8,
    )
    assert obs.shape == (OBS_DIM,)
    assert abs(float(obs[-1]) - 0.42) < 1e-6
    assert abs(float(obs[-2]) - 3 / 40) < 1e-6
    print("OK", PROTOCOL, "dim", OBS_DIM, "extras", schema["extras_names"])


if __name__ == "__main__":
    main()
