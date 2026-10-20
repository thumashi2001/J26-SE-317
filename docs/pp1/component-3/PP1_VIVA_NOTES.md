# AdaptiveLearnSE Component 3 — PP1 Viva Defense Notes & Technical Q&A

**Candidate Milestone:** Project Performance 1 (PP1)  
**Viva Date:** 22 October 2026  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Supervisor / Evaluation Panel:** SLIIT Faculty of Computing — Department of Software Engineering

---

## 1. Quick Technical Pitch (2-Minute Elevator Summary)

> *"Good morning, respected panel members. My research contribution in AdaptiveLearnSE is Component 3: The AI-Powered Automated Marking & Answer Analysis System.*
>
> *Existing automated essay scoring systems suffer from three major deficiencies in university software engineering education: first, they act as unexplainable black boxes that award a single monolithic number without linking back to student sentences; second, when using generative LLMs, they hallucinate credit simply because keywords appear; and third, they fail to integrate into practical classroom workflows where a lecturer must grade an entire cohort against one rubric.*
>
> *To address these gaps, Component 3 provides: (1) a multi-criterion rubric-aware marking engine that strictly bounds scores by evidence; (2) automatic extraction of sentence-level evidence and diagnostic concept states—demonstrated, partial, and missing; (3) dynamic generation of hierarchical concept mind maps from student answers; (4) a high-throughput lecturer batch-marking studio; and (5) a human-in-the-loop review architecture where the lecturer remains the final authority.*
>
> *On our canonical benchmark test split of 150 controlled answers across 25 Software Engineering questions, our rubric-aware engine achieves an MAE of 4.640, outperforming naive lexical baseline marking by 17.3%, with 94.3% concept diagnosis F1 and sub-millisecond latency. All 140 automated tests pass across our Node.js and Python tiers."*

---

## 2. Core Research Questions & Contributions

| Dimension | Research Problem / Gap | Component 3 Contribution |
| :--- | :--- | :--- |
| **Explainability** | Black-box LLMs award marks without showing which sentence earned which mark. | Links specific sentence IDs to rubric criteria, scoring levels, and concept matches. |
| **Cognitive Diagnostics** | Traditional graders fail to identify what specific conceptual gaps a student has. | Diagnoses demonstrated, partially demonstrated, and missing concepts with an interactive mind map. |
| **Workflow Practicality** | Graders require re-creating rubrics for each student individually. | Shared batch setup: Configure once in Step 1, import cohort in Step 2, pre-validate in Step 3, mark and finalize in Step 4. |
| **Academic Governance** | Autonomous AI grading violates university accountability policies. | Enforces human-in-the-loop: AI proposes (`pending_review`); lecturer accepts or overrides with mandatory reason. |

---

## 3. Anticipated Viva Defense Questions & Truthful Defensible Answers

### Q1: "Why did you use a synthetic dataset instead of evaluating on real SLIIT student exam papers?"
**Defensible Answer:**
> *"Processing and publishing authentic student exam papers requires formal institutional ethics approval and strict student anonymization protocols to prevent privacy violations. Because those approvals were not in place for PP1, we constructed a controlled synthetic benchmark dataset of 167 questions and 1,002 answers based strictly on approved SLIIT SE3010–SE3040 course syllabi. 
> 
> Furthermore, real exams rarely contain balanced distributions of specific failure modes. Our synthetic dataset features six controlled variants per question—FULL, MOSTLY_CORRECT, PARTIAL, MISSING_CONCEPT, MISCONCEPTION, and IRRELEVANT—allowing us to test edge cases with absolute ground-truth control. We have explicitly stated in our reports that expert human validation has not been claimed."*

---

### Q2: "Why isn't OCR or handwritten student answer evaluation implemented?"
**Defensible Answer:**
> *"Computer Vision and Optical Character Recognition are distinct research problems with their own error rates. If we introduced OCR at this stage, handwriting misrecognition errors would confound our semantic marking and rubric scoring evaluations. Our approved research proposal explicitly focused on semantic understanding, evidence tracing, rubric-aware scoring, and mind mapping of natural language text. Therefore, OCR was intentionally excluded, and our backend explicitly rejects image uploads with a clear HTTP 400 error."*

---

### Q3: "What is your baseline, and why did you compare against it?"
**Defensible Answer:**
> *"Per our research guidelines, every advanced AI method must be compared against a defensible baseline. We implemented a deterministic token-overlap cosine similarity baseline. On our test split, our Rubric-Aware Marking Engine achieved an MAE of 4.640 compared to 5.609 for the baseline—a 17.3% error reduction. The baseline fails because it awards marks to verbose answers that repeat vocabulary without satisfying specific rubric criteria, whereas our engine enforces criterion-level scoring rules."*

---

### Q4: "What is the status of your GraphRAG and Vector-RAG experiments (Conditions A–F)?"
**Defensible Answer:**
> *"In our research methodology, we have structured six experimental conditions from A (LLM-only) through F (Full Multimodal Ensemble). For the PP1 milestone, we have implemented and empirically validated Condition E—our deterministic concept evidence and rubric-aware baseline prototype. Conditions A, B, C, D, and F are documented as planned research conditions for Phase 4. We chose not to run preliminary or uncalibrated LLM calls to avoid presenting non-rigorous numbers during this viva."*

---

### Q5: "How does Component 3 integrate with the other AdaptiveLearnSE components?"
**Defensible Answer:**
> *"Component 3 integrates downstream with Component 1 (the Cognitive Digital Twin) through our live integration bridge (`syncC3AssessmentToC1`). When an assessment is marked, it emits a provisional learning event to the MongoDB `learning_events` collection. When the lecturer reviews and finalizes the assessment, the bridge updates the event in-place with the final authoritative score, review decision, and demonstrated concepts. This contract is completely idempotent: retrying a batch or re-finalizing does not duplicate events."*

---

### Q6: "How do you guarantee that a lecturer re-running batch marking doesn't duplicate database records?"
**Defensible Answer:**
> *"In `submissionService.js` and `batchMarkingService.js`, our persistence layer performs an idempotent check on the compound key `(student_id, batch_id)`. If an existing submission is found for that student in that batch, it updates the submission and result records in-place rather than inserting duplicate MongoDB documents. We have an automated regression test (`c3.test.js:38`) verifying this exact behavior."*
