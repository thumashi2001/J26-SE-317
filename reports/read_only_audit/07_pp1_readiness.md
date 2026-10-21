# 07 PP1 readiness assessment

## Scope compliance (agent C reading, spot-checked)
| Constraint | Evidence | Verdict |
|---|---|---|
| Condition E is the deterministic PP1 baseline | `AGENTS.md:57`; `CLAIM_EVIDENCE_DECISION_LOG.md:79`; `PROPOSAL_COMMENT_RESPONSE_MATRIX.md:27` (COM-07); `EXPERIMENT_A_TO_F_TRACEABILITY.md:34,306-307` | V compliant |
| Synthetic data primary; no public benchmark substituted | `AGENTS.md:62`; `CLAIM_EVIDENCE_DECISION_LOG.md:68-72` | V compliant |
| No unvalidated AI output as ground truth | repair pipeline is deterministic; LLM generator/trial outputs exist only in git history (7049ff8…76e4953, removed in 50d3f5a); ground truth stated as researcher-constructed | V compliant |
| No tuning on held-out test | `evaluate_repaired.py` fits nothing; F fits on validation (never run) | V compliant |
| Lecturer review/override preserved | `backend/src/modules/c3/routes/index.js:19-20` (lecturer/admin only); `services/submissionService.js:332-413` keeps `automated_mark`, stores `final_mark`/`lecturer_decision`/`override_reason`/`reviewed_by`; reason mandatory. Known gaps (AUDIT-B2/B3/B5): finalized results can be reopened by re-posting a batch id, no upper bound on override marks, finalize not atomic. | V present; with listed defects |
| A–D/F deferred (COM-07) vs later decision to treat A–F as PP1 results | committed docs still say deferred; **the later decision is not recorded in any committed document** (grep) | **CONTRADICTION (B: needs the supervisor/user decision recorded)** |
| Limitations disclosed accurately | cards state synthetic, no expert validation, test split shrank, ratio check FAIL; gaps: card does not say the lexical baseline may be a length/template artefact; card says "ground truth researcher-constructed" only in the audit | Mostly V; fix wording |

## Demonstrably ready (V)
- A reproducible, hash-verified repair of the original dataset with a full ledger, quarantine with original values, deterministic reruns, and a validator with injected-defect tests.
- A repaired primary set: 96 questions / 576 answers, six variants each, splits unchanged, no `nan`, marks in range.
- Offline lexical baseline and Condition E results on the repaired test split (n = 90) that I reproduced exactly, with legacy figures reproduced and explained.
- Live Neo4j (5 tests pass); real Gemini/OpenAI provider code; the lecturer review flow exists.

## Blocked / not ready
- **Rubric-aware evaluation:** no scoring levels exist; 391/487 criterion ids unresolved; Condition E is run as a binary 0-or-full predictor. A–D/F cannot run on this schema (and no LLM condition has ever run). (V)
- **API access:** Gemini free tier (≈20 requests/day/model) and OpenAI with no credits (REPORTED earlier in this session from live responses; not re-checked here – B).
- **Validation:** ratio-concentration fails (hard) – 0.758 overall, 1.0 on validation, 0.917 on test.
- **Statistical comparability:** test n = 90 from 15 questions; the 100-mark questions dominate absolute MAE.
- **Backend:** AUDIT-B1…B9 todos (client-supplied rubric/answer key accepted, ownership checks missing, NoSQL operator injection, persistence failure masked as success, forgeable tokens when `AUTH_SECRET` unset) – security issues, separate from the dataset.

## Claims that must NOT be made
1. That the dataset is "fully repaired", "validated" or "ALL PASS" (hard check fails; criterion ids unresolved).
2. That Condition E beats the lexical baseline (on the repaired test split the baseline is better; the documented 17.3 % reduction is not reproducible and the 5.609 baseline figure does not reproduce).
3. That the test results demonstrate rubric-aware partial-credit marking (E is binary here).
4. Any result for Conditions A–D/F, any genuine LLM inference, dense-retrieval results or GraphRAG results (none exist).
5. Expert validation, authentic student responses, or generalisation beyond synthetic template-like answers (answers are template-generated; 96 IRRELEVANT answers are one sentence; MOSTLY/MISSING/MISCONCEPTION share marks in 96/96 questions).
6. End-to-end readiness of the Express ↔ FastAPI ↔ Mongo ↔ lecturer flow (not run).
7. That test sets are leakage-free (a 0.903 near-duplicate question pair spans train/test; 9 cross-question duplicate answers are unflagged).

## Needed before PP1 evaluation (summary; see 08)
Record the A–F decision; decide how to treat the failing ratio check; resolve the leaking pair and the incomplete scope flags; choose a rubric-level strategy (O1/O4) and build the loader adapter; fix baseline definition and report normalised metrics with n; update or banner the ~29 stale documents.
