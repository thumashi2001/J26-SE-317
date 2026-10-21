"""Orchestrate smoke / full SE simulation runs (no ASSISTments artifacts required)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .catalogue import catalogue_hash, catalogue_payload
from .config import (
    FULL_SEEDS,
    FULL_TIMESTEPS,
    SMOKE_SEEDS,
    SMOKE_TIMESTEPS,
    SeEnvConfig,
    frozen_config_dict,
)
from .evaluate import compare_validation, final_test_evaluation
from .export_bundle import export_se_bundle
from .observation import observation_schema
from .paths import ensure_dir, new_run_dir
from .protocol import protocol_manifest
from .provenance import write_json
from .train_rl import train_maskable_ppo


def run_training_and_validation(
    artifacts_root: Path | str,
    *,
    mode: str = "smoke",
    timesteps: int | None = None,
    seeds: list[int] | None = None,
    eval_episodes: int = 10,
    device: str = "cpu",
    cfg: SeEnvConfig | None = None,
    run_full: bool = False,
) -> dict[str, Any]:
    """
    mode='smoke': small budget, one seed.
    mode='full': requires run_full=True explicit flag; >=3 seeds.
    """
    cfg = cfg or SeEnvConfig()
    cfg.validate()
    if mode == "smoke":
        ts = int(timesteps if timesteps is not None else SMOKE_TIMESTEPS)
        seed_list = list(seeds if seeds is not None else SMOKE_SEEDS)
    elif mode == "full":
        if not run_full:
            raise RuntimeError(
                "Full SE training requires explicit run_full=True "
                "(notebook flag RUN_FULL_TRAINING). Refusing to start."
            )
        ts = int(timesteps if timesteps is not None else FULL_TIMESTEPS)
        seed_list = list(seeds if seeds is not None else FULL_SEEDS)
        if len(seed_list) < 3:
            raise ValueError("full mode requires at least three training seeds")
    else:
        raise ValueError(mode)

    root = ensure_dir(artifacts_root)
    run_dir = new_run_dir(root, mode)
    write_json(run_dir / "protocol.json", protocol_manifest())
    write_json(run_dir / "topic_catalogue.json", {**catalogue_payload(), "sha256": catalogue_hash()})
    write_json(run_dir / "observation_schema.json", observation_schema(cfg))
    write_json(run_dir / "train_config.json", frozen_config_dict(cfg))

    model_paths: dict[int, Path] = {}
    train_metas = []
    for s in seed_list:
        seed_dir = run_dir / f"seed_{s}" / "maskable_ppo"
        meta = train_maskable_ppo(
            seed_dir, timesteps=ts, seed=s, device=device, cfg=cfg
        )
        train_metas.append(meta)
        model_paths[s] = seed_dir / "maskable_ppo_final.zip"

    selection = compare_validation(
        run_dir=run_dir,
        train_seeds=seed_list,
        n_episodes=eval_episodes,
        cfg=cfg,
        model_paths=model_paths,
    )
    # Freeze selection marker
    write_json(
        run_dir / "SELECTION_FROZEN.json",
        {
            "frozen": True,
            "selected": selection["selected"],
            "path": "selection_val.json",
        },
    )

    export_dir = run_dir / "export_bundle"
    export_se_bundle(
        export_dir=export_dir,
        run_dir=run_dir,
        cfg=cfg,
        selected_algorithm=selection["selected"],
        model_paths=model_paths,
        selection=selection,
        include_final_test=False,
    )
    return {
        "run_dir": str(run_dir),
        "export_dir": str(export_dir),
        "selection": selection,
        "model_paths": {str(k): str(v) for k, v in model_paths.items()},
        "train_metas": train_metas,
        "mode": mode,
    }


def run_final_evaluation(
    run_dir: Path | str,
    *,
    run_final: bool = False,
    eval_episodes: int = 10,
    cfg: SeEnvConfig | None = None,
) -> dict[str, Any]:
    if not run_final:
        raise RuntimeError(
            "Final simulator evaluation requires explicit run_final=True "
            "(notebook flag RUN_FINAL_EVALUATION) after selection is frozen."
        )
    run_dir = Path(run_dir)
    cfg = cfg or SeEnvConfig()
    selection_path = run_dir / "selection_val.json"
    frozen = run_dir / "SELECTION_FROZEN.json"
    if not frozen.is_file():
        raise FileNotFoundError(f"Missing {frozen}; freeze validation selection first.")

    # Discover model paths
    model_paths: dict[int, Path] = {}
    for p in sorted(run_dir.glob("seed_*/maskable_ppo/maskable_ppo_final.zip")):
        seed = int(p.parts[-3].split("_")[1])
        model_paths[seed] = p
    if not model_paths:
        raise FileNotFoundError("No maskable_ppo_final.zip under run_dir")

    seeds = sorted(model_paths.keys())
    plan = final_test_evaluation(
        run_dir=run_dir,
        train_seeds=seeds,
        n_episodes=eval_episodes,
        cfg=cfg,
        model_paths=model_paths,
        selection_path=selection_path,
    )
    # Refresh export with final metrics
    import json

    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    export_se_bundle(
        export_dir=run_dir / "export_bundle",
        run_dir=run_dir,
        cfg=cfg,
        selected_algorithm=selection.get("selected", "maskable_ppo"),
        model_paths=model_paths,
        selection=selection,
        include_final_test=True,
    )
    return plan
