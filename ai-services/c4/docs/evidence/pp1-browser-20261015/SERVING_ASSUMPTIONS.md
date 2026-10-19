# Live serving assumptions (honest)

Date: 2026-10-16

## Path (`se-path-sim-v1/live-serving-v1`) — experimental

| Slot | Training | Live serving | Status |
|---|---|---|---|
| mastery / available / mean / frac | Simulator | C1 twin + semester ∩ bank ∩ twin | Verified transforms |
| elapsed_env_step_frac | 1 env step = 1 practice attempt | Deduplicated quiz_answer since episode start ÷ 40 | **Serving approximation** — mismatch not eliminated |
| prior_strength | Simulator latent | **Assumed constant 0.45** | **Remaining mismatch** (intentional for frozen v1) |

When usable, recommended topic may be pinned as next practice. Calendar packing = heuristic.

**v2** (replace prior_strength with episode_init_mean_mastery): files preserved; **paused / not activated**.

## This-quiz estimate (`c4-practice-quiz-estimate-v1`) — heuristic formula

**Not a trained model.** No weights.

```
predicted_score = mean over snapshotted questions q of:
  topic_accuracy[topic(q)] from quiz_answer events with timestamp ≤ cutoff
  if attempts on that topic == 0 → use default 0.5 (explicit cold/partial default)
predicted_pass = predicted_score >= 0.6  (product rule, not institutional)
```

Cold start = no prior quiz_answer events before cutoff (all questions use 0.5).

## Sim exam/pass (`se-supervised-sim-v1`) — secondary experimental

Different training target from this practice-bank quiz. Keep clearly labelled experimental.

## Response model

Unavailable live (no C1 item difficulty on training scale).
