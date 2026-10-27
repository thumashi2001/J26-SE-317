# 26 — Proposal coverage, free-tier LLM options, cleanup (2026-10-26)

Sources: `c3_functional_requirements_matrix.csv`, `experiment_status_matrix.csv`, the Component 3 proposal (Sept 2026).
Nothing here is a new experimental result; counts are tallies of the existing matrices.

## 1. Coverage of the proposal

| Proposal item | Count | Detail |
|---|---|---|
| Functional requirements FR-C3-01..46 | 33 PASS / 5 PARTIAL / 2 FAIL / 6 BLOCKED | PARTIAL: 05, 06, 08, 17, 34. FAIL: 09, 33. BLOCKED: 16, 18, 19, 20 (LLM/RAG), 42, 44 (C2 and C4 integration). |
| Non-functional NFR-C3-01..30 | 19 PASS / 8 PARTIAL / 3 NOT TESTED | NOT TESTED: 12, 15 (PII handling, ethics), 30 (usability evaluation). |
| Specific objectives SO1..SO6 | 3 PASS / 3 PARTIAL | PASS: SO2 marking, SO3 concept analysis, SO4 explainable feedback. PARTIAL: SO1 semantic analysis, SO5 mind map, SO6 comparative evaluation. |
| Experiments (Table 4 baselines) | 7 built and tested, 1 partial, 4 deferred, 2 blocked, 1 not implemented | see below |

**Done:** MCQ marking, lexical baseline, TF-IDF, SBERT, RoBERTa, rubric engine (Condition E), F-lite, vector RAG library and retrieval-only evaluation, lecturer review/override, feedback, mind map, security hardening.

**Left to cover**
1. LLM without RAG, rubric-prompted LLM, RAG vs non-RAG, multiple-LLM comparison, Condition F (FR-C3-16/18/19/20). The cause is LLM quota, which the free providers below address.
2. Condition D (GraphRAG over the CCKG): the CCKG is not populated.
3. Benchmark datasets (Mohler, ASAP-SAS, SciEntsBank, ASAG2024): not implemented. The supervisor has since directed synthetic data (see section 3).
4. FR-C3-09 and FR-C3-33 (FAIL): semantic marking and answer-derived relationships are only lexical, so paraphrase is not recognised.
5. Concept-detection precision/recall/F1 needs concept annotations (listed in the proposal as a threat to validity).
6. Feedback-quality and usability evaluation (NFR-C3-30), and an automated robustness suite.
7. C2 and C4 integration (FR-C3-42/44).
8. Human-marked data. The labels are tier-derived. Ratio-concentration fails (0.766) and a length-only model beats TF-IDF and SBERT, so no semantic-skill claim is supportable yet.

## 2. Free-tier LLM options (must be re-checked on each provider's page; limits change)

DeepSeek is **not free**: it is pay-per-token, possibly with short-lived trial credits, so it does not meet a free-only rule. Its open-weight models can still be used free through OpenRouter free models or a local Ollama.

Candidates with a free tier per the 2026 comparisons surveyed (limits are third-party figures and conflict): Google AI Studio (Flash / Flash-Lite), Groq, OpenRouter (`:free` models), Cerebras, Mistral, GitHub Models, Cloudflare Workers AI, and local Ollama (no quota).

**Code support added:** `C3_LLM_PROVIDER` now also accepts `groq | openrouter | deepseek | cerebras | mistral`. All reuse `OpenAIProvider` (OpenAI-compatible protocol) with their own key variable, base URL, `C3_<NAME>_MODEL` and per-host rate limiter (`C3_LLM_RPM_<NAME>`). Default model names are starting points; verify against the provider's current list before a run. Models used in a comparison must be recorded in the run manifest.

## 3. Synthetic data (supervisor direction)
The existing v5/v2 sets are already synthetic (see section 5), so no new set was generated. Constraint from `CLAUDE.md`: the repaired v5/v2 sets stay untouched; any further synthetic set must be separate and labelled.

## 4. Cleanup done
Removed local caches (`.ruff_cache`, `.pytest_cache`, `.coverage`) and nine unreferenced empty-directory `.gitkeep` placeholders (staged with `git rm`). Not removed, needs your decision: `datasets/archive/earlier_inplace_repair_20261020.zip`, and a stray empty `ai-services/c3/.venv` (the real venv is `.venv_c3`).

## 5. Component 3 completion work (2026-10-26, second pass)
- **Multi-LLM harness:** `experiments/multi_llm_comparison.py` marks the same answers with 2-3 providers x {no RAG, vector RAG}. It resumes from a JSONL cache, stops a provider that hits its quota, excludes failed calls, and writes a BLOCKED artefact instead of any marks when keys or `--run-live` are missing. Offline tests use stub providers only.
- **Status of live runs:** NOT RUN. Only `GEMINI_API_KEY` (free tier, about 20 requests/day/model) and `OPENAI_API_KEY` (credit reported exhausted) exist in `.env`. Add free keys for two more providers (for example `GROQ_API_KEY`, `OPENROUTER_API_KEY`) and run the command in section 6. No LLM result exists in this repository yet.
- **FR-C3-05:** markup is now stripped in preprocessing (unit-tested). **FR-C3-33:** same-sentence "co_mentioned" concept links added (co-occurrence only, not typed relations).
- **Synthetic data:** the existing v5/v2 sets are already synthetic (`synthetic_data_status`, `generation_method` columns), which satisfies the supervisor's direction; no new LLM-generated set was created.
- **Still open:** FR-C3-09 (semantic matching; needs SBERT/LLM evidence evaluated against the length-only baseline), typed relationships, concept-detection P/R/F1 annotations, human-marked data, C2/C4 integration, CCKG population, usability study.

## 6. Command to run the multi-LLM comparison once keys exist
```
cd ai-services/c3
.venv_c3\Scripts\python.exe -m experiments.multi_llm_comparison --out ..\..\reports\c3_remediation\experiments\multi_llm --providers groq,openrouter,gemini --split test --run-live
```
Rerun the same command on later days to resume after a quota stop (cached responses are reused).
