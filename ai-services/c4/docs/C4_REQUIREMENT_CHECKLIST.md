# C4 requirement → implementation map (confirmed client scope)

Legend: **I** implemented · **T** automated-tested · **L** browser-verified · **X** unmet / blocked · **P** paused (prepared, not active)

Proposal PDF: not found in-repo or elsewhere in this workspace on 2026-10-18. Proposal reconciliation could not be performed. Mapping uses the confirmed client requirement list only.

| Confirmed client requirement | Status | Implemented behavior / evidence |
|---|---|---|
| Personalized adaptive learning paths using C1 learner info | I T L | Heuristic schedule from twin; experimental se-path-sim-v1 may pin next practice |
| Daily study activities (dates, days, time budget) | I T | Practice + C1 revision + C4 quiz for top weak topics; coding **not scheduled** (no C3 launch) |
| Exam urgency | I T | Rank penalty when exam date is within 14 days |
| Engagement (rate, streak, frequency) | I T | Asia/Colombo window; self-report ≠ verified; missing ≠ zero mastery |
| RL multi-action policy | **v2 imported; synthetic floor passed; not a real-student result** | `se-path-multi-v2-coverage-r2` seed 1 is the active checkpoint. Validation simulated mean mastery change was about 0.083 on Y3S1 and 0.130 on Y3S2, with invalid-action rate 0. Calendar packing stays `weakest_stored_mastery_v1`. If the checkpoint is missing or the action is ineligible, the plan says so and uses the heuristic. Coding stays unavailable. Rollback: remove `runtime-artifacts/se_path_multi_v2/active/`; the run folder stays. |
| Adaptive mock blueprint | I T | Weak-topic order + round-robin; **difficulty adaptation unavailable** |
| Pass probability for this quiz | Blocked pending a product decision | The proposal PDF is not in the workspace (`SE_PATH_SIM_V0.md`). `SE_MODEL_TRAINING_SPEC.md` §G says this needs outcome labels and a signed feature catalogue, and it is not a verified proposal clause. `train.py` keeps `activation_allowed` false under `real_student_learner_disjoint_validation_required` so synthetic numbers are not shown as P(pass). The live UI keeps the heuristic. |
| Practice participation/completion + adaptive replanning | I T L | observed / verified / self-report; replan keeps completed |
| Mock assessment + performance feedback | I T L | create/save/resume/submit/review |
| Readiness / pass estimation | I T | **Heuristic** this-quiz estimate (`c4-practice-quiz-estimate-v1`) + **experimental** sim readiness (secondary) |
| Component-to-component integration | I T L | C1↔C4 verified; **C2 past papers X** (no delivery API) |
| Trainable models + reproducible notebooks + evaluation outputs | I | Frozen v1 artifacts stay. `se-path-multi-v2-coverage-r2_20261017T040345500695Z` is imported with its executed notebook and validation JSON. Final-test numbers were not used to choose the seed. |
| Missing / invalid / failure handling | I T | usable:false, cold-start defaults labelled, AI fallback explicit |
| Coherent student UI in shared app | I L | `/c4` tabs in shared shell |
| Architecture / code explanations / 2-min demo docs | I | `C4_ARCHITECTURE_ACTUAL`, `C4_CODE_EXPLAINER`, `C4_STARTUP_AND_DEMO` |
| Working C2 past-paper assessment | X | Re-checked 2026-10-18: no C2 Node delivery API. Contract remains in `c2ExamAdapter.js`. |
| Live next-answer response model | X | Item difficulty unavailable on C1; cannot serve v1 response contract without inventing difficulty or replacement training |
| Lecturer class/roster view | **Blocked** | Page and service exist. Live scope is fail-closed. No approved roster. Test fixtures only. |
| Real-student validated predictive accuracy | X | Not established; sim metrics ≠ live accuracy |

## Honest notes (do not over-claim)

1. **`c4-practice-quiz-estimate-v1` is a statistical heuristic**, not a trained model:  
   `mean over quiz questions of (topic prior accuracy)`, with **0.5 default** when a topic has no prior attempts (cold start / partial defaults labelled in UI).
2. **se-path-sim-v1** remains **experimental**; **`prior_strength = 0.45` assumed**. Attempt-based `step_frac` is a serving approximation — **training/serving mismatch is not eliminated**.
3. Daily packing is **not** RL scheduling (`weakest_stored_mastery_v1`).
4. **se-path-multi-v2** can choose the next eligible practice, revision, or quiz. Passing the synthetic floor is not real-student effectiveness and does not beat every baseline. Online logs do not update frozen weights. The Colab manifest field `serves_students` stays false. Readiness reports that as `artifact_serves_students` and reports `student_plan_integration: requestable` when the checkpoint can be called. A student was served only for the authenticated plan request recorded in `docs/browser-evidence/2026-10-17-se-path-multi-v2.md`.
5. **Coding exercises** are not scheduled: C3 has no student launch. Revision uses `/c1/topic/:id`. Quizzes use the C4 practice bank.
6. **Pass probability for this quiz** is not shown as a number. Stored submitted attempts on 2026-10-18 were 4 rows from 1 student, which cannot support a learner-disjoint model. The new pipeline is synthetic and inactive. Heuristic 0.6 is a decision rule.
7. C3 marking, feedback, and submission review are mounted. They are not a coding-exercise catalogue, launch path, or completion contract. Coding stays masked. See `c3CodingAdapter.js`. C2 still has no student paper-delivery API. See `c2ExamAdapter.js`.

## Student / Lecturer matrix

Proposal PDF was not available. Rows below are the confirmed scope, not extra proposals.

| Role | Requirement | Status | Evidence |
|---|---|---|---|
| Student | Daily plan from mastery, weaknesses, progress, urgency | Completed | 2026-10-19 browser: reload kept revision 10, replan reached revision 11, today is 2026-10-19 |
| Student | RL next activity; heuristic calendar | Completed | Same session pinned Communication and Stakeholder Management practice, seed 1, checkpoint `71f66525cd16`, calendar stayed heuristic |
| Student | Practice, revision, quiz launch and distinct completion | Completed | Links resolved. Framework revision Mark done stayed `self_reported` with no practice evidence. Framework practice stayed `practice_verified` |
| Student | Practice-bank mock quiz and labelled heuristic estimate | Completed. P(pass) blocked | 3-question focus quiz `af_framework_selection`, save, reload, submit, review. Frozen estimate stayed 0. List had no answer keys |
| Student | Streak, frequency, feedback | Completed | Labelled feedback survived reload |
| Lecturer | Read study plans for an authorized class | Blocked for live use | `lecturerPlan.test.js`; page shows not operational |
| Lecturer | Edit plans, mark complete, or read private feedback | Not required | No lecturer mutation routes |
| Admin | C4 dashboard | Not a confirmed requirement | No admin page added |

## Automated / browser evidence

- Targeted tests: attempt steps, pin, heuristic quiz estimate, exam create/submit — pass.
- Browser: plan/practice/replan, quiz estimate labels, pin-on-replan; screenshots `01`–`20` preserved.
- 2026-10-17 authenticated Y3S1 replan used `se-path-multi-v2-coverage-r2` seed 1. Evidence: `docs/browser-evidence/2026-10-17-se-path-multi-v2.md`. This does not mark the whole component complete.
