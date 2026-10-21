"""Release writer: explicit JSON dumps, hard refusal of nan/None, manifest with per-file hashes, generated card."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import DATASET_VERSION, tier_spec_sha256
from .source import SOURCE_FILE_LABEL

QUESTION_COLUMNS = [
    "question_id", "parent_question_id", "part_label", "module_code", "source_type", "split",
    "question_text_raw", "question_text", "ocr_noise_ratio", "max_marks", "answer_type", "reference_answer",
    "expected_concepts", "concept_graph", "rubric_id", "rubric_status", "scope_status", "generator_model",
    "structure_prompt_hash", "rubric_prompt_hash", "dataset_version",
]  # fmt: skip
RUBRIC_COLUMNS = [
    "rubric_id", "question_id", "rubric_title", "criterion_id", "criterion_index", "description", "max_marks",
    "required_concepts", "scoring_levels", "rubric_status", "dataset_version",
]  # fmt: skip
ANSWER_COLUMNS = [
    "answer_id", "question_id", "parent_question_id", "split", "tier", "sub_kind", "style", "register",
    "student_answer", "word_count", "expected_mark", "max_marks", "normalized_mark", "criterion_marks",
    "concept_status", "incorrect_concepts", "evidence_spans", "gold_mindmap", "generation_seed", "generator_model",
    "prompt_hash", "blind_grade_agreement", "needs_review", "blind_grade_levels", "blind_grade_mark",
    "verification", "check_flags", "dataset_version",
]  # fmt: skip
EXCLUDED_COLUMNS = [
    "question_id", "parent_question_id", "module_code", "source_type", "question_text_raw", "stage",
    "exclusion_class", "reason", "diagnostic", "source_file", "source_row", "dataset_version",
]  # fmt: skip
REJECTED_COLUMNS = ["answer_id", "question_id", "tier", "student_answer", "reasons", "dataset_version"]
EXPERT_COLUMNS = [
    "answer_id", "question_id", "module_code", "question_text", "max_marks", "student_answer",
    "expert_total_mark", "expert_criterion_levels", "expert_notes", "expert_id",
]  # fmt: skip

JSON_COLUMNS = {
    "expected_concepts", "concept_graph", "required_concepts", "scoring_levels", "criterion_marks", "concept_status",
    "incorrect_concepts", "evidence_spans", "gold_mindmap", "blind_grade_levels", "check_flags", "reasons",
}  # fmt: skip
OPTIONAL_EMPTY = {"part_label", "expert_total_mark", "expert_criterion_levels", "expert_notes", "expert_id"}
_UNRESOLVED = re.compile(r"<<[A-Z_]+>>|\{\{|\}\}|\{[a-z_]+\}")


class WriteError(ValueError):
    pass


@dataclass
class ReleaseData:
    questions: list[dict]
    rubrics: list[dict]
    answers: list[dict]
    excluded: list[dict]
    rejected: list[dict] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _cell(row: dict, col: str, spec: dict, blank_answer_ok: bool = False) -> str:
    if col not in row:
        raise WriteError(f"row missing column {col}: {row.get('answer_id') or row.get('question_id')}")
    v = row[col]
    ident = row.get("answer_id") or row.get("question_id") or row.get("rubric_id")
    if v is None or (isinstance(v, float) and math.isnan(v)):
        raise WriteError(f"{col} is None/NaN for {ident}")
    if col in JSON_COLUMNS:
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(round(v, 6))
    s = str(v)
    if col == "student_answer":
        if not s.strip() and row.get("tier") != "EMPTY" and not blank_answer_ok:
            raise WriteError(f"empty student_answer outside EMPTY tier: {ident}")
        if s.strip() and row.get("tier") == "EMPTY":
            raise WriteError(f"EMPTY tier answer must be blank: {ident}")
    elif not s.strip() and col not in OPTIONAL_EMPTY:
        raise WriteError(f"{col} is empty for {ident}")
    if s.strip().casefold() in {x.casefold() for x in spec["forbidden_text_values"]}:
        raise WriteError(f"{col} holds forbidden literal {s!r} for {ident}")
    if col in ("student_answer", "reference_answer") and _UNRESOLVED.search(s):
        raise WriteError(f"{col} has an unresolved placeholder for {ident}")
    return s


def write_csv(path: Path, columns: list[str], rows: list[dict], spec: dict, blank_answer_ok: bool = False) -> None:
    rendered = [[_cell(r, c, spec, blank_answer_ok) for c in columns] for r in rows]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        w.writerows(rendered)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def agreement_stats(answers: list[dict]) -> dict:
    graded = [a for a in answers if a["verification"] == "blind_llm"]
    out: dict[str, Any] = {"n_graded": len(graded), "overall_level_agreement": None, "per_tier": {}, "needs_review": 0}
    if not graded:
        return out
    out["overall_level_agreement"] = round(sum(a["blind_grade_agreement"] for a in graded) / len(graded), 4)
    out["needs_review"] = sum(1 for a in graded if a["needs_review"])
    tiers: dict[str, list[dict]] = {}
    for a in graded:
        tiers.setdefault(a["tier"], []).append(a)
    for t, rows in sorted(tiers.items()):
        out["per_tier"][t] = {
            "n": len(rows),
            "level_agreement": round(sum(r["blind_grade_agreement"] for r in rows) / len(rows), 4),
            "needs_review_rate": round(sum(1 for r in rows if r["needs_review"]) / len(rows), 4),
        }
    return out


def expert_sample(answers: list[dict], questions: dict[str, dict], fraction: float, seed: int) -> list[dict]:
    k = max(1, math.ceil(fraction * len(answers))) if answers else 0
    chosen = random.Random(seed).sample(sorted(answers, key=lambda a: a["answer_id"]), k)
    rows = []
    for a in sorted(chosen, key=lambda a: a["answer_id"]):
        q = questions[a["question_id"]]
        rows.append(
            {
                "answer_id": a["answer_id"], "question_id": a["question_id"], "module_code": q["module_code"],
                "question_text": q["question_text"], "max_marks": a["max_marks"], "student_answer": a["student_answer"],
                "expert_total_mark": "", "expert_criterion_levels": "", "expert_notes": "", "expert_id": "",
            }
        )  # fmt: skip
    return rows


def write_release(out_dir: Path, data: ReleaseData, spec: dict, seed: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    qmap = {q["question_id"]: q for q in data.questions}
    files: dict[str, Path] = {}

    def emit(name: str, cols: list[str], rows: list[dict], blank_answer_ok: bool = False) -> None:
        write_csv(out_dir / name, cols, rows, spec, blank_answer_ok)
        files[name] = out_dir / name

    emit("questions.csv", QUESTION_COLUMNS, data.questions)
    emit("rubrics.csv", RUBRIC_COLUMNS, data.rubrics)
    emit("answers.csv", ANSWER_COLUMNS, data.answers)
    emit("excluded_questions.csv", EXCLUDED_COLUMNS, data.excluded)
    emit("rejected_answers.csv", REJECTED_COLUMNS, data.rejected)
    for split in ("train", "validation", "test"):
        emit(f"questions_{split}.csv", QUESTION_COLUMNS, [q for q in data.questions if q["split"] == split])
        emit(f"answers_{split}.csv", ANSWER_COLUMNS, [a for a in data.answers if a["split"] == split])
    emit(
        "expert_review_sample.csv",
        EXPERT_COLUMNS,
        expert_sample(data.answers, qmap, spec["thresholds"]["expert_review_fraction"], seed),
        blank_answer_ok=True,
    )

    meta = data.meta
    by_tier = Counter(a["tier"] for a in data.answers)
    manifest = {
        "dataset_version": DATASET_VERSION,
        "expert_validation": False,
        "rubric_status": "llm_drafted_unverified",
        "seed": seed,
        "n_per_tier": meta.get("n_per_tier"),
        "generator_provider": meta.get("generator_provider"),
        "generator_model": meta.get("generator_model"),
        "verifier_provider": meta.get("verifier_provider"),
        "verifier_model": meta.get("verifier_model"),
        "verifier_same_model_family_as_generator": meta.get("verifier_same_model_family_as_generator"),
        "prompt_hashes": meta.get("prompt_hashes"),
        "tier_spec_sha256": tier_spec_sha256(),
        "source_questions": meta.get("source_questions"),
        "source_file": SOURCE_FILE_LABEL,
        "source_question_ids": meta.get("source_question_ids"),
        "counts": {
            "questions": len(data.questions),
            "parent_questions": len({q["parent_question_id"] for q in data.questions}),
            "rubric_criteria": len(data.rubrics),
            "answers": len(data.answers),
            "excluded_questions": len(data.excluded),
            "rejected_answers": len(data.rejected),
            "answers_by_tier": dict(sorted(by_tier.items())),
            "answers_by_split": dict(sorted(Counter(a["split"] for a in data.answers).items())),
            "questions_by_split": dict(sorted(Counter(q["split"] for q in data.questions).items())),
            "excluded_by_class": dict(sorted(Counter(e["exclusion_class"] for e in data.excluded).items())),
            "excluded_by_reason": dict(sorted(Counter(e["reason"] for e in data.excluded).items())),
            "excluded_top_reasons": [
                {"reason": r, "count": n} for r, n in Counter(e["reason"] for e in data.excluded).most_common(10)
            ],
        },
        "agreement": agreement_stats(data.answers),
        "files": {},
    }
    for name, path in sorted(files.items()):
        with path.open(encoding="utf-8", newline="") as fh:
            n_rows = sum(1 for _ in csv.reader(fh)) - 1
        manifest["files"][name] = {"sha256": sha256_file(path), "rows": n_rows}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "DATASET_CARD.md").write_text(render_card(manifest, spec), encoding="utf-8")
    return manifest


def _table(header: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def render_card(manifest: dict, spec: dict) -> str:
    """Dataset card generated only from the manifest and tier_spec (no hand-typed numbers)."""
    c, th = manifest["counts"], spec["thresholds"]
    tier_rows = []
    for tier in spec["core_tiers"] + spec["edge_tiers"]:
        rule, rng = spec["plan_rules"][tier], spec["normalized_mark_ranges"][tier]
        lo = ("(" if rng.get("min_exclusive") else "[") + f"{rng['min']:g}"
        hi = f"{rng['max']:g}" + (")" if rng.get("max_exclusive") else "]")
        tier_rows.append(
            [tier, rule["kind"], rule.get("description", ""), f"{lo}, {hi}", c["answers_by_tier"].get(tier, 0)]
        )
    chain = " ; ".join(f"{x['higher']} {'>' if x['strict'] else '>='} {x['lower']}" for x in spec["order_chain"])
    ag = manifest["agreement"]
    ag_rows = [[t, v["n"], v["level_agreement"], v["needs_review_rate"]] for t, v in ag["per_tier"].items()]
    files_rows = [[n, f["rows"], f["sha256"][:16] + "..."] for n, f in manifest["files"].items()]
    parts = [
        f"# C3 Synthetic Marking Dataset {manifest['dataset_version']}",
        "",
        "_Generated file. Every number below is read from `manifest.json` and `tier_spec.json`._",
        "",
        "## Status and provenance",
        f"- expert_validation: **{manifest['expert_validation']}** (no human has verified labels or rubrics; "
        f"rubric_status = `{manifest['rubric_status']}`).",
        f"- Generator: `{manifest.get('generator_provider')}` / `{manifest['generator_model']}`; "
        f"independent blind-grader: `{manifest.get('verifier_provider')}` / `{manifest['verifier_model']}` "
        f"(same model family as generator: {manifest.get('verifier_same_model_family_as_generator')}).",
        f"- Seed: {manifest['seed']}; answers per core tier per question: {manifest['n_per_tier']}.",
        f"- tier_spec sha256: `{manifest['tier_spec_sha256']}`.",
        "- Questions are cut verbatim from the exam source; reference answers, rubrics, student answers and labels are "
        "LLM-drafted. Labels are sums of explicit rubric level marks chosen by a planner, never percentage formulas.",
        "- Prompt template hashes (sha256): "
        + ", ".join(f"{k}=`{v[:12]}`" for k, v in manifest["prompt_hashes"].items()),
        "",
        "## Counts",
        _table(
            ["quantity", "value"],
            [[k, v] for k, v in c.items() if not isinstance(v, dict)],
        ),
        "",
        "Answers by split: " + ", ".join(f"{k}={v}" for k, v in c["answers_by_split"].items()),
        "Questions by split: " + ", ".join(f"{k}={v}" for k, v in c["questions_by_split"].items()),
        "Exclusions by class: " + (", ".join(f"{k}={v}" for k, v in c["excluded_by_class"].items()) or "none"),
        "Exclusions by reason: " + (", ".join(f"{k}={v}" for k, v in c["excluded_by_reason"].items()) or "none"),
        "",
        "## Tiers and label rules",
        f"Required per-question ordering of tier means: {chain}; IRRELEVANT is always 0.",
        "",
        _table(["tier", "plan rule", "description", "allowed normalized mark", "answers"], tier_rows),
        "",
        "Style (concise/standard/verbose) and register (formal/informal/minor_typos) are drawn independently of tier.",
        "",
        "## Validation thresholds enforced by `validate_dataset.py`",
        f"Label-ratio concentration check (`max_share_on_top7_ratios` = {th['max_share_on_top7_ratios']}): "
        f"{th['ratio_metric_scope']}.",
        "",
        _table(["threshold", "value"], [[k, v] for k, v in th.items() if not isinstance(v, dict)]),
        "",
        "## Blind-grader agreement (verification only; flagged rows are kept with needs_review=True)",
        f"Graded answers: {ag['n_graded']}; overall exact level agreement: {ag['overall_level_agreement']}; "
        f"flagged needs_review: {ag['needs_review']}.",
        "",
        _table(["tier", "n", "level agreement", "needs_review rate"], ag_rows) if ag_rows else "No graded answers.",
        "",
        "## Files",
        _table(["file", "rows", "sha256 (prefix)"], files_rows),
        "",
        "## Known limitations",
        "- All content is synthetic and unverified by humans; use `expert_review_sample.csv` for human validation.",
        "- Blind-grader agreement is a consistency check between two LLM calls, not ground truth.",
        "- Questions that need code, diagrams or unavailable figures are excluded (see `excluded_questions.csv`).",
        "",
    ]
    return "\n".join(parts)
