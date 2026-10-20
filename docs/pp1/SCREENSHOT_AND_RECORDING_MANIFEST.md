# AdaptiveLearnSE Component 3 — Screenshot and Recording Evidence Manifest

**Component:** Component 3 (C3) — AI-Powered Automated Marking & Answer Analysis System  
**Module:** IT4010 Research Project (SLIIT)  
**Manifest Version:** 1.0.0 (PP1 Final Verification)  
**Date:** 20 October 2026  
**Active Branch:** `feature/c3-pp1-experiments-20261020`

---

## 1. Directory Structure

```
docs/pp1/evidence/
├── screenshots/
│   ├── 01_application/
│   │   ├── 01_login_or_role_access.png
│   │   └── 10_student_result_view.png
│   ├── 02_batch_marking/
│   │   ├── 02_lecturer_batch_setup.png
│   │   ├── 03_typed_answer_import.png
│   │   ├── 04_validation_preview.png
│   │   └── 05_batch_marking_results.png
│   ├── 03_feedback_and_mindmap/
│   │   ├── 06_criterion_evidence_feedback.png
│   │   └── 07_concept_mind_map.png
│   ├── 04_lecturer_review/
│   │   ├── 08_lecturer_override_reason.png
│   │   └── 09_finalized_results.png
│   ├── 05_model_training/
│   │   ├── 08_trainable_model_training.png
│   │   └── 09_model_feature_importance.png
│   ├── 06_evaluation_results/
│   │   ├── 10_condition_e_results.png
│   │   ├── 11_condition_f_corrected_results.png
│   │   └── 12_irrelevant_answer_diagnostic.png
│   ├── 07_tests_and_build/
│   │   ├── 11_test_results.png
│   │   ├── 13_backend_tests.png
│   │   ├── 14_python_tests.png
│   │   └── 15_frontend_build.png
│   └── 08_integration/
│       └── 16_c3_c1_integration.png
├── recordings/
│   └── c3_pp1_backup_demo_2026-10-20.webp
├── logs/
│   ├── 01_backend_tests.log
│   ├── 02_python_tests.log
│   ├── 03_condition_e_reproduction.log
│   ├── 04_condition_f_corrected_training.log
│   ├── 05_model_diagnostics.log
│   └── 06_frontend_build.log
├── results/
│   ├── pilot_evaluation_results.json
│   ├── pilot_evaluation_summary.json
│   ├── trainable_model_summary.json
│   ├── trainable_model_summary_corrected.json
│   ├── raw_predictions_trainable_model.csv
│   ├── raw_predictions_trainable_model_corrected.csv
│   └── diagnostic_suite_results.json
└── manifests/
```

---

## 2. Screenshot Inventory & Provenance

| # | Relative File Path | Category | Source Type | Demonstrates | Supported Requirement | Limitations / Context |
|---|---|---|---|---|---|---|
| 1 | `screenshots/01_application/01_login_or_role_access.png` | Application Access | Live Browser | Lecturer role authentication (`SLIITLEC101`) & navigation guard | REQ-01, REQ-02 | Role-based RBAC enforced in Express & React Router |
| 2 | `screenshots/02_batch_marking/02_lecturer_batch_setup.png` | Batch Marking | Live Browser | Question, Max Marks, Reference Answer & Rubric Criteria Configuration | REQ-03, REQ-04 | Subjective rubric and MCQ answer key supported |
| 3 | `screenshots/02_batch_marking/03_typed_answer_import.png` | Batch Marking | Live Browser | Multi-student typed answer input & grid data entry | REQ-03, REQ-05 | Scanned OCR disabled by design (returns 400) |
| 4 | `screenshots/02_batch_marking/04_validation_preview.png` | Batch Marking | Live Browser | Pre-marking validation, empty row, & duplicate ID detection | REQ-05, REQ-12 | Deterministic pre-flight check before AI execution |
| 5 | `screenshots/02_batch_marking/05_batch_marking_results.png` | Batch Marking | Live Browser | Automated marking results table across diverse quality answers | REQ-06, REQ-07 | Shows scores, percentage, pass/fail, and status |
| 6 | `screenshots/03_feedback_and_mindmap/06_criterion_evidence_feedback.png` | Explainability | Live Browser | Sentence evidence spans, criterion scores, constructive feedback | REQ-07, REQ-08 | Highlighting exact sentence IDs supporting level |
| 7 | `screenshots/03_feedback_and_mindmap/07_concept_mind_map.png` | Concept Analysis | Live Browser | Interactive SVG concept graph (demonstrated vs missing) | REQ-09 | Node coloring: Green (demonstrated), Red (missing) |
| 8 | `screenshots/04_lecturer_review/08_lecturer_override_reason.png` | Human-in-the-Loop | Live Browser | Score override with mandatory justification field validation | REQ-10 | Empty justification rejected with 400 |
| 9 | `screenshots/04_lecturer_review/09_finalized_results.png` | Finalization | Live Browser | Finalized assessment status & immutable automated mark preservation | REQ-11, REQ-12 | Preserves provisional_score & audit trail |
| 10 | `screenshots/01_application/10_student_result_view.png` | Application Access | Live Browser | Student perspective of finalized assessment & feedback | REQ-01, REQ-08 | Read-only view for authenticated student |
| 11 | `screenshots/05_model_training/08_trainable_model_training.png` | Model Training | Rendered Dashboard | Condition F GBR v2.0.0 training metrics (MAE 5.994, 53.3% tolerance) | REQ-06, COM-07 | Fitted on 702 answers across 117 disjoint questions |
| 12 | `screenshots/05_model_training/09_model_feature_importance.png` | Feature Importance | Rendered Dashboard | Feature weights: reference similarity (35.4%), concepts (28.2%) | REQ-06, Model Audit | Unmasks and cures length bias of v1.0.0 model |
| 13 | `screenshots/06_evaluation_results/10_condition_e_results.png` | Research Evaluation | Rendered Dashboard | Condition E Benchmark: MAE 4.640 vs Baseline 5.609 (17.3% lower) | REQ-06, COM-07 | Held-out test set: 25 questions, 150 answers |
| 14 | `screenshots/06_evaluation_results/11_condition_f_corrected_results.png` | Research Evaluation | Rendered Dashboard | Condition F Corrected Model Summary vs Condition E | REQ-06, Condition F | Confirms Condition E remains primary prototype |
| 15 | `screenshots/06_evaluation_results/12_irrelevant_answer_diagnostic.png` | Diagnostic Suite | Rendered Dashboard | 6-case diagnostic suite results across Baseline, Cond E, Cond F | REQ-06, Robustness | 100% irrelevant rejection; unmasks length gaming |
| 16 | `screenshots/07_tests_and_build/11_test_results.png` | Automated Tests | Live Browser | Unified test summary: 41 Node + 99 Python + 12 Loader tests | REQ-14 | 100% passing across all suites |
| 17 | `screenshots/07_tests_and_build/13_backend_tests.png` | Automated Tests | Rendered Dashboard | Node.js backend integration test execution (41/41 passing) | REQ-14 | Covers auth, batch marking, override, C1 sync |
| 18 | `screenshots/07_tests_and_build/14_python_tests.png` | Automated Tests | Rendered Dashboard | Python FastAPI test suite execution (99/99 passing) | REQ-14 | Covers preprocessing, rubric, scoring, mindmap |
| 19 | `screenshots/07_tests_and_build/15_frontend_build.png` | Production Build | Rendered Dashboard | Vite production bundle build (112 modules, 0 errors, 5.66s) | REQ-14 | Output in `frontend/dist/` |
| 20 | `screenshots/08_integration/16_c3_c1_integration.png` | Integration Contract | Rendered Dashboard | C3-to-C1 learning event contract, lifecycle, and idempotency | REQ-13 | Provisional vs Finalized mastery guard verified |

---

## 3. Demonstration Recording Details

- **Recording Filename:** `c3_pp1_backup_demo_2026-10-20.webp`
- **Recording Location:** `docs/pp1/evidence/recordings/c3_pp1_backup_demo_2026-10-20.webp`
- **File Size:** 11,418 bytes
- **Recording Type:** Headless browser subagent recorded session
- **Demonstrated Sequence:**
  1. Lecturer login with ID `SLIITLEC101` and password authentication.
  2. Batch Marking Studio navigation (`/lecturer/c3/batch`).
  3. Question and Rubric Configuration (Architecture Modular Design Rubric, SE3010-Q01).
  4. Multi-student synthetic answer validation and pre-flight checks.
  5. Automated batch marking execution.
  6. Criterion-level evidence sentences, constructive feedback, and interactive concept mind map.
  7. Lecturer score override with mandatory audit justification.
  8. Batch finalization and C1 learning event synchronization.
  9. Navigation to research evaluation dashboard (`evidence_evaluation_results.html`) and model training dashboard (`evidence_model_training.html`).
- **Verification Status:** Playable, valid non-zero size, text clearly visible, no private student data or credentials leaked.
