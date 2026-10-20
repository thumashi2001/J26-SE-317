"""Validation-only sensitivity audit of learning/forgetting assumptions.

Historical ``c4-env-eval-v1.1`` defaults are **not** modified here.
Hypothetical dynamics are evaluated as transfer/sensitivity settings only.

Declare the parameter grid first (``DECLARED_SENSITIVITY_GRID``), then execute
every setting and report all results — do not cherry-pick favourable cells.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .baselines import (
    COMPARISON_LABELS,
    RandomValidBaseline,
    RecentPerformanceBaseline,
    WeakestMasteryBaseline,
    rollout_policy,
)
from .config import EnvConfig
from .environment import make_env
from .paths import ensure_dir
from .protocol import ENV_PROTOCOL_VERSION, val_episode_seed
from .provenance import utc_now, write_json
from .simulator import Simulator
from .train_rl import summarise

# Separate version for *proposed* semantic changes — not applied to default EnvConfig.
DYNAMICS_PROPOSAL_VERSION = "c4-sim-dynamics-proposal-v1"

# Known Colab Drive locations for the real-data-backed forgetting audit.
COLAB_DRIVE_RUNS_ROOT = "/content/drive/MyDrive/AdaptiveLearnSE/c4_runs"
COLAB_ARTIFACTS_DIR = f"{COLAB_DRIVE_RUNS_ROOT}/artifacts"
COLAB_V11_SMOKE_RUN_DIR = (
    f"{COLAB_DRIVE_RUNS_ROOT}/"
    "train_smoke_c4-env-eval-v1.1_20261012T044411.975097+0000"
)
# MaskablePPO in that smoke run was trained with seed 42.
COLAB_MASKABLE_TRAIN_SEED = 42

# ---------------------------------------------------------------------------
# DECLARED PARAMETER GRID (frozen before execution)
# ---------------------------------------------------------------------------
# All rows are evaluated. Labels mark which row is the unchanged v1.1 default
# versus explicitly hypothetical alternatives.
DECLARED_SENSITIVITY_GRID: tuple[dict[str, Any], ...] = (
    {
        "setting_id": "v1_1_current_default",
        "label": "Unchanged c4-env-eval-v1.1 default (current)",
        "hypothetical": False,
        "assumed_mastery_gain_correct": 0.08,
        "assumed_mastery_gain_incorrect": 0.02,
        "assumed_forgetting_per_step": 0.005,
        "notes": "Practice-interference forgetting on non-selected skills each valid step.",
    },
    {
        "setting_id": "no_forgetting_control",
        "label": "Hypothetical control: no forgetting",
        "hypothetical": True,
        "assumed_mastery_gain_correct": 0.08,
        "assumed_mastery_gain_incorrect": 0.02,
        "assumed_forgetting_per_step": 0.0,
        "notes": "Removes interference decay; gains accumulate without cross-skill penalty.",
    },
    {
        "setting_id": "half_forgetting",
        "label": "Hypothetical: forgetting 0.0025 (half of default)",
        "hypothetical": True,
        "assumed_mastery_gain_correct": 0.08,
        "assumed_mastery_gain_incorrect": 0.02,
        "assumed_forgetting_per_step": 0.0025,
        "notes": "Weaker practice interference.",
    },
    {
        "setting_id": "break_even_forgetting_20skills",
        "label": "Hypothetical: forgetting 0.004 (correct answer break-even at K=20)",
        "hypothetical": True,
        "assumed_mastery_gain_correct": 0.08,
        "assumed_mastery_gain_incorrect": 0.02,
        "assumed_forgetting_per_step": 0.004,
        "notes": (
            "For K=20, correct net total ≈ 0.08 - 19*0.004 = 0.004 > 0; "
            "chosen as a near break-even interference scale, not fitted from data."
        ),
    },
    {
        "setting_id": "time_like_forgetting_note_only_same_as_default",
        "label": (
            "Documentation control: same numbers as default "
            "(elapsed-time decay is NOT implemented; see notes)"
        ),
        "hypothetical": True,
        "assumed_mastery_gain_correct": 0.08,
        "assumed_mastery_gain_incorrect": 0.02,
        "assumed_forgetting_per_step": 0.005,
        "notes": (
            "Placeholder row emphasising that true calendar-time forgetting "
            "(decay on every env step including invalid) is a different mechanism "
            "and is not silently enabled in this audit."
        ),
        "skip_rollout_duplicate_of": "v1_1_current_default",
    },
)


@dataclass(frozen=True)
class NetMasteryArithmetic:
    n_skills: int
    gain_correct: float
    gain_incorrect: float
    forgetting_per_other_skill: float

    @property
    def n_other(self) -> int:
        return max(0, self.n_skills - 1)

    @property
    def forgetting_mass_per_valid_step(self) -> float:
        return self.n_other * self.forgetting_per_other_skill

    @property
    def net_total_if_correct_interior(self) -> float:
        return self.gain_correct - self.forgetting_mass_per_valid_step

    @property
    def net_total_if_incorrect_interior(self) -> float:
        return self.gain_incorrect - self.forgetting_mass_per_valid_step

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "n_other": self.n_other,
            "forgetting_mass_per_valid_step": self.forgetting_mass_per_valid_step,
            "net_total_if_correct_interior": self.net_total_if_correct_interior,
            "net_total_if_incorrect_interior": self.net_total_if_incorrect_interior,
            "reward_uses_selected_gain_not_net_total": True,
        }


def expected_arithmetic_for_config(cfg: EnvConfig, n_skills: int) -> NetMasteryArithmetic:
    return NetMasteryArithmetic(
        n_skills=n_skills,
        gain_correct=cfg.assumed_mastery_gain_correct,
        gain_incorrect=cfg.assumed_mastery_gain_incorrect,
        forgetting_per_other_skill=cfg.assumed_forgetting_per_step,
    )


def print_declared_sensitivity_grid(
    grid: tuple[dict[str, Any], ...] | None = None,
) -> None:
    """Print the complete declared grid before any rollouts execute."""
    rows = grid if grid is not None else DECLARED_SENSITIVITY_GRID
    print("=== DECLARED_SENSITIVITY_GRID (complete; before any rollouts) ===")
    for i, row in enumerate(rows):
        print(f"[{i}] setting_id={row['setting_id']}")
        for key in (
            "label",
            "hypothetical",
            "assumed_mastery_gain_correct",
            "assumed_mastery_gain_incorrect",
            "assumed_forgetting_per_step",
            "notes",
            "skip_rollout_duplicate_of",
        ):
            if key in row:
                print(f"    {key}: {row[key]}")
    print(f"=== end grid ({len(rows)} rows) ===")


def new_sensitivity_output_dir(
    base_metrics_dir: str | Path,
    *,
    prefix: str = "forgetting_sensitivity_val",
) -> Path:
    """Create a new timestamped output folder on every call (never overwrite)."""
    stamp = utc_now().replace(":", "").replace("-", "")
    out = Path(base_metrics_dir) / f"{prefix}_{stamp}"
    return ensure_dir(out)


def locate_unique_maskable_checkpoint(
    run_dir: str | Path,
    *,
    train_seed: int = COLAB_MASKABLE_TRAIN_SEED,
) -> Path:
    """
    Locate exactly one ``maskable_ppo_final.zip`` under ``run_dir/seed_{train_seed}/``.

    Raises FileNotFoundError if none; RuntimeError if more than one match.
    """
    run = Path(run_dir)
    seed_dir = run / f"seed_{int(train_seed)}"
    if not seed_dir.is_dir():
        raise FileNotFoundError(
            f"Expected seed folder missing: {seed_dir}\n"
            f"Action: confirm the v1.1 smoke run path and that MaskablePPO was trained "
            f"with seed {train_seed}."
        )
    matches = sorted(seed_dir.rglob("maskable_ppo_final.zip"))
    if len(matches) == 0:
        raise FileNotFoundError(
            f"No maskable_ppo_final.zip under {seed_dir}\n"
            "Action: confirm MaskablePPO was included in that smoke run and the "
            "checkpoint was saved."
        )
    if len(matches) > 1:
        listed = "\n".join(f"  - {p}" for p in matches)
        raise RuntimeError(
            f"Ambiguous MaskablePPO checkpoints under {seed_dir} "
            f"({len(matches)} matches). Need exactly one:\n{listed}"
        )
    return matches[0]


def load_summary_table(path: str | Path) -> list[dict[str, Any]]:
    """Load ``summary_table.json`` (a JSON list) produced by the sensitivity harness."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"summary_table.json missing: {p}")
    import json

    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError(
            f"summary_table.json must be a JSON list of row objects; got {type(data).__name__}"
        )
    return data


def display_summary_table(path: str | Path) -> list[dict[str, Any]]:
    """
    Print ``summary_table.json`` using its implemented schema.

    Row keys (executed methods):
      setting_id, hypothetical, method, evaluation_kind,
      return_mean, valid_practice_count_mean, invalid_action_rate_mean,
      selected_skill_mastery_gain_sum_mean,
      total_mastery_delta_final_minus_initial_mean, forgetting_per_step

    Skipped rows may include: skipped_rollout, duplicate_of, skipped, reason, label.
    """
    rows = load_summary_table(path)
    print(f"=== summary_table.json ({len(rows)} rows) from {path} ===")
    print(
        "schema_columns_for_executed_rows: "
        "setting_id | hypothetical | method | evaluation_kind | "
        "return_mean | valid_practice_count_mean | invalid_action_rate_mean | "
        "selected_skill_mastery_gain_sum_mean | "
        "total_mastery_delta_final_minus_initial_mean | forgetting_per_step"
    )
    for row in rows:
        if row.get("skipped_rollout"):
            print(
                f"[skip_rollout] setting_id={row.get('setting_id')} "
                f"duplicate_of={row.get('duplicate_of')} label={row.get('label')}"
            )
            continue
        if row.get("skipped"):
            print(
                f"[skipped] setting_id={row.get('setting_id')} "
                f"method={row.get('method')} reason={row.get('reason')}"
            )
            continue
        print(
            f"{row.get('setting_id')} | hyp={row.get('hypothetical')} | "
            f"{row.get('method')} | {row.get('evaluation_kind')} | "
            f"return={row.get('return_mean')} | "
            f"valid_n={row.get('valid_practice_count_mean')} | "
            f"invalid_rate={row.get('invalid_action_rate_mean')} | "
            f"sel_gain={row.get('selected_skill_mastery_gain_sum_mean')} | "
            f"net_total_dM={row.get('total_mastery_delta_final_minus_initial_mean')} | "
            f"forget={row.get('forgetting_per_step')}"
        )
    print("=== end summary_table ===")
    return rows


def _policy_factory(name: str, n_skills: int, seed: int) -> Any:
    if name == "weakest_mastery":
        return WeakestMasteryBaseline(n_skills)
    if name == "random_valid":
        return RandomValidBaseline(seed=seed + 300)
    if name == "recent_performance":
        return RecentPerformanceBaseline(n_skills)
    if name == "maskable_ppo":
        raise ValueError("maskable_ppo requires a checkpoint path; use build_maskable_policy")
    raise ValueError(name)


def build_maskable_policy(model_path: Path, env) -> Any:
    from sb3_contrib import MaskablePPO

    model = MaskablePPO.load(str(model_path))

    class Masked:
        def predict(self, observation, action_mask=None):
            masks = action_mask if action_mask is not None else env.action_masks()
            action, _ = model.predict(observation, deterministic=True, action_masks=masks)
            return int(action)

        def reset_episode(self):
            return None

        def observe_transition(self, info):
            return None

    return Masked()


def _metrics_block(rolls: list[dict]) -> dict[str, Any]:
    summary = summarise(rolls)
    # Flatten means for the audit table.
    return {
        "return_mean": summary.get("return", {}).get("mean"),
        "valid_practice_count_mean": summary.get("valid_practice_count", {}).get("mean"),
        "invalid_action_rate_mean": summary.get("invalid_action_rate", {}).get("mean"),
        "selected_skill_mastery_gain_sum_mean": summary.get(
            "selected_skill_mastery_gain_sum", {}
        ).get("mean"),
        "total_mastery_delta_final_minus_initial_mean": summary.get(
            "total_mastery_delta_final_minus_initial", {}
        ).get("mean"),
        "mean_mastery_delta_final_minus_initial_mean": summary.get(
            "mean_mastery_delta_final_minus_initial", {}
        ).get("mean"),
        "summary": summary,
    }


def run_forgetting_sensitivity(
    base_simulator: Simulator,
    base_env: EnvConfig,
    *,
    output_dir: Path | str,
    train_seed: int = COLAB_MASKABLE_TRAIN_SEED,
    episodes: int = 10,
    scenario: str = "sim_val",
    methods: tuple[str, ...] = (
        "weakest_mastery",
        "random_valid",
        "recent_performance",
        "maskable_ppo",
    ),
    maskable_ppo_checkpoint: str | Path | None = None,
    checkpoint_training_seed: int | None = None,
    grid: tuple[dict[str, Any], ...] | None = None,
    print_grid_before_rollouts: bool = True,
) -> dict[str, Any]:
    """
    Validation-only sensitivity / transfer evaluation.

    - Uses the existing response model (no refit).
    - Does not retrain policies under new dynamics.
    - Evaluating ``maskable_ppo`` under non-default dynamics is **transfer**
      evaluation of a checkpoint trained under v1.1 defaults.
    - ``train_seed`` drives paired ``val_episode_seed(train_seed, episode)`` for
      every method and every grid setting. For the Colab smoke checkpoint, use 42.
    """
    out = ensure_dir(output_dir)
    grid = grid if grid is not None else DECLARED_SENSITIVITY_GRID
    ckpt_seed = (
        int(checkpoint_training_seed)
        if checkpoint_training_seed is not None
        else int(train_seed)
    )
    if print_grid_before_rollouts:
        print_declared_sensitivity_grid(grid)

    # Persist declared grid before any rollouts.
    write_json(
        out / "DECLARED_SENSITIVITY_GRID.json",
        {
            "declared_before_execution": True,
            "declared_at_utc": utc_now(),
            "grid": list(grid),
            "env_protocol_version_unchanged": ENV_PROTOCOL_VERSION,
            "dynamics_proposal_version": DYNAMICS_PROPOSAL_VERSION,
            "paired_validation_seed_fn": "val_episode_seed(train_seed, episode)",
            "train_seed": int(train_seed),
            "checkpoint_training_seed": ckpt_seed,
            "episodes": episodes,
            "scenario": scenario,
            "maskable_ppo_checkpoint": str(maskable_ppo_checkpoint)
            if maskable_ppo_checkpoint
            else None,
            "data_kind_note": (
                "Colab Drive runs use real ASSISTments-backed artifacts. "
                "Local fixture sensitivity results are software checks only."
            ),
        },
    )

    arith = expected_arithmetic_for_config(base_env, base_simulator.n_skills)
    results: dict[str, Any] = {
        "purpose": "validation_only_forgetting_sensitivity",
        "not_final_test_evaluation": True,
        "not_retrained_under_altered_dynamics": True,
        "env_protocol_version": ENV_PROTOCOL_VERSION,
        "dynamics_proposal_version": DYNAMICS_PROPOSAL_VERSION,
        "train_seed": int(train_seed),
        "checkpoint_training_seed": ckpt_seed,
        "maskable_ppo_checkpoint": str(maskable_ppo_checkpoint)
        if maskable_ppo_checkpoint
        else None,
        "output_dir": str(out),
        "base_arithmetic_at_n_skills": arith.to_dict(),
        "reward_objective_mismatch": {
            "reward_includes": [
                "correctness_reward_weight * correct",
                "mastery_gain_weight * selected_skill_gain",
                "- time_cost_weight",
            ],
            "reward_excludes": ["net total mastery change across all skills"],
            "implication": (
                "A policy can earn positive return while net total mastery falls "
                "whenever forgetting_mass > selected gain."
            ),
        },
        "settings": {},
        "created_at_utc": utc_now(),
    }

    seed_fn = lambda ep: val_episode_seed(train_seed, ep)

    for row in grid:
        sid = row["setting_id"]
        if row.get("skip_rollout_duplicate_of"):
            results["settings"][sid] = {
                "label": row["label"],
                "hypothetical": row["hypothetical"],
                "skipped_rollout": True,
                "duplicate_of": row["skip_rollout_duplicate_of"],
                "notes": row["notes"],
                "parameters": {
                    "assumed_mastery_gain_correct": row["assumed_mastery_gain_correct"],
                    "assumed_mastery_gain_incorrect": row["assumed_mastery_gain_incorrect"],
                    "assumed_forgetting_per_step": row["assumed_forgetting_per_step"],
                },
            }
            continue

        cfg = replace(
            base_env,
            assumed_mastery_gain_correct=float(row["assumed_mastery_gain_correct"]),
            assumed_mastery_gain_incorrect=float(row["assumed_mastery_gain_incorrect"]),
            assumed_forgetting_per_step=float(row["assumed_forgetting_per_step"]),
        )
        sim = Simulator(
            response_model=base_simulator.response_model,
            skill_list=list(base_simulator.skill_list),
            env_config=cfg,
            parent_real_checksum=base_simulator.parent_real_checksum,
        )
        setting_arith = expected_arithmetic_for_config(cfg, sim.n_skills)
        method_results: dict[str, Any] = {}

        for method in methods:
            if method == "maskable_ppo":
                if maskable_ppo_checkpoint is None or not Path(maskable_ppo_checkpoint).exists():
                    method_results[method] = {
                        "skipped": True,
                        "reason": "maskable_ppo_checkpoint missing",
                        "evaluation_kind": "transfer_sensitivity_if_checkpoint_present",
                    }
                    continue
                env = make_env(sim, cfg, scenario=scenario, seed=train_seed)
                policy = build_maskable_policy(Path(maskable_ppo_checkpoint), env)
                rolls = rollout_policy(
                    env, policy, episodes=episodes, seed=0, seed_fn=seed_fn
                )
                method_results[method] = {
                    "label": COMPARISON_LABELS.get(method, method),
                    "evaluation_kind": (
                        "transfer_sensitivity_checkpoint_trained_under_v1_1_defaults"
                        if row["hypothetical"] or sid != "v1_1_current_default"
                        else "validation_rollout_same_dynamics_as_training_defaults"
                    ),
                    "checkpoint": str(maskable_ppo_checkpoint),
                    "checkpoint_training_seed": ckpt_seed,
                    "eval_train_seed_for_val_episode_seeds": int(train_seed),
                    "metrics": _metrics_block(rolls),
                    "episodes": rolls,
                }
            else:
                env = make_env(sim, cfg, scenario=scenario, seed=train_seed)
                policy = _policy_factory(method, sim.n_skills, train_seed)
                rolls = rollout_policy(
                    env, policy, episodes=episodes, seed=0, seed_fn=seed_fn
                )
                method_results[method] = {
                    "label": COMPARISON_LABELS.get(method, method),
                    "evaluation_kind": "validation_sensitivity_no_retrain",
                    "metrics": _metrics_block(rolls),
                    "episodes": rolls,
                }

        results["settings"][sid] = {
            "label": row["label"],
            "hypothetical": row["hypothetical"],
            "notes": row["notes"],
            "parameters": {
                "assumed_mastery_gain_correct": cfg.assumed_mastery_gain_correct,
                "assumed_mastery_gain_incorrect": cfg.assumed_mastery_gain_incorrect,
                "assumed_forgetting_per_step": cfg.assumed_forgetting_per_step,
            },
            "arithmetic": setting_arith.to_dict(),
            "methods": method_results,
        }
        write_json(out / f"setting_{sid}.json", results["settings"][sid])

    write_json(out / "forgetting_sensitivity_report.json", results)
    write_json(out / "summary_table.json", _flatten_table(results))
    return results


def _flatten_table(results: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for sid, setting in results.get("settings", {}).items():
        if setting.get("skipped_rollout"):
            rows.append(
                {
                    "setting_id": sid,
                    "label": setting.get("label"),
                    "skipped_rollout": True,
                    "duplicate_of": setting.get("duplicate_of"),
                }
            )
            continue
        for method, payload in setting.get("methods", {}).items():
            if payload.get("skipped"):
                rows.append(
                    {
                        "setting_id": sid,
                        "method": method,
                        "skipped": True,
                        "reason": payload.get("reason"),
                    }
                )
                continue
            m = payload.get("metrics", {})
            rows.append(
                {
                    "setting_id": sid,
                    "hypothetical": setting.get("hypothetical"),
                    "method": method,
                    "evaluation_kind": payload.get("evaluation_kind"),
                    "return_mean": m.get("return_mean"),
                    "valid_practice_count_mean": m.get("valid_practice_count_mean"),
                    "invalid_action_rate_mean": m.get("invalid_action_rate_mean"),
                    "selected_skill_mastery_gain_sum_mean": m.get(
                        "selected_skill_mastery_gain_sum_mean"
                    ),
                    "total_mastery_delta_final_minus_initial_mean": m.get(
                        "total_mastery_delta_final_minus_initial_mean"
                    ),
                    "forgetting_per_step": setting.get("parameters", {}).get(
                        "assumed_forgetting_per_step"
                    ),
                }
            )
    return rows
