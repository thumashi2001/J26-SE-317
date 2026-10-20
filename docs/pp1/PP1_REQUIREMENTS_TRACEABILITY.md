# AdaptiveLearnSE — Master PP1 Requirements Traceability Matrix

**Project:** IT4010 AdaptiveLearnSE — AI-Powered Cognitive Digital Twin for Adaptive Learning, Exam Intelligence, and Automated Assessment  
**Candidate Component:** Component 3 (C3) — AI-Powered Automated Marking & Answer Analysis System  
**Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Document Version:** 2.0.0 (Authoritative Rubric Traceability)  
**Authoritative Basis:** SLIIT CDAP PP1 Assessment Mark Sheet & Schedule Guidelines  

---

## 1. PP1 Assessment Structure & Rubric Weighting

The official CDAP Project Performance 1 (PP1) evaluation evaluates the candidate across five core assessment pillars (total 100%), conducted over a 40-minute individual/group defense session:
- **Presentation:** 10 minutes
- **System Demonstration:** 10 minutes
- **Viva Voce & Technical Defense:** 15 minutes
- **Marking & Deliberation:** 5 minutes

| Category ID | Core Assessment Pillar | Pillar Weight | Sub-Criteria & Internal Allocation | Effective Overall Weight |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | **Proven Gap / Creative Solution** | **10%** | P1.1: Problem Definition (30%)<br>P1.2: Proof of Concept & Gap Verification (70%) | **3.0%**<br>**7.0%** |
| **P2** | **Specialized Knowledge** | **25%** | P2.1: Application of Key Knowledge Pillars (30%)<br>P2.2: Application of Relevant Technologies (70%) | **7.5%**<br>**17.5%** |
| **P3** | **Solution Implementation** | **40%** | P3.1: Design Excellence & Architecture (20%)<br>P3.2: Prototype / Research Completion (30%)<br>P3.3: Standards, Clean Code & Best Practices (20%)<br>P3.4: User & Functional Requirements Fulfilled (20%)<br>P3.5: Risk Mitigation & Failure Handling (10%) | **8.0%**<br>**12.0%**<br>**8.0%**<br>**8.0%**<br>**4.0%** |
| **P4** | **Effective Communication** | **15%** | P4.1: Technical Defense & Communication (60%)<br>P4.2: Slide Presentation & Demo Structure (40%) | **9.0%**<br>**6.0%** |
| **P5** | **Commercialization / Potential** | **10%** | P5.1: Market Need, Scalability & Viability (100%) | **10.0%** |
| **TOTAL** | **Full PP1 Evaluation** | **100%** | **11 Sub-Criteria Evaluated** | **100.0%** |

---

## 2. Comprehensive Traceability Matrix

The following matrix traces every official rubric criterion to the actual implementation, empirical evidence, current completion status, documented limitations, and corrective actions.

| Criterion ID | Official Rubric Criterion | Weight | Examiner Expectations | Existing Repository Evidence & File Paths | Implementation Status | Gaps, Limitations & Corrective Actions | Owner |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **P1.1** | **Problem Definition** | 3.0% | Clearly articulated educational assessment bottleneck; why manual subjective grading in SE education is slow, inconsistent, lacks formative feedback, and suffers from cohort scaling challenges. | `docs/pp1/PP1_PRESENTATION_OUTLINE.md` (Slide 2)<br>`README.md:1-25` | ✅ **Verified Complete** | None for C3. Candidate must clearly state the SE grading bottleneck within the first 2 minutes of the presentation. | Candidate (C3) |
| **P1.2** | **Proof of Concept & Gap Verification** | 7.0% | Functional proof that automated subjective marking can combine evidence extraction with rubric alignment, avoiding generative hallucinations and token-overlap false positives. | `ai-services/c3/experiments/verify_evaluation.py`<br>`ai-services/c3/experiments/results/raw_predictions_test_split.csv`<br>`ss/12_evaluation_results.png` | ✅ **Verified Complete** | 150-answer benchmark demonstrates 17.3% MAE reduction over token overlap and 100% rejection of irrelevant answers. Limitation: Synthetic benchmark used due to institutional privacy. | Candidate (C3) |
| **P2.1** | **Key Knowledge Pillars** | 7.5% | Theoretical grounding in Natural Language Processing (tokenization, sentence segmentation, semantic cosine similarity), Educational Rubrics (Bloom-aligned criteria, scoring levels), Graph Structures (DAGs for concept hierarchies), and Psychometrics. | `ai-services/c3/services/rubric_validator.py`<br>`ai-services/c3/services/criterion_evaluator.py`<br>`ai-services/c3/services/mindmap_generator.py`<br>`ai-services/c3/services/preprocessor.py` | ✅ **Verified Complete** | Theory is cleanly embodied in Python services. Examiner defense questions prepared in `docs/pp1/PP1_VIVA_QA.md`. | Candidate (C3) |
| **P2.2** | **Relevant Technologies** | 17.5% | Justified modern tech stack: React 18 + Vite (reactive UI), Node.js Express (RESTful backend, JWT auth), Python 3.14 + FastAPI (high-performance async NLP engine), MongoDB Atlas (document persistence), Pytest & Node Native Runner. | `frontend/package.json`<br>`backend/package.json`<br>`ai-services/c3/requirements.txt`<br>`ai-services/c3/app/main.py` | ✅ **Verified Complete** | Stack is running live across ports 5173, 3000, 8003 with MongoDB Atlas. | Candidate (C3) |
| **P3.1** | **Design Excellence & Architecture** | 8.0% | Clean, modular architectural separation; decoupled AI service from application backend; stateless marking pipeline; clear API contracts; interactive DAG concept visualization. | `docs/pp1/ARCHITECTURE_DIAGRAM.md`<br>`frontend/src/pages/c3/components/MindMapGraph.jsx`<br>`backend/src/modules/c3/controllers/c3Controller.js` | ✅ **Verified Complete** | SVG DAG visualization is dynamically computed without external charting bloat. | Candidate (C3) |
| **P3.2** | **Prototype / Research Completion** | 12.0% | Functional end-to-end prototype: assessment setup, typed answer import, validation, marking, evidence display, lecturer override, batch finalization, and empirical evaluation. | `backend/src/modules/c3/services/batchMarkingService.js`<br>`frontend/src/pages/c3/LecturerBatchMarkingPage.jsx`<br>`ss/01`–`12_*.png` | ✅ **Verified Complete** | Software prototype is 100% complete and demonstrable. Research scope limitation: Condition E active prototype; Conditions A–D, F deferred post-PP1. | Candidate (C3) |
| **P3.3** | **Standards, Clean Code & Best Practices** | 8.0% | Adherence to SOLID principles, layered architecture, RBAC security, input validation, idempotent batch retries, no hardcoded secrets, and regression test suites. | `docs/pp1/SOLID_AND_CODE_QUALITY_AUDIT.md`<br>`backend/src/modules/c3/tests/c3.test.js`<br>`ai-services/c3/tests/` | ✅ **Verified Complete** | 140 automated tests passing (41 Node + 99 Python); clean Vite build (112 modules). | Candidate (C3) |
| **P3.4** | **User & Functional Requirements** | 8.0% | Lecturer creates setup once -> submits cohort -> validates -> automated grading -> inspects evidence/mindmap -> overrides with reason -> finalizes -> C1 digital twin receives learning events. | `frontend/src/pages/c3/LecturerBatchMarkingPage.jsx`<br>`backend/src/modules/c3/services/submissionService.js`<br>`backend/src/integration/c3-c1/index.js` | ✅ **Verified Complete** | Realized in 4-step wizard. Handled empty rows, duplicate students, and malformed rubrics. | Candidate (C3) |
| **P3.5** | **Risk Mitigation & Failure Handling** | 4.0% | Explicit handling of remote service timeouts (502), internal AI errors (500), input validation errors (400), duplicate prevention, and network fallback. | `backend/src/modules/c3/tests/c3.test.js:7,8,16,17,38`<br>`docs/pp1/RISKS_AND_MITIGATIONS.md`<br>`docs/pp1/DEMO_RECOVERY_PLAN.md` | ✅ **Verified Complete** | Comprehensive recovery procedures and failure injection tests verified. | Candidate (C3) |
| **P4.1** | **Communication & Technical Defense** | 9.0% | Clear, honest technical articulation during viva; ability to explain why baseline has lower RMSE, why 0.34ms latency is in-process CPU time, and how C3 links to C1. | `docs/pp1/PP1_VIVA_QA.md`<br>`docs/pp1/CODE_WALKTHROUGH.md` | ✅ **Prepared for Viva** | Candidate must memorize the 20 prepared defense answers and avoid claiming universal superiority. | Candidate (C3) |
| **P4.2** | **Presentation & Demo Structure** | 6.0% | Structured 10-minute presentation deck and 10-minute seamless live demo runbook telling a coherent user story. | `docs/pp1/PP1_PRESENTATION_OUTLINE.md`<br>`docs/pp1/PP1_DEMO_SCRIPT.md`<br>`docs/pp1/DEMO_RUNBOOK.md` | ✅ **Verified Complete** | Exact time allocations, spoken cues, and click paths documented. | Candidate (C3) |
| **P5.1** | **Commercialization & Scalability** | 10.0% | Practical deployment viability; SaaS business model for higher education; compute cost efficiency (0.34ms in-process CPU vs expensive GPU/LLM tokens); LMS integration potential (LTI standard). | `docs/pp1/PP1_PRESENTATION_OUTLINE.md` (Slide 10)<br>`docs/pp1/FINAL_PP1_GAP_AND_READINESS_REPORT.md` | ✅ **Verified Complete** | High commercial appeal due to ultra-low operational inference cost and privacy-first local deterministic processing. | Candidate (C3) |

---

## 3. Rubric Score Contribution Breakdown

To ensure no false assumptions are made, passing automated tests and clean UI builds represent essential prerequisites for **P3 (Solution Implementation - 40%)**, but do not guarantee marks in **P1 (Gap/Creativity - 10%)**, **P2 (Specialized Knowledge - 25%)**, **P4 (Communication - 15%)**, or **P5 (Commercialization - 10%)**.

```
[Total PP1 Potential: 100%]
 ├── P1: Proven Gap & Research Proof-of-Concept ── 10% (Verified via 150-answer benchmark & 17.3% MAE reduction)
 ├── P2: Specialized Knowledge & Technologies ──── 25% (Verified via NLP/DAG architecture & 140 passing tests)
 ├── P3: Solution Implementation & Quality ─────── 40% (Verified via Batch Studio, Override governance, C1 sync, Vite build)
 ├── P4: Effective Viva Defense & Presentation ─── 15% (Prepared via 10-min deck, 10-min demo, and 20 Q&A defenses)
 └── P5: Commercial Viability & Scalability ────── 10% (Prepared via EdTech SaaS model & ultra-low latency compute profile)
```

---

## 4. Distinction Between Missing Features vs. Missing Evidence

| Category | Item Description | Actual Code Status | Evidence Status | Required Action for Viva |
| :--- | :--- | :--- | :--- | :--- |
| **Batch Marking Studio** | Configure question once, grade cohort | Fully functional in `LecturerBatchMarkingPage.jsx` | Captured in `ss/02`, `03`, `04`, `05` | Rehearse live demonstration using Demo Runbook. |
| **Sentence Evidence Spans** | Highlighting source sentences linked to criteria | Generated by `criterion_evaluator.py` | Captured in `ss/06_criterion_evidence_feedback.png` | Demonstrate in Review Modal on student `IT21001001`. |
| **Concept Mind Map DAG** | Dynamic SVG visualizer showing concept masteries | Rendered by `MindMapGraph.jsx` | Captured in `ss/07_concept_mind_map.png` | Explain DAG node color coding (green=demonstrated, orange=partial, gray=missing). |
| **Lecturer Override Governance** | Mandatory reason enforcement on mark change | Enforced in `c3Controller.js:reviewSubmission` | Captured in `ss/08_lecturer_override_reason.png` | Demonstrate rejected override when reason is blank. |
| **C1 Learning Event Sync** | Idempotent emission of provisional/finalized marks | Enforced in `syncC3AssessmentToC1` | Verified in `c3.test.js:18-21, 40` | Highlight code-level contract in `c1/services/eventService.js:71`. |
| **Research Dataset Validity** | Controlled synthetic benchmark (167 questions) | Verified by `test_dataset_loader.py` | Evaluated in `raw_predictions_test_split.csv` | Present zero-leakage guarantee and honest MAE vs RMSE trade-off. |
| **Two-Minute Backup Video** | Rapid backup video in case of network collapse | Not recorded as MP4 | Documented in `TWO_MINUTE_DEMO_VIDEO_SCRIPT.md` | Provide script and storyboard; capture if recording tools available. |
