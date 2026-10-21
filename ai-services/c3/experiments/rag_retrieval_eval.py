"""Retrieval-only evaluation of the Vector RAG index (NOT a marking evaluation).

Corpus: TRAIN-split eligible questions of the frozen v2 dataset (reference answers + expected concepts).
Queries: validation and test questions (question text + reference answer), i.e. what is known at assessment time.
Relevance proxy (no human relevance labels exist): the retrieved document comes from the same module (course) as the query
question. Controls: random retrieval and a TF-IDF index. Also reports the near-duplicate rate (top-1 cosine >= 0.9), which
would indicate that a held-out question is almost identical to a training document.

Usage: python -m experiments.rag_retrieval_eval --out DIR [--embedding local|gemini|openai]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from services.rag.corpus import build_training_corpus  # noqa: E402
from services.rag.embeddings import get_embedding_provider  # noqa: E402
from services.rag.rag_marking import retrieve_evidence  # noqa: E402
from services.rag.vector_store import CurriculumVectorStore  # noqa: E402

DATASET = HERE / "datasets" / "c3_phase3_v5_repaired_v2"
SEED = 20261021


def evaluate(store: CurriculumVectorStore, queries: pd.DataFrame, k: int, threshold: float) -> dict:
    hit_at_k, top1_sims, empty, near_dup, counts = [], [], 0, 0, []
    for q in queries.to_dict("records"):
        res = retrieve_evidence(store, f"{q['question_text']} {q['reference_answer']}", q["question_id"], top_k=k, threshold=threshold)
        hits = res["hits"]
        counts.append(len(hits))
        if not hits:
            empty += 1
            hit_at_k.append(0.0)
            continue
        hit_at_k.append(float(any(h["citation"] and store_module(store, h["doc_id"]) == q["module_code"] for h in hits)))
        top1_sims.append(hits[0]["relevance_score"])
        near_dup += int(hits[0]["relevance_score"] >= 0.9)
    return {"queries": len(queries), "k": k, "threshold": threshold, "same_module_hit_rate_at_k": float(np.mean(hit_at_k)),
            "mean_top1_similarity": float(np.mean(top1_sims)) if top1_sims else None, "empty_retrieval_rate": empty / len(queries),
            "mean_docs_returned": float(np.mean(counts)), "near_duplicate_top1_rate": near_dup / len(queries)}


def store_module(store: CurriculumVectorStore, doc_id: str) -> str:
    return next(d["module_code"] for d in store.docs if d["doc_id"] == doc_id)


def random_control(docs: list[dict], queries: pd.DataFrame, k: int, trials: int = 200) -> float:
    rng = np.random.default_rng(SEED)
    hits = []
    for q in queries.to_dict("records"):
        pool = [d for d in docs if d["question_id"] != q["question_id"]]
        for _ in range(trials):
            pick = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
            hits.append(float(any(pool[i]["module_code"] == q["module_code"] for i in pick)))
    return float(np.mean(hits))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--embedding", default="local")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    docs, prov = build_training_corpus(DATASET)
    qb = pd.read_csv(DATASET / "01_question_bank.csv", dtype=str, keep_default_na=False)
    queries = qb[(qb["split"].isin(["validation", "test"])) & (qb["eligibility_status"] == "eligible")].reset_index(drop=True)
    t0 = time.time()
    embedder = get_embedding_provider(a.embedding)
    dense = CurriculumVectorStore(docs, embedding_backend="dense", embedding_provider=embedder)
    tfidf = CurriculumVectorStore(docs, embedding_backend="tfidf")
    results = {"meta": {"dataset": DATASET.name, "corpus_provenance": prov, "embedding": embedder.diagnostics(),
                        "queries": {"validation": int((queries["split"] == "validation").sum()), "test": int((queries["split"] == "test").sum())},
                        "relevance_proxy": "same module_code as the query question (no human relevance labels exist)",
                        "scope": "retrieval only; says nothing about marking accuracy"}, "runs": []}
    for k, thr in ((1, 0.0), (3, 0.0), (3, 0.3), (5, 0.0)):
        for name, store in (("dense_local_sbert" if a.embedding == "local" else f"dense_{a.embedding}", dense), ("tfidf", tfidf)):
            r = evaluate(store, queries, k, thr)
            r["index"] = name
            results["runs"].append(r)
        results["runs"].append({"index": "random_control", "k": k, "threshold": None,
                                "same_module_hit_rate_at_k": random_control(docs, queries, k), "queries": len(queries)})
    results["runtime_seconds"] = round(time.time() - t0, 1)
    (a.out / "rag_retrieval_eval.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    for r in results["runs"]:
        print(r["index"], "k", r["k"], "thr", r.get("threshold"), "hit", round(r["same_module_hit_rate_at_k"], 3),
              "top1", None if r.get("mean_top1_similarity") is None else round(r["mean_top1_similarity"], 3),
              "empty", r.get("empty_retrieval_rate"), "neardup", r.get("near_duplicate_top1_rate"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
