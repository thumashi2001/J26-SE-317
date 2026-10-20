"""End-to-end SE supervised simulation pipeline (smoke / gated full / gated final)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .catalogue import catalogue_hash, catalogue_payload
from .contract import (
    PRIMARY_SCENARIO,
    SCENARIOS,
    PASS_THRESHOLD,
    frozen_contract_dict,
    sizes_for_mode,
)
from .export_bundle import export_run_bundle
from .features_exam import build_exam_feature_table, exam_feature_names
from .features_response import build_response_feature_table, response_feature_names
from .generate import generate_all_scenarios
from .inventory import inventory_local_se_exports
from .leakage import run_leakage_suite
from .model_cards import (
    write_exam_score_model_card,
    write_pass_model_card,
    write_response_model_card,
)
from .models_exam import (
    fit_exam_score_candidates,
    fit_pass_candidates,
    load_exam_bundle,
    pass_enabled,
    predict_exam_bundle,
    predict_pass_bundle,
    save_exam_bundle,
    save_pass_bundle,
    select_best_exam,
    select_best_pass,
)
from .models_response import (
    fit_response_candidates,
    load_response_bundle,
    predict_response_bundle,
    save_response_bundle,
    select_best_response,
)
from .paths import ensure_dir, new_run_dir, read_json, write_json
from .provenance import capture_versions
from .protocol import DOMAIN_MARKERS, PROTOCOL_VERSION
from .splits import assign_split_column, split_learner_ids, split_meta


def _load_scenario_tables(data_dir: Path, scenario: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    scen = data_dir / "scenarios" / scenario
    practice = pd.read_csv(scen / "practice_attempts.csv")
    exams = pd.read_csv(scen / "mock_exams.csv")
    return practice, exams


def _prepare_tables(
    practice: pd.DataFrame,
    exams: pd.DataFrame,
    *,
    max_response_rows: int,
    id_sets: dict[str, set[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    resp = build_response_feature_table(practice, max_rows_per_learner=max_response_rows)
    exam_f = build_exam_feature_table(practice, exams)
    resp = assign_split_column(resp, id_sets)
    exam_f = assign_split_column(exam_f, id_sets)
    return resp, exam_f


def _split_frames(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "train": df[df["split"] == "train"].reset_index(drop=True),
        "validation": df[df["split"] == "validation"].reset_index(drop=True),
        "test": df[df["split"] == "test"].reset_index(drop=True),
    }


def run_training_and_validation(
    artifacts_root: Path | str,
    *,
    mode: str = "smoke",
    master_seed: int = 42,
    run_full: bool = False,
    c4_root: Path | str | None = None,
) -> dict[str, Any]:
    """Generate synthetic data, fit models on train, select on validation.

    Full mode requires run_full=True (Colab gate). Smoke is the local default.
    """
    if mode == "full" and not run_full:
        raise RuntimeError("Full training gated: pass run_full=True explicitly.")
    if mode not in {"smoke", "full"}:
        raise ValueError(mode)

    artifacts_root = Path(artifacts_root)
    run_dir = new_run_dir(artifacts_root, mode)
    sizes = sizes_for_mode(mode)

    # Inventory (informational)
    inv_root = Path(c4_root) if c4_root else Path(__file__).resolve().parents[1]
    inventory = inventory_local_se_exports(inv_root)
    write_json(run_dir / "data_inventory.json", inventory)

    contract = frozen_contract_dict(mode=mode, master_seed=master_seed)
    write_json(run_dir / "frozen_contract.json", contract)

    data_dir = ensure_dir(run_dir / "synthetic_data")
    gen_index = generate_all_scenarios(data_dir, mode=mode, master_seed=master_seed)
    write_json(run_dir / "generation_index.json", gen_index)

    # Splits from primary scenario learners (same IDs reused across scenarios).
    primary_learners = pd.read_csv(
        data_dir / "scenarios" / PRIMARY_SCENARIO / "learners.csv"
    )
    id_sets = split_learner_ids(
        primary_learners["learner_id"], master_seed=master_seed
    )
    write_json(run_dir / "split_ids.json", split_meta(id_sets, master_seed))

    practice, exams = _load_scenario_tables(data_dir, PRIMARY_SCENARIO)
    resp, exam_f = _prepare_tables(
        practice,
        exams,
        max_response_rows=sizes.max_response_rows_per_learner,
        id_sets=id_sets,
    )
    leakage = run_leakage_suite(practice, exams, resp, exam_f, id_sets)
    write_json(run_dir / "leakage_checks.json", leakage)

    resp_splits = _split_frames(resp)
    exam_splits = _split_frames(exam_f)

    # --- Response models ---
    resp_cands = fit_response_candidates(
        resp_splits["train"], resp_splits["validation"], seed=master_seed
    )
    resp_best = select_best_response(resp_cands, primary="log_loss")
    resp_comparison = [
        {"name": c.name, "train_metrics": c.train_metrics, "val_metrics": c.val_metrics}
        for c in resp_cands
    ]
    write_json(run_dir / "comparison_val_response.json", resp_comparison)

    # --- Exam score ---
    exam_cands = fit_exam_score_candidates(
        exam_splits["train"], exam_splits["validation"], seed=master_seed
    )
    exam_best = select_best_exam(exam_cands, primary="mae")
    exam_comparison = [
        {"name": c.name, "train_metrics": c.train_metrics, "val_metrics": c.val_metrics}
        for c in exam_cands
    ]
    write_json(run_dir / "comparison_val_exam_score.json", exam_comparison)

    # --- Optional pass ---
    pass_info = pass_enabled(exam_splits["train"])
    write_json(run_dir / "pass_enablement.json", pass_info)
    pass_cands = fit_pass_candidates(
        exam_splits["train"], exam_splits["validation"], seed=master_seed
    )
    pass_best = select_best_pass(pass_cands) if pass_cands else None
    pass_comparison = [
        {"name": c.name, "train_metrics": c.train_metrics, "val_metrics": c.val_metrics}
        for c in pass_cands
    ]
    write_json(run_dir / "comparison_val_pass.json", pass_comparison)

    selection = {
        **DOMAIN_MARKERS,
        "primary_scenario": PRIMARY_SCENARIO,
        "response": {
            "name": resp_best.name,
            "val_metrics": resp_best.val_metrics,
            "primary_metric": "log_loss",
        },
        "exam_score": {
            "name": exam_best.name,
            "val_metrics": exam_best.val_metrics,
            "primary_metric": "mae",
        },
        "pass": (
            {
                "name": pass_best.name,
                "val_metrics": pass_best.val_metrics,
                "primary_metric": "log_loss",
                "pass_threshold": PASS_THRESHOLD,
            }
            if pass_best
            else {"enabled": False, **pass_info}
        ),
    }
    write_json(run_dir / "selection_val.json", selection)
    write_json(run_dir / "SELECTION_FROZEN.json", selection)

    models_dir = ensure_dir(run_dir / "models")
    save_response_bundle(
        models_dir / "response_selected.joblib",
        resp_best,
        {"target": "y_correct", **DOMAIN_MARKERS},
    )
    save_exam_bundle(
        models_dir / "exam_score_selected.joblib",
        exam_best,
        {"target": "y_exam_score", **DOMAIN_MARKERS},
    )
    if pass_best is not None:
        save_pass_bundle(
            models_dir / "pass_selected.joblib",
            pass_best,
            {"target": "y_pass", "pass_threshold": PASS_THRESHOLD, **DOMAIN_MARKERS},
        )

    write_json(
        run_dir / "feature_schema_response.json",
        {
            "features": response_feature_names(),
            "target": "y_correct",
            "cutoff": "strictly before attempt",
        },
    )
    write_json(
        run_dir / "feature_schema_exam.json",
        {
            "features": exam_feature_names(),
            "targets": ["y_exam_score", "y_pass"],
            "cutoff": "practice timestamp <= prediction_cutoff_utc; exam after",
            "pass_threshold": PASS_THRESHOLD,
        },
    )
    write_json(
        run_dir / "target_definitions.json",
        {
            "y_correct": "binary correctness of the practice attempt being predicted",
            "y_exam_score": "fraction correct on subsequent synthetic mock exam [0,1]",
            "y_pass": f"1 if y_exam_score >= {PASS_THRESHOLD}",
            "pass_threshold_note": contract["contract"]["pass_threshold_note"],
        },
    )
    write_json(
        run_dir / "topic_catalogue.json",
        {**catalogue_payload(), "sha256": catalogue_hash()},
    )
    write_json(run_dir / "runtime_versions.json", capture_versions())

    # Sensitivity: evaluate selected model families on ALL scenarios' validation splits
    # using freshly built tables + same learner split IDs (no retuning).
    sensitivity: dict[str, Any] = {"rule": "report_all_predeclared_scenarios", "scenarios": {}}
    for scen_name in SCENARIOS:
        p, e = _load_scenario_tables(data_dir, scen_name)
        r_tab, e_tab = _prepare_tables(
            p, e, max_response_rows=sizes.max_response_rows_per_learner, id_sets=id_sets
        )
        r_val = r_tab[r_tab["split"] == "validation"]
        e_val = e_tab[e_tab["split"] == "validation"]
        # Refit candidates within scenario for honest within-scenario comparison
        # (still no generator retuning).
        r_c = fit_response_candidates(
            r_tab[r_tab["split"] == "train"], r_val, seed=master_seed
        )
        e_c = fit_exam_score_candidates(
            e_tab[e_tab["split"] == "train"], e_val, seed=master_seed
        )
        sensitivity["scenarios"][scen_name] = {
            "response_val": [
                {"name": c.name, "val_metrics": c.val_metrics} for c in r_c
            ],
            "exam_score_val": [
                {"name": c.name, "val_metrics": c.val_metrics} for c in e_c
            ],
            "practice_correct_rate": float(p["correct"].mean()),
            "exam_score_mean": float(e["y_exam_score"].mean()),
        }
    write_json(run_dir / "scenario_sensitivity.json", sensitivity)

    cards = ensure_dir(run_dir / "model_cards")
    write_response_model_card(
        cards / "MODEL_CARD_RESPONSE.md",
        {
            "selection": selection["response"],
            "comparison_val": resp_comparison,
            "primary_metric": "log_loss",
            "primary_scenario": PRIMARY_SCENARIO,
            "final_test": None,
        },
    )
    write_exam_score_model_card(
        cards / "MODEL_CARD_EXAM_SCORE.md",
        {
            "selection": selection["exam_score"],
            "comparison_val": exam_comparison,
            "final_test": None,
        },
    )
    write_pass_model_card(
        cards / "MODEL_CARD_PASS.md",
        None
        if pass_best is None
        else {
            "selection": selection["pass"],
            "comparison_val": pass_comparison,
        },
    )

    export_run_bundle(run_dir)

    return {
        "run_dir": str(run_dir),
        "selection": selection,
        "inventory": inventory,
        "leakage": leakage,
        "mode": mode,
        "protocol": PROTOCOL_VERSION,
    }


def run_final_evaluation(
    run_dir: Path | str,
    *,
    run_final: bool = False,
) -> dict[str, Any]:
    """One-shot final-test evaluation. Requires saved SELECTION_FROZEN.json.

    Does not fall back to default configuration.
    """
    if not run_final:
        raise RuntimeError("Final evaluation gated: pass run_final=True explicitly.")

    run_dir = Path(run_dir)
    frozen_path = run_dir / "SELECTION_FROZEN.json"
    contract_path = run_dir / "frozen_contract.json"
    if not frozen_path.is_file():
        raise FileNotFoundError(f"Missing SELECTION_FROZEN.json under {run_dir}")
    if not contract_path.is_file():
        raise FileNotFoundError(f"Missing frozen_contract.json under {run_dir}")

    selection = read_json(frozen_path)
    contract = read_json(contract_path)
    if not isinstance(selection, dict) or "response" not in selection:
        raise RuntimeError("SELECTION_FROZEN.json is incomplete; refusing defaults.")
    if not isinstance(contract, dict) or "contract" not in contract:
        raise RuntimeError("frozen_contract.json is incomplete; refusing defaults.")

    master_seed = int(contract["contract"]["master_seed"])
    mode = str(contract["contract"]["mode"])
    sizes = sizes_for_mode(mode)
    data_dir = run_dir / "synthetic_data"
    split_payload = read_json(run_dir / "split_ids.json")
    id_sets = {
        k: set(v) for k, v in split_payload["learner_ids"].items()  # type: ignore[index]
    }

    practice, exams = _load_scenario_tables(data_dir, PRIMARY_SCENARIO)
    resp, exam_f = _prepare_tables(
        practice,
        exams,
        max_response_rows=sizes.max_response_rows_per_learner,
        id_sets=id_sets,
    )
    resp_test = resp[resp["split"] == "test"]
    exam_test = exam_f[exam_f["split"] == "test"]

    resp_bundle = load_response_bundle(run_dir / "models" / "response_selected.joblib")
    exam_bundle = load_exam_bundle(run_dir / "models" / "exam_score_selected.joblib")

    from .metrics import classification_metrics, regression_metrics

    p_resp = predict_response_bundle(resp_bundle, resp_test)
    y_resp = resp_test["y_correct"].astype(int).to_numpy()
    resp_test_metrics = classification_metrics(y_resp, p_resp)

    y_hat_exam = predict_exam_bundle(exam_bundle, exam_test)
    y_exam = exam_test["y_exam_score"].astype(float).to_numpy()
    exam_test_metrics = regression_metrics(y_exam, y_hat_exam)

    pass_test_metrics = None
    pass_path = run_dir / "models" / "pass_selected.joblib"
    if pass_path.is_file():
        pass_bundle = load_exam_bundle(pass_path)
        p_pass = predict_pass_bundle(pass_bundle, exam_test)
        pass_test_metrics = classification_metrics(
            exam_test["y_pass"].astype(int).to_numpy(), p_pass
        )

    out_dir = ensure_dir(run_dir / "final_test")
    result = {
        **DOMAIN_MARKERS,
        "loaded_selection": selection,
        "loaded_contract_mode": mode,
        "master_seed": master_seed,
        "response_test": resp_test_metrics,
        "exam_score_test": exam_test_metrics,
        "pass_test": pass_test_metrics,
        "note": "One-shot final test on learner-disjoint synthetic test split. Not real SE validation.",
    }
    write_json(out_dir / "final_test_metrics.json", result)
    export_run_bundle(run_dir)
    return result


def reload_run(run_dir: Path | str) -> dict[str, Any]:
    """Reload a saved run after Colab restart (no config fallback)."""
    run_dir = Path(run_dir)
    required = [
        "frozen_contract.json",
        "SELECTION_FROZEN.json",
        "split_ids.json",
        "models/response_selected.joblib",
        "models/exam_score_selected.joblib",
    ]
    missing = [r for r in required if not (run_dir / r).is_file()]
    if missing:
        raise FileNotFoundError(f"Incomplete run at {run_dir}; missing {missing}")
    return {
        "run_dir": str(run_dir),
        "contract": read_json(run_dir / "frozen_contract.json"),
        "selection": read_json(run_dir / "SELECTION_FROZEN.json"),
        "versions": read_json(run_dir / "runtime_versions.json")
        if (run_dir / "runtime_versions.json").is_file()
        else None,
    }
