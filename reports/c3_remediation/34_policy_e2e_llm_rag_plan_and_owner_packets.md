# 34 — Policy and relationship E2E coverage, LLM/RAG plan, and coordination packets for the C2 and C4 owners (2026-10-28)

Status of this work: **uncommitted** in the working tree on top of `91537ff`. Nothing pushed. The paraphrase benchmark (82 `draft_unreviewed` items, no human labels) and the two earlier semantic experiments are untouched and are not used for any claim below.

## 1. E2E coverage for both contradiction policies and typed relationships (executed)
New script: `reports/c3_remediation/ui_tests/policy_relationships.mjs` (guarded: refuses anything but an isolated local database). It takes the policy the Python service was started with, first proves the service really runs it (`analysis.contradiction_check`), then runs API and Chrome checks on hand-written answers. These checks assert wiring and policy behaviour, **not detection accuracy** (accuracy is unmeasured).

Environment: Docker Desktop was relaunched (its two stale Unix-socket folders had to be renamed again, same reversible fix as report 33); throwaway MongoDB `c3-e2e-mongo` on `127.0.0.1:27018`, database `adaptivelearnse_c3_e2e`, backend on :3100 with explicit `MONGO_URI`/`MONGO_DB`, Vite on :5174. Atlas was not contacted. The stack and container were removed afterwards.

| Run | Service started with | Result |
|---|---|---|
| `policy_relationships.mjs warn_only` | `C3_CONTRADICTION_POLICY` **unset** (tests the real default) | 15 of 15 passed |
| `policy_relationships.mjs withhold_credit` | `C3_CONTRADICTION_POLICY=withhold_credit` | 15 of 15 passed (after the fix below; 14 of 15 before it) |
| `e2e.mjs` (existing browser + API suite) re-run on the current code, default policy | unset | **106 of 106 passed** (this one is after the policy change) |

What the 15 checks cover: affirmed answer gets the full mark with no flag; a denied answer is flagged; under `warn_only` its rubric mark equals the affirmed answer's (4/4) and under `withhold_credit` it is 0; the lecturer warning wording follows the policy; feedback lists contradicted concepts; the student response has no `ai_estimate` or `review_history`; a fixed cue phrase gives a typed `part_of` relation with the evidence note; typing never changes the mark; a negated cue is not typed; the lecturer review page shows the possible-contradiction note and the mark for the active policy; the mind-map inspector lists the relation as "Is part of ... as the student wrote them"; no page errors.
Evidence files: `reports/c3_remediation/experiments/e2e_2026-10-28/` (both policy runs, the 106-check results, the API permission matrix).

**Defect found by this run and fixed.** Under `withhold_credit`, a zero-mark answer showed no contradiction note in the feedback: at the zero level the rubric's concepts are "next level" items, not "missing", so the note was built from an empty list. Also, the note said "Credit was not withheld" because the wording depended on that list rather than the policy. Fix in `services/feedback/generator.py`: the note now covers next-level concepts and its wording follows the active policy. Regression test added (`test_withhold_credit_zero_mark_answer_still_names_the_contradicted_concepts_in_feedback`). Default (`warn_only`) behaviour was not affected.

Limits: one answer set, one demo assessment (`arch-full`); the browser checks are on the lecturer review page, not every screen; no cross-browser or accessibility testing.

## 2. Reproducible LLM / RAG comparison plan (NOT RUN)
**Why not run now.** The full matched comparison needs 2 conditions x 90 test answers = 180 calls. The free Gemini tier allows about 20 requests per day per model, so one model needs roughly 9 days; Groq and OpenRouter keys are absent; Ollama is not running. A smaller subset (for example 20 calls) would execute but could not support a claim. No LLM result is produced here.

**Protocol (fixed in advance, using the existing harness `experiments/rag_vs_norag.py`).**
| Item | Setting |
|---|---|
| Inputs | `c3_phase3_v5_repaired_v2` **test** split, the same 90 answers in both conditions, reference answers loaded via `load_answers_with_reference()` |
| Conditions | A: LLM without retrieval. B: the same LLM with Vector RAG from the TRAIN-only corpus. The only difference is the evidence block in the prompt |
| Fixed | model id, temperature 0, rubric text, scoring scale, prompt template version, retrieval settings (top-k, embedding provider) |
| Logged per call | model identifier, prompt hash, retrieved passage ids, latency, failure reason; failed calls are excluded and counted, never scored 0; LLM responses cached in the JSONL cache for reruns |
| Metrics | nMAE, MAE in marks, Pearson r, QWK on 11 bins, failure rate, mean latency (already implemented in the framework) |
| Reference marks | currently **tier-derived, not human**. Any result is therefore *exploratory*, reported as agreement with tier-derived labels, and may not be called agreement with human markers |
| Gate for a confirmatory claim | human-labelled gold marks (report 25 readiness work), then re-run once on the sealed test set |
| Interpretation rules | no claim that RAG improves accuracy unless condition B beats A on the pre-stated metrics with the question-bootstrap interval excluding zero on the gold marks; a null or negative result is reported as such |
| Not used | the paraphrase benchmark; the semantic layer stays off |
**Budget options:** (a) one Gemini model over about 9 days at 20 calls/day; (b) a paid or higher-quota key (one afternoon); (c) a second provider only for the multi-LLM comparison (all candidate models must see identical inputs).
**Harness change (2026-10-28, tested, no LLM calls made):** `experiments/rag_vs_norag.py` now has `--shard I/K` and `--aggregate K`. The test answers are put in one fixed order (sorted by `answer_id`); shard I takes every K-th answer, so the K shards are disjoint and cover all 90 answers regardless of row order, day or run order. Each shard writes `rag_vs_norag_predictions_shard{I}of{K}.csv` and its own summary, never overwriting another. `--aggregate K` makes no LLM calls: it refuses a missing shard, a duplicated answer, an answer without both conditions or an incomplete cover, then writes the combined files; the comparison is complete only after that check. Summaries now also list the model ids and the run configuration. `--limit` stays a fixed-seed pilot subsample and cannot be combined with `--shard`. **Correction to an earlier draft of this plan:** I first wrote that a larger `--limit` picks a different sample; checking showed it is reproducible for the same file and, with the current pandas/numpy, nested, but it depends on the row order of the data file and the nesting is not guaranteed, which is why sharding is used for multi-day runs. Example day-by-day command: `python -m experiments.rag_vs_norag --out <dir> --provider gemini --run-live --shard 3/9` (10 answers x 2 conditions = 20 calls per day), then `--aggregate 9` after day 9.

**Decision needed from you:** which budget option, and whether an exploratory tier-label comparison is wanted before human labels exist.

**E2E guard check (2026-10-28).** The new script's guard was exercised with unsafe settings from a copy that has Playwright installed; every case exited with code 2 and a refusal message before any request: a database name outside `adaptivelearnse_c3_*` (for example `adaptivelearnse_dev`), a `mongodb+srv://` URI, a non-loopback Mongo host, credentials in the Mongo URI, a non-loopback API base, missing variables and an invalid policy argument.

## 3. Coordination packet for the C2 owner (send as is)
Subject: C3 needs a route and four fields from C2 before assessment can be wired.
1. **Current state (verified in the repository):** `ai-services/c2/services/question_repository.py::build_question_repository` produces question records; there is no HTTP route (`ai-services/c2/app/routes` is empty; `backend/src/modules/c2` holds only `.gitkeep`).
2. **What C3 already accepts:** `POST /c3/assess` on the C3 service with the payload in `backend/src/integration/c2-c3/README.md` section 2.1; invalid or inconsistent input returns 422. `services/integration/c2_adapter.py` converts a C2 record into the question context.
3. **Please decide and tell us:** (a) transport: a backend route or a file/database hand-off, and who calls whom; (b) authentication: which token or role a C2 caller uses (the C3 Python service has none; the Node backend enforces JWT); (c) stable `question_id` values across papers; (d) who supplies `answer_type`, the rubric (criteria, marks, levels, required concepts), `expected_concepts` and `reference_answer`, since C2 records contain none of them, and `topic`/`bloom_level` are currently `None`.
4. **Acceptance:** a sample payload from the real C2 path passes `ai-services/c3/tests/integration/test_c2_c3_contract.py` unchanged; the real route is exercised end to end in an isolated environment; `marks` must equal the rubric total or the request is rejected.

## 4. Coordination packet for the C4 owner — PROPOSED, REQUIRES C4 OWNER APPROVAL
Subject: Does C4 want C3 learning signals, and by which route?
1. **Verified:** no C3-to-C4 contract exists. `backend/src/modules/c4/services/c3CodingAdapter.js` documents only a future coding-exercise provider (`available:false`). C4 reads no C3 concept data today. C3 already writes concept-level evidence to C1 `learning_events` (`c3_automated_assessment` provisional, `c3_finalized_assessment` finalized), which is a C1 output.
2. **Option A (no new C3 code):** C4 reads C3 evidence from C1 `learning_events`. **Option B:** a new read endpoint `GET /api/v1/c3/learning-signals?student_id=...` returning, per finalized submission: `submission_id`, `question_id`, `topic`, `lifecycle_stage`, `final_score`, `total_possible`, `demonstrated_concepts`, `partial_concepts`, `missing_concepts`, optional `possibly_contradicted_concepts` (heuristic, accuracy unmeasured), `finalized_at`; student-self or C4-service authorization.
3. **Please answer:** A or B; finalized results only or provisional too; which student identifier (pseudonymous?); should the contradiction flag be exported; transport and token.
4. **Acceptance tests once agreed:** schema validation, finalized-only filter, student isolation, idempotent re-read, unknown-student error, backward compatibility of `learning_events`.
Nothing will be implemented until this is approved.

## 5. Test results for this working tree (fresh)
| Suite | Result |
|---|---|
| C3 Python `pytest -q` | 705 passed, 9 deselected, 13 xfailed, 0 failed |
| Backend `npm test` (services stopped) | 118 tests: 113 pass, 0 fail, 3 skipped, 2 todo |
| Frontend `npm test` | 10 of 10 pass |
| Browser E2E (isolated) | 106 of 106; policy/relationship script 15 of 15 under each policy |

## 6. Remaining gaps
Heuristic contradiction and typed relations remain unmeasured; `withhold_credit` needs supervisor approval before becoming a default; LLM/RAG comparison, C2 transport and authentication, the C4 contract, human gold labels and the paraphrase benchmark annotation are all still open.
