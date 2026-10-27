"""Optional semantic concept matching (FR-C3-09): does a sentence MEAN the concept, even in different words?

SIMPLE ENGLISH
    The lexical analyser only sees shared words, so "the parts of the system talk through interfaces" does not match the
    concept "components". This matcher turns the concept and each answer sentence into vectors with a pretrained
    sentence-embedding model (all-MiniLM-L6-v2 by default, run locally, not trained here) and compares them by cosine
    similarity. A concept counts as semantically found when its best sentence reaches a threshold.

WHAT IT DOES NOT DO
    It never awards marks. It only adds evidence (a status upgrade flagged `match_method="semantic"` plus the score) that
    the rubric engine then reads exactly like lexical evidence; marks still come only from explicit rubric levels and the
    lecturer stays final. The threshold is calibrated on TRAIN answers only (experiments/semantic_concept_eval.py).

SWITCH
    Off unless C3_SEMANTIC_MATCH=local. Any failure (no sentence-transformers, no weights, bad input) returns None and the
    lexical result is used unchanged.

STATUS: optional runtime component of POST /c3/assess; off by default.
"""

from __future__ import annotations

import logging
import os
import threading

import numpy as np

logger = logging.getLogger("c3.semantic_matcher")

ENV_SWITCH = "C3_SEMANTIC_MATCH"
ENV_THRESHOLD = "C3_SEMANTIC_THRESHOLD"
DEFAULT_THRESHOLD = 0.5  # replaced by the TRAIN-calibrated value recorded in the evaluation report


def semantic_threshold() -> float:
    """Similarity cut-off from C3_SEMANTIC_THRESHOLD (default if unset or not a number)."""
    try:
        return float(os.getenv(ENV_THRESHOLD, DEFAULT_THRESHOLD))
    except ValueError:
        return DEFAULT_THRESHOLD


class SemanticMatcher:
    """Lazy, thread-safe wrapper around the local embedding model."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._provider = None
        self._failure: str | None = None

    def _get(self):
        """Create the embedding model on first use; remember a failure instead of raising."""
        with self._lock:
            if self._provider is None and self._failure is None:
                try:
                    from services.rag.embeddings import LocalSentenceTransformerEmbedding

                    provider = LocalSentenceTransformerEmbedding()
                    if not provider.is_available():
                        raise RuntimeError("sentence-transformers is not installed")
                    self._provider = provider
                except Exception as exc:  # optional component: never break analysis
                    self._failure = f"{type(exc).__name__}: {exc}"[:300]
                    logger.warning("Semantic matcher unavailable: %s", self._failure)
            return self._provider

    def similarities(self, concepts: list[str], sentences: list[str]) -> np.ndarray | None:
        """(n_concepts, n_sentences) cosine matrix, or None when unavailable or there is nothing to compare."""
        if not concepts or not sentences:
            return None
        provider = self._get()
        if provider is None:
            return None
        try:
            concept_vecs = provider.embed(concepts)
            sentence_vecs = provider.embed(sentences)
            return concept_vecs @ sentence_vecs.T
        except Exception as exc:
            logger.warning("Semantic matching failed: %s", exc)
            return None


_matcher: SemanticMatcher | None = None
_matcher_lock = threading.Lock()


def get_matcher() -> SemanticMatcher | None:
    """The shared matcher when C3_SEMANTIC_MATCH=local, else None (feature off)."""
    global _matcher
    if os.getenv(ENV_SWITCH, "").strip().lower() != "local":
        return None
    with _matcher_lock:
        if _matcher is None:
            _matcher = SemanticMatcher()
        return _matcher
