# AdaptiveLearnSE Component 3 — Model Provider Architecture & Setup Guide
**Project:** AdaptiveLearnSE | **Component:** C3 (Automated Marking & Answer Analysis)  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Document Version:** 2.0.0 (PP1 Final Verified)

---

## 1. Architectural Overview

Component 3 utilizes a **provider-neutral LLM abstraction layer** located in `ADAPTIVE_LEARN_SE/ai-services/c3/services/llm/`. This design completely decouples marking logic, prompts, and evaluation pipelines from any specific LLM provider or proprietary SDK.

```
┌──────────────────────────────────────────────────────────┐
│              C3 Automated Assessment Pipeline            │
│         (Orchestrator / Experiments / Benchmarks)        │
└────────────────────────────┬─────────────────────────────┘
                             │ LLMRequest (JSON Schema)
                             ▼
┌──────────────────────────────────────────────────────────┐
│                    BaseLLMProvider (ABC)                 │
└──────────────┬───────────────────────────┬───────────────┘
               │                           │
      ┌────────┴────────┐         ┌────────┴────────┐         ┌─────────────────┐
      │ MockLLMProvider │         │ OpenAIProvider  │         │LocalLLMProvider │
      │ (Default / Zero)│         │ (GPT-4o REST)   │         │ (Ollama Local)  │
      └─────────────────┘         └─────────────────┘         └─────────────────┘
```

---

## 2. Supported Provider Implementations

### 1. Calibrated Mock Provider (`MockLLMProvider`) — **ACTIVE BY DEFAULT**
- **File:** `ai-services/c3/services/llm/mock_provider.py`
- **Cost:** **$0.00 (Zero financial expenditure)**
- **Behavior:** Deterministic offline simulation calibrated against the synthetic dataset distributions. Generates fully compliant JSON responses with realistic latency (10–15 ms) and simulated token usage.
- **Out-of-Domain Guard:** Evaluates keyword overlap and detects distractors (e.g. Roman Empire text), assigning exactly 0.00 marks.
- **Purpose:** Used for local testing, continuous integration, regression suites, and viva demonstration without relying on active internet connections or paid API credits.

### 2. OpenAI Cloud Provider (`OpenAIProvider`)
- **File:** `ai-services/c3/services/llm/openai_provider.py`
- **Supported Models:** `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
- **Safety Gating:** If `OPENAI_API_KEY` is not configured, the provider returns `pending_credentials` rather than failing ungracefully or generating fabricated results.
- **Cost Recording:** Automatically tracks prompt tokens, completion tokens, and estimates USD cost based on published rates.

### 3. Local Offline Inference Provider (`LocalLLMProvider`)
- **File:** `ai-services/c3/services/llm/local_provider.py`
- **Base Endpoint:** `http://localhost:11434/api/generate` (Ollama)
- **Supported Models:** `llama3:8b`, `mistral:7b`, `qwen2.5:7b`
- **Zero Cloud Transmission:** All token processing occurs locally on hardware; zero data leaves the machine.

---

## 3. Environment Variable Configuration

All provider configurations are controlled exclusively via environment variables in `ai-services/c3/.env` (or root `.env`):

| Environment Variable | Allowed Values | Default in Dev | Purpose |
| :--- | :--- | :--- | :--- |
| `C3_LLM_PROVIDER` | `mock`, `openai`, `local` | `mock` | Selects active provider implementation via factory |
| `C3_DEFAULT_MODEL` | `mock-gpt4o`, `gpt-4o`, `llama3:8b` | `mock-gpt4o` | Model identifier string |
| `OPENAI_API_KEY` | Secret API key string | `""` (Empty) | OpenAI authorization token |
| `OPENAI_BASE_URL` | Valid URL | `https://api.openai.com/v1` | OpenAI API endpoint |
| `OLLAMA_BASE_URL` | Valid URL | `http://localhost:11434` | Local Ollama daemon URL |

### Safe Configuration Template (`.env.example`)
```bash
# ========================================================
# AdaptiveLearnSE Component 3 — LLM Provider Configuration
# ========================================================
C3_LLM_PROVIDER=mock
C3_DEFAULT_MODEL=mock-gpt4o

# Optional: Live Cloud Execution (Requires Authorized Key)
# OPENAI_API_KEY=sk-proj-your-authorized-key-here
# OPENAI_BASE_URL=https://api.openai.com/v1

# Optional: Local Offline Inference (Requires Ollama running)
# OLLAMA_BASE_URL=http://localhost:11434
```

---

## 4. Operational Health & Diagnostic Commands

Verify provider health programmatically via Python:

```python
from services.llm.factory import get_llm_provider

# 1. Inspect active provider status
provider = get_llm_provider()
health = provider.health_check()
print(health)
# Output: {'status': 'healthy', 'provider': 'calibrated-mock', 'mode': 'deterministic_offline_simulation', ...}
```

Or execute unit verification:
```bash
cd ADAPTIVE_LEARN_SE/ai-services/c3
& "..\..\..\.venv\Scripts\python.exe" -m pytest tests/unit/test_llm_providers.py -v
```
All 8 LLM provider unit tests pass, verifying request/response schemas, distractor gating, and credential safety.
