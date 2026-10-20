"""
AdaptiveLearnSE Component 3 — Experiment framework (real models only).

Shared building blocks for conditions A-F: metric computation with bootstrap intervals,
provenance-stamped result files, prompt builders and strict response parsing. A failed model call
is recorded as `failed` and excluded from the error metrics (and counted); it is never scored as 0.
"""

import hashlib
import json
import math
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RESULTS_ROOT = Path(__file__).resolve().parent / "results"
CORE_TIERS = ("FULL", "MOSTLY_CORRECT", "PARTIAL", "MISSING_CONCEPT", "MISCONCEPTION", "IRRELEVANT")
BOOTSTRAP_SAMPLES = 2000


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, cwd=Path(__file__).parent
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------- metrics


def pearson(a: np.ndarray, b: np.ndarray) -> float | None:
    """Pearson r, or None when undefined (constant input / fewer than 3 points)."""
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _bootstrap_ci(values: np.ndarray, seed: int = 20261021) -> list[float] | None:
    if len(values) < 5:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(BOOTSTRAP_SAMPLES, len(values)))
    means = values[idx].mean(axis=1)
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


def _block(df: pd.DataFrame) -> dict[str, Any]:
    err = (df["predicted_mark"] - df["expected_mark"]).abs().to_numpy(dtype=float)
    norm_err = err / df["max_marks"].to_numpy(dtype=float)
    exp = df["expected_mark"].to_numpy(dtype=float)
    pred = df["predicted_mark"].to_numpy(dtype=float)
    r = pearson(exp, pred)
    return {
        "n": int(len(df)),
        "mae": round(float(err.mean()), 4),
        "mae_ci95": _bootstrap_ci(err),
        "rmse": round(float(math.sqrt((err**2).mean())), 4),
        "normalized_mae": round(float(norm_err.mean()), 4),
        "normalized_mae_ci95": _bootstrap_ci(norm_err),
        "pearson_r": None if r is None else round(r, 4),
        "within_2_marks_pct": round(float((err <= 2.0).mean() * 100), 2),
        "within_10pct_of_max_pct": round(float((norm_err <= 0.10).mean() * 100), 2),
        "mean_signed_error": round(float((pred - exp).mean()), 4),
    }


def compute_metrics(preds: pd.DataFrame) -> dict[str, Any]:
    """preds columns: answer_id, question_id, tier, expected_mark, max_marks, predicted_mark, failed."""
    failed = preds["failed"].astype(bool)
    scored = preds[~failed]
    out: dict[str, Any] = {"n_total": int(len(preds)), "n_failed": int(failed.sum()), "n_scored": int(len(scored))}
    if scored.empty:
        out["overall"] = None
        return out
    out["overall"] = _block(scored)
    out["by_tier"] = {t: _block(g) for t, g in scored.groupby("tier") if len(g)}
    core = scored[scored["tier"].isin(CORE_TIERS)]
    out["core_tiers"] = _block(core) if len(core) else None
    return out


# ----------------------------------------------------------------------------- provenance


@dataclass
class RunContext:
    run_id: str
    condition: str
    provider: str
    model: str
    dataset_version: str
    split: str
    prompt_hash: str
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "condition": self.condition,
            "provider": self.provider,
            "model": self.model,
            "is_real_execution": True,
            "dataset_version": self.dataset_version,
            "split": self.split,
            "prompt_hash": self.prompt_hash,
            "commit": git_commit(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **self.extra,
        }


def write_run(out_dir: Path, name: str, ctx: RunContext, preds: pd.DataFrame, extra_summary: dict[str, Any]) -> dict:
    """Write predictions CSV + summary JSON. `is_real_execution` is true only if every scored row was real."""
    out_dir.mkdir(parents=True, exist_ok=True)
    preds.to_csv(out_dir / f"predictions_{name}.csv", index=False)
    summary = {**ctx.as_dict(), "metrics": compute_metrics(preds), **extra_summary}
    if "real_execution" in preds.columns:
        summary["is_real_execution"] = bool(preds.loc[~preds["failed"].astype(bool), "real_execution"].all())
    (out_dir / f"summary_{name}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


# ----------------------------------------------------------------------------- prompts

SYSTEM_PROMPT = (
    "You are a careful university examiner for software engineering modules. "
    "Judge only the content of the student's answer. Do not reward length, confident tone or keywords "
    "that are not explained. Respond with JSON only."
)


def rubric_text(rubric: dict[str, Any]) -> str:
    lines = []
    for crit in rubric["criteria"]:
        lines.append(f"Criterion {crit['criterion_id']} - {crit['description']} (max {crit['max_marks']:g} marks)")
        for lvl in crit["scoring_levels"]:
            concepts = ", ".join(lvl.get("required_concepts", [])) or "-"
            lines.append(
                f"  - level {lvl['level_id']} [{lvl['mark']:g} marks] {lvl['label']}: {lvl['descriptor']} "
                f"(key concepts: {concepts})"
            )
    return "\n".join(lines)


def prompt_condition_a(question: dict[str, Any], answer: str) -> str:
    return (
        f"Question:\n{question['question_text']}\n\nMaximum marks: {question['max_marks']:g}\n\n"
        f'Student answer:\n"""{answer}"""\n\n'
        'Award a mark between 0 and the maximum. Return JSON: {"total_awarded_mark": <number>}'
    )


def prompt_rubric(question: dict[str, Any], rubric: dict[str, Any], answer: str, context: str = "") -> str:
    extra = f"\n\n{context}\n" if context else "\n"
    ids = ", ".join(c["criterion_id"] for c in rubric["criteria"])
    return (
        f"Question:\n{question['question_text']}\n\nMaximum marks: {question['max_marks']:g}\n\n"
        f"Marking rubric (choose exactly one level per criterion):\n{rubric_text(rubric)}{extra}\n"
        f'Student answer:\n"""{answer}"""\n\n'
        f"Select the level that the answer supports for each criterion ({ids}). If the answer shows no "
        "evidence for a criterion, choose its zero-mark level.\n"
        'Return JSON: {"criteria": [{"criterion_id": "<id>", "level_id": "<level id>"}, ...]}'
    )


def context_block_rag(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "Retrieved reference material: none above the relevance threshold."
    parts = [f"[{i}] ({h['citation']}) {h['content']}" for i, h in enumerate(hits, 1)]
    return "Retrieved reference material from other questions (may be only loosely related):\n" + "\n".join(parts)


def context_block_graph(graph_ctx: dict[str, Any]) -> str:
    text = graph_ctx.get("graphrag_context_text", "").strip()
    return "Curriculum knowledge-graph context:\n" + (text or "no concepts resolved in the graph")


# ----------------------------------------------------------------------------- parsing


class ParseError(ValueError):
    pass


def parse_total_mark(parsed: dict[str, Any] | None, max_marks: float) -> float:
    if not parsed or "total_awarded_mark" not in parsed:
        raise ParseError("missing total_awarded_mark")
    try:
        value = float(parsed["total_awarded_mark"])
    except (TypeError, ValueError) as exc:
        raise ParseError("total_awarded_mark is not numeric") from exc
    if not math.isfinite(value):
        raise ParseError("total_awarded_mark is not finite")
    return float(min(max(value, 0.0), max_marks))


def parse_level_selection(parsed: dict[str, Any] | None, rubric: dict[str, Any]) -> tuple[float, list[dict]]:
    """Return (mark, chosen). Marks come ONLY from the rubric's level marks."""
    if not parsed or not isinstance(parsed.get("criteria"), list):
        raise ParseError("missing criteria list")
    by_crit = {c["criterion_id"]: {lv["level_id"]: float(lv["mark"]) for lv in c["scoring_levels"]}
               for c in rubric["criteria"]}
    chosen: dict[str, str] = {}
    for item in parsed["criteria"]:
        cid, lid = item.get("criterion_id"), item.get("level_id")
        if cid not in by_crit:
            raise ParseError(f"unknown criterion_id {cid!r}")
        if lid not in by_crit[cid]:
            raise ParseError(f"unknown level_id {lid!r} for {cid}")
        chosen[cid] = lid
    missing = set(by_crit) - set(chosen)
    if missing:
        raise ParseError(f"no level chosen for {sorted(missing)}")
    total = sum(by_crit[c][chosen[c]] for c in by_crit)
    return total, [{"criterion_id": c, "level_id": chosen[c], "mark": by_crit[c][chosen[c]]} for c in by_crit]
