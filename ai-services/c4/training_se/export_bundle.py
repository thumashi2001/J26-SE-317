"""Export simulation-only SE path artifacts with SHA-256 manifest."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .catalogue import catalogue_hash, catalogue_payload
from .config import SeEnvConfig, frozen_config_dict
from .observation import observation_schema
from .protocol import protocol_manifest
from .provenance import sha256_file, synthetic_banner, utc_now, write_json


def export_se_bundle(
    *,
    export_dir: Path | str,
    run_dir: Path | str,
    cfg: SeEnvConfig,
    selected_algorithm: str,
    model_paths: dict[int, Path],
    selection: dict[str, Any] | None,
    include_final_test: bool = False,
) -> Path:
    out = Path(export_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_dir = Path(run_dir)

    write_json(out / "topic_catalogue.json", {**catalogue_payload(), "sha256": catalogue_hash()})
    write_json(out / "observation_schema.json", observation_schema(cfg))
    write_json(out / "protocol.json", protocol_manifest())
    write_json(out / "train_config.json", frozen_config_dict(cfg))
    write_json(
        out / "synthetic_provenance.json",
        synthetic_banner(
            exported_at_utc=utc_now(),
            source_run=str(run_dir),
            readiness_claims=False,
            pass_probability_claims=False,
            production_integration=False,
            label="simulation_only",
        ),
    )

    models_dir = out / "models"
    models_dir.mkdir(exist_ok=True)
    for seed, mp in model_paths.items():
        dest = models_dir / f"seed_{seed}"
        dest.mkdir(exist_ok=True)
        if mp.is_file():
            shutil.copy2(mp, dest / "maskable_ppo_final.zip")

    if selection is not None:
        write_json(out / "selection_val.json", selection)
        write_json(out / "comparison_val.json", selection)

    final_src = run_dir / "final_simulator_test"
    if include_final_test and final_src.is_dir():
        dest_f = out / "final_simulator_test"
        if dest_f.exists():
            shutil.rmtree(dest_f)
        shutil.copytree(final_src, dest_f)

    card = _model_card(cfg, selected_algorithm, selection)
    (out / "MODEL_CARD_SE_SIM.md").write_text(card, encoding="utf-8")

    # Manifest
    sha: dict[str, str] = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            rel = path.relative_to(out).as_posix()
            sha[rel] = sha256_file(path)
    manifest = synthetic_banner(
        selected_algorithm=selected_algorithm,
        sha256=sha,
        catalogue_hash=catalogue_hash(),
        exported_at_utc=utc_now(),
    )
    write_json(out / "manifest.json", manifest)
    # Re-hash manifest excluded; done.
    return out


def _model_card(cfg: SeEnvConfig, selected: str, selection: dict | None) -> str:
    lines = [
        "# Model card — SE path simulation (se-path-sim-v0)",
        "",
        "**Simulation only.** Not measured SE student behaviour. No readiness/pass-probability claims.",
        "",
        f"- Protocol: `se-path-sim-v0`",
        f"- Selected (validation): `{selected}`",
        f"- Actions: 12 C1 practice topics (see topic_catalogue.json)",
        f"- Observation dim: 28 (mastery×12 + availability×12 + 4)",
        f"- Forgetting: **none** (explicit v0 default)",
        f"- Max episode steps: {cfg.max_episode_steps}",
        "",
        "Do not integrate automatically into production. Heuristic Node path remains separate.",
        "",
    ]
    if selection and "mean_val_return_by_algorithm" in selection:
        lines.append("## Validation return (mean ± sample SD across seeds)")
        for k, v in selection["mean_val_return_by_algorithm"].items():
            lines.append(f"- `{k}`: {v.get('mean'):.4f} ± {v.get('sample_sd'):.4f}")
        lines.append("")
    return "\n".join(lines) + "\n"
