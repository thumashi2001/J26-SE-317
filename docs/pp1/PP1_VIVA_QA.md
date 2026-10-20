# AdaptiveLearnSE Component 3 — PP1 Viva Voce Q&A Defense Guide

**Document Version:** 2.0.0 (Authoritative Technical Defense Guide)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Allocated Viva Time:** 15 Minutes (Examiner Questioning)  
**Candidate Preparation:** 15 High-Probability Questions & Model Answers  

---

### Q1: "Your evaluation report shows that the baseline token-overlap model achieved a lower RMSE (6.530) than your proposed rubric-aware model (7.220). Doesn't that mean the baseline is better?"
**Model Answer:**  
*"No, respected examiner, and this reflects a classic statistical trade-off in educational measurement:  
1. **MAE vs. RMSE:** Our proposed rubric-aware model achieved a **17.3% reduction in Mean Absolute Error (MAE: 4.640 vs. 5.609)** and achieved a **56.0% tolerance agreement within 2.0 marks**, compared to only **20.7%** for the baseline.  
2. **The Mathematics of RMSE:** RMSE squares all prediction errors ($e^2$). Our rubric evaluator operates as a discrete educational step-down function: if an answer completely omits a mandatory concept, the criterion drops to zero. In synthetic edge cases where the ground truth gave intermediate credit, this step drop produces a localized residual (e.g. 3 marks), which squares to 9 in RMSE.  
3. **The Flaw of Token Overlap:** Lexical token overlap outputs a smooth, continuous linear function of word overlap, which artificially avoids large squared errors, keeping RMSE lower. However, in classroom practice, token overlap is invalid because it awards passing marks to verbose fluff filled with common keywords. On our held-out test split, our proposed system achieved a **100% rejection rate on irrelevant answers**, whereas token overlap consistently over-awarded marks."*

---

### Q2: "You report a marking latency of 0.34 milliseconds. Can a full web system really evaluate an essay answer that quickly?"
**Model Answer:**  
*"Thank you for that question. I want to clarify the latency scope transparently:  
- The **0.34 ms figure** measures purely the **local algorithmic in-process CPU execution time** within the Python interpreter for lexical extraction, regex concept matching, rubric criteria scoring, and mind-map DAG generation.  
- When we account for the full web stack—including client HTTP dispatch, Express middleware processing, localhost network serialization, and MongoDB Atlas database writes—the **total end-to-end web round-trip latency in the browser is approximately 45 to 80 milliseconds**.  
- This is still virtually instantaneous, enabling real-time feedback without the 1-to-2 second delays typically incurred by external cloud LLMs."*

---

### Q3: "Why did you use a synthetic dataset instead of authentic student exam papers from SLIIT?"
**Model Answer:**  
*"Under university policy and standard research ethics, processing, analyzing, or storing authentic student examination papers requires formal Institutional Review Board (IRB) ethics clearance and signed student data protection waivers to avoid privacy breaches.  
Because those institutional approvals were not in place for PP1, we constructed a controlled synthetic benchmark dataset of **167 questions and 1,002 student answers (C3-Phase3-v5-FINAL)** based strictly on approved SLIIT Year 3 Software Engineering syllabi (SE3010 through SE3040). Furthermore, synthetic data allowed us to test controlled failure conditions—such as missing concepts, misconceptions, and irrelevant responses—with known mathematical ground truth."*

---

### Q4: "Your report claims 100% feedback validity and 100% mind-map validity. Were these evaluated by human pedagogical experts?"
**Model Answer:**  
*"No, respected examiner, and we document this boundary explicitly in our reports. The 100% validity metric represents **structural schema validation**:  
1. Every generated feedback payload conforms to our Pydantic schema, containing non-empty summary strings, demonstrated strengths arrays, and actionable improvement recommendations.  
2. Every generated mind map is a topologically valid Directed Acyclic Graph (DAG) with an intact root anchor and complete reachability across all concept nodes.  
Independent pedagogical trials with educational psychologists are scheduled as future post-PP1 validation."*

---

### Q5: "Why does Component 3 not support scanned handwritten exam papers or OCR?"
**Model Answer:**  
*"Our research proposal and approved scope explicitly define Component 3 as evaluating **typed natural language student responses**.  
Computer vision, handwriting segmentation, and Optical Character Recognition (OCR) represent a completely separate engineering domain. Introducing OCR would introduce optical recognition noise (e.g., misread characters), confounding our ability to evaluate the semantic marking engine accurately. To enforce this boundary, any attempt to upload scanned image files to C3 is defensively rejected with an HTTP 400 Bad Request error."*

---

### Q6: "Your proposal outlines Conditions A through F. Why are only Condition E results reported for PP1?"
**Model Answer:**  
*"In rigorous AI research, one must establish an authoritative, deterministic baseline before evaluating probabilistic large language models.  
Condition E—our deterministic concept evidence and rubric-aware prototype—is our authoritative active baseline. Conditions A (Zero-shot LLM), B (Few-shot Rubric), C (Vector-RAG), D (GraphRAG), and F (Multimodal Ensemble) are documented as planned research conditions for Phase 4. We chose not to present uncalibrated zero-shot LLM numbers during PP1 to avoid presenting volatile, hallucination-prone results."*

---

### Q7: "How does Component 3 communicate with Component 1? Show me the integration."
**Model Answer:**  
*"Component 3 communicates with Component 1 via an asynchronous, idempotent event bridge implemented in `backend/src/integration/c3-c1/index.js` using the MongoDB collection `learning_events`.  
1. When C3 grades an answer, it emits an event with `lifecycle_stage: 'provisional'`. In Component 1 (`c1/services/eventService.js:71`), C1 explicitly filters out provisional events so unverified AI marks do not alter student cognitive states.  
2. When the lecturer approves or overrides the mark and finalizes the batch, C3 updates the exact same record in-place to `lifecycle_stage: 'finalized'`. C1 then ingests the final mark, updates topic mastery, and recalculates student risk."*

---

### Q8: "How does your system handle multiple-choice questions compared to subjective answers?"
**Model Answer:**  
*"We enforce a strict separation of concerns:  
- Objective MCQs have exact mathematical ground truths. We implemented MCQ evaluation natively in Node.js via `mcqMarkingService.js` (< 1 ms execution, zero NLP overhead, 100% deterministic accuracy).  
- Subjective natural language answers are dispatched to our Python FastAPI service on port 8003, which executes our F1–F4 NLP evaluation pipeline.  
Both engines return structurally identical response contracts, allowing the frontend review modal and C1 event bridge to handle them polymorphically."*

---

### Q9: "What happens if a lecturer changes an AI mark? How do you prevent abuse?"
**Model Answer:**  
*"We implement strict human-in-the-loop governance:  
1. The original AI proposed mark is permanently preserved in the database field `automated_mark`.  
2. The adjusted score is stored in `final_mark`.  
3. In `c3Controller.js:reviewSubmission`, the system strictly mandates a non-empty `override_reason` string. If a lecturer attempts to change a mark without an explanation, the request is rejected with HTTP 400 Bad Request.  
4. The reviewer's user ID and timestamp are permanently recorded in the audit trail."*

---

### Q10: "What happens if a lecturer clicks 'Mark Batch' twice or re-runs a batch after a network interruption?"
**Model Answer:**  
*"Our marking pipeline is strictly idempotent:  
In `backend/src/modules/c3/services/submissionService.js:79-95`, the database query searches for an existing submission matching the compound key `{ student_id, batch_id }`. If found, it updates the existing record in-place using MongoDB `$set` rather than appending duplicate rows. This guarantees that batch retries never duplicate submissions, distort cohort statistics, or emit duplicate C1 events."*

---

### Q11: "How does your system handle invalid inputs like empty text or duplicate students?"
**Model Answer:**  
*"We implement a defensive 4-step batch workflow:  
In Step 3 (Preview & Validation), `batchMarkingService.js:validateBatchAnswers` pre-scans all rows before grading. It detects duplicate student IDs within the cohort and flags empty or whitespace-only answers. These rows are presented to the lecturer as validation warnings and excluded from AI grading, preventing runtime crashes."*

---

### Q12: "You show Neo4j and a Curriculum Knowledge Graph (CCKG) in your architecture. Is that running?"
**Model Answer:**  
*"In our high-level architectural blueprint, CCKG is envisioned as the shared curriculum graph connecting all four components, and Docker Compose provisions a Neo4j container.  
However, for this Project Performance 1 (PP1) milestone, CCKG remains classified as **Proposed Architecture**. No Cypher schemas or backend drivers have been implemented yet, and team ownership is currently unassigned. For Component 3, we implemented visual concept hierarchies natively using SVG Directed Acyclic Graphs (DAGs). Condition D, which integrates Neo4j GraphRAG, will be developed in Phase 4 once the shared CCKG is implemented by the team."*

---

### Q13: "Is your Component 3 AI model trainable? What parameters are being optimized?"
**Model Answer:**  
*"For the active PP1 prototype (Condition E), our engine utilizes deterministic NLP algorithms—tokenization, stopword normalization, regex token concept discovery, and discrete rubric scoring levels—which do not have backpropagation-trained weights.  
We do not describe our deterministic rubric evaluator as a trained neural network. In our post-PP1 Phase 4 roadmap, trainable dense vector embeddings (Condition C) and fine-tuned LLM evaluators (Condition B) will introduce trainable parameters evaluated against our held-out 150-answer test split."*

---

### Q14: "What software engineering best practices and design patterns did you follow?"
**Model Answer:**  
*"Our codebase follows SOLID principles and clean architecture:  
1. **Single Responsibility (SRP):** Controller handles HTTP routing; services handle business logic; Python handles NLP; MongoDB handles persistence.  
2. **Interface Segregation (ISP):** C1 integration bridge consumes only focused learner signals, not raw NLP token vectors.  
3. **Dependency Inversion (DIP):** Database access is abstracted via `getDb()` accessor functions, enabling hermetic mocking in our 41 backend tests.  
4. **Comprehensive QA:** 140 automated tests pass with 100% green status, and our Vite frontend builds with 0 errors across 112 modules."*

---

### Q15: "What is the commercialization and scalability potential of Component 3?"
**Model Answer:**  
*"Component 3 has strong commercial viability in the global EdTech assessment market:  
1. **Ultra-Low Compute Cost:** Because our Condition E prototype runs on standard CPUs in 0.34 ms without expensive cloud GPU instances, operating costs are negligible compared to commercial LLM wrappers ($0.00 vs $0.05 per answer).  
2. **Data Privacy First:** University exams can be marked on-premise without transmitting confidential student data to third-party US cloud providers.  
3. **LMS Compatibility:** The modular REST architecture is ready for packaging into a standard LTI (Learning Tools Interoperability) plugin for Canvas and Moodle."*
