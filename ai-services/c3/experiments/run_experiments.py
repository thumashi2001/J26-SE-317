"""
AdaptiveLearnSE Component 3 — Experiment runner for conditions baseline, A, B, C, D, E, F.

    python experiments/run_experiments.py --smoke
    python experiments/run_experiments.py --conditions baseline,E,A,B,C,D,F --providers gemini,openai
    python experiments/run_experiments.py --preflight --conditions A,B,C,F --providers gemini,openai   # needs keys

All LLM/embedding/Neo4j calls are real. Outputs (predictions CSV, summary JSON, results table,
run manifest) are written to experiments/results/<run_id>/ and contain only measured values.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from datasets.loader import load_release  # noqa: E402
from experiments import conditions as cond  # noqa: E402
from experiments import framework as fw  # noqa: E402
from services.llm.gemini_provider import GeminiProvider  # noqa: E402
from services.llm.openai_provider import OpenAIProvider  # noqa: E402
from services.llm.preflight import ModelRequirement, preflight_or_report  # noqa: E402
from services.rag.embeddings import get_embedding_provider  # noqa: E402

ALL_CONDITIONS = ["baseline", "E", "A", "B", "C", "D", "F"]


def _ctx(run_id, condition, provider, model, release, split, prompt_hash, extra=None) -> fw.RunContext:
    return fw.RunContext(run_id, condition, provider, model, release.version, split, prompt_hash, extra or {})


def _prompt_hash(condition: str) -> str:
    import inspect

    sources = {"A": fw.prompt_condition_a, "B": fw.prompt_rubric, "C": fw.prompt_rubric, "D": fw.prompt_rubric,
               "F": fw.prompt_rubric}
    fn = sources.get(condition)
    return fw.sha256_text(inspect.getsource(fn) + fw.SYSTEM_PROMPT) if fn else "n/a (no prompt)"


def results_table(summaries: list[dict]) -> str:
    header = ("| Condition | Provider | Model | n scored / failed | MAE | nMAE | RMSE | r | within ±2 marks % | "
              "within 10% of max % |\n|---|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    for s in summaries:
        m = s["metrics"]
        o = m.get("overall")
        if not o:
            rows.append(
                f"| {s['condition']} | {s['provider']} | {s['model']} | 0 / {m['n_failed']} | - | - | - | - | - | - |"
            )
            continue
        rows.append(
            f"| {s['condition']} | {s['provider']} | {s['model']} | {m['n_scored']} / {m['n_failed']} | {o['mae']} | "
            f"{o['normalized_mae']} | {o['rmse']} | {o['pearson_r']} | {o['within_2_marks_pct']} | "
            f"{o['within_10pct_of_max_pct']} |"
        )
    return header + "\n".join(rows) + "\n"


def required_models(conds: list[str], providers: list[str], f_provider: str | None = None) -> list[ModelRequirement]:
    """Remote models the requested conditions will call (local/deterministic conditions need none)."""
    reqs: list[ModelRequirement] = []

    def add(role: str, provider: str, model: str, kind: str = "llm") -> None:
        if not any((r.provider, r.model, r.kind) == (provider, model, kind) for r in reqs):
            reqs.append(ModelRequirement(role, provider, model, kind))

    def llm_model(provider: str) -> str | None:
        return {"gemini": GeminiProvider, "openai": OpenAIProvider}[provider]().model if provider in (
            "gemini", "openai") else None

    wanted = [(p, "llm") for c in conds if c in cond.LLM_CONDITIONS for p in providers]
    if "F" in conds:
        wanted.append((f_provider or os.getenv("C3_LLM_PROVIDER", "gemini"), "llm"))
    for provider, _ in wanted:
        model = llm_model(provider)
        if model:
            add(f"llm:{provider}", provider, model)
    if "C" in conds or "F" in conds:
        embedder = get_embedding_provider()
        add("embedding", embedder.provider_name, embedder.model, "embedding")
    return reqs


def run_model_preflight(reqs: list[ModelRequirement], out_dir: Path) -> bool:
    ok, summary = preflight_or_report(reqs, out_dir / "preflight.json", probe=True)
    print("Model preflight:\n" + summary)
    if not ok:
        print(f"ERROR: model preflight failed; no experiment call was made (see {out_dir / 'preflight.json'}).")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", default=",".join(ALL_CONDITIONS))
    ap.add_argument("--providers", default="gemini,openai")
    ap.add_argument("--split", default="test", choices=["train", "validation", "test"])
    ap.add_argument("--limit", type=int, default=None, help="deterministic subset size per condition")
    ap.add_argument("--smoke", action="store_true", help="5 answers per condition per provider")
    ap.add_argument("--release", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--f-provider", default=None, help="provider whose rubric-LLM (condition B) feeds F")
    ap.add_argument("--preflight", action="store_true",
                    help="only verify that every required model exists (needs API keys), then exit")
    args = ap.parse_args()

    conds = [c.strip() for c in args.conditions.split(",") if c.strip()]
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    limit = 5 if args.smoke else args.limit
    run_id = args.run_id or (("smoke_" if args.smoke else "run_") + time.strftime("%Y%m%d_%H%M%S"))
    out_dir = fw.RESULTS_ROOT / run_id
    reqs = required_models(conds, providers, args.f_provider)
    if args.preflight:
        if not reqs:
            print("No remote model is required by the requested conditions; nothing to verify.")
            return 0
        return 0 if run_model_preflight(reqs, out_dir) else 2
    if reqs and not run_model_preflight(reqs, out_dir):  # never substitute a model: abort before any call
        return 2
    release = load_release(args.release)
    if release.manifest.get("expert_validation") is not False:
        print("WARNING: manifest does not declare expert_validation=false")
    print(f"Run {run_id} | dataset {release.version} | split={args.split} | limit={limit}")

    summaries: list[dict] = []
    e_preds = None
    failures: list[str] = []

    def record(name, ctx, preds, extra):
        s = fw.write_run(out_dir, name, ctx, preds, extra)
        summaries.append(s)
        o = s["metrics"].get("overall")
        print(f"  [{name}] scored={s['metrics']['n_scored']} failed={s['metrics']['n_failed']} "
              f"MAE={o['mae'] if o else 'n/a'}")
        return s

    if "baseline" in conds:
        preds = cond.run_lexical_baseline(release, args.split, limit)
        record("baseline", _ctx(run_id, "baseline", "lexical", "token-cosine", release, args.split, "n/a"), preds, {})
    if "E" in conds:
        e_preds = cond.run_condition_e(release, args.split, limit)
        record("E", _ctx(run_id, "E", "deterministic", "services.marking baseline-v1", release, args.split, "n/a"),
               e_preds, {})

    llm_preds: dict[tuple[str, str], pd.DataFrame] = {}
    for cname in [c for c in conds if c in cond.LLM_CONDITIONS]:
        for provider in providers:
            try:
                preds, info = cond.run_llm_condition(release, args.split, cname, provider, limit,
                                                     cache_dir=fw.RESULTS_ROOT / "llm_cache")
            except (cond.ConditionError, Exception) as exc:  # noqa: BLE001 - surfaced, never swallowed
                failures.append(f"{cname}/{provider}: {type(exc).__name__}: {exc}")
                print(f"  [{cname}_{provider}] NOT RUN: {exc}")
                continue
            llm_preds[(cname, provider)] = preds
            model = ",".join(info["model_identifiers"]) or info["provider_model_setting"]
            record(f"{cname}_{provider}", _ctx(run_id, cname, provider, model, release, args.split,
                                               _prompt_hash(cname), {"llm_info": info}), preds, {})

    if "F" in conds:
        try:
            f_provider = args.f_provider or os.getenv("C3_LLM_PROVIDER", "gemini")
            embedder = get_embedding_provider(cache_file=fw.RESULTS_ROOT / "embedding_cache.jsonl")
            bounds = cond.similarity_bounds(release, embedder)
            val_e = cond.run_condition_e(release, "validation", limit)
            val_l, _ = cond.run_llm_condition(release, "validation", "B", f_provider, limit,
                                              cache_dir=fw.RESULTS_ROOT / "llm_cache")
            params = cond.fit_condition_f(cond.build_f_features(release, "validation", val_e, val_l, embedder, bounds))
            test_e = (e_preds if (e_preds is not None and args.split == "test")
                      else cond.run_condition_e(release, args.split, limit))
            test_l = llm_preds.get(("B", f_provider))
            if test_l is None:
                test_l, _ = cond.run_llm_condition(release, args.split, "B", f_provider, limit,
                                                   cache_dir=fw.RESULTS_ROOT / "llm_cache")
            feat = cond.build_f_features(release, args.split, test_e, test_l, embedder, bounds)
            feat["predicted_mark"] = cond.apply_condition_f(feat, params)
            feat["failed"] = False
            feat["error_message"] = ""
            feat["real_execution"] = True
            feat["needs_review"] = ""
            n_dropped = len(release.split_answers(args.split)) - len(feat) if not limit else None
            record("F", _ctx(run_id, "F", f"{f_provider}+{embedder.provider_name}",
                             f"E+embedding({embedder.model})+B", release, args.split, _prompt_hash("F"),
                             {"fusion_params_fit_on": "validation", "fusion_params": params,
                              "similarity_bounds_fit_on": "train", "similarity_bounds": list(bounds),
                              "rows_dropped_for_missing_component": n_dropped}),
                   feat, {})
        except Exception as exc:  # noqa: BLE001
            failures.append(f"F: {type(exc).__name__}: {exc}")
            print(f"  [F] NOT RUN: {exc}")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results_table.md").write_text(results_table(summaries), encoding="utf-8")
    manifest = {"run_id": run_id, "dataset_version": release.version, "split": args.split, "limit": limit,
                "commit": fw.git_commit(), "conditions_requested": conds, "providers_requested": providers,
                "summaries": [s["condition"] + ":" + s["provider"] for s in summaries], "not_run": failures}
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(results_table(summaries))
    if failures:
        print("NOT RUN / FAILED:\n  " + "\n  ".join(failures))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
