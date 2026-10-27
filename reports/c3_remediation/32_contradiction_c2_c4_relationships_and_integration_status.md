# 32 — Contradiction flag, C2/C4 contracts, typed mind-map relationships, integration status (2026-10-27)

Nothing here is committed or pushed. The paraphrase benchmark (report 31, commits `7eaffc9` and `f9fdc90`), `experiments/semantic_matching` and `semantic_concept_eval.py` were not modified (checked with `git diff` against `f9fdc90`). No benchmark result is claimed anywhere in this report.

## 1. Contradicted-concept detection (FR-06 diagnostic, was MISSING)
**Before:** no code existed (`ConceptStatus` had three values; the strict xfail `AUDIT-S1` recorded that "The system does not cover encryption." earned credit for `encryption`).
**Now (rule-based, deliberately small):** `services/semantic/negation.py` finds sentences that contain all of a concept's words with a negation cue placed to scope over them (verb cues such as not/never/cannot/doesn't within 4 words either side; determiner cues no/none/without/nor only BEFORE the concept; "not only" and "no longer" ignored).
- Every mention negated -> `contradicted=True`, status `not_demonstrated`, evidence points at the negating sentence, a lecturer-facing warning is added. Existing marking, feedback and mind-map code therefore give it no credit with no change to the marking engine.
- Mentions both affirmed and negated -> `conflicting=True`, status unchanged, warning only.
- The optional semantic layer can not upgrade a contradicted concept.
- Feedback gains `contradicted_concepts` (additive) and a student-facing "possible contradiction ... your lecturer will check" warning; the lecturer concept table shows the flag.
- Provenance: `analysis.contradiction_check = "negation-cue-v1"` on every analysis.
**Not detected (tested as documented limitations):** wrong statements without a negation word ("exposes all data"), related-but-incorrect statements, keyword traps. **False positives by design:** a correct negated sentence ("does not mean exposing data") is flagged, so the output is a *possible* contradiction for the lecturer, never a verified error.
**Evidence:** `tests/unit/test_contradiction_detection.py` (23 tests); AUDIT-S1 xfail marker removed because the behaviour is now fixed (its assertion is unchanged). A first version of the rule wrongly flagged the correct sentence "1NF requires ... atomic values with no repeating groups" (an existing test caught it), which is why determiner cues only scope forward.
**No accuracy is claimed:** no labelled contradiction data exists. The paraphrase benchmark (unlabelled by humans) was not used.

## 2. C2 input (FR-13) — what the repository really contains
- C2 is **not** an empty scaffold: `ai-services/c2/services/question_repository.py::build_question_repository` produces question records (`question_id`, `question_text`, `context`, `marks`, `marks_status`, `topic`, ...). It has **no HTTP route** (`ai-services/c2/app/routes` empty; `backend/src/modules/c2` only `.gitkeep`). It provides **no rubric, reference answer or expected concepts**.
- C3's own contract document `backend/src/integration/c2-c3/README.md` was stale in its response example (failed validation against `AssessmentResponse` with 45 errors). It is regenerated from the real service and section 4 records the verified status.
- Added: `services/integration/c2_adapter.py` (keeps real C2 fields, trusts `marks` only for `extracted`/`calculated`, refuses unusable records, never invents a rubric) and an optional `max_marks` field on the request that must equal the rubric total (422 otherwise; never used to compute a mark).
- `tests/integration/test_c2_c3_contract.py` (18 tests): the documented request returns 200 and the documented response validates; 7 invalid inputs -> 422; the adapter is exercised on records produced by the real C2 function loaded from file.
- **Open (needs the C2 owner):** transport and authentication between C2 and the Node backend; who supplies rubrics and reference answers. Nothing was invented.

## 3. C4 output (FR-13)
- No C3->C4 contract exists in the repository. `backend/src/modules/c4/services/c3CodingAdapter.js` only documents a future *coding-exercise* provider and returns `available:false`; the `GET /api/v1/c3/exercises` endpoint it names does not exist.
- C4 reads no C3 concept data directly. The only concept-level export is C3 -> C1 `learning_events` (`demonstrated_concepts`, `partial_concepts`, `missing_concepts`, provisional/finalized), which is the existing path to the learner model. Contradicted concepts appear there as missing (no schema change; adding a field to the shared C1 collection needs C1's agreement).
- **Not implemented, deliberately:** any C4 endpoint or payload. Dependency recorded: C4 owner must say whether it wants C3 concept signals via C1 events or a new C3 endpoint.

## 4. Mind-map relationship typing (FR-C3-33/34; was reported untyped)
The map already had evidence-based `co_mentioned` lines. Now, when both concepts are demonstrated/partial and sit contiguously in one sentence with a fixed cue phrase between them (no negation word, <= 5 words, articles ignored), the line is typed and directed: `is_a`, `part_of`, `depends_on`, `leads_to`, `contrasts_with`; the evidence names the sentence and cue phrase and says it records what the student wrote, not that it is correct. Otherwise it stays `co_mentioned`. Credit gating means a contradicted or missing concept is never typed. The inspector panel lists a selected node's relationships with the evidence.
**Limits:** small hand-written cue list; misses other phrasings; says nothing about correctness. Whether typing is *required* by the approved scope is unresolved: the proposal wording is "relationships where evidence exists", which `co_mentioned` already met; typing is an enhancement within that wording.
**Evidence:** `tests/unit/test_relationship_typing.py` (19 tests: directions, negation, no cue, out-of-range sentences, determinism, rubric mark unchanged end-to-end).

## 5. LLM and RAG experiments (FR-05) — status only
Inspected: `experiments/rag_vs_norag.py` (matched no-RAG vs RAG, TRAIN-only corpus, temperature 0, refuses without `--run-live`), `multi_llm_comparison.py`, `rag_retrieval_eval.py`. Gemini and OpenAI keys are present in the git-ignored `.env` (values not read or printed); Groq/OpenRouter keys are absent; Ollama is not running. The free Gemini tier (about 20 requests/day/model) can not cover the 2 x 90 calls of the full comparison, so **no new LLM or RAG experiment was run** (a live call would also send data to an external provider). The only executed LLM evidence remains the earlier 5-answer Gemini pilot (validation split, tier-derived labels, `reports/c3_remediation/experiments/multi_llm_pilot/`), which is too small to compare conditions.

| Configuration | Status |
|---|---|
| Lexical baseline, semantic-enabled (concept eval), fine-tuned/classical models | EXECUTED earlier (reports 03, 27, 28) |
| LLM without RAG vs with RAG (full test split) | NOT RUN (quota) |
| Multi-LLM comparison | NOT RUN (one working provider) |
| GraphRAG | NOT RUN (CCKG seed has 8 demo concepts) |

## 6. Services and end-to-end
- **Why the services were down:** nothing in the project starts them; `uvicorn` (C3, :8003) and `npm run dev` (backend, :3000) are manual, and the backend needs MongoDB (Atlas from `backend/.env` or local Docker).
- **Started:** the C3 service on :8003 (`/health` OK). Live checks against it with the C2-style payload: full answer 10/10, partial 5/10, unrelated 0/10, contradicted ("Atomicity is not required ...") 5/10 with the two negated concepts flagged, empty answer 0/10 with 200, missing rubric 422, `max_marks` mismatch 422.
- **Not started:** the backend and browser E2E. Docker Desktop was launched but its engine never came up within about 3 minutes, no local `mongod` exists, and `backend/.env` points at the shared Atlas database, which the E2E guard (`ui_tests/guard.mjs`) and this project's rules forbid for test writes. **E2E: NOT RUN.** Lecturer review/override/audit and student redaction were therefore verified only by the existing automated tests (fake database), not end to end today.
- The first Node run had the C3 service up, so the live-microservice tests ran; the pre-commit re-run (service stopped) skipped them.

## 7. Test results (exact)
| Suite | Result |
|---|---|
| C3 Python `pytest -q` | **699 passed, 9 deselected, 12 xfailed, 0 failed** (before this work: 638 passed, 13 xfailed; +60 new tests, plus one former xfail now a normal passing test) |
| New files | contradiction 23, relationship typing 19, C2 contract 18, all passing |
| Backend `npm test` | 118 tests, 0 fail, 2 todo (AUDIT-B9 known bugs). With the C3 service running on :8003: 116 pass, 0 skipped. Re-run before committing with the service stopped: 113 pass, 3 skipped (the live-microservice tests skip when nothing listens on :8003) |
| Frontend `npm test` | 10 of 10 pass; `vite build` succeeds |
| Browser E2E | NOT RUN |
| Ruff on new files | only E501 docstring line-length findings (same class as the repo's existing backlog) |

## 8. Known defects and blockers
- Contradiction rule: false positives on correct negations; misses un-negated wrong statements.
- Paraphrase failure is unchanged (report 31); the semantic layer remains off by default and unproven.
- The Node `c3` export to C1 does not carry the contradiction flag.
- `CLAUDE.md` still says C2 modules are empty scaffolds; `ai-services/c2` has code (not edited).
- Blocked on others: C2 transport/auth, C4 consumer contract, Docker/local MongoDB for E2E, LLM quota, human labels for the benchmark.
