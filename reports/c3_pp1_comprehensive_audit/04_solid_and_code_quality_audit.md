# 04 SOLID and code-quality audit

Row-level findings (66, with file:line, severity, minimal fix, test needed, mandatory-before-PP1 flag): `solid_findings.csv` (28 Python PY-xx, 38 Node/React N-xx). Labels V/I as in the CSV. SOLID is not in the PP1 rubric; it supports "design excellence" and "standards/best practices" (LO3).

## 1. Python service (`ai-services/c3`)
| Principle | Verdict | Evidence |
|---|---|---|
| **S** | Mostly good; 4 violations | Compliant: `text_normalizer` (46 lines), `semantic/baseline`, `rubric_validator`, mind-map and feedback split into node/edge/assembly and classify/text/assembly, one-handler routes. Violations: `assess_answer` 95 lines (`orchestrator.py:49-143`), `_level_evidence` 95 (`criterion_evaluator.py:35-129`), `concept_status_lists` 94, `LocalLLMProvider.generate` 106 |
| **O** | Acceptable for PP1 | No strategy seam for a second marking engine (`orchestrator.py:72-75` imports `evaluate_criterion` directly); adding an LLM provider touches 3–4 places (`factory.py:15,40-61`, `run_experiments.py:79`); adding an experiment condition touches 4 sites. Positive: `CachedLLMProvider` wraps any provider |
| **L** | Local provider deviates | Invalid JSON returns success; no `model` attribute (cache key collapses to "default", `cache.py:80`); `is_available` does HTTP; `/health` makes network calls for provider=local despite its "no network" docstring |
| **I** | Good | 3-method `BaseLLMProvider`; separate `EmbeddingProvider`; no split needed |
| **D** | Core excellent, edges weak | Marking/feedback/mindmap/semantic/preprocessing import only schemas, stdlib, siblings (strongest property). Weak: module-level singletons (`factory.py:17`, `vector_store.py:138`, `graph_adapter.py:287`), `provider.model = override` mutates registry (`conditions.py:109`), 34 `os.getenv` reads in 11 files, `load_dotenv()` at import |
| DRY | Violations | `_analysis_request` ×3 (`orchestrator.py:17`, `marking_engine.py:14`, `generator.py:25`, one differs), `_overall_explanation` ×2, version constants ×2; two different "lexical baseline" algorithms (cosine vs set recall) with different numbers |
| KISS/cohesion | Good in `services/*`; `datasets/repair/*` are long procedural scripts (436 and 341 lines; low runtime impact) |
| Errors | Cross-field invalid rubric → HTTP 500 on `/c3/assess`, `/feedback/generate` (AUDIT-A1); retry layer good but `Retry-After` unbounded and `int(os.getenv)` unguarded |
| Typing/lint | No mypy config; ruff 111 findings (reported, not fixed) |

Top fixes if approved (all small): (1) one `RubricValidationError` handler; (2) merge duplicated helpers and delete the tautological authority check; (3) provider `model` property + Local failure semantics; (4) criterion-concept merge rule (AUDIT-M4) together with multi-level rubrics; (5) size limits on request schemas.

## 2. Node/Express backend
- **Architecture rule breach:** `mcqMarkingService.js` (lines 97–328) is a full second marking engine (scoring, feedback, concepts, mind map) in Node, while the project rule says AI marking lives in Python. Output schema differs from Python's (UI crash risk, N30).
- **Controllers vs services:** `c3Controller.assessAnswer` mixes engine selection, OCR check, persistence and error masking; services call `getDb()` directly (hidden global).
- **Positive:** module auto-mount (`app.js:17-25`), scrypt + `timingSafeEqual`, HS256 pinned, role guards on review/finalize/batch, student ownership on detail, honest 400 for OCR, `automated_mark` never overwritten, C1 sync idempotent with provisional/finalized lifecycle.
- **DRY:** 4 `httpError` copies, 2 `parseId`, 3 `handle()` wrappers; result-doc literal duplicated.

## 3. React frontend
God components: `LecturerBatchMarkingPage.jsx` ≈1,456 lines (~45 state variables, `alert()` for errors) and `AssessmentPage.jsx` ≈900; student page sends rubric/answer key/`is_demo` from client state (trust boundary, N34); `MindMapGraph` expects the Python shape (`relationships`, `node_id`), so MCQ results likely throw (N30); no frontend tests; no hooks lint; `menus.js:42` says "before students see them" but students see the AI mark immediately.

## 4. Verdict for the viva
Strong: layered pure core, provider abstraction, caching/retry, hermetic tests, honest known-bug tests. Weak: duplication, a few long functions, global singletons, Node/Python duplication of marking logic, large UI components. None of the weaknesses blocks the demo; the security-related ones (05) are the ones an examiner can exploit.
