# C4 key code guide (viva)

## 1. Heuristic sequencer — `sequencer.js`

- **In:** twin mastery, optional insights topics, horizon, completed activities, optional mock-weakness boost topics, optional `pinFirstTopic` from path policy.
- **Out:** ordered `c1_practice` activities + unavailable list; optional `next_activity` flag on pinned row.
- **Algorithm:** weakest score first (estimatedNow → storedScore → twin.score); tie-break topic id; then optional model pin to front.
- **Validation:** only topics in practice bank ∩ twin; pin ignored if topic not eligible.
- **If changed:** product ranking / next activity changes; calendar packing still separate.

## 2. Daily schedule — `scheduleBuilder.js`

- **In:** activities + prefs (start/exam dates, daily minutes, study weekdays, plan days).
- **Out:** per-day cards, overdue flags, unscheduled with reasons.
- **Validation:** positive budget; exam ≥ start; estimate ≤ budget.
- **Failure:** 400 on bad prefs; never silently drop overflow work.
- **Assumption:** default 15 min/activity is an **estimate**.

## 3. Practice sync — `practiceSync.js`

- **In:** path doc + C1 `practice_sessions` / `learning_events` (read-only).
- **Out:**
  - `practice_verified` only when `practice_sessions.completed===true` and not `abandoned`,
    with `completed_at >= activity.eligible_since`, and session not already claimed.
  - `practice_observed` for open sessions with answers or quiz_answer events (participation only).
- **Does not:** treat a single quiz_answer or link click as activity completion; does not write C1.
- **C1 fact:** sessions complete when every item is answered (`QUESTIONS_PER_SESSION` typically 7).

## 4. Live features / inference — `liveFeatureBuilders.js`, `liveInference.js`, `liveModelAdapter.js`

- **Path in:** semester, twin mastery, **deduplicated quiz_answer attempt count** since episode start, frozen prior constant.
- **Path out:** observation+mask → `POST /v1/se-path-multi-v2/predict` → pin the next eligible practice, revision, or quiz. Completed activity ids are removed from the mask. Calendar packing stays heuristic.
- **This-quiz estimate:** heuristic formula (not trained) — mean topic prior accuracy; 0.5 default when attempts=0; product target 0.6. Pass probability stays insufficient evidence. The inactive gate in `training_practice_quiz_v1` is an implementation hold: the proposal PDF is not in the workspace, and `SE_MODEL_TRAINING_SPEC.md` §G says a pass model needs labels plus a signed feature catalogue.
- **Sim exam in:** `learning_events` ≤ attempt `created_at`; skip abandoned; dedupe session+question.
- **Sim exam out:** secondary experimental readiness (different target) + pass P.
- **Response:** `usable:false` (no item difficulty) — unmet for live serving without new contract/training.
- **Assumptions:** `prior_strength=0.45` is only an input to the older experimental practice pin. Multi-action v2 does not use that slot. Attempt steps are deduped practice answers, not Mark done.
- **Ownership:** C4 `resolveC4StudentId` — lecturers fail closed without roster.

## 5. Mock exams — `examService.js` + `c2ExamAdapter.js`

- **In:** topics / questionCount / timeLimit; C1 practice bank snapshot.
- **Out:** public questions (no keys). Attempt lists omit `review` and `correctIndexes`. Review is returned only when the attempt is opened after submit.
- **Pre-exam:** primary this-quiz estimate + secondary sim readiness; frozen at create; never rebuilt from answers; `prediction_outcome` on submit.
- **Timing:** `expires_at` enforced on save/submit.
- **Idempotency:** `clientRequestId`; duplicate submit returns same result.
- **C2:** adapter returns unavailable + required interface once (no delivery API).

## 6. Simulation proxy — `c4AiClient.js` / `simDemoController.js`

- **In:** authenticated browser → Node → `C4_AI_URL` (never from client).
- **Out:** synthetic predictions; `demo_not_persisted`.
- **Failures:** 400 validation, 502 timeout/unreachable, 503 model not ready.
