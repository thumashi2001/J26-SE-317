"""Separate model cards for each supervised target (synthetic only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .contract import PASS_THRESHOLD, PASS_THRESHOLD_NOTE
from .protocol import DOMAIN_MARKERS, NON_CLAIMS, PROTOCOL_VERSION


def _md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_response_model_card(path: Path, payload: dict[str, Any]) -> None:
    sel = payload["selection"]
    comps = payload["comparison_val"]
    lines = [
        "# Model card — SE next-attempt correctness (synthetic)",
        "",
        f"- Protocol: `{PROTOCOL_VERSION}`",
        f"- Domain markers: `{DOMAIN_MARKERS}`",
        f"- Selected model (validation `{payload['primary_metric']}`): **{sel['name']}**",
        f"- Primary scenario: `{payload['primary_scenario']}`",
        "",
        "## Target",
        "",
        "Predict `y_correct` for the next practice attempt using features computed",
        "strictly before that attempt. Synthetic generator agreement only.",
        "",
        "## Validation comparison",
        "",
    ]
    for row in comps:
        lines.append(
            f"- `{row['name']}`: log_loss={row['val_metrics'].get('log_loss')}, "
            f"brier={row['val_metrics'].get('brier')}, "
            f"roc_auc={row['val_metrics'].get('roc_auc')}, "
            f"prevalence={row['val_metrics'].get('prevalence')}, n={row['val_metrics'].get('n')}"
        )
    lines += [
        "",
        "## Final test",
        "",
        (
            f"Executed: {payload.get('final_test') is not None}. "
            + (
                str(payload.get("final_test"))
                if payload.get("final_test")
                else "Not run (gated). Do not invent metrics."
            )
        ),
        "",
        "## Non-claims",
        "",
    ]
    lines.extend(f"- {c}" for c in NON_CLAIMS)
    lines += [
        "",
        "## Sensitivity scenarios",
        "",
        "All predeclared scenarios are reported in `scenario_sensitivity.json`.",
        "Generator settings were not retuned after seeing metrics.",
        "",
    ]
    _md(path, lines)


def write_exam_score_model_card(path: Path, payload: dict[str, Any]) -> None:
    sel = payload["selection"]
    comps = payload["comparison_val"]
    lines = [
        "# Model card — synthetic mock-exam score",
        "",
        f"- Protocol: `{PROTOCOL_VERSION}`",
        f"- Domain markers: `{DOMAIN_MARKERS}`",
        f"- Selected model (validation MAE): **{sel['name']}**",
        f"- Score scale: fraction correct in [0, 1]",
        "",
        "## Target",
        "",
        "At prediction cutoff (end of practice), predict subsequent mock-exam",
        "`y_exam_score` from prior practice features only. Exam answers and",
        "latents are excluded.",
        "",
        "## Validation comparison",
        "",
    ]
    for row in comps:
        lines.append(
            f"- `{row['name']}`: mae={row['val_metrics'].get('mae')}, "
            f"rmse={row['val_metrics'].get('rmse')}, "
            f"y_mean={row['val_metrics'].get('y_mean')}, n={row['val_metrics'].get('n')}"
        )
    lines += [
        "",
        "## Final test",
        "",
        (
            f"Executed: {payload.get('final_test') is not None}. "
            + (
                str(payload.get("final_test"))
                if payload.get("final_test")
                else "Not run (gated)."
            )
        ),
        "",
        "## Non-claims",
        "",
    ]
    lines.extend(f"- {c}" for c in NON_CLAIMS)
    _md(path, lines)


def write_pass_model_card(path: Path, payload: dict[str, Any] | None) -> None:
    if payload is None:
        _md(
            path,
            [
                "# Model card — synthetic mock-exam pass (optional)",
                "",
                "Pass models were **not enabled** for this run (insufficient class support",
                f"or skipped). Pass threshold (declared a priori): {PASS_THRESHOLD}.",
                "",
                PASS_THRESHOLD_NOTE,
                "",
                *NON_CLAIMS,
            ],
        )
        return
    sel = payload["selection"]
    comps = payload["comparison_val"]
    lines = [
        "# Model card — synthetic mock-exam pass (optional)",
        "",
        f"- Pass threshold (declared before training): **{PASS_THRESHOLD}**",
        f"- Note: {PASS_THRESHOLD_NOTE}",
        f"- Selected model: **{sel['name']}**",
        "",
        "## Validation comparison",
        "",
    ]
    for row in comps:
        lines.append(
            f"- `{row['name']}`: log_loss={row['val_metrics'].get('log_loss')}, "
            f"brier={row['val_metrics'].get('brier')}, "
            f"roc_auc={row['val_metrics'].get('roc_auc')}, "
            f"prevalence={row['val_metrics'].get('prevalence')}"
        )
    lines += ["", "## Non-claims", ""]
    lines.extend(f"- {c}" for c in NON_CLAIMS)
    _md(path, lines)
