# AdaptiveLearnSE Component 3 — Proposal & Supervisor Comment Response Matrix

**Document Version:** 2.0.0 (Authoritative Governance & Supervisor Feedback Matrix)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  

---

## 1. Governance & Feedback Traceability Overview

During the research proposal defense, Topic Assessment Form (TAF) review, and subsequent supervisor progress consultations, key comments and architectural directives were provided to ensure research rigor, academic integrity, and practical feasibility.

The matrix below maps each specific comment to the architectural decision made, the concrete implementation evidence in the repository, its current status, and any remaining supervisor confirmations required.

---

## 2. Proposal & Supervisor Feedback Matrix

| Ref ID | Source / Stage | Original Comment / Directive | Decision & Strategy Adopted | Concrete Implementation Evidence & Paths | Status | Remaining Action / Supervisor Confirmation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **COM-01** | Proposal Panel | *"Automated subjective evaluation must not be a black box. The system must explain exactly why a mark was awarded, linking points to student evidence."* | **ACCEPTED & IMPLEMENTED:** Designed the F2 rubric scoring engine to extract sentence-level evidence spans (`evidence_spans`) linking each awarded mark to the specific student answer sentence. | `ai-services/c3/services/criterion_evaluator.py:155-185`<br>`frontend/src/pages/c3/components/CriterionCard.jsx`<br>`ss/06_criterion_evidence_feedback.png` | ✅ **Implemented & Verified** | None for PP1. Demonstrable in review modal during live demo. |
| **COM-02** | Supervisor Review | *"There must be a rigorous research methodology involved when creating evaluation data. You cannot simply test on ad-hoc answers without ground truth."* | **ACCEPTED & IMPLEMENTED:** Constructed a controlled synthetic benchmark (`C3-Phase3-v5-FINAL`) containing 167 questions and 1,002 answers based on SLIIT SE3010–SE3040 course syllabi, featuring 6 controlled quality conditions (Full to Irrelevant) with zero train/test leakage. | `ai-services/c3/datasets/synthetic/07_DATASET_README.md`<br>`ai-services/c3/tests/unit/test_dataset_loader.py`<br>`raw_predictions_test_split.csv` | ✅ **Implemented & Verified** | Formal institutional ethics approval is required post-PP1 before authentic student papers can be ingested. |
| **COM-03** | Proposal Panel | *"Fully autonomous grading violates university examination governance. A certified lecturer must remain authoritatively in control of final marks."* | **ACCEPTED & IMPLEMENTED:** Implemented human-in-the-loop workflow. Automated marks enter MongoDB as `pending_review` (AI Proposed). Finalization requires lecturer sign-off, and score overrides mandate a written justification string. | `backend/src/modules/c3/controllers/c3Controller.js:reviewSubmission`<br>`backend/src/modules/c3/services/submissionService.js:375`<br>`ss/08_lecturer_override_reason.png` | ✅ **Implemented & Verified** | Present during live demo: attempt an override without reason to prove governance enforcement. |
| **COM-04** | Supervisor Review | *"Concept mind maps must not be decorative static pictures. They must dynamically reflect the student's actual conceptual mastery."* | **ACCEPTED & IMPLEMENTED:** Implemented a dynamic Directed Acyclic Graph (DAG) generator in Python and an SVG visualizer in React that color-codes concept nodes by mastery status (`demonstrated` [green], `partial` [orange], `missing` [gray]). | `ai-services/c3/services/mindmap_generator.py`<br>`frontend/src/pages/c3/components/MindMapGraph.jsx`<br>`ss/07_concept_mind_map.png` | ✅ **Implemented & Verified** | None for PP1. Graph dynamically updates per student response. |
| **COM-05** | TAF Review | *"Clarify whether handwritten answer parsing and OCR are in scope for Component 3."* | **ACCEPTED & CLARIFIED:** Formally established that OCR and scanned handwriting recognition are **EXCLUDED FROM SCOPE**. Component 3 evaluates typed natural language text. Any image upload is defensively rejected with HTTP 400. | `backend/src/modules/c3/routes/index.js:31-32`<br>`backend/src/modules/c3/controllers/c3Controller.js:50-56`<br>`c3.test.js:16, 17` | ✅ **Enforced by Design** | State clearly to examiners that handwriting OCR was excluded to avoid confounding NLP marking accuracy with OCR error noise. |
| **COM-06** | Proposal Defense | *"How will your component share data with the Cognitive Digital Twin (Component 1)?"* | **ACCEPTED & IMPLEMENTED:** Designed and tested an asynchronous event bridge emitting structured learning events to MongoDB `learning_events` with two-stage lifecycle (`provisional` vs. `finalized`), allowing C1 to update student topic mastery. | `backend/src/integration/c3-c1/index.js`<br>`backend/src/modules/c1/services/eventService.js:71`<br>`c3.test.js:18-21, 40` | ✅ **Implemented & Verified** | Joint demonstration with Component 1 prepared for the group session. |
| **COM-07** | Supervisor Progress Check | *"Do not present uncalibrated zero-shot LLM numbers during PP1 if parameters are not yet tuned."* | **ACCEPTED & BOUNDED:** Deployed Condition E (Deterministic Concept Evidence + Rubric) as the authoritative active baseline prototype for PP1. Documented Conditions A–D and F as planned post-PP1 research conditions. | `docs/pp1/EXPERIMENT_STATUS.md`<br>`docs/pp1/DATASET_AND_EVALUATION_REPORT.md` | ✅ **Bounded & Documented** | Candidate must consult supervisor following PP1 on selecting cloud LLM API provider (Gemini 1.5 Pro vs GPT-4o) for Phase 4. |

---

## 3. Specific Questions for Next Supervisor Consultation (Post-PP1)

Following the PP1 evaluation on 22–26 October 2026, the candidate will formally confirm the following with the project supervisor:
1. **Institutional Ethics Approval for Authentic Student Trials:** Confirm the application procedure for institutional ethics clearance to pilot Component 3 with real student submissions from Year 3 Software Architecture classes.
2. **Phase 4 RAG Model Selection (Condition C & D):** Align on whether to use open-weights dense embeddings (e.g. `all-MiniLM-L6-v2`) or Gemini Embeddings for course slide retrieval.
3. **Shared CCKG Assignment:** Request formal supervisor resolution on the team assignment and timeline for implementing the Neo4j Curriculum Concept Knowledge Graph.
