"""Matched LLM marking comparison: Condition A (no retrieval) vs Condition B (same LLM + Vector RAG) on the v2 TEST split.

The ONLY difference between the conditions is the retrieved EVIDENCE block (see services.rag.rag_marking.build_prompt):
same model, rubric, scoring scale, temperature 0, same answers. Retrieval uses the TRAIN-only corpus.

SAFETY: real LLM calls happen only with --run-live AND a configured provider. Without them the script writes a BLOCKED
artefact (exit 0) and NO marks are produced. Mock/simulated outputs are never generated.

Usage: python -m experiments.rag_vs_norag --out DIR [--provider gemini|openai|local] [--run-live] [--limit N]
       python -m experiments.rag_vs_norag --out DIR --run-live --shard I/K      (one slice of the fixed test order)
       python -m experiments.rag_vs_norag --out DIR --aggregate K              (combine the K finished slices; no LLM calls)

MULTI-DAY RUNS (free-tier quota): the test answers are put in one fixed order (sorted by answer_id) and shard I of K takes
every K-th answer, so the K shards are disjoint and together cover the whole test split no matter when or in which order they
run. Each shard writes its own files and never overwrites another. `--limit N` is a different thing: a fixed-seed random
subsample for a cheap pilot. It is reproducible for the same file, but the sample depends on the row order of the data file, and
the observation that a larger N contains a smaller N's answers holds for the current pandas/numpy only (checked 2026-10-28, not
guaranteed), so --limit is not used for multi-day runs and can not be combined with --shard. The comparison counts as complete
only after --aggregate has verified all K shards.

STATUS: offline research script. BLOCKED while no LLM credentials/quota exist; it then writes a BLOCKED artefact and
produces no marks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(HERE / ".env")  # same behaviour as the FastAPI app: keys come from the git-ignored .env (never printed)

from experiments.model_comparison import load_answers_with_reference  # noqa: E402
from services.llm import get_llm_provider  # noqa: E402
from services.rag.corpus import build_training_corpus  # noqa: E402
from services.rag.embeddings import get_embedding_provider  # noqa: E402
from services.rag.rag_marking import rag_assess  # noqa: E402
from services.rag.vector_store import CurriculumVectorStore  # noqa: E402

DATASET = HERE / "datasets" / "c3_phase3_v5_repaired_v2"
PRED_FILE = "rag_vs_norag_predictions.csv"
SUMMARY_FILE = "rag_vs_norag_summary.json"


# Writes an explicit BLOCKED artefact instead of any marks when the live run cannot happen (never fabricates results).
def blocked(out: Path, reason: str, provider: str) -> int:
    """Write a BLOCKED result (no marks generated) explaining why the live comparison could not run."""
    art = {"status": "BLOCKED", "reason": reason, "provider_requested": provider,
           "test_answers": int((pd.read_csv(DATASET / "02_controlled_answers_eligible.csv", dtype=str)["split"] == "test").sum()),
           "calls_required": "2 x test answers (conditions A and B)", "results": None,
           "note": "No marks were generated; nothing here is an experimental result."}
    (out / "rag_vs_norag_status.json").write_text(json.dumps(art, indent=1), encoding="utf-8")
    print("BLOCKED:", reason)
    return 0


def parse_shard(text: str) -> tuple[int, int]:
    """'I/K' (1-based) -> (I, K); raises ValueError for anything else."""
    try:
        i, k = (int(x) for x in text.split("/"))
    except ValueError as exc:
        raise ValueError(f"--shard must look like 2/9, got {text!r}") from exc
    if not 1 <= i <= k:
        raise ValueError(f"--shard {text}: need 1 <= I <= K")
    return i, k


def select_answers(test: pd.DataFrame, limit: int | None = None, shard: tuple[int, int] | None = None) -> pd.DataFrame:
    """The answers to run: all, a fixed-seed random subsample (--limit) or one deterministic slice (--shard I/K)."""
    if limit and shard:
        raise ValueError("--limit and --shard can not be combined (a subsample can not be extended by later runs)")
    if shard:
        i, k = shard
        ordered = test.sort_values("answer_id").reset_index(drop=True)
        return ordered.iloc[i - 1::k].reset_index(drop=True)
    if limit:
        return test.sample(n=min(limit, len(test)), random_state=20261021).reset_index(drop=True)
    return test


def summarise(df: pd.DataFrame, provider: str, prov: dict, extra: dict | None = None) -> dict:
    """Per-condition counts and nMAE. Failed LLM calls are counted and excluded, never scored as zero."""
    summary = {"status": "EXECUTED", "provider": provider, "n_answers": int(df["answer_id"].nunique()), "corpus_provenance": prov,
               "models": sorted({str(m) for m in df["model"].dropna()}), "per_condition": {}, **(extra or {})}
    for cond, g in df.groupby("condition"):
        ok = g[g["llm_status"] == "ok"]
        if len(ok):
            err = (ok["predicted_mark"].astype(float) / ok["max_marks"] - ok["expected_mark"] / ok["max_marks"]).abs()
            summary["per_condition"][cond] = {"n_ok": int(len(ok)), "n_failed": int(len(g) - len(ok)), "nmae": float(err.mean())}
        else:
            summary["per_condition"][cond] = {"n_ok": 0, "n_failed": int(len(g))}
    return summary


def aggregate_shards(out: Path, k: int, expected_ids: set[str], provider: str, prov: dict) -> dict:
    """Combine shard files 1..K into the full result. Refuses a missing shard, a duplicate answer or an incomplete cover."""
    frames = []
    for i in range(1, k + 1):
        path = out / f"rag_vs_norag_predictions_shard{i}of{k}.csv"
        if not path.exists():
            raise FileNotFoundError(f"shard {i}/{k} has not been run (missing {path.name})")
        frames.append(pd.read_csv(path, dtype={"answer_id": str}))
    df = pd.concat(frames, ignore_index=True)
    per_answer = df.groupby("answer_id")["condition"].nunique()
    if (per_answer != 2).any():
        raise ValueError("every answer must have exactly conditions A and B; a shard is incomplete or overlaps another")
    if df.duplicated(["answer_id", "condition"]).any():
        raise ValueError("an answer appears in more than one shard")
    if set(df["answer_id"]) != set(expected_ids):
        raise ValueError(f"shards cover {df['answer_id'].nunique()} answers, the test split has {len(expected_ids)}")
    df.to_csv(out / PRED_FILE, index=False)
    summary = summarise(df, provider, prov, {"aggregated_from_shards": k})
    (out / SUMMARY_FILE).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    """Compare marking with and without retrieved context; refuses to call a live LLM without --run-live."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--provider", default=os.getenv("C3_LLM_PROVIDER", "gemini"))
    ap.add_argument("--run-live", action="store_true", help="allow real (billable / quota-limited) LLM calls")
    ap.add_argument("--limit", type=int, default=None, help="fixed-seed random subsample for a cheap pilot (depends on file row order; use --shard for multi-day runs)")
    ap.add_argument("--shard", default=None, help="run slice I of K of the fixed test order, e.g. 2/9 (multi-day runs)")
    ap.add_argument("--aggregate", type=int, default=None, metavar="K", help="combine K finished shards; makes no LLM calls")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.2)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    try:
        shard = parse_shard(a.shard) if a.shard else None
        if a.limit and shard:
            raise ValueError("--limit and --shard can not be combined")
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if a.aggregate:
        # No LLM involved: only verifies and merges shard files already produced by live runs.
        ans = load_answers_with_reference(DATASET)
        test_ids = set(ans[ans["split"] == "test"]["answer_id"].astype(str))
        _, prov = build_training_corpus(DATASET)
        try:
            summary = aggregate_shards(a.out, a.aggregate, test_ids, a.provider, prov)
        except (FileNotFoundError, ValueError) as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(summary["per_condition"], indent=1))
        return 0
    try:
        provider = get_llm_provider(a.provider)
    except Exception as exc:
        return blocked(a.out, f"provider '{a.provider}' unavailable: {type(exc).__name__}", a.provider)
    # Gate 1: credentials. Gate 2 (below): the caller must opt in to real, quota-limited calls with --run-live.
    if not provider.is_available():
        return blocked(a.out, f"no credentials configured for '{a.provider}'", a.provider)
    if not a.run_live:
        return blocked(a.out, "live LLM calls not enabled (--run-live not given). Free-tier quota (about 20 requests/day/model) "
                              "cannot cover 2 x 90 calls; OpenAI credit was reported exhausted earlier in the project (not re-probed)", a.provider)

    # TRAIN-only retrieval corpus, so test answers cannot be retrieved as evidence (no leakage).
    docs, prov = build_training_corpus(DATASET)
    store = CurriculumVectorStore(docs, embedding_backend="dense", embedding_provider=get_embedding_provider("local"))
    ans = load_answers_with_reference(DATASET)  # the answers file alone has empty reference answers
    test = ans[ans["split"] == "test"].reset_index(drop=True)
    test = select_answers(test, a.limit, shard)  # all answers, a fixed-seed pilot subsample, or one deterministic shard
    rows = []
    for r in test.to_dict("records"):
        mx = float(r["max_marks"])
        # Dataset has a single overall criterion per question, so one holistic rubric line is used for both conditions.
        rubric = [{"criterion_id": "C1", "description": "Overall correctness and completeness against the reference answer", "max_marks": mx}]
        # Same model, prompt, rubric and answer in both conditions; only the retrieved EVIDENCE block differs.
        for use_rag in (False, True):
            t0 = time.time()
            res = rag_assess(provider=provider, store=store, question_id=r["question_id"], question=r["question_text"],
                             reference_answer=r["reference_answer"], rubric=rubric, max_marks=mx, student_answer=r["student_answer"],
                             use_rag=use_rag, top_k=a.top_k, threshold=a.threshold)
            rows.append({"answer_id": r["answer_id"], "question_id": r["question_id"], "tier": r["answer_quality"], "condition": res["condition"],
                         "max_marks": mx, "expected_mark": float(r["expected_mark"]), "llm_status": res["llm_status"],
                         "predicted_mark": res.get("total_awarded_marks"), "retrieved": json.dumps([h["citation"] for h in res["retrieval"]["hits"]]),
                         "latency_s": round(time.time() - t0, 2), "tokens": res.get("tokens"), "model": res.get("model")})
    df = pd.DataFrame(rows)
    run_config = {"top_k": a.top_k, "threshold": a.threshold, "dataset": DATASET.name, "limit": a.limit,
                  "shard": f"{shard[0]}/{shard[1]}" if shard else None}
    # A shard writes its own files so a later shard never overwrites an earlier one; --aggregate builds the full result.
    tag = f"_shard{shard[0]}of{shard[1]}" if shard else ""
    df.to_csv(a.out / PRED_FILE.replace(".csv", f"{tag}.csv"), index=False)
    summary = summarise(df, a.provider, prov, {"run_config": run_config})
    (a.out / SUMMARY_FILE.replace(".json", f"{tag}.json")).write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary["per_condition"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
