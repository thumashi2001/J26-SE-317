"""Matched LLM marking comparison: Condition A (no retrieval) vs Condition B (same LLM + Vector RAG) on the v2 TEST split.

The ONLY difference between the conditions is the retrieved EVIDENCE block (see services.rag.rag_marking.build_prompt):
same model, rubric, scoring scale, temperature 0, same answers. Retrieval uses the TRAIN-only corpus.

SAFETY: real LLM calls happen only with --run-live AND a configured provider. Without them the script writes a BLOCKED
artefact (exit 0) and NO marks are produced. Mock/simulated outputs are never generated.

Usage: python -m experiments.rag_vs_norag --out DIR [--provider gemini|openai|local] [--run-live] [--limit N]

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


# Writes an explicit BLOCKED artefact instead of any marks when the live run cannot happen (never fabricates results).
def blocked(out: Path, reason: str, provider: str) -> int:
    art = {"status": "BLOCKED", "reason": reason, "provider_requested": provider,
           "test_answers": int((pd.read_csv(DATASET / "02_controlled_answers_eligible.csv", dtype=str)["split"] == "test").sum()),
           "calls_required": "2 x test answers (conditions A and B)", "results": None,
           "note": "No marks were generated; nothing here is an experimental result."}
    (out / "rag_vs_norag_status.json").write_text(json.dumps(art, indent=1), encoding="utf-8")
    print("BLOCKED:", reason)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--provider", default=os.getenv("C3_LLM_PROVIDER", "gemini"))
    ap.add_argument("--run-live", action="store_true", help="allow real (billable / quota-limited) LLM calls")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.2)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
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
    # Optional fixed-seed subsample for a cheap pilot run on a small free-tier quota.
    if a.limit:
        test = test.sample(n=min(a.limit, len(test)), random_state=20261021).reset_index(drop=True)
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
    df.to_csv(a.out / "rag_vs_norag_predictions.csv", index=False)
    summary = {"status": "EXECUTED", "provider": a.provider, "n_answers": len(test), "corpus_provenance": prov, "per_condition": {}}
    # Failed LLM calls are counted and excluded, never scored as zero.
    for cond, g in df.groupby("condition"):
        ok = g[g["llm_status"] == "ok"]
        if len(ok):
            err = (ok["predicted_mark"].astype(float) / ok["max_marks"] - ok["expected_mark"] / ok["max_marks"]).abs()
            summary["per_condition"][cond] = {"n_ok": int(len(ok)), "n_failed": int(len(g) - len(ok)), "nmae": float(err.mean())}
        else:
            summary["per_condition"][cond] = {"n_ok": 0, "n_failed": int(len(g))}
    (a.out / "rag_vs_norag_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary["per_condition"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
