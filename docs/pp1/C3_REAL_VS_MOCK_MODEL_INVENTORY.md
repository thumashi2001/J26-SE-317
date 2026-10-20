# AdaptiveLearnSE Component 3 — Real vs Mock Model Provider Inventory

**Project:** AdaptiveLearnSE — IT4010 Research Project  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Date:** October 20, 2026  
**Auditor:** Senior AI/ML Engineer & Research Reviewer  
**Status:** AUDITED, STRENGTHENED & FORMALLY CLASSIFIED

---

## 1. Executive Summary

Component 3 requires explicit architectural distinction between **genuine neural model inference** and **deterministic mock simulations**. Under no circumstances should mock simulations be represented as real GPT-4o, Claude, or Llama executions.

This document registers the authoritative inventory of all AI/ML models, providers, baselines, and fallback mechanisms implemented in Component 3, their verified execution status, and exact run commands.

---

## 2. Authoritative Model & Provider Classification

| Model / Pipeline Component | Class / Paradigm | Implementation File | Verified Status on Current Host | Real Execution vs Mock Simulation |
| :--- | :--- | :--- | :--- | :--- |
| **Deterministic Rubric Engine (Condition E)** | Deterministic Rule-Based Marking | `app/services/marking/service.py` | **OPERATIONAL & EXECUTED** | **Real Deterministic Rule Engine** (MAE: 1.289 on canonical n=90) |
| **Lexical Token Baseline** | Statistical Bag-of-Words Overlap | `experiments/run_evaluation.py` | **OPERATIONAL & EXECUTED** | **Real Statistical Baseline** |
| **Gradient Boosting Regressor (Condition F)** | Trained Scikit-Learn Model | `experiments/semantic_models/gbr_v2.pkl` | **OPERATIONAL & EXECUTED** | **Real Trained ML Model** (8 Handcrafted Semantic Features) |
| **Ollama Local LLM (`llama3.2`)** | Local Instruction-Tuned LLM (3.2B) | `services/llm/local_provider.py` | **CONFIGURED & ADAPTER VERIFIED**; Execution **BLOCKED (Host Dependency: Ollama daemon not running)** | **Real Neural LLM** (When active; never falls back to mock) |
| **Ollama Local LLM (`qwen2.5:7b`)** | Local Instruction-Tuned LLM (7B) | `services/llm/local_provider.py` | **CONFIGURED**; Execution **BLOCKED (Host Dependency: Ollama daemon not running)** | **Real Neural LLM** (When active) |
| **Real Sentence Embeddings (`all-MiniLM-L6-v2`)** | Dense Semantic Bi-Encoder (384-dim) | `services/rag/vector_store.py` | **CONFIGURED & ADAPTER VERIFIED**; Execution **BLOCKED (Host Dependency: sentence_transformers not installed in .venv)** | **Real Dense Vector Embedding** |
| **TF-IDF Curriculum Vector Store** | Sparse N-Gram Cosine Retrieval | `services/rag/vector_store.py` | **OPERATIONAL & EXECUTED** | **Real Lexical-Semantic Retrieval** |
| **In-Memory CCKG Ontology Adapter** | Graph-Grounded Ontology Traversal | `services/cckg/graph_adapter.py` | **OPERATIONAL & EXECUTED** | **Real Graph Retrieval** (In-Memory Deterministic Fallback) |
| **Calibrated Mock Provider (`mock-gpt4o`)** | Heuristic Simulation Function | `services/llm/mock_provider.py` | **OPERATIONAL & EXECUTED** | **Mock Simulation Only** (Explicitly labeled `is_real_execution: False`) |
| **Calibrated Mock Provider (`mock-claude-3-5-sonnet`)** | Heuristic Simulation Function | `services/llm/mock_provider.py` | **OPERATIONAL & EXECUTED** | **Mock Simulation Only** (Explicitly labeled `is_real_execution: False`) |
| **Calibrated Mock Provider (`mock-llama-3-8b`)** | Heuristic Simulation Function | `services/llm/mock_provider.py` | **OPERATIONAL & EXECUTED** | **Mock Simulation Only** (Explicitly labeled `is_real_execution: False`) |
| **OpenAI Cloud API (`gpt-4o-mini`)** | Commercial Cloud REST API | `services/llm/openai_provider.py` | **BLOCKED (Zero-Cost Policy: No paid API keys configured)** | **Real Cloud API** (Requires explicit key and authorization) |

---

## 3. Real Local Model Setup & Verification Instructions

### 3.1 Provider A: Ollama Local LLM (`llama3.2`)

To execute real local LLM inference using open-weight models without external cloud costs:

1. **Install Ollama for Windows:**
   - Download the Windows installer from `https://ollama.com/download/windows`.
   - Complete installation (Ollama runs as a background service on `http://127.0.0.1:11434`).

2. **Pull the Llama 3.2 Candidate Model:**
   ```powershell
   ollama pull llama3.2
   ```

3. **Verify Model is Installed:**
   ```powershell
   ollama list
   # Output should show:
   # NAME                ID              SIZE      MODIFIED
   # llama3.2:latest     a80c4f17acd5    2.0 GB    ...
   ```

4. **Configure Component 3 to Use Ollama:**
   In `ai-services/c3/.env`:
   ```bash
   C3_LLM_PROVIDER=ollama
   OLLAMA_BASE_URL=http://127.0.0.1:11434
   OLLAMA_MODEL=llama3.2
   ```

5. **Verify Provider Health via API:**
   ```powershell
   Invoke-RestMethod -Uri 'http://127.0.0.1:8003/api/v1/provider/status' | ConvertTo-Json -Depth 4
   ```

### 3.2 Provider B: Real Sentence Embeddings (`sentence-transformers/all-MiniLM-L6-v2`)

To execute genuine 384-dimensional dense semantic embeddings and cosine retrieval:

1. **Install sentence-transformers in Python Virtual Environment:**
   *(Requires explicit supervisor/user authorization per repository safety rules)*
   ```powershell
   & "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\.venv\Scripts\python.exe" -m pip install sentence-transformers torch
   ```

2. **Verify Model Loading:**
   ```powershell
   & "c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\.venv\Scripts\python.exe" -c "
   from services.rag.vector_store import RealSentenceTransformerEmbedding
   adapter = RealSentenceTransformerEmbedding()
   print('Loaded:', adapter.is_loaded)
   print('Dimension:', adapter.expected_dim)
   "
   ```

3. **Set Active Backend:**
   In `ai-services/c3/.env`:
   ```bash
   C3_VECTOR_BACKEND=sentence-transformers
   ```

---

## 4. Separation of Mock vs Real Execution: Architecture Invariants

1. **No Silent Fallback:**
   If `C3_LLM_PROVIDER=ollama` is configured, but the Ollama daemon is offline or the model is not pulled, `LocalLLMProvider` **never falls back to mock output**. It immediately logs an error and returns `is_success: False, is_real_execution: False`.
2. **Transparent Diagnostic Metadata:**
   All `LLMResponse` instances include the explicit boolean `is_real_execution`.
   - `MockLLMProvider` $\rightarrow$ `is_real_execution = False`.
   - `LocalLLMProvider` $\rightarrow$ `is_real_execution = True` (only when genuine tokens were generated).
   - `OpenAIProvider` $\rightarrow$ `is_real_execution = True` (only when live API HTTP 200 returned).
3. **HTTP Diagnostic Route:**
   `GET /api/v1/provider/status` exposes runtime provider status, registered models, vector store dimensions, and knowledge graph connection type without leaking tokens, credentials, or student answers.

---

## 5. Experiment Matrix Differentiation

In all research reports and presentations, the experiment matrix strictly distinguishes:

- **Empirical Baseline Experiments:** Lexical Token Overlap, Deterministic Rubric Engine, and Gradient Boosting Regressor (GBR v2).
- **Mock Simulation Experiments:** Experiments 1 to 5 conducted with `MockLLMProvider` simulating latency, token limits, and heuristic bounds. These demonstrate **pipeline architecture correctness and schema validation**, but are **not** real GPT-4o or Claude performance.
- **Genuine Neural Experiments:** Conducted with real local weights (`llama3.2` via Ollama) or real dense embeddings (`all-MiniLM-L6-v2`).
