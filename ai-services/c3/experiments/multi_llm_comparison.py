"""Multi-LLM comparison on identical inputs: several FREE-tier providers x {no RAG, Vector RAG} on the frozen v2 split.

Every provider marks exactly the same answers with the same prompt, rubric, temperature 0 and (for RAG) the same TRAIN-only
retrieval corpus, so differences come from the model and the retrieval block only. Metrics are measured against the
dataset's expected marks, which are tier-derived (not human-marked): treat results as a comparison between models, not as
evidence of human-level marking.

Safety / honesty rules
- Real calls only with --run-live. A provider without credentials is recorded as BLOCKED and skipped; nothing is simulated.
- Failed or invalid calls are counted and excluded, never scored as 0.
- Responses are cached (JSONL) so an interrupted or quota-limited run resumes without repeating paid/limited calls.
- If a provider hits its quota (repeated 429/quota errors) it is stopped and marked quota_exhausted; rerun later to resume.

Usage: python -m experiments.multi_llm_comparison --out DIR --providers groq,openrouter,gemini [--run-live] [--limit N]
                                                   [--split test|validation] [--conditions no_rag,rag]

STATUS: offline research script (run from ai-services/c3). Not used by live marking.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(HERE / ".env")  # keys come from the git-ignored .env and are never printed

from experiments.model_comparison import load_answers_with_reference  # noqa: E402
from services.llm import get_llm_provider  # noqa: E402
from services.llm.base import BaseLLMProvider  # noqa: E402
from services.llm.cache import CachedLLMProvider  # noqa: E402
from services.rag.corpus import build_training_corpus  # noqa: E402
from services.rag.embeddings import get_embedding_provider  # noqa: E402
from services.rag.rag_marking import rag_assess  # noqa: E402
from services.rag.vector_store import CurriculumVectorStore  # noqa: E402

DATASET = HERE / "datasets" / "c3_phase3_v5_repaired_v2"
SEED = 20261021
# Substrings that identify a quota/rate-limit failure in a provider error message.
QUOTA_MARKERS = ("429", "quota", "rate limit", "rate_limit", "resource_exhausted", "too many requests")
# Stop a provider after this many consecutive quota failures (its daily allowance is gone; resume later via the cache).
MAX_CONSECUTIVE_QUOTA_ERRORS = 3


def select_answers(answers: pd.DataFrame, split: str, limit: int | None) -> pd.DataFrame:
    """Same rows for every provider: the split, optionally a fixed-seed subsample (stable order by answer_id)."""
    sub = answers[answers["split"] == split].sort_values("answer_id").reset_index(drop=True)
    if limit and limit < len(sub):
        sub = sub.sample(n=limit, random_state=SEED).sort_values("answer_id").reset_index(drop=True)
    return sub


def _is_quota_error(detail: str | None) -> bool:
    text = (detail or "").lower()
    return any(m in text for m in QUOTA_MARKERS)


def run_provider(name: str, provider: BaseLLMProvider, answers: pd.DataFrame, store: CurriculumVectorStore | None,
                 conditions: tuple[str, ...], top_k: int, threshold: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Mark every answer under every condition with one provider. Returns (rows, run_status)."""
    rows: list[dict[str, Any]] = []
    quota_streak, stopped = 0, None
    for rec in answers.to_dict("records"):
        mx = float(rec["max_marks"])
        # The dataset has one overall criterion per question, so one holistic rubric line is used for all conditions.
        rubric = [{"criterion_id": "C1", "max_marks": mx,
                   "description": "Overall correctness and completeness against the reference answer"}]
        for cond in conditions:
            t0 = time.time()
            res = rag_assess(provider=provider, store=store, question_id=rec["question_id"], question=rec["question_text"],
                             reference_answer=rec["reference_answer"], rubric=rubric, max_marks=mx,
                             student_answer=rec["student_answer"], use_rag=(cond == "rag"), top_k=top_k, threshold=threshold)
            rows.append({"provider": name, "condition": cond, "answer_id": rec["answer_id"], "question_id": rec["question_id"],
                         "tier": rec["answer_quality"], "max_marks": mx, "expected_mark": float(rec["expected_mark"]),
                         "llm_status": res["llm_status"], "predicted_mark": res.get("total_awarded_marks"),
                         "detail": res.get("detail", ""), "model": res.get("model"),
                         # FR-C3-18: record exactly which context was retrieved (empty for no_rag or when nothing passed the threshold)
                         "retrieved": json.dumps([h["citation"] for h in res["retrieval"]["hits"]]),
                         "retrieval_status": res["retrieval"].get("status"), "tokens": res.get("tokens"),
                         "latency_s": round(time.time() - t0, 2)})
            quota_streak = quota_streak + 1 if (res["llm_status"] == "error" and _is_quota_error(res.get("detail"))) else 0
            if quota_streak >= MAX_CONSECUTIVE_QUOTA_ERRORS:
                stopped = "quota_exhausted"
                break
        if stopped:
            break
    return rows, {"stopped": stopped, "rows": len(rows)}


def _qwk(y_true: np.ndarray, y_pred: np.ndarray, bins: int = 11) -> float | None:
    """Quadratic weighted kappa on the mark ratio quantised to 11 bins (same convention as model_comparison)."""
    from sklearn.metrics import cohen_kappa_score

    a, b = np.rint(y_true * (bins - 1)).astype(int), np.rint(y_pred * (bins - 1)).astype(int)
    if len(set(a)) < 2 and len(set(b)) < 2:
        return None
    return float(cohen_kappa_score(a, b, weights="quadratic", labels=list(range(bins))))


def summarise(df: pd.DataFrame) -> dict[str, Any]:
    """Per provider x condition: counts of ok/failed calls and error metrics on the ok rows only."""
    out: dict[str, Any] = {}
    for (prov, cond), g in df.groupby(["provider", "condition"]):
        ok = g[g["llm_status"] == "ok"]
        entry: dict[str, Any] = {"n_calls": int(len(g)), "n_ok": int(len(ok)), "n_failed": int(len(g) - len(ok)),
                                 "failure_reasons": g[g["llm_status"] != "ok"]["llm_status"].value_counts().to_dict()}
        if len(ok):
            y = ok["expected_mark"].to_numpy(float) / ok["max_marks"].to_numpy(float)
            p = ok["predicted_mark"].to_numpy(float) / ok["max_marks"].to_numpy(float)
            err = p - y
            entry.update({"nmae": float(np.abs(err).mean()), "mae_marks": float(np.abs(ok["predicted_mark"].astype(float)
                          - ok["expected_mark"]).mean()), "mean_signed_error": float(err.mean()),
                          "pearson_r": float(np.corrcoef(y, p)[0, 1]) if len(ok) > 2 and p.std() > 0 and y.std() > 0 else None,
                          "qwk_11bins": _qwk(y, p), "mean_latency_s": float(ok["latency_s"].mean())})
        out[f"{prov}|{cond}"] = entry
    return out


def pairwise_agreement(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Mean absolute mark-ratio difference between providers on answers BOTH marked successfully (same condition)."""
    ok = df[df["llm_status"] == "ok"].copy()
    ok["ratio"] = ok["predicted_mark"].astype(float) / ok["max_marks"]
    result = []
    for cond, g in ok.groupby("condition"):
        wide = g.pivot_table(index="answer_id", columns="provider", values="ratio")
        cols = list(wide.columns)
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                both = wide[[a, b]].dropna()
                if len(both):
                    result.append({"condition": cond, "a": a, "b": b, "n_common": int(len(both)),
                                   "mean_abs_diff": float((both[a] - both[b]).abs().mean())})
    return result


def build_store(embedding: str) -> tuple[CurriculumVectorStore, dict[str, Any]]:
    """TRAIN-only retrieval corpus (no test/validation text can be retrieved)."""
    docs, prov = build_training_corpus(DATASET)
    return CurriculumVectorStore(docs, embedding_backend="dense", embedding_provider=get_embedding_provider(embedding)), prov


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--providers", default="groq,openrouter,gemini", help="comma list; use 2-3 free-tier providers")
    ap.add_argument("--conditions", default="no_rag,rag")
    ap.add_argument("--split", default="test", choices=["test", "validation"])
    ap.add_argument("--limit", type=int, default=None, help="fixed-seed subsample (same answers for every provider)")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.2)
    ap.add_argument("--embedding", default="local")
    ap.add_argument("--run-live", action="store_true", help="allow real (quota-limited) LLM calls")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    names = [n.strip() for n in a.providers.split(",") if n.strip()]
    conditions = tuple(c.strip() for c in a.conditions.split(",") if c.strip())

    answers = select_answers(load_answers_with_reference(DATASET), a.split, a.limit)
    status: dict[str, Any] = {}
    usable: dict[str, BaseLLMProvider] = {}
    for n in names:
        try:
            prov = get_llm_provider(n)
        except Exception as exc:  # unknown provider name
            status[n] = {"status": "BLOCKED", "reason": f"{type(exc).__name__}: {exc}"}
            continue
        if not prov.is_available():
            status[n] = {"status": "BLOCKED", "reason": "no credentials configured"}
        else:
            usable[n] = prov
    if not a.run_live or not usable:
        reason = "--run-live not given" if usable else "no provider has credentials"
        art = {"status": "BLOCKED", "reason": reason, "providers": status | {n: {"status": "READY"} for n in usable},
               "answers": len(answers), "calls_per_provider": len(answers) * len(conditions),
               "note": "No marks were generated; nothing here is an experimental result."}
        (a.out / "multi_llm_status.json").write_text(json.dumps(art, indent=1), encoding="utf-8")
        print("BLOCKED:", reason, json.dumps(art["providers"]))
        return 0

    store, corpus_prov = build_store(a.embedding) if "rag" in conditions else (None, None)
    rows: list[dict[str, Any]] = []
    for n, prov in usable.items():
        cached = CachedLLMProvider(prov, a.out / "cache" / f"{n}.jsonl")
        r, st = run_provider(n, cached, answers, store, conditions, a.top_k, a.threshold)
        rows += r
        status[n] = {"status": "EXECUTED" if not st["stopped"] else st["stopped"].upper(), "cache_hits": cached.hits,
                     "cache_misses": cached.misses, "model": getattr(prov, "model", None), **st}
    df = pd.DataFrame(rows)
    df.to_csv(a.out / "multi_llm_predictions.csv", index=False)
    summary = {"dataset": DATASET.name, "split": a.split, "n_answers": len(answers), "conditions": conditions,
               "label_caveat": "expected marks are tier-derived, not human-marked", "corpus_provenance": corpus_prov,
               "provider_status": status, "per_provider_condition": summarise(df) if len(df) else {},
               "pairwise_agreement": pairwise_agreement(df) if len(df) else []}
    (a.out / "multi_llm_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary["per_provider_condition"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
