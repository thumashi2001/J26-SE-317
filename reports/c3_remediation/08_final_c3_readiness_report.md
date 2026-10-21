# 08 Final C3 readiness report (2026-10-21)

## What was done
| Workstream | Status | Evidence |
|---|---|---|
| Git cleanup | **Done, pushed** (29 commits, only target branch) | `git_history_cleanup.md`, 06, 07 |
| Future attribution | Project-local `.claude/settings.local.json` (`attribution` empty) + CLAUDE.md rule | cleanup report |
| Dataset | v2 derived (3 train questions quarantined); **ratio-concentration still FAILS (0.766 > 0.45)**, threshold untouched | 02, `dataset_v2_hash_manifest.json` |
| Security (C3) | B1, B2, B3/X1, B4, B5, B6, B7, B8 fixed with tests; B9 and shared-app items open | 04, 05 |
| Models | TF-IDF, SBERT, RoBERTa trained/evaluated on v2 with validation-only selection; Condition E and baseline re-scored | 03 |
| LLM / RAG conditions | **Not run** (no credits/quota); not simulated | 03 |
| Integration | Python pipeline code unchanged (324 pass); Node suite 91 pass; Express↔FastAPI live tests pass; frontend builds; no browser walkthrough | 05 |
| Commit/push of remediation | **None** (as instructed) | `git status` |

## Headline results
- RoBERTa-base (validation-selected): test nMAE 0.038, QWK 0.98; TF-IDF 0.081; SBERT-ridge 0.084; lexical baseline 0.112; Condition E 0.209 (binary rubric). A length-only diagnostic scores 0.067, so TF-IDF/SBERT gains are not proof of semantic skill. Labels are tier-based, so all numbers measure recovery of synthetic tiers, not human agreement.
- Preferred model: RoBERTa as a *scorer candidate*; the explainable deterministic pipeline stays the live C3 path. Provisional (one seed, 90 test answers, 15 questions).

## Remaining limitations and prioritised actions
1. **P0 before presenting numbers:** state that the dataset fails ratio-concentration and is tier-labelled; do not call it validated.
2. **P0:** commit decision for the uncommitted remediation (backend security, tests, frontend change, v2 dataset, experiment code, reports) — awaiting your authorization; remember the new `.claude/settings.local.json` must not be committed.
3. **P1:** manual smoke test of the student page after the security change (presets now go through `demo_id`; "custom" assessments are lecturer-only) and of the lecturer batch flow with a student `batch_id` submission.
4. **P1:** external check on EngSAF / ASAP-SAS (planned in Day 23) and, if possible, human-marked answers; add seeds and a saved RoBERTa checkpoint.
5. **P1:** rubric levels for graded partial credit (so Condition E can compete), QWK-based reporting in the evaluator, server-side question bank UI for lecturers.
6. **P2:** AUDIT-B9 JSON 404/error middleware, rate limiting on login and `/assess`, CORS restriction, Python service shared secret, review history array, `finalize-all` auto-accept review, raw proxy restriction.
7. **P2:** LLM/RAG conditions once API quota exists; collaborator note about the rewritten branch; decide on the 9 Thumashi trailer commits (needs team coordination).
8. **P3:** lint cleanup (ESLint 10, ruff E501), refactors from the SOLID audit.
