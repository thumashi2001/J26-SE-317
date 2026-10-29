# 35. Requirements completion pass (everything except LLM and RAG)

Date: 2026-10-29. Branch `feature/c3-stage1-dataset-integrity`. Scope: the open rows of
`c3_requirements_traceability_matrix.csv` that can be built deterministically, without a language model or retrieval.

## What was added

| Requirement | Change | Where | Status in the matrix |
|---|---|---|---|
| D6-FR-C3-017 keywords and phrases | `analysis.keywords`: most frequent content words and repeated adjacent pairs (no model) | `services/semantic/keywords.py` | Implemented, not validated against human keyword choices |
| D6-FR-C3-020 / 095 off-topic flag | `analysis.relevance` (`relevant` / `off_topic` / `not_assessed`) plus a warning; threshold `C3_OFF_TOPIC_BELOW`, default 0.10 | `services/semantic/relevance.py` | Implemented, not validated |
| D6-FR-C3-073 disconnected concepts | `mindmap.summary.disconnected_concepts` (credited concepts with no concept-to-concept line; needs 2 or more) | `services/mindmap/generator.py` | Implemented, not validated |
| D6-FR-C3-079 review rules | `review` on the assessment: six named rules, configurable with `C3_REVIEW_RULES`, unknown names rejected | `services/assessment/review_rules.py` | Implemented, not validated |
| D6-FR-C3-093 below-threshold evaluations | Same review rules; a statistical confidence still does not exist | same | Still partial |
| D6-FR-C3-010 MCQ penalty | `incorrect_penalty` (0 to max marks) recorded as `penalty_applied` for an answered wrong selection | `mcqMarkingService.js` | Implemented and tested |
| D6-FR-C3-011 MCQ total | `aggregateMcqResults`: awarded, penalty, net (floored at 0), percentage | `mcqMarkingService.js` | Implemented and tested (service level) |

None of these changes a mark. The off-topic flag, the keywords, the disconnected list and the review flag are
information for the lecturer. An MCQ question's own mark is still full marks or 0; the penalty only enters the total.

## Verification (2026-10-29)

- C3 Python: 757 passed, 13 expected failures, 0 failed (741 before, plus 16 new tests in
  `tests/unit/test_keywords_relevance_review.py`). `ruff` is clean on `app`, `services` and the new test file.
- Backend: 124 tests, 119 pass, 0 fail, 3 skipped, 2 todo (118 / 113 before, plus 6 new tests in
  `c3_mcq_penalty_total.test.js`).
- Frontend and browser E2E were not rerun and the frontend does not yet display the new fields.

## Limits that must be stated with these results

- The off-topic rule is a word-overlap heuristic. A correct answer in different words can be flagged, and an
  off-topic answer that reuses the question's words is not. The 0.10 threshold is a design choice, not measured.
- The review rules say when a lecturer should look; they are not a confidence score and are not tuned on any human
  review decisions.
- "Disconnected" only reflects the cue-phrase and same-sentence links the mind map already finds.
- Keywords are descriptive counts, not a judgement of importance.

## Still open, with the reason

| Requirement | Why it is not done |
|---|---|
| D6-FR-C3-018 structured-answer segments | Needs a decision on the structured-answer format (also blocks D6-FR-C3-003) |
| D6-FR-C3-033 rubric edit / deactivate | Backend and database work with role and finalisation rules; separate task |
| D6-FR-C3-081 / 082 class analytics | Needs finalised results across a class; backend and UI work; separate task |
| D6-FR-C3-089 admin configuration | The matrix asks whether it is in C3's scope; needs an owner decision |
| D6-FR-C3-016, 021, 022, 025, 035, 069, 070, 090 | Partial for stated design reasons (no open concept extraction, no semantic validation, no human-annotated relations, no admin status view); not closable by code alone |
| LLM and RAG rows (042-044, 049, 051-056, FR-C3-16..20) | Excluded by request; RAG quota not decided |
| C2 / C4 rows (FR-C3-42, 44) | Waiting on owner answers |
