# AdaptiveLearnSE Component 3 — 10-Minute Live Demo Script

**Event:** Project Performance 1 (PP1) Live Demonstration  
**Allocated Demonstration Time:** 10 Minutes (Strictly Enforced)  
**Presenter:** Component 3 Engineer  
**Live Portals:** Frontend: `http://localhost:5173` | Backend: `http://localhost:3000` | AI Service: `http://localhost:8003`  

---

## Chronological Cue-by-Cue Demonstration Script

### Minute 0:00 – 1:00 | System Entry & Role-Based Navigation
- **UI Action:** Open browser at `http://localhost:5173/login`. Enter `SLIITLEC101` / `password123`. Click **Login**.
- **Spoken Words:**  
  *"Good morning respected examiners. I will now demonstrate Component 3: The AI-Powered Automated Marking & Answer Analysis System.  
  I am logging in using the authorized lecturer account SLIITLEC101. Notice the role-based navigation sidebar. Under the components heading, Component 3 exposes the Batch Marking Studio and the Marking Review Queue. I will click on 'Batch marking' to initiate a cohort assessment."*
- **Visual Displayed:** Redirection to `/lecturer/c3/batch`.

---

### Minute 1:00 – 2:30 | Step 1: Assessment Setup & Rubric Configuration
- **UI Action:** Review the pre-populated assessment form. Point to Module `SE3010`, Question `SE3010-Q01`, Max Marks `4`. Expand the rubric criteria cards. Click **"Save & Continue to Answers ->"**.
- **Spoken Words:**  
  *"In university assessment, a major bottleneck is having to re-enter rubric rules repeatedly. Component 3 solves this by allowing the lecturer to define the question metadata, expected concepts, and multi-criterion rubric once.  
  Here we have Question SE3010-Q01 on Modular Abstraction worth 4 marks, divided into two criteria: High Cohesion worth 2 marks, and Loose Coupling worth 2 marks, each with Full, Partial, and None scoring levels.  
  When I click 'Save & Continue', the system locks and persists this setup into MongoDB collection c3_batch_setups."*
- **Visual Displayed:** Step 2 wizard unlocks with animation.

---

### Minute 2:30 – 4:00 | Step 2 & 3: Cohort Ingestion & Pre-Marking Validation
- **UI Action:** Click **"⚡ Fill Sample Cohort"**. Point to the 7 rows. Click **"Validate Answers ->"**.
- **Spoken Words:**  
  *"Now we import the student answers. In production, a lecturer can paste a CSV or enter answers dynamically. For this demonstration, I click 'Fill Sample Cohort', which loads 7 diverse student submissions representing varied academic qualities.  
  Before executing AI evaluation, our system runs a defensive pre-validation pass. I click 'Validate Answers'.  
  Notice Step 3: Out of 7 rows, 5 are flagged as valid and 2 have validation warnings. Specifically, student IT21001001 was entered twice, and the system flagged the duplicate to prevent double grading. Furthermore, row IT21001005 was completely empty, and the system flagged it to prevent runtime crashes. This ensures that only clean, valid submissions proceed to grading."*
- **Visual Displayed:** Step 3 validation summary cards and warning banners.

---

### Minute 4:00 – 5:30 | Step 4: Automated Batch Marking Execution
- **UI Action:** Click **"Mark Valid Cohort (AI) ->"**. Observe results table populate.
- **Spoken Words:**  
  *"I will now execute automated grading by clicking 'Mark Valid Cohort'.  
  In less than one second, all 5 valid student answers were evaluated by our Python NLP engine against the shared rubric.  
  Looking at the results: Student IT21001001 received 4 out of 4 (100%) as an AI Proposed mark. Students IT21001002 and IT21001003 received partial marks of 2 out of 4 (50%).  
  Crucially, look at student IT21001006. This student submitted a grammatically coherent, verbose paragraph discussing relational database normalization—completely irrelevant to software architecture. A pure token-overlap or bag-of-words model awards marks for vocabulary; our rubric engine awarded exactly 0.0 marks with zero hallucinations."*
- **Visual Displayed:** Cohort results table with marks, percentages, and `AI Proposed` badges.

---

### Minute 5:30 – 7:00 | Step 5: Explainable Criterion Evidence & SVG Mind Map
- **UI Action:** Click **"Inspect Evidence & Mind Map"** on student `IT21001001`. Scroll through modal.
- **Spoken Words:**  
  *"Let us inspect the evidence for student IT21001001. Rather than presenting a black-box scalar score, Component 3 provides complete explainability.  
  Under Criterion Breakdown, the system displays the exact sentence where the student demonstrated high cohesion and loose coupling.  
  Under Formative Feedback, the system provides automated feedback summarizing demonstrated strengths and actionable improvement suggestions.  
  Below, observe our interactive Concept Mind Map. This is a Directed Acyclic Graph rendered dynamically in pure SVG. The root question connects to concept nodes color-coded by mastery: green indicates verified concepts, orange indicates partial demonstrations, and gray indicates missing concepts. A student or lecturer can diagnose conceptual understanding in under three seconds."*
- **Visual Displayed:** Review modal showing evidence spans and interactive concept DAG graph.

---

### Minute 7:00 – 8:30 | Step 6: Lecturer Review & Override with Mandatory Justification
- **UI Action:** In modal, enter score `3.5`. Leave reason blank. Click **"Apply Lecturer Override"** (show rejection). Enter reason: `"Awarded 3.5 marks. Strong microservices justification with minor terminology gap."` Click **"Apply Lecturer Override"**.
- **Spoken Words:**  
  *"In university assessment, final marks must be awarded under certified lecturer authority. To prevent arbitrary grade adjustments, Component 3 enforces strict governance.  
  If I attempt to change the mark to 3.5 without providing an explanation, the system blocks the action with a validation warning.  
  Now I provide a professional justification: 'Awarded 3.5 marks. Strong microservices justification with minor terminology gap'. When I apply the override, the status transitions to 'Reviewed'. The original AI mark of 4.0 is preserved in the database audit trail alongside my authoritative final mark of 3.5, my lecturer ID, and the timestamp."*
- **Visual Displayed:** Status updates to `Reviewed`; badge changes color.

---

### Minute 8:30 – 9:30 | Step 7: Batch Finalization & Component 1 Live Event Sync
- **UI Action:** Close modal. Click **"⚡ Finalize All Submissions"**. Confirm dialogue.
- **Spoken Words:**  
  *"Now that the cohort has been audited, the lecturer finalizes the batch. I click 'Finalize All Submissions'.  
  In one atomic operation, all submissions transition to 'Finalized'.  
  Simultaneously, Component 3 emits structured learning events to MongoDB's learning_events collection. This directly integrates with Component 1—the Cognitive Digital Twin. The digital twin consumes these finalized marks to update student topic mastery, apply Ebbinghaus forgetting curves, and recalculate academic risk."*
- **Visual Displayed:** Cohort table reaches 100% Finalized audit state.

---

### Minute 9:30 – 10:00 | Step 8: Persistence Proof & Conclusion
- **UI Action:** Press `F5` to refresh the browser page. Show all data reloads intact.
- **Spoken Words:**  
  *"To prove full data persistence across sessions, I refresh the browser. Notice that all batch configurations, student submissions, overrides, and audit trails reload seamlessly from MongoDB Atlas.  
  This completes the live demonstration of Component 3. We have verified assessment setup, cohort pre-validation, automated grading, explainable evidence tracing, concept mind-map visual synthesis, lecturer override governance, and cross-component digital twin integration. Thank you, and I look forward to your questions."*
