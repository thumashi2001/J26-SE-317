# C4 architecture (actual)

```text
[Browser / shared Layout + Auth]
        |
        v
[Node Express /api/v1/c4]
  pathService ──► liveInference se-path-multi-v2 → pin next eligible practice, revision, or quiz
               └► sequencer (heuristic ranks; v2 pin when eligible)
               └► scheduleBuilder (dates / days / budget packing; heuristic)
  examService  ──► practice-bank snapshot
               ├► c4-practice-quiz-estimate-v1 heuristic (primary this-quiz; not trained)
               ├► liveInference exam/pass (secondary experimental, different target)
               ├► training_practice_quiz_v1 (inactive; not called by Node)
               └► c2ExamAdapter (unavailable — provider sketch only)
  feedbackService
  lecturerPlan ──► live scope unavailable (test fixtures only; no student scan)
  simDemoController ──► synthetic scenarios only
        |
        +── read-only ──► Mongo: mastery_state, learning_events, practice_sessions
        +── write ──────► Mongo: c4_learning_paths, c4_exam_attempts, c4_feedback, …
        |
        v
[C1 AI :8001] twin maths (used via C1 Node modules; C4 does not write C1)

[C4 AI :8004] se-path-multi-v2 active checkpoint; se-path-sim-v1 and se-supervised-sim-v1 remain separate
```

## Component connections verified in code

| From → To | Mechanism |
|---|---|
| C1 twin → C4 plan | `c1Reader` snapshot → sequencer + schedule |
| Path policy → plan | se-path-multi-v2 pins the next eligible practice, revision, or quiz when the action is still open |
| C4 → C1 practice | `launch_path` `/c1/practice/:topic` |
| C1 sessions/events → C4 | `practiceSync` on refresh; attempt steps from `quiz_answer` |
| Events → this-quiz estimate | Blueprint + topic priors ≤ attempt `created_at` |
| Events → sim readiness | Same cutoff; different target (secondary) |
| C2 → C4 | **None** (adapter reports unavailable) |
| Lecturer → C4 plan | `GET /c4/lecturer/*` checks the token role, then fails closed. `studentId` is not authorization. |

## What changes if you alter critical logic

| Change | Effect |
|---|---|
| Mastery threshold 0.8 in mask | Different topics eligible for path policy; may reopen-all |
| `prior_strength` constant | Shifts v1 observation bias; still not measured student trait |
| Attempt-step window / dedupe | Changes step_frac; Mark done must never enter the count |
| Inject `episode_init_mean` into v1 obs | **Forbidden** under v1 weights — use se-path-sim-v2 |
| Exam cutoff later than create | Would leak future/exam answers — **forbidden** |
| Practice-quiz target 0.6 | Changes product “meets target” label only — not institutional |
| Heuristic vs model for calendar | Would redefine packing; currently packing ≠ RL multi-day forecast |

## Training / metrics locations (genuine saved)

- Path v1: `ai-services/c4/experiments/results/se_path_simulation_v1/`
- Supervised v1: `experiments/results/se_supervised_simulation_v1/.../final_test/`
- Path v2: active checkpoint `se-path-multi-v2-coverage-r2` seed 1. Calendar packing stays heuristic.
- This-quiz pass pipeline: `training_practice_quiz_v1/` — synthetic, `activation_allowed=false`.
