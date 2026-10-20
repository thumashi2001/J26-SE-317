"""Leakage-safe splitting by parent question, grouped by topic cluster, stratified by module and mark scale."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

from .checks import normalized_hash
from .planning import stable_int
from .source import mark_scale_bucket

SPLITS = ("train", "validation", "test")
LINK_DISTANCE = 0.6  # average-linkage cosine distance for topic clusters


class SplitError(RuntimeError):
    pass


@dataclass(frozen=True)
class ParentDoc:
    parent_id: str
    module_code: str
    marks: float
    text: str  # question text of all parts + expected concepts


def build_parent_docs(rows: list[dict]) -> list[ParentDoc]:
    """rows: dicts with parent_question_id, module_code, max_marks, question_text, expected_concepts (list[str])."""
    texts: dict[str, list[str]] = defaultdict(list)
    meta: dict[str, tuple[str, float]] = {}
    for r in rows:
        pid = r["parent_question_id"]
        texts[pid].append(r["question_text"])
        texts[pid].extend(r["expected_concepts"])
        meta[pid] = (r["module_code"], meta.get(pid, ("", 0.0))[1] + float(r["max_marks"]))
    return [ParentDoc(pid, meta[pid][0], meta[pid][1], " ".join(texts[pid])) for pid in sorted(texts)]


def similarity_matrix(docs: list[ParentDoc]) -> np.ndarray:
    if len(docs) < 2:
        return np.eye(len(docs))
    mat = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform([d.text for d in docs])
    return (mat @ mat.T).toarray()


def max_cross_split_cosine(docs: list[ParentDoc], split_of: dict[str, str]) -> tuple[float, tuple[str, str] | None]:
    sim = similarity_matrix(docs)
    best, pair = 0.0, None
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            if split_of[docs[i].parent_id] != split_of[docs[j].parent_id] and sim[i, j] > best:
                best, pair = float(sim[i, j]), (docs[i].parent_id, docs[j].parent_id)
    return best, pair


def topic_groups(docs: list[ParentDoc], max_cosine: float) -> list[list[int]]:
    """Agglomerative topic clusters, then union any pair that is too similar to be separated."""
    n = len(docs)
    sim = similarity_matrix(docs)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    if n >= 2:
        labels = AgglomerativeClustering(
            n_clusters=None, metric="precomputed", linkage="average", distance_threshold=LINK_DISTANCE
        ).fit_predict(1.0 - np.clip(sim, 0.0, 1.0))
        first: dict[int, int] = {}
        for i, lab in enumerate(labels):
            union(i, first.setdefault(int(lab), i))
        for i in range(n):
            for j in range(i + 1, n):
                if sim[i, j] >= max_cosine - 1e-9:
                    union(i, j)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return list(groups.values())


def _attempt(
    docs: list[ParentDoc], groups: list[list[int]], ratios: dict[str, float], rng: random.Random
) -> dict[str, str]:
    n = len(docs)
    target = {s: ratios[s] * n for s in SPLITS}
    mods: dict[str, int] = defaultdict(int)
    buckets: dict[str, int] = defaultdict(int)
    for d in docs:
        mods[d.module_code] += 1
        buckets[mark_scale_bucket(d.marks)] += 1
    count = dict.fromkeys(SPLITS, 0)
    mcount: dict[tuple[str, str], int] = defaultdict(int)
    bcount: dict[tuple[str, str], int] = defaultdict(int)
    order = sorted(groups, key=lambda g: (-len(g), rng.random()))
    assign: dict[int, str] = {}
    for g in order:
        best, best_score = SPLITS[0], -1e18
        for s in SPLITS:
            score = 2.0 * (target[s] - count[s] - len(g) / 2) / max(1.0, target[s])
            for i in g:
                m, b = docs[i].module_code, mark_scale_bucket(docs[i].marks)
                score += (ratios[s] * mods[m] - mcount[(s, m)]) / max(1.0, ratios[s] * mods[m])
                score += 0.5 * (ratios[s] * buckets[b] - bcount[(s, b)]) / max(1.0, ratios[s] * buckets[b])
            score += rng.random() * 1e-3
            if score > best_score:
                best, best_score = s, score
        for i in g:
            assign[i] = best
            count[best] += 1
            mcount[(best, docs[i].module_code)] += 1
            bcount[(best, mark_scale_bucket(docs[i].marks))] += 1
    return {docs[i].parent_id: s for i, s in assign.items()}


def _module_coverage_ok(docs: list[ParentDoc], split_of: dict[str, str], min_q: int) -> bool:
    per_mod: dict[str, list[str]] = defaultdict(list)
    for d in docs:
        per_mod[d.module_code].append(split_of[d.parent_id])
    return all(len(set(v)) == len(SPLITS) for v in per_mod.values() if len(v) >= min_q)


def _deviation(docs: list[ParentDoc], split_of: dict[str, str], ratios: dict[str, float]) -> float:
    n = len(docs)
    return sum(abs(sum(1 for v in split_of.values() if v == s) / n - ratios[s]) for s in SPLITS)


def split_parents(docs: list[ParentDoc], spec: dict, seed: int, attempts: int = 60) -> dict[str, str]:
    """Map parent_question_id -> split. Raises SplitError if constraints cannot be met."""
    if len(docs) < len(SPLITS):
        raise SplitError("need at least 3 parent questions to populate three splits")
    th = spec["thresholds"]
    ratios = th["split_ratios"]
    groups = topic_groups(docs, th["max_cross_split_cosine"])
    best: dict[str, str] | None = None
    best_dev = 1e9
    for a in range(attempts):
        rng = random.Random(stable_int(seed, "split", a))
        cand = _attempt(docs, groups, ratios, rng)
        if not _module_coverage_ok(docs, cand, th["min_questions_for_module_in_every_split"]):
            continue
        if any(not any(v == s for v in cand.values()) for s in SPLITS):
            continue
        dev = _deviation(docs, cand, ratios)
        if dev < best_dev:
            best, best_dev = cand, dev
    if best is None:
        raise SplitError("no split satisfied module coverage; add questions or relax stratification")
    cross, pair = max_cross_split_cosine(docs, best)
    if cross >= th["max_cross_split_cosine"]:
        raise SplitError(f"cross-split question similarity {cross:.2f} >= threshold for {pair}")
    return best


def check_answer_leakage(texts_by_split: dict[str, list[str]]) -> None:
    """Exact duplicate non-empty answer text across splits is a hard error."""
    owner: dict[str, str] = {}
    for split, texts in texts_by_split.items():
        for t in texts:
            if not t.strip():
                continue
            h = normalized_hash(t)
            if owner.setdefault(h, split) != split:
                raise SplitError(f"duplicate answer text across splits {owner[h]} / {split}: {t[:60]!r}")
