"""Colab entry for se-path-multi-v2. Not invoked by smoke tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .evaluate import compare_validation, frozen_test
from .export_bundle import write_full_export
from .objective import FULL_SEEDS, FULL_TIMESTEPS, TRAINING_REVISION, VAL_EPISODES
from .train_rl import train_maskable_ppo


def run_full(parent: Path, *, timesteps: int = FULL_TIMESTEPS, episodes: int = VAL_EPISODES) -> dict:
    if int(timesteps) < 10_000:
        raise RuntimeError("full run refuses a smoke-sized budget")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out_dir = Path(parent) / f"{TRAINING_REVISION}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    seed_dirs: dict[int, Path] = {}
    for seed in FULL_SEEDS:
        folder = out_dir / "seeds" / f"seed_{seed}"
        trained = train_maskable_ppo(folder, timesteps=int(timesteps), seed=seed)
        del trained["model"]
        seed_dirs[seed] = folder
    selection = compare_validation(
        model_paths={seed: seed_dirs[seed] / "maskable_ppo_final.zip" for seed in FULL_SEEDS},
        seeds=FULL_SEEDS,
        episodes=episodes,
    )
    chosen = int(selection["selected_seed"])
    held_out = frozen_test(
        model_path=seed_dirs[chosen] / "maskable_ppo_final.zip",
        seed=chosen,
        episodes=episodes,
    )
    manifest = write_full_export(
        out_dir / "export",
        seed_dirs=seed_dirs,
        selection=selection,
        final_test=held_out,
        timesteps=int(timesteps),
    )
    manifest["run_dir"] = str(out_dir)
    print(
        "criterion_met",
        manifest["criterion_met"],
        "activation_allowed",
        manifest["activation_allowed"],
        "serves_students",
        False,
        "run_dir",
        out_dir,
    )
    return manifest
