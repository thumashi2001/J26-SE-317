# Live C1 input compatibility — se-*-sim-v1 (+ practice-quiz estimate)

Protocol targets: **`se-path-sim-v1`** (obs dim 96) and **`se-supervised-sim-v1`**
(response 54 / exam 98 features). Catalogue hash
`95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622` (46 topics;
**46/46 ID match** with current C1 practice keys).

**Primary this-quiz score estimate** uses product protocol
**`c4-practice-quiz-estimate-v1`**: a **statistical heuristic formula** (not a trained model).

Path/supervised **models** remain simulation-trained where labelled and **experimental**.
`prior_strength=0.45` is **assumed**; training/serving mismatch is **not** eliminated.
Operational calendar packing uses Node heuristic `weakest_stored_mastery_v1`.
When the path policy is usable, its topic may be **pinned** as next practice.
**se-path-sim-v2 work is paused** (files preserved, not activated).

---

## Serving status

| Target | Live product wiring | Notes |
|---|---|---|
| Path next activity | **Experimental live** via `live-serving-v1` | Twin mastery real; step_frac serving approx.; **`prior_strength=0.45` assumed**; may pin next practice |
| This practice-bank quiz score | **Heuristic** `c4-practice-quiz-estimate-v1` | Formula: mean topic prior accuracy; **0.5 default** cold/partial; target **0.6** product rule |
| Exam readiness (sim) | **Experimental secondary** at mock create | Different target from this quiz; clearly labelled |
| Response (next-answer) | **Blocked / research demo only** | Difficulty unavailable; not required for core path/quiz |
| Synthetic demo | Separate simulation tab | Unchanged |

---

## A. Path observation (`se-path-sim-v1` / `live-serving-v1`)

Training layout:  
`[mastery×46, available×46, mean_mastery, frac_mastered, elapsed_env_step_frac, prior_strength]`.

| Feature | Live source | Provenance |
|---|---|---|
| mastery | C1 twin `score/100` | Missing twin key → `available=0`, mastery 0 (not observed zero) |
| available | semester ∩ practice bank ∩ twin key | Verified rules only |
| mean / frac_mastered | Derived over available | Threshold 0.8 = **simulator** config |
| elapsed_env_step_frac | Deduplicated `quiz_answer` attempts since path episode `created_at` ÷ 40 | Serving approximation of training attempt units. Mark done never counted. **Mismatch not eliminated.** |
| prior_strength | Protocol constant `0.45` frozen on path episode | **Assumed** (not measured). Remaining training/serving mismatch. v2 paused. |

Action mask: semester ∩ available ∩ mastery &lt; 0.8, with training reopen-all-available rule.

Product: next activity pinned when inference succeeds; calendar packing remains heuristic.

---

## B. Response features (54 cols) — blocked

| Feature | Status |
|---|---|
| topic priors / streak / learner_step / topic_oh | Derivable from `learning_events` chronologically |
| **difficulty** | **Unavailable** — no C1 numeric difficulty on the synthetic training scale |

**Verdict:** Research/demo only. Not wired into student path or quiz UX as a live feature.

---

## C. This-quiz estimate (`c4-practice-quiz-estimate-v1`) — heuristic (not trained)

| Item | Rule |
|---|---|
| Kind | **Statistical heuristic formula** — no learned weights |
| Blueprint | Snapshotted C4 practice-bank questions at attempt create |
| Formula | `mean_q(topic_accuracy[topic(q)])`; attempts=0 → **explicit 0.5 default** |
| Cutoff | C4 attempt `created_at` (frozen; never uses current answers/keys) |
| Cold start | No prior quiz_answer events → all questions use 0.5 (labelled in UI) |
| Pass / target | Product `PRACTICE_QUIZ_SCORE_TARGET = 0.6` — **not** institutional |
| After submit | Observed score separate; prediction/outcome pair stored; pre-exam unchanged |

---

## D. Simulation-trained exam/pass (secondary)

Cutoff and event rules as before. Meaning = synthetic overall readiness — **not** this quiz’s score.
Pass label 0.55 and classifier 0.5 remain training/classifier thresholds only.

---

## E. Explicit non-goals

1. Demo simulation tab must not write student progress.
2. Heuristic packing remains the calendar builder; RL does not invent multi-day futures from one frozen observation.
3. Never invent confidence→prior_strength or calendar-days→env-steps.
4. Never load v2 semantics under v1 weights.
5. C2 past-paper delivery remains unavailable (see `c2ExamAdapter.js` provider sketch).
