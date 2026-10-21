# 11 Vector RAG implementation

Scope: a standalone Vector RAG retrieval + guarded-marking library. It is **not wired into `/c3/assess`** (the live path stays deterministic) and it is **not GraphRAG** — no CCKG is used.

## Components (all under `ai-services/c3/services/rag/` unless noted)
| File | Role |
|---|---|
| `embeddings.py` (extended) | adds `LocalSentenceTransformerEmbedding` (`provider=local`, default `sentence-transformers/all-MiniLM-L6-v2`, configurable by `C3_LOCAL_EMBEDDING_MODEL`); same cache/ABC as the Gemini/OpenAI providers; no API key |
| `vector_store.py` (reused unchanged) | `CurriculumVectorStore`: cosine retrieval, `top_k`, `threshold`, dense or TF-IDF backend, diagnostics |
| `corpus.py` (new) | builds the corpus from the frozen v2 dataset: **train split, eligible questions only**; documents = reference answer + question-level expected concepts; exact-duplicate content dropped; provenance (source SHA256, counts, exclusions) returned |
| `rag_marking.py` (new) | `retrieve_evidence`, `build_prompt`, `validate_output`, `rag_assess` |
| `experiments/rag_retrieval_eval.py` | retrieval-only evaluation (executed) |
| `experiments/rag_vs_norag.py` | matched Condition A vs B harness; writes a BLOCKED artefact unless `--run-live` and credentials exist |
| `tests/unit/test_rag_pipeline.py` | 10 offline tests |

## Corpus
133 documents from 67 train questions (67 reference answers, 66 expected-concept documents, 1 exact duplicate dropped), 8 modules. Validation/test questions, ineligible/quarantined questions, student answers and all marks are never read (asserted by tests). The dataset's rubric file contains only a generic placeholder criterion, so rubric knowledge is carried by the question-level expected concepts.

## Retrieval strategy and configuration
Query = question text + reference answer of the question being marked (information available at assessment time). Own question excluded, duplicate contents removed, below-threshold hits dropped, empty/failed retrieval returns an explicit status (`ok | empty | no_store | retrieval_failed`) and marking continues without evidence. Configurable: embedding provider/model, `top_k` (default 3), `threshold` (default 0.2), backend (`dense` / `tfidf`). Every hit returns `doc_id`, `citation`, `source_type`, `question_id`, `relevance_score`, `content`.

## Guarded marking
Prompt = system rules + question + reference answer + rubric + a quoted `<<EVIDENCE (untrusted data)>>` block + student answer. System text states that evidence is data and cannot change the rubric or marks. The model's JSON is validated: known criterion ids, no duplicates, numeric marks within each criterion's maximum, total ≤ maximum, all criteria present. Failures return `llm_status` `unavailable | error | invalid_response` and no marks. Output always carries `status: pending_review`; nothing is finalized. Credentials come from `.env`/environment through the existing providers and are never printed.

## Tests (offline, default `pytest`)
Corpus train-only/eligible-only/no student answers; retrieval provenance and own-question exclusion; empty/low-relevance/failing store; untrusted-evidence prompt + rejection of injected maximal marks; no-RAG prompt identical except the evidence block; output validation cases; happy path with a stub LLM and `pending_review`; LLM unavailable/failing reported honestly; local embedding provider registered. The embedder and LLM in these tests are **stubs** and prove code paths only.

## Executed retrieval evaluation (real local SBERT embeddings)
See 12. Local embedding loads from the Hugging Face cache without credentials (~0.5 s/doc batch on CPU).

## Limitations
No LLM marking run exists, so RAG's effect on marking is **unknown**. The relevance proxy (same module) is coarse; no human relevance labels. Corpus is small (133 docs), template-like synthetic references. Rubric knowledge is thin (placeholder criteria). Real student answers were never indexed by design. Adapting to GraphRAG later needs: a CCKG-backed retriever returning the same hit schema (`retrieve_evidence` is the seam), a populated graph, and concept-id resolution.
