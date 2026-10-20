"""Deterministic checks shared by the generator and the release validator, plus annotation derivation."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from services.preprocessing.text_normalizer import extract_sentences, normalize_text

_WORD = re.compile(r"[a-z0-9']+")
_STOP = frozenset(
    "a an the of and or to in on for with by is are was were be been it its this that these those as at from "
    "which can will may should would could not no do does did have has had than then also into over under using use "
    "used their they them we you your i my our".split()
)
_SYNTHETIC_LABELS = ("demonstrated", "partial")


def tokens(text: str) -> list[str]:
    return _WORD.findall(text.casefold())


def content_tokens(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in _STOP]


def normalized_hash(text: str) -> str:
    return hashlib.sha256(" ".join(tokens(text)).encode("utf-8")).hexdigest()


def token_cosine(a: str, b: str) -> float:
    ca, cb = Counter(tokens(a)), Counter(tokens(b))
    num = sum(ca[t] * cb[t] for t in ca.keys() & cb.keys())
    den = math.sqrt(sum(v * v for v in ca.values())) * math.sqrt(sum(v * v for v in cb.values()))
    return num / den if den else 0.0


def max_tfidf_cosine(text: str, others: list[str]) -> float:
    """Max TF-IDF cosine between text and any of others (0 when there is nothing to compare)."""
    others = [o for o in others if o.strip()]
    if not text.strip() or not others:
        return 0.0
    try:
        mat = TfidfVectorizer(token_pattern=r"[A-Za-z0-9']+").fit_transform(others + [text])
    except ValueError:
        return 0.0
    sims = (mat[:-1] @ mat[-1].T).toarray().ravel()
    return float(sims.max()) if sims.size else 0.0


def contains_phrase(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


# -- per-answer deterministic checks --------------------------------------------------------------------
def answer_flags(
    text: str,
    tier: str,
    style: str,
    reference: str,
    omitted_concepts: list[str],
    sibling_texts: list[str],
    spec: dict,
) -> list[str]:
    """Return reasons an LLM-written answer must be regenerated (empty list = accepted)."""
    th = spec["thresholds"]
    flags: list[str] = []
    for phrase in spec["banned_cue_phrases"]:
        if contains_phrase(text, phrase):
            flags.append(f"banned_cue_phrase:{phrase}")
    cap = th["max_reference_cosine_full"] if tier == "FULL" else th["max_reference_cosine_non_full"]
    if tier != "PARAPHRASE_FULL" and token_cosine(text, reference) > cap:
        flags.append("too_similar_to_reference")
    wc = len(text.split())
    rng = spec["style_word_ranges"].get(style)
    if rng and tier not in ("TOO_SHORT", "EMPTY") and not (rng["min"] <= wc <= rng["max"]):
        flags.append(f"word_count_{wc}_outside_{style}_range")
    if tier == "MISSING_CONCEPT":
        for concept in omitted_concepts:
            if contains_phrase(text, concept):
                flags.append(f"mentions_omitted_concept:{concept}")
    h = normalized_hash(text)
    if any(normalized_hash(s) == h for s in sibling_texts):
        flags.append("exact_duplicate")
    elif max_tfidf_cosine(text, sibling_texts) > th["max_answer_near_duplicate_cosine"]:
        flags.append("near_duplicate")
    return flags


# -- ordering / ranges ------------------------------------------------------------------------------------
def tier_order_violations(means: dict[str, float], spec: dict, eps: float = 1e-9) -> list[str]:
    out = []
    for link in spec["order_chain"]:
        hi, lo = link["higher"], link["lower"]
        if hi not in means or lo not in means:
            continue
        if link["strict"] and not means[hi] > means[lo] + eps:
            out.append(f"{hi} ({means[hi]:.3f}) must be strictly above {lo} ({means[lo]:.3f})")
        if not link["strict"] and means[hi] < means[lo] - eps:
            out.append(f"{hi} ({means[hi]:.3f}) must not be below {lo} ({means[lo]:.3f})")
    if "IRRELEVANT" in means and abs(means["IRRELEVANT"]) > eps:
        out.append(f"IRRELEVANT mean must be 0 (got {means['IRRELEVANT']:.3f})")
    return out


def in_range(value: float, rng: dict, eps: float = 1e-9) -> bool:
    lo, hi = rng["min"], rng["max"]
    if rng.get("min_exclusive"):
        if not value > lo + eps:
            return False
    elif value < lo - eps:
        return False
    if rng.get("max_exclusive"):
        return value < hi - eps
    return value <= hi + eps


# -- annotations ------------------------------------------------------------------------------------------
def split_sentences(text: str) -> list[str]:
    """Same splitter as the production preprocessing pipeline."""
    return extract_sentences(normalize_text(text))


def _stem(tok: str) -> str:
    return tok[:5]


def _concept_stems(concept: str) -> list[str]:
    return [_stem(t) for t in content_tokens(concept)] or [_stem(t) for t in tokens(concept)]


def _stem_hit(ctoks: list[str], sentence_stems: set[str]) -> bool:
    return bool(ctoks) and sum(1 for t in ctoks if t in sentence_stems) >= max(1, math.ceil(0.6 * len(ctoks)))


def concept_in_sentence(concept: str, sentence: str) -> bool:
    return _stem_hit(_concept_stems(concept), {_stem(t) for t in tokens(sentence)})


def derive_evidence_spans(text: str, concept_status: dict[str, str]) -> dict[str, list[int]]:
    """Sentence indices (production splitter) containing each demonstrated/partial concept, from the FINAL text."""
    sentence_stems = [{_stem(t) for t in tokens(s)} for s in split_sentences(text)]
    spans: dict[str, list[int]] = {}
    for concept, status in concept_status.items():
        if status in _SYNTHETIC_LABELS:
            ctoks = _concept_stems(concept)
            spans[concept] = [i for i, st in enumerate(sentence_stems) if _stem_hit(ctoks, st)]
    return spans


def derive_gold_mindmap(
    concept_status: dict[str, str], concept_graph: list[dict[str, str]], tier: str
) -> dict[str, list[dict[str, str]]]:
    if tier in ("EMPTY", "IRRELEVANT"):
        return {"nodes": [], "edges": []}
    nodes = [{"id": f"n{i}", "label": c, "status": s} for i, (c, s) in enumerate(concept_status.items())]
    ids = {n["label"]: n["id"] for n in nodes}
    active = {c for c, s in concept_status.items() if s in _SYNTHETIC_LABELS}
    edges = [
        {"source": ids[e["source"]], "target": ids[e["target"]], "type": e["type"]}
        for e in concept_graph
        if e["source"] in active and e["target"] in active
    ]
    return {"nodes": nodes, "edges": edges}


# -- dataset-level statistics (used by the validator) ---------------------------------------------------
def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3:
        return 0.0
    x, y = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def ratio_concentration(ratios: list[float], top_n: int = 7) -> float:
    """Share of answers on the top_n most frequent ratios (3 d.p.), excluding the anchors 0 and 1."""
    inner = [round(r, 3) for r in ratios if 0.0 < r < 1.0]
    if not inner:
        return 0.0
    return sum(c for _, c in Counter(inner).most_common(top_n)) / len(inner)


def distinct_sentence_ratio(texts: list[str]) -> float:
    sents = [" ".join(tokens(s)) for t in texts for s in split_sentences(t)]
    sents = [s for s in sents if s]
    return len(set(sents)) / len(sents) if sents else 1.0


def _cue_doc(text: str) -> str:
    first = tokens(text)[:4]
    return text + " " + " ".join(f"FIRSTWORD{i}_{w}" for i, w in enumerate(first))


def cue_classifier_accuracy(
    train_texts: list[str], train_labels: list[str], test_texts: list[str], test_labels: list[str]
) -> float:
    """Accuracy of a text-only classifier (n-grams + first-4-word features) predicting the tier on unseen questions."""
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True, token_pattern=r"[A-Za-z0-9_']+")
    xtr = vec.fit_transform([_cue_doc(t) for t in train_texts])
    clf = LogisticRegression(max_iter=1000, random_state=0).fit(xtr, train_labels)
    pred = clf.predict(vec.transform([_cue_doc(t) for t in test_texts]))
    return float(np.mean(np.asarray(pred) == np.asarray(test_labels)))
