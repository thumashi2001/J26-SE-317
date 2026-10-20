# AdaptiveLearnSE Component 3 — PP1 Last-Day Preparation & Rehearsal Checklist

**Target Milestone:** Project Performance 1 (PP1) Viva  
**Candidate Date:** 21 October 2026 (Rehearsal & Final Verification)  
**Assigned Component:** Component 3 (C3) — AI-Powered Automated Marking & Answer Analysis System  
**Scheduled Viva Dates:** 22, 23, and 26 October 2026 (Verify personal assigned slot)

---

## 1. Morning Rehearsal: Two-Minute Technical Pitch

Practice delivering this 2-minute pitch out loud 3 to 5 times with a timer:

- **[0:00 - 0:20] Problem & Core Objective:**
  *"Good morning. In software engineering higher education, manual marking of open-ended descriptive answers is slow, inconsistent, and offers minimal feedback. In AdaptiveLearnSE, I am responsible for Component 3: an AI-powered automated marking and answer analysis system that delivers criterion-level grading, sentence-level evidence extraction, and interactive concept mind maps."*

- **[0:20 - 0:45] Architecture & Live Workflow:**
  *"Our architecture combines a React Batch Marking Studio, an Express/MongoDB backend, and a Python FastAPI analytical service. A lecturer configures a question and rubric once. The system pre-validates student submissions, performs automated rubric-aware evaluation, highlights exact evidence sentences supporting each mark, and renders a concept DAG. The lecturer retains ultimate control through a human-in-the-loop override requiring mandatory written justification before finalization."*

- **[0:45 - 1:10] Trained Model & Training Audit (Condition F):**
  *"To explore supervised scoring, we trained a Gradient Boosted Regressor on 702 answers across 117 disjoint questions and tested on 150 held-out answers across 25 unseen questions. Our audit unmasked that an initial model suffered from length bias—scoring 9.99 on Roman Empire distractor essays because answer length mirrored marks in synthetic data. We corrected this by removing raw length, incorporating pairwise TF-IDF reference similarity (35.4% importance), and enforcing relevance gating. The corrected model successfully rejects 100% of out-of-domain distractors with 0.00 marks."*

- **[1:10 - 1:40] Empirical Results & Scientific Comparison:**
  *"Comparing our approaches: Our primary explainable prototype, Condition E, achieves an MAE of 4.640 marks—beating the token-overlap baseline of 5.609 marks by 17.3% with 100% irrelevant answer rejection. The trained Condition F model achieves an MAE of 5.994 marks with 53.3% tolerance agreement within ±2 marks. This demonstrates that while supervised regressor models are feasible, our deterministic rubric engine remains the superior, explainable, and defensible choice for PP1."*

- **[1:40 - 2:00] Teammate Integration, Boundaries & Phase 4:**
  *"Upon lecturer finalization, C3 emits an idempotent learning event to Component 1 to update the student's Cognitive Digital Twin without corrupting provisional mastery. In compliance with supervisor directive COM-07, zero-shot uncalibrated LLM numbers are not presented today. In Phase 4, we will introduce deep natural language inference to detect adversarial inverted reasoning and integrate authentic lecture slide embeddings."*

---

## 2. Technical Environment Sanity Check

Perform this 3-command check on the morning of the demonstration:

```powershell
# 1. Verify Node.js Backend Tests
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\backend
npm test
# EXPECT: 41 passing, 0 failing

# 2. Verify Python AI Tests
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3
..\..\..\.venv\Scripts\python.exe -m pytest tests/
# EXPECT: 99 passed, 0 failed

# 3. Verify Frontend Production Build
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\frontend
npm run build
# EXPECT: 112 modules transformed, built in ~5.6s (0 errors)
```

---

## 3. Live Demonstration Fail-Safe Runbook

| Scenario | Immediate Action | Backup Asset |
|---|---|---|
| **Live network drop or localhost crash** | Do not panic. Switch to offline slides and backup video. | `docs/pp1/evidence/recordings/c3_pp1_backup_demo_2026-10-20.webp` |
| **Examiner questions accuracy & metrics** | Open the static HTML dashboard in Chrome. | `http://localhost:5173/evidence_evaluation_results.html` or `docs/pp1/evidence/screenshots/06_evaluation_results/10_condition_e_results.png` |
| **Examiner asks about the trained model** | Open the model training & feature importance dashboard. | `http://localhost:5173/evidence_model_training.html` or `docs/pp1/evidence/screenshots/05_model_training/08_trainable_model_training.png` |
| **Examiner asks about edge cases / gaming** | Show the 6-case diagnostic table from Case 1 to Case 6. | `ai-services/c3/experiments/results/diagnostic_suite_results.json` |
| **Examiner asks about C1 integration** | Show the integration contract checklist and test cases. | `http://localhost:5173/evidence_integration.html` |

---

## 4. Key Defense Statements for Tough Viva Questions

1. **"Why is MAE 4.640 marks rather than 0?"**
   - *Defense:* "4.640 marks is on a 100-percentage scale across 150 held-out answers on unseen questions. It is 17.3% more accurate than the lexical baseline (5.609) and rejects 100% of irrelevant answers."

2. **"Why did RMSE worsen from 6.530 to 7.220 while MAE improved?"**
   - *Defense:* "RMSE penalizes large outliers quadratically. Condition E uses strict all-or-nothing concept criteria. When a student uses alternative valid phrasing not captured in the controlled vocabulary, the criterion awards 0, creating a few large error spikes that inflate RMSE even while the average error (MAE) is lower."

3. **"Did you train a model, or is it just rules?"**
   - *Defense:* "We implemented and audited both. Condition E is our primary explainable prototype using deterministic rubric trees and concept evidence. Condition F is our trained supervised Gradient Boosted Regressor fitted on 702 answers. We audited Condition F, unmasked synthetic length bias, and corrected it with reference TF-IDF similarity and semantic gating."

4. **"Why did you not present LLM results for Condition A and B?"**
   - *Defense:* "Per supervisor directive COM-07, uncalibrated zero-shot LLM figures must not be presented before hyperparameter tuning and calibration are complete. Presenting raw uncalibrated LLM outputs would violate supervisor instructions."

5. **"Can students submit scanned handwritten answers?"**
   - *Defense:* "No. Handwriting OCR is strictly out of scope for C3 in our approved proposal and TAF. Any attempt to upload images is explicitly rejected by our API with a 400 Bad Request error by design."
