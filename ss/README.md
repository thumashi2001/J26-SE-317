# AdaptiveLearnSE Component 3 — Verification Screenshot Index

This directory contains authoritative, real screenshots captured directly from the running AdaptiveLearnSE Component 3 system (React Vite frontend, Node.js/Express backend, Python FastAPI AI service, and MongoDB Atlas persistence).

**Capture Date:** 20 October 2026  
**Environment:** Windows 11, Node.js v20+, Python 3.14 / 3.13 venv, Chrome Headless / Vite 5.4.21  
**Scope:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)

---

## Screenshot Index

| Filename | Purpose & View Description | Reproduction Steps | Verified Status |
| :--- | :--- | :--- | :--- |
| `01_login_or_role_access.png` | Role-based authentication entry point (`/login`). Shows SLIIT institutional login portal for Student, Lecturer, and Admin accounts. | Navigate to `http://localhost:5173/login`. | Verified Real Capture |
| `02_lecturer_batch_setup.png` | Lecturer Batch Marking Studio — Step 1: Assessment Setup (`/lecturer/c3/batch`). Configures question, rubric, criteria, max marks, and scoring levels. | Sign in as `SLIITLEC101`, open `/lecturer/c3/batch`, click preset or load sample question. | Verified Real Capture |
| `03_typed_answer_import.png` | Batch Marking Studio — Step 2: Student Typed Answer Entry. Shows CSV cohort import and dynamic answer grid. (No OCR). | Click "Fill Sample Cohort" or paste student answers CSV. | Verified Real Capture |
| `04_validation_preview.png` | Batch Marking Studio — Step 3: Preview & Validation. Pre-marking checks: valid rows, duplicate detection, and empty response flags. | Click "Validate Answers ->" on Step 2. | Verified Real Capture |
| `05_batch_marking_results.png` | Batch Marking Studio — Step 4: Automated Batch Marking Results. Displays marks, percentages, and AI proposed status across cohort. | Click "Mark Valid Cohort (AI) ->" on Step 3. | Verified Real Capture |
| `06_criterion_evidence_feedback.png` | Individual Review Modal — Criterion Evidence & Feedback. Displays sentence-level evidence, rubric level descriptors, and actionable advice. | Click "Review" or "Inspect Evidence" on any student row in Step 4. | Verified Real Capture |
| `07_concept_mind_map.png` | Individual Review Modal — Concept Mind Map Graph. SVG DAG visualizer displaying demonstrated, partial, and missing concept nodes. | Scroll to the Concept Mind Map visualizer inside the review modal. | Verified Real Capture |
| `08_lecturer_override_reason.png` | Lecturer Review & Override Workflow. Shows score adjustment form with mandatory override justification requirement. | Enter new score and mandatory reason in the Override section of modal. | Verified Real Capture |
| `09_finalized_results.png` | Finalized Results State. All cohort submissions marked as Finalized (100%), synced to C1 learning events. | Click "Finalize Student Result" or "Finalize Entire Batch". | Verified Real Capture |
| `10_student_result_view.png` | Student-Facing Result & Provenance View (`/c3`). Shows automated marks, feedback, concept diagnosis, and provenance indicator. | Sign in as `IT10000001`, open `/c3`, submit answer or inspect completed assessment. | Verified Real Capture |
| `11_test_results.png` | Full Automated Test Suite Results. 41 Node backend tests + 99 Python AI tests (including 12 synthetic dataset loader tests) = 140 total tests passing + Vite frontend build. | Run `npm test` in backend, `pytest` in ai-services/c3, `npm run build` in frontend. | Verified Real Capture |
| `12_evaluation_results.png` | Research Benchmark Evaluation Dashboard. Quantitative comparison of Rubric-Aware Marking vs Baseline across 150 test items (MAE: 4.640 vs 5.609; 56% vs 20.7% tolerance). | Run `python experiments/verify_evaluation.py` and inspect generated metrics. | Verified Real Capture |

---

## Privacy & Redaction Statement

All screenshots use synthetic student identifiers (`IT21001001`–`IT21001007`, `IT10000001`) and approved academic questions from SE modules. No confidential student data, passwords, API keys, or private environment variables are shown.
