"""
AdaptiveLearnSE Component 3 — Experimental conditions A-F (real execution only).

  baseline  Lexical token-overlap cosine to the reference answer x max marks.
  A         Zero-shot LLM (question + answer only).
  B         LLM + criterion-level rubric (levels chosen by the LLM, marks derived from the rubric).
  C         B + dense vector RAG over TRAIN-split reference answers only (no leakage).
  D         B + GraphRAG over the live Neo4j CCKG (strict: fails if Neo4j is unreachable).
  E         Deterministic concept-evidence + rubric engine (services.marking, no LLM).
  F         Combined: E gating + embedding similarity + rubric-LLM judgement; weights tuned on
            VALIDATION only, then frozen for the test split.

Every LLM call goes through CachedLLMProvider so a re-run reproduces the recorded real responses.
"""

import itertools
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.schemas.marking import MarkingRequest
from datasets.loader import Release
from experiments import framework as fw
from services.cckg.graph_adapter import CCKGGraphAdapter
from services.llm import CachedLLMProvider, LLMRequest, get_llm_provider
from services.marking.marking_engine import mark_answer
from services.rag.embeddings import get_embedding_provider
from services.rag.vector_store import CurriculumVectorStore
from services.semantic.baseline import lexical_cosine_similarity

LLM_CONDITIONS = ("A", "B", "C", "D")


class ConditionError(RuntimeError):
    pass


def _select(release: Release, split: str, limit: int | None) -> pd.DataFrame:
    answers = release.split_answers(split)
    if limit:
        # deterministic stratified smoke subset: first `limit` rows after a seeded shuffle
        answers = answers.sample(n=min(limit, len(answers)), random_state=20261021).reset_index(drop=True)
    return answers


def _row_base(row: pd.Series) -> dict[str, Any]:
    return {
        "answer_id": row["answer_id"],
        "question_id": row["question_id"],
        "tier": row["tier"],
        "expected_mark": float(row["expected_mark"]),
        "max_marks": float(row["max_marks"]),
        "needs_review": row["needs_review"],
    }


# ----------------------------------------------------------------------------- baseline and E


def run_lexical_baseline(release: Release, split: str, limit: int | None = None) -> pd.DataFrame:
    rows = []
    for _, row in _select(release, split, limit).iterrows():
        q = release.question(row["question_id"])
        sim = lexical_cosine_similarity(row["student_answer"], q["reference_answer"])
        rows.append({**_row_base(row), "predicted_mark": sim * float(row["max_marks"]), "failed": False,
                     "error_message": "", "real_execution": True})
    return pd.DataFrame(rows)


def _marking_request(release: Release, row: pd.Series) -> MarkingRequest:
    q = release.question(row["question_id"])
    return MarkingRequest.model_validate(
        {
            "question_id": row["question_id"],
            "question_text": q["question_text"],
            "student_answer": row["student_answer"],
            "reference_answer": q["reference_answer"],
            "expected_concepts": q["expected_concepts"],
            "answer_type": "structured",
            "rubric": release.rubric_for(row["question_id"]),
        }
    )


def run_condition_e(release: Release, split: str, limit: int | None = None) -> pd.DataFrame:
    rows = []
    for _, row in _select(release, split, limit).iterrows():
        base = _row_base(row)
        try:
            result = mark_answer(_marking_request(release, row))
            rows.append({**base, "predicted_mark": float(result.total_awarded_marks), "failed": False,
                         "error_message": "", "real_execution": True})
        except Exception as exc:
            rows.append({**base, "predicted_mark": np.nan, "failed": True,
                         "error_message": f"{type(exc).__name__}: {exc}", "real_execution": True})
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- LLM conditions


def make_provider(provider_name: str, cache_dir: Path, model_override: str | None = None):
    provider = get_llm_provider(provider_name)
    if model_override:
        provider.model = model_override
    if not provider.is_available():
        raise ConditionError(f"Provider '{provider_name}' has no credentials; set its API key in .env")
    return CachedLLMProvider(provider, cache_dir / f"{provider_name}.jsonl")


def build_train_corpus(release: Release) -> list[dict[str, Any]]:
    """Retrieval corpus = reference answers of TRAIN questions only (never validation/test)."""
    train = release.split_questions("train")
    return [
        {
            "doc_id": q["question_id"],
            "title": q["question_text"][:90],
            "content": q["reference_answer"],
            "citation": f"train:{q['question_id']}",
        }
        for _, q in train.iterrows()
    ]


class ContextBuilder:
    """Per-question context for conditions C and D, computed once and reused for every answer."""

    def __init__(self, release: Release, condition: str, embedding_provider: str | None = None):
        self.condition = condition
        self.release = release
        self._cache: dict[str, str] = {}
        self.store = None
        self.graph = None
        if condition == "C":
            embedder = get_embedding_provider(embedding_provider, cache_file=fw.RESULTS_ROOT / "embedding_cache.jsonl")
            self.store = CurriculumVectorStore(build_train_corpus(release), embedding_backend="dense",
                                               embedding_provider=embedder)
        elif condition == "D":
            self.graph = CCKGGraphAdapter(strict=True)  # raises if Neo4j is not live

    def for_question(self, question_id: str) -> str:
        if question_id in self._cache:
            return self._cache[question_id]
        q = self.release.question(question_id)
        if self.condition == "C":
            hits = [h for h in self.store.retrieve(q["question_text"], top_k=4, threshold=0.0)
                    if h["doc_id"] != question_id][:3]
            text = fw.context_block_rag(hits)
        elif self.condition == "D":
            text = fw.context_block_graph(self.graph.retrieve_graphrag_context(question_id, concepts=q["expected_concepts"]))
        else:
            text = ""
        self._cache[question_id] = text
        return text


def run_llm_condition(
    release: Release,
    split: str,
    condition: str,
    provider_name: str,
    limit: int | None = None,
    cache_dir: Path | None = None,
    model_override: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if condition not in LLM_CONDITIONS:
        raise ConditionError(f"Unknown LLM condition {condition}")
    cache_dir = cache_dir or fw.RESULTS_ROOT / "llm_cache"
    provider = make_provider(provider_name, cache_dir, model_override)
    ctx = ContextBuilder(release, condition) if condition in ("C", "D") else None
    rows, model_ids = [], set()
    hits = misses = 0

    for _, row in _select(release, split, limit).iterrows():
        q = release.question(row["question_id"])
        base = _row_base(row)
        if condition == "A":
            prompt = fw.prompt_condition_a(q, row["student_answer"])
            rubric = None
        else:
            rubric = release.rubric_for(row["question_id"])
            prompt = fw.prompt_rubric(q, rubric, row["student_answer"], ctx.for_question(row["question_id"]) if ctx else "")
        res = provider.generate(LLMRequest(prompt=prompt, system_prompt=fw.SYSTEM_PROMPT, temperature=0.0,
                                           max_tokens=1024, response_format="json", timeout_seconds=90.0))
        model_ids.add(res.model_identifier)
        hits, misses = hits + int(res.cached), misses + int(not res.cached)
        meta = {"latency_ms": res.latency_ms, "tokens": res.usage.total_tokens, "cached": res.cached,
                "real_execution": res.is_real_execution, "model_identifier": res.model_identifier}
        try:
            if not res.is_success:
                raise fw.ParseError(res.error_message or "provider call failed")
            if condition == "A":
                mark, chosen = fw.parse_total_mark(res.parsed_json, float(row["max_marks"])), None
            else:
                mark, chosen = fw.parse_level_selection(res.parsed_json, rubric)
            rows.append({**base, **meta, "predicted_mark": mark, "failed": False, "error_message": "",
                         "chosen_levels": json.dumps(chosen) if chosen else ""})
        except fw.ParseError as exc:
            rows.append({**base, **meta, "predicted_mark": np.nan, "failed": True, "error_message": str(exc),
                         "chosen_levels": ""})

    info = {"model_identifiers": sorted(model_ids), "cache_hits": hits, "cache_misses": misses,
            "provider_model_setting": getattr(provider.inner, "model", None)}
    return pd.DataFrame(rows), info


# ----------------------------------------------------------------------------- condition F


def _norm(df: pd.DataFrame, col: str) -> np.ndarray:
    return (df[col].to_numpy(dtype=float) / df["max_marks"].to_numpy(dtype=float)).clip(0.0, 1.0)


def fit_condition_f(feat: pd.DataFrame, step: float = 0.1) -> dict[str, float]:
    """Grid-search fusion weights on VALIDATION features: pred = wE*E + wL*L + wS*S (all in [0,1]).

    A gate zeroes the prediction when E scores 0 and similarity is below tau. The objective is
    normalised MAE against gold marks on the validation split only.
    """
    target = _norm(feat, "expected_mark")
    e, lm, s = feat["e_norm"].to_numpy(), feat["l_norm"].to_numpy(), feat["s_norm"].to_numpy()
    best: dict[str, float] | None = None
    grid = np.arange(0.0, 1.0 + 1e-9, step)
    for w_e, w_l in itertools.product(grid, grid):
        w_s = 1.0 - w_e - w_l
        if w_s < -1e-9:
            continue
        for tau in (0.0, 0.1, 0.2, 0.3, 0.4):
            pred = w_e * e + w_l * lm + max(w_s, 0.0) * s
            pred = np.where((e == 0.0) & (s < tau), 0.0, pred)
            loss = float(np.abs(pred - target).mean())
            if best is None or loss < best["val_nmae"] - 1e-12:
                best = {"w_e": round(float(w_e), 3), "w_l": round(float(w_l), 3), "w_s": round(float(max(w_s, 0.0)), 3),
                        "tau": tau, "val_nmae": round(loss, 5)}
    assert best is not None
    return best


def apply_condition_f(feat: pd.DataFrame, params: dict[str, float]) -> np.ndarray:
    e, lm, s = feat["e_norm"].to_numpy(), feat["l_norm"].to_numpy(), feat["s_norm"].to_numpy()
    pred = params["w_e"] * e + params["w_l"] * lm + params["w_s"] * s
    pred = np.where((e == 0.0) & (s < params["tau"]), 0.0, pred)
    return pred.clip(0.0, 1.0) * feat["max_marks"].to_numpy(dtype=float)


def similarity_features(release: Release, answers: pd.DataFrame, embedder) -> np.ndarray:
    """Cosine similarity (real embeddings) between each student answer and its question's reference."""
    refs = [release.question(q)["reference_answer"] for q in answers["question_id"]]
    a = embedder.embed(list(answers["student_answer"].replace("", " ")), task="document")
    r = embedder.embed(refs, task="document")
    return np.einsum("ij,ij->i", a, r)


def build_f_features(
    release: Release, split: str, e_preds: pd.DataFrame, l_preds: pd.DataFrame, embedder, sim_bounds: tuple[float, float]
) -> pd.DataFrame:
    answers = release.split_answers(split)
    sims = similarity_features(release, answers, embedder)
    lo, hi = sim_bounds
    feat = pd.DataFrame({"answer_id": answers["answer_id"], "question_id": answers["question_id"],
                         "tier": answers["tier"], "expected_mark": answers["expected_mark"].astype(float),
                         "max_marks": answers["max_marks"].astype(float), "s_norm": ((sims - lo) / (hi - lo)).clip(0, 1)})
    e = e_preds.set_index("answer_id")
    l_ = l_preds.set_index("answer_id")
    feat = feat[feat["answer_id"].isin(e.index) & feat["answer_id"].isin(l_.index)].copy()
    feat = feat[~e.loc[feat["answer_id"], "failed"].to_numpy() & ~l_.loc[feat["answer_id"], "failed"].to_numpy()]
    feat["e_norm"] = (e.loc[feat["answer_id"], "predicted_mark"].to_numpy(dtype=float) / feat["max_marks"]).clip(0, 1)
    feat["l_norm"] = (l_.loc[feat["answer_id"], "predicted_mark"].to_numpy(dtype=float) / feat["max_marks"]).clip(0, 1)
    return feat.reset_index(drop=True)


def similarity_bounds(release: Release, embedder) -> tuple[float, float]:
    """5th/95th percentile answer-reference similarity on TRAIN only (used to rescale similarity to [0,1])."""
    train = release.split_answers("train")
    sims = similarity_features(release, train, embedder)
    lo, hi = float(np.percentile(sims, 5)), float(np.percentile(sims, 95))
    if hi - lo < 1e-6:
        raise ConditionError("degenerate similarity distribution on train; cannot scale condition F")
    return lo, hi


def env_flag(name: str) -> bool:
    return os.getenv(name, "0") == "1"
