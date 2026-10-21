"""MaskablePPO training for se-path-sim-v0 (masks in learn + predict)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import SeEnvConfig
from .environment import make_env
from .paths import ensure_dir
from .protocol import PROTOCOL_VERSION
from .provenance import synthetic_banner, utc_now, write_json


def maskable_ppo_available() -> bool:
    try:
        import sb3_contrib  # noqa: F401

        return True
    except ImportError:
        return False


def _versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in (
        "numpy",
        "gymnasium",
        "stable_baselines3",
        "sb3_contrib",
        "torch",
    ):
        try:
            mod = __import__(name)
            out[name] = getattr(mod, "__version__", "unknown")
        except ImportError:
            out[name] = "missing"
    return out


def train_maskable_ppo(
    out_dir: Path,
    *,
    timesteps: int,
    seed: int,
    device: str = "cpu",
    cfg: SeEnvConfig | None = None,
    checkpoint_freq: int = 1000,
) -> dict[str, Any]:
    if not maskable_ppo_available():
        raise ImportError("sb3-contrib required for MaskablePPO")
    from sb3_contrib import MaskablePPO
    from stable_baselines3.common.callbacks import CheckpointCallback
    from stable_baselines3.common.monitor import Monitor

    cfg = cfg or SeEnvConfig()
    cfg.validate()
    ensure_dir(out_dir)
    env = Monitor(make_env(cfg, scenario="sim_train", seed=seed))
    assert hasattr(env.unwrapped, "action_masks")
    model = MaskablePPO(
        "MlpPolicy",
        env,
        learning_rate=3e-4,
        n_steps=min(256, max(64, timesteps // 4)),
        batch_size=64,
        n_epochs=5,
        gamma=0.99,
        verbose=0,
        seed=seed,
        device=device,
    )
    ckpt = CheckpointCallback(
        save_freq=max(1, checkpoint_freq),
        save_path=str(out_dir / "checkpoints"),
        name_prefix="maskable_ppo",
    )
    model.learn(total_timesteps=int(timesteps), callback=ckpt, use_masking=True)
    # SB3 may stop slightly above requested budget; record both.
    actual = int(getattr(model, "num_timesteps", timesteps))
    path = out_dir / "maskable_ppo_final.zip"
    model.save(str(path))
    env.close()
    meta = synthetic_banner(
        algorithm="maskable_ppo",
        seed=seed,
        requested_timesteps=int(timesteps),
        actual_timesteps=actual,
        device=device,
        checkpoint=str(path),
        created_at_utc=utc_now(),
        protocol=PROTOCOL_VERSION,
        versions=_versions(),
        masks_in_training=True,
        masks_in_evaluation=True,
    )
    write_json(out_dir / "train_meta.json", meta)
    return meta
