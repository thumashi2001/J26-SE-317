"""CLI: build the C3-v6 synthetic marking dataset with a real LLM (never simulated).

python datasets/generate_c3_dataset.py --dry-run          # deterministic stats only, no API key needed
python datasets/generate_c3_dataset.py --preflight        # verify the generator/verifier models exist (needs keys)
python datasets/generate_c3_dataset.py --limit 3          # first 3 source questions (needs the keys below)
python datasets/generate_c3_dataset.py                    # full run; add --resume to continue from the cache

Roles (set in ai-services/c3/.env or the environment; real environment variables win over .env):
  generator  Gemini  model C3_GENERATOR_MODEL (default gemini-2.5-pro)       key GEMINI_API_KEY
  verifier   C3_VERIFIER_PROVIDER = openai (default) | gemini, model C3_VERIFIER_MODEL
             keys OPENAI_API_KEY or GEMINI_API_KEY respectively
A real run first verifies every required model (preflight.json) and aborts with exit 2 if one is unavailable.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datasets.generator import C3_ROOT, DEFAULT_SEED, load_tier_spec  # noqa: E402
from datasets.generator.roles import (  # noqa: E402
    RoleConfigError,
    load_env,
    missing_key_vars,
    resolve_roles,
    role_meta,
    verifier_cache_name,
)
from datasets.generator.source import SOURCE_CSV, dry_run_stats, load_source  # noqa: E402
from services.llm.preflight import preflight_or_report  # noqa: E402

DEFAULT_OUT = C3_ROOT / "datasets" / "c3_synthetic_v6"


def estimate_calls(n_questions: int, n_per_tier: int, n_core: int = 6) -> dict[str, int]:
    """Upper-ish estimate assuming ~20% of questions are excluded and ~1.2 parts per kept question."""
    parts = round(n_questions * 0.8 * 1.2)
    llm_edge = 3
    return {
        "structure_question": n_questions,
        "draft_rubric": parts,
        "generate_answers": parts * (n_core + llm_edge),
        "blind_grade": parts * (n_core * n_per_tier + llm_edge),
        "retries_and_regeneration_allowance": round(parts * 2.5),
    }


def print_roles(args: argparse.Namespace) -> None:
    """Which provider/model plays each role and which variable NAMES must be set (values are never printed)."""
    print("Roles (no calls are made in dry-run):")
    try:
        generator, verifier = resolve_roles()
    except RoleConfigError as exc:
        print(f"  ERROR: {exc}")
        return
    for role in (generator, verifier):
        state = "set" if role.build().is_available() else "NOT SET"
        print(
            f"  {role.name:<9} {role.provider} / {role.model}   model var: {role.model_env}   "
            f"required env: {role.key_env} ({state})"
        )
    meta = role_meta(generator, verifier)
    print(f"  verifier_same_model_family_as_generator: {meta['verifier_same_model_family_as_generator']}")
    print(f"  verifier cache file: {args.out / '_llm_cache' / verifier_cache_name(verifier)}")
    print("  selection vars: C3_GENERATOR_MODEL, C3_VERIFIER_PROVIDER (gemini|openai; default openai),")
    print("                  C3_VERIFIER_MODEL")


def run_dry(args: argparse.Namespace, spec: dict) -> int:
    questions = load_source(limit=args.limit)
    stats = dry_run_stats(questions, spec["thresholds"]["max_ocr_noise_ratio"])
    print(f"DRY RUN (no LLM, no API key needed). Source: {SOURCE_CSV}")
    print(f"seed={args.seed} n_per_tier={args.n_per_tier} out={args.out}")
    print(f"source questions: {stats['questions']}  total marks: {stats['total_marks']:g}")
    print(f"modules: {', '.join(stats['modules'])}")
    print(f"mark scales (marks: count): {stats['mark_scales']}")
    print(f"OCR-noise flagged (> {spec['thresholds']['max_ocr_noise_ratio']}): {len(stats['ocr_flagged'])}")
    print(f"regex multi-part marker candidates: {len(stats['multipart_marker_candidates'])}")
    print(f"code/diagram keyword hints (LLM decides scope): {len(stats['code_or_diagram_hints'])}")
    print("Answers planned per kept question part:")
    for tier in spec["core_tiers"]:
        print(f"  {tier:<16} x{args.n_per_tier}   ({spec['plan_rules'][tier]['kind']})")
    for tier in spec["edge_tiers"]:
        kind = "deterministic" if tier in spec["deterministic_tiers"] else "LLM"
        print(f"  {tier:<16} x1   ({kind})")
    print("Estimated LLM calls:", estimate_calls(stats["questions"], args.n_per_tier))
    print_roles(args)
    print("Kept/excluded counts need the LLM scope step and are not reported in dry-run.")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_env()  # ai-services/c3/.env; real environment variables still win
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--limit", type=int, default=None, help="only the first N source questions")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preflight", action="store_true", help="only verify the required models exist, then exit")
    ap.add_argument("--resume", action="store_true", help="reuse an existing _llm_cache instead of refusing")
    ap.add_argument("--n-per-tier", type=int, default=2)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--workers", type=int, default=1, help="parallel questions (rate limit: C3_LLM_RPM)")
    args = ap.parse_args(argv)
    spec = load_tier_spec()
    if args.dry_run:
        return run_dry(args, spec)

    from datasets.generator.llm_tasks import LLMTasks
    from datasets.generator.pipeline import Pipeline, cache_dir
    from datasets.generator.writer import write_release
    from services.llm.cache import CachedLLMProvider

    try:
        gen_role, ver_role = resolve_roles()
    except RoleConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    missing = missing_key_vars([gen_role, ver_role])
    if missing:
        print(
            "ERROR: required API key variable(s) not configured: "
            + ", ".join(missing)
            + ". Refusing to generate (no simulated fallback).",
            file=sys.stderr,
        )
        return 2
    cdir = cache_dir(args.out)
    if not args.preflight and cdir.exists() and any(cdir.iterdir()) and not args.resume:
        print(f"ERROR: {cdir} already has cached responses; pass --resume to reuse them.", file=sys.stderr)
        return 2
    ok, summary = preflight_or_report([gen_role.requirement, ver_role.requirement], args.out / "preflight.json")
    print("Model preflight:\n" + summary)
    if not ok:
        print(f"ERROR: model preflight failed; nothing generated (see {args.out / 'preflight.json'}).", file=sys.stderr)
        return 2
    if args.preflight:
        return 0
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tasks = LLMTasks(
        CachedLLMProvider(gen_role.build(), cdir / "generator.jsonl"),
        CachedLLMProvider(ver_role.build(), cdir / verifier_cache_name(ver_role)),
        spec,
    )
    pipe = Pipeline(
        tasks, spec, args.seed, args.n_per_tier, gen_role.model, ver_role.model, workers=args.workers,
        extra_meta=role_meta(gen_role, ver_role),
    )  # fmt: skip
    data, failures = pipe.run(load_source(limit=args.limit))
    if failures or data is None:
        print(f"FAILED: {len(failures)} failure(s); nothing written. Re-run with --resume.", file=sys.stderr)
        for f in failures:
            print(f"  - {f['question_id']} [{f['task']}] {f['key']}: {f['message']}", file=sys.stderr)
        return 1
    manifest = write_release(args.out, data, spec, args.seed)
    print(f"Wrote C3 dataset {manifest['dataset_version']} to {args.out}: {manifest['counts']}")
    from datasets.validate_dataset import build_report, print_report, validate_with_stats

    violations, stats = validate_with_stats(args.out)
    print_report(violations, stats)
    report = args.out / "validation_report.json"
    report.write_text(json.dumps(build_report(args.out, violations, stats), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote validation report to {report}")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
