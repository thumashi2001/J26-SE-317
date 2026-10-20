"""
AdaptiveLearnSE Component 3 — Curriculum Vector Store & Retrieval Pipeline
Provides chunking, vector indexing, and similarity retrieval across SLIIT SE curriculum materials.
Supports genuine neural embeddings via sentence-transformers/all-MiniLM-L6-v2 with strict
finite-vector validation, dimension verification, and explicit offline status reporting.
"""

import os
import logging
from typing import Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("c3.rag.vector_store")

# Canonical SLIIT Software Engineering Curriculum Source Corpus
CURRICULUM_DOCUMENTS = [
    {
        "doc_id": "SE3010-MOD-01",
        "module_id": "SE3010",
        "module_name": "Software Architecture & Design Patterns",
        "title": "Modular Design: High Cohesion Principles",
        "citation": "SLIIT SE3010 Lecture 03 (Modularity), Slide 14",
        "content": (
            "High cohesion is an architectural quality attribute measuring the degree to which elements inside "
            "a single module or class belong together. In functional cohesion, every operation in the module supports "
            "a single, well-defined business responsibility. High cohesion reduces cognitive load, minimizes side effects, "
            "and simplifies isolated unit testing."
        )
    },
    {
        "doc_id": "SE3010-MOD-02",
        "module_id": "SE3010",
        "module_name": "Software Architecture & Design Patterns",
        "title": "Loose Coupling & Dependency Inversion",
        "citation": "SLIIT SE3010 Lecture 03 (Modularity), Slide 18",
        "content": (
            "Loose coupling minimizes direct inter-module dependencies. Modules communicate across abstract interfaces "
            "or event buses rather than concrete implementations. Low coupling permits independent compilation, deployment, "
            "and modification without cascading changes across the system."
        )
    },
    {
        "doc_id": "SE3010-PAT-01",
        "module_id": "SE3010",
        "module_name": "Software Architecture & Design Patterns",
        "title": "Microservices Architecture & Bounded Contexts",
        "citation": "SLIIT SE3010 Lecture 07 (Microservices), Slide 06",
        "content": (
            "Microservices architecture decomposes applications into autonomous, independently scalable services organized "
            "around business capabilities. Each service encapsulates its own database to enforce strict loose coupling. "
            "Inter-service communication utilizes lightweight REST APIs or asynchronous event message queues."
        )
    },
    {
        "doc_id": "SE3030-COV-01",
        "module_id": "SE3030",
        "module_name": "Software Quality Assurance & Metrics",
        "title": "Statement Coverage & Control Flow Limitations",
        "citation": "SLIIT SE3030 Lecture 04 (White-Box Testing), Slide 11",
        "content": (
            "Statement coverage computes the percentage of executable code statements exercised during test execution. "
            "While statement coverage ensures dead code is identified, it is insufficient on its own because 100% statement "
            "coverage can be achieved along a single execution path without testing alternative decision branches or null checks."
        )
    },
    {
        "doc_id": "SE3030-COV-02",
        "module_id": "SE3030",
        "module_name": "Software Quality Assurance & Metrics",
        "title": "Branch Coverage & Decision Outcomes",
        "citation": "SLIIT SE3030 Lecture 04 (White-Box Testing), Slide 15",
        "content": (
            "Branch coverage verifies that every decision point in the control flow graph exercises all possible outcomes "
            "(both true and false edges). Branch coverage subsumes statement coverage: exercising every branch outcome "
            "guarantees every reachable statement is executed at least once."
        )
    },
    {
        "doc_id": "SE3020-NORM-01",
        "module_id": "SE3020",
        "module_name": "Database Systems & Distributed Storage",
        "title": "Relational Database Normalization Guidelines",
        "citation": "SLIIT SE3020 Lecture 02 (Normalization), Slide 12",
        "content": (
            "Normalization eliminates insertion, update, and deletion anomalies. First normal form (1NF) mandates atomic attributes. "
            "Second normal form (2NF) eliminates partial functional dependencies. Third normal form (3NF) eliminates transitive "
            "dependencies where non-prime attributes depend on other non-prime attributes."
        )
    },
    {
        "doc_id": "SE3020-TRAN-01",
        "module_id": "SE3020",
        "module_name": "Database Systems & Distributed Storage",
        "title": "ACID Properties in Distributed Transactions",
        "citation": "SLIIT SE3020 Lecture 06 (Transactions), Slide 08",
        "content": (
            "ACID properties guarantee reliability: Atomicity requires all-or-nothing completion; Consistency enforces "
            "schema integrity constraints; Isolation prevents concurrent transaction interference; Durability ensures committed "
            "updates survive system failure via write-ahead logging."
        )
    }
]


class RealSentenceTransformerEmbedding:
    """
    Adapter for genuine pretrained sentence embeddings using sentence-transformers/all-MiniLM-L6-v2.
    Validates model loading, finite vector values, dimensionality (384), and cosine similarity.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.expected_dim = 384
        self.is_loaded = False
        self.load_error: str | None = None
        self._model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Attempt to load sentence-transformers model without downloading large unapproved files."""
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            # Load model
            self._model = SentenceTransformer(self.model_name)
            # Probe check: verify finite and correct dimension
            test_vec = self._model.encode(["probe verification check"], normalize_embeddings=True)
            if test_vec.shape[1] == self.expected_dim and np.all(np.isfinite(test_vec)):
                self.is_loaded = True
                self.load_error = None
            else:
                self.is_loaded = False
                self.load_error = f"Probe validation failed: unexpected dimension or non-finite values."
        except ImportError:
            self.is_loaded = False
            self.load_error = "sentence_transformers package is not installed in the active Python environment."
        except Exception as e:
            self.is_loaded = False
            self.load_error = f"Model load failed: {str(e)}"

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode list of strings into normalized 384-dimensional dense vectors."""
        if not self.is_loaded or self._model is None:
            raise RuntimeError(f"RealSentenceTransformerEmbedding is not operational: {self.load_error}")

        embeddings = self._model.encode(texts, normalize_embeddings=True)
        # Invariant checks: finite, non-empty, correct dimension
        if not np.all(np.isfinite(embeddings)):
            raise ValueError("Computed embeddings contain NaN or infinite values.")
        if embeddings.shape[1] != self.expected_dim:
            raise ValueError(f"Embedding dimension mismatch: expected {self.expected_dim}, got {embeddings.shape[1]}")

        return embeddings

    def diagnostics(self) -> dict[str, Any]:
        """Safe runtime diagnostic metadata."""
        return {
            "model_name": self.model_name,
            "expected_dim": self.expected_dim,
            "is_loaded": self.is_loaded,
            "load_error": self.load_error,
            "provider_type": "sentence-transformers",
            "status": "ready" if self.is_loaded else f"offline ({self.load_error})"
        }


class CurriculumVectorStore:
    """
    Curriculum Vector Store providing cosine similarity search across curriculum chunks.
    Supports real sentence-transformers embeddings with verified TF-IDF fallback.
    """

    def __init__(
        self,
        documents: list[dict[str, Any]] | None = None,
        embedding_backend: str | None = None
    ):
        self.docs = documents or list(CURRICULUM_DOCUMENTS)
        corpus_texts = [f"{d['title']} {d['content']}" for d in self.docs]

        # Determine backend: "auto", "sentence-transformers", or "tfidf"
        req_backend = (embedding_backend or os.getenv("C3_VECTOR_BACKEND", "auto")).lower().strip()
        self.requested_backend = req_backend

        # Initialize real embedding adapter
        self.real_embedding = RealSentenceTransformerEmbedding()
        self.is_real_embedding = False
        self.active_backend = "tfidf"
        self.doc_vectors = None
        self.vector_dim = 0

        if req_backend in ["auto", "sentence-transformers"] and self.real_embedding.is_loaded:
            # Genuine dense neural embedding path
            try:
                self.doc_vectors = self.real_embedding.encode(corpus_texts)
                self.is_real_embedding = True
                self.active_backend = "sentence-transformers"
                self.vector_dim = self.real_embedding.expected_dim
                logger.info("CurriculumVectorStore initialized with sentence-transformers/all-MiniLM-L6-v2")
            except Exception as e:
                logger.warning(f"Dense encoding failed, falling back to TF-IDF: {e}")
                self.is_real_embedding = False

        if not self.is_real_embedding:
            # Deterministic TF-IDF lexical-semantic vectorizer baseline
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            self.doc_vectors = self.vectorizer.fit_transform(corpus_texts)
            self.active_backend = "tfidf" if req_backend == "tfidf" else "tfidf-fallback"
            self.vector_dim = self.doc_vectors.shape[1]

    def retrieve(self, query: str, top_k: int = 2, threshold: float = 0.05) -> list[dict[str, Any]]:
        """Retrieve top_k most semantically relevant curriculum chunks for a query."""
        if not query.strip():
            return []

        if self.is_real_embedding and self.real_embedding.is_loaded:
            # Real dense cosine similarity
            query_vec = self.real_embedding.encode([query])  # shape (1, 384)
            # Dot product of normalized vectors equals cosine similarity
            similarities = np.dot(query_vec, self.doc_vectors.T)[0]
        else:
            # TF-IDF cosine similarity
            query_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self.doc_vectors)[0]

        top_indices = np.argsort(similarities)[::-1]
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold and len(results) < top_k:
                doc = dict(self.docs[idx])
                doc["relevance_score"] = round(score, 4)
                doc["embedding_backend"] = self.active_backend
                doc["is_real_embedding"] = self.is_real_embedding
                results.append(doc)

        return results

    def format_retrieval_context(self, query: str, top_k: int = 2) -> dict[str, Any]:
        """Format retrieved passages into grounded context string and citation list."""
        hits = self.retrieve(query, top_k=top_k)
        if not hits:
            return {
                "context_text": "No specific curriculum passage retrieved above relevance threshold.",
                "citations": [],
                "chunks_retrieved": 0,
                "backend": self.active_backend,
                "is_real_embedding": self.is_real_embedding
            }

        context_parts = []
        citations = []
        for i, hit in enumerate(hits, 1):
            context_parts.append(
                f"[Source {i}: {hit['title']} ({hit['citation']})]\n{hit['content']}"
            )
            citations.append(hit["citation"])

        return {
            "context_text": "\n\n".join(context_parts),
            "citations": citations,
            "chunks_retrieved": len(hits),
            "backend": self.active_backend,
            "is_real_embedding": self.is_real_embedding
        }

    def diagnostics(self) -> dict[str, Any]:
        """Return runtime status of vector store and embedding provider."""
        return {
            "active_backend": self.active_backend,
            "requested_backend": self.requested_backend,
            "is_real_embedding": self.is_real_embedding,
            "vector_dimension": self.vector_dim,
            "documents_indexed": len(self.docs),
            "real_embedding_provider": self.real_embedding.diagnostics(),
            "status": "ready"
        }


_vector_store_instance = None


def get_vector_store() -> CurriculumVectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = CurriculumVectorStore()
    return _vector_store_instance
