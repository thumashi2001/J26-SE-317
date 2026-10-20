"""Data-quality reporting for ASSISTments interactions."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .provenance import write_json


def build_quality_report(raw: pd.DataFrame, normalised: pd.DataFrame) -> dict[str, Any]:
    dtypes = {c: str(t) for c, t in raw.dtypes.items()}
    n_learners = int(normalised["user_id"].nunique())
    n_interactions = int(len(normalised))
    skill_token_counts = (
        normalised["skill_tokens"].explode().dropna().astype(str).value_counts()
        if n_interactions
        else pd.Series(dtype=int)
    )

    # Duplicate interactions: same learner + order_id (+ problem if available)
    dup_keys = ["user_id", "order_id"]
    if "problem_id" in normalised.columns:
        dup_keys.append("problem_id")
    n_dup = int(normalised.duplicated(subset=dup_keys, keep="first").sum())

    missing = {c: int(raw[c].isna().sum()) for c in raw.columns}
    multi = normalised["is_multi_skill"].sum() if "is_multi_skill" in normalised.columns else 0

    # Chronology check: fraction of within-learner order_id increases
    chrono_ok = 0
    chrono_total = 0
    for _, g in normalised.groupby("user_id", sort=False):
        oid = g["order_id"].to_numpy()
        if len(oid) < 2:
            continue
        chrono_total += len(oid) - 1
        chrono_ok += int((oid[1:] >= oid[:-1]).sum())

    exclusions = [
        {
            "rule": "drop_rows_with_non_numeric_correct",
            "reason": "Target label required for supervised response modelling.",
            "rows_before": int(len(raw)),
            "rows_after": int(len(normalised)),
        },
        {
            "rule": "do_not_drop_multi_skill_rows",
            "reason": "Multi-skill tags are preserved (skill_tokens / is_multi_skill).",
            "multi_skill_rows_kept": int(multi),
        },
    ]

    report: dict[str, Any] = {
        "available_columns": list(raw.columns),
        "column_dtypes": dtypes,
        "n_raw_rows": int(len(raw)),
        "n_normalised_interactions": n_interactions,
        "n_learners": n_learners,
        "n_distinct_primary_skills": int(normalised["primary_skill"].nunique()),
        "n_distinct_skill_tokens": int(skill_token_counts.shape[0]),
        "top_skill_tokens": skill_token_counts.head(20).to_dict(),
        "missing_values_raw": missing,
        "duplicate_interactions_by_keys": {"keys": dup_keys, "count": n_dup},
        "multi_skill": {
            "n_multi_skill_rows": int(multi),
            "fraction": float(multi / n_interactions) if n_interactions else 0.0,
            "representation": (
                "Collapsed skill1_skill2 in skill_id for corrected export; "
                "parsed into skill_tokens without dropping rows."
            ),
        },
        "chronological_ordering": {
            "within_learner_sort_keys": ["user_id", "order_id"],
            "order_id_monotonic_nondecreasing_fraction": (
                float(chrono_ok / chrono_total) if chrono_total else 1.0
            ),
            "limitation": (
                "ASSISTments documents order_id as a non-timestamp identifier; "
                "within-learner order_id sort is a reproducible convention, not a verified wall-clock timeline."
            ),
        },
        "correctness_rate": float(normalised["correct"].mean()) if n_interactions else None,
        "exclusions": exclusions,
        "domain_warning": (
            "These are K-12 mathematics ASSISTments observations. "
            "They are not Software Engineering student observations from AdaptiveLearnSE."
        ),
    }
    return report


def save_quality_report(report: dict[str, Any], path: str) -> None:
    write_json(path, report)
