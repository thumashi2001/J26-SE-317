# 29 — SOLID / best-practice review of the C3 service (2026-10-27)

Scope: `ai-services/c3` runtime code (`app/`, `services/`). Behaviour was kept identical; the suite is unchanged apart from 7 new
structure tests (603 passed, 13 xfailed).

## What already followed the principles
- **Single responsibility by stage:** analysis, marking, feedback, mind map, RAG, LLM, CCKG and ML scoring are separate packages;
  feedback and mind map are built *from* finished marks and cannot change them (this is also the research-integrity rule).
- **Interface segregation / Liskov:** `BaseLLMProvider` has three methods (`is_available`, `health_check`, `generate`); Gemini, OpenAI
  (and its compatible hosts), Local and the cache wrapper are interchangeable behind it. Embedding providers share one base class.
- **Dependency inversion (partly):** the optional AI estimate and semantic matcher are reached through `get_scorer()` /
  `get_matcher()` and fail soft, so marking does not depend on them being installed; tests swap them with fakes.

## Changes made
| Principle | Problem | Change |
|---|---|---|
| Single responsibility | `assess_answer` mixed orchestration with mark computation | Marking extracted into `_mark()`; `assess_answer` now only sequences the steps |
| Open/closed | `get_llm_provider` used an if/elif chain, so a new provider meant editing it | `_BUILDERS` registry; a provider is one entry (test keeps it in sync with `SUPPORTED_PROVIDERS`) |
| DRY / Liskov | Identical `_failure()` copied into the Gemini and OpenAI providers | Moved once into `BaseLLMProvider` |
| Tidy | `_ai_estimate` fetched the scorer twice | Fetched once |
| Removed | A "mark authority" check compared the marking object with the very values it had just been built from (it could never fail) | Deleted; the rule is enforced by structure (only `_mark` produces marks) |

## Known remaining deviations (not changed, to avoid risky rewrites)
- Module-level singletons (`_provider_registry`, scorer and matcher registries) are global state; acceptable for a service, but they
  need care in tests (existing fixtures reset them).
- `analyze_answer` and `evaluate_criterion` are called directly rather than injected, so swapping the analyser means editing the
  orchestrator. A small `Analyzer` protocol would fix this if a second analyser becomes a real requirement.
- Several experiment scripts are long procedural files with local closures (`model_comparison.py`); they are research scripts, not
  service code, and are documented rather than restructured.
- Ruff reports many pre-existing style findings (line length, import order) that this work did not address.
