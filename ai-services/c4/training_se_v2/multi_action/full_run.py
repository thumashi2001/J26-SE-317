"""Colab full run. Not invoked by local smoke or parity tests."""

from __future__ import annotations

from pathlib import Path

from .evaluate import compare_validation, frozen_test
from .export_bundle import write_full_export
from .train_rl import FULL_SEEDS, FULL_TIMESTEPS, train_maskable_ppo


def run_full(out_dir: Path, *, timesteps: int = FULL_TIMESTEPS, episodes: int = 20) -> dict:
    if int(timesteps) < 10_000:
        raise RuntimeError("full run refuses a smoke-sized budget")
    out_dir = Path(out_dir)
    seed_dirs: dict[int, Path] = {}
    for seed in FULL_SEEDS:
        folder = out_dir / "seeds" / f"seed_{seed}"
        # Alternate the reset semester by seed so both semesters appear in training.
        semester = "Y3S1" if seed % 2 == 0 else "Y3S2"
        train_maskable_ppo(folder, timesteps=int(timesteps), seed=seed, semester=semester)
        seed_dirs[seed] = folder
    selection = compare_validation(
        model_paths={s: seed_dirs[s] / "maskable_ppo_final.zip" for s in FULL_SEEDS},
        seeds=FULL_SEEDS,
        episodes=episodes,
    )
    chosen = int(selection["selected_seed"])
    held_out = frozen_test(
        model_path=seed_dirs[chosen] / "maskable_ppo_final.zip",
        seed=chosen,
        episodes=episodes,
    )
    return write_full_export(
        out_dir / "export",
        seed_dirs=seed_dirs,
        selection=selection,
        final_test=held_out,
        timesteps=int(timesteps),
    )
