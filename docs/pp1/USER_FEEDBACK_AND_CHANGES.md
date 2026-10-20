# AdaptiveLearnSE Component 3 — User Feedback Protocol & Iterative Improvement Log

**Document Version:** 2.0.0 (PP1 User Feedback & Usability Protocol)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Status:** **Formal Task-Based Protocol Prepared for Planned Lecturer Trials; Internal Usability Iterations Documented**  

---

## 1. Ethical Transparency Disclosure

In strict adherence to academic integrity guidelines:
- **No fabricated external user sessions, fictional lecturer quotes, or simulated Likert survey scores are presented in this report.**
- Conducting formal user studies with university lecturers and authentic student cohorts requires formal institutional ethics clearance and privacy compliance.
- For the PP1 evaluation, this document presents:
  1. A rigorous **Task-Based Usability Protocol** and observation instrument designed for authorized lecturer trials.
  2. The **Iterative Engineering Change Log** detailing real UI/UX refinements, input validation safeguards, and regression tests implemented in response to internal developer/examiner smoke testing.

---

## 2. Structured Task-Based Lecturer Usability Protocol

The protocol below is designed to observe lecturers performing authentic grading workflows, measuring objective task completion rates, execution times, error rates, and qualitative cognitive friction.

### Protocol Parameters:
- **Target Participants:** 3–5 University Lecturers / Teaching Assistants in Software Engineering.
- **Session Duration:** 30–35 minutes per participant.
- **Evaluation Method:** Concurrent Think-Aloud (CTA) observation combined with system telemetry.
- **Privacy Safeguard:** Synthetic, anonymized student answer sets (`IT21001001`–`IT21001007`) are used exclusively. No authentic student identities or marks are processed.

### The 7 Core Evaluation Tasks:

| Task ID | Task Description | User Goal | Success Criterion | Target Completion Time |
| :--- | :--- | :--- | :--- | :--- |
| **TASK-01** | **Configure Rubric Setup** | Configure a 2-criterion rubric for Question `SE3010-Q01` with scoring levels (Full, Partial, None) totaling 4 marks. | Setup saved and locked in `c3_batch_setups` without validation errors. | $\le 180$ seconds |
| **TASK-02** | **Import Cohort Answers** | Enter a cohort of 7 student answers via dynamic grid or CSV paste (including intentional duplicates and empty answers). | 7 answer rows populated in UI grid. | $\le 60$ seconds |
| **TASK-03** | **Pre-Marking Validation** | Run pre-marking validation and identify invalid or duplicate student rows. | Lecturer successfully identifies the duplicate ID and empty row without guidance. | $\le 45$ seconds |
| **TASK-04** | **Execute Automated Grading** | Trigger AI batch marking for the valid cohort. | Results table populates with marks, percentages, and AI Proposed status. | $\le 30$ seconds |
| **TASK-05** | **Inspect Criterion Evidence** | Open the inspector modal on student `IT21001001`; locate the sentence-level evidence supporting Criterion 1. | Lecturer quotes the specific answer sentence highlighted by the system. | $\le 60$ seconds |
| **TASK-06** | **Interpret Mind Map DAG** | Inspect the concept mind-map graph; identify which concept is marked as missing/not demonstrated. | Lecturer correctly identifies the unfulfilled concept node (gray). | $\le 45$ seconds |
| **TASK-07** | **Apply Override with Reason** | Attempt to lower mark from 4.0 to 3.5 without entering a reason (observe rejection); then enter a valid justification and submit. | Final mark updated to 3.5; original AI mark (4.0) preserved; status: `reviewed`. | $\le 90$ seconds |
| **TASK-08** | **Batch Finalization** | Finalize all cohort submissions in one confirmed action. | All items transition to `finalized`; C1 event emission verified. | $\le 30$ seconds |

---

## 3. Task Observation & Measurement Template

During live user observation sessions, the observer completes the following matrix:

```markdown
### Participant Observation Sheet
- **Participant Code:** LEC-P01
- **Role / Teaching Module:** Lecturer / SE3010 Software Architecture
- **Date & Location:** [Scheduled Post-PP1]

| Task ID | Completed? (Yes/No) | Attempts | Time Taken (sec) | Confusion / Friction Points Observed | Spoken Participant Comments |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TASK-01 | [ ] | [ ] | [ ] s | | |
| TASK-02 | [ ] | [ ] | [ ] s | | |
| TASK-03 | [ ] | [ ] | [ ] s | | |
| TASK-04 | [ ] | [ ] | [ ] s | | |
| TASK-05 | [ ] | [ ] | [ ] s | | |
| TASK-06 | [ ] | [ ] | [ ] s | | |
| TASK-07 | [ ] | [ ] | [ ] s | | |
| TASK-08 | [ ] | [ ] | [ ] s | | |
```

---

## 4. Iterative Engineering Change Log (Internal Testing ➔ Code Fixes)

During internal verification and test trials, specific usability and reliability flaws were identified and rectified through concrete code enhancements and regression tests:

| Observation / Usability Finding | Root Cause | Engineering Solution Implemented | Regression Test Added |
| :--- | :--- | :--- | :--- |
| **1. Accidental Unjustified Overrides:** During initial testing, lecturers could alter marks without explaining why, destroying academic auditability. | Score override endpoint did not enforce a minimum string length for justification. | Modified `c3Controller.js:reviewSubmission` to reject empty or whitespace `override_reason` with HTTP 400 Bad Request. | `c3.test.js:13` (`lecturer override without reason is rejected (400)`) |
| **2. Duplicate Submission Pollution:** Re-running batch marking for a cohort appended duplicate submission documents to MongoDB. | Insert operation lacked a unique composite index or upsert logic. | Added upsert logic in `submissionService.js` checking `{ student_id, batch_id }` and updating in-place. | `c3.test.js:38` (`retrying batch does not create duplicate submissions`) |
| **3. Empty Answer Crashes:** When a student submitted an empty or blank answer, the preprocessor threw a zero-length string exception. | Python tokenizer expected at least 1 valid lexical token. | Added empty-row guard in `validateBatchAnswers` and defensive fallback in `preprocessor.py` awarding 0.0 marks safely. | `c3.test.js:24` and `c3.test.js:36` |
| **4. Criteria Sum Mismatch:** Lecturers could configure a rubric where criterion max marks did not equal the assessment max marks (e.g., criteria sum 6 marks for a 4-mark question). | Lack of client/server validation on total marks consistency. | Implemented strict validation in `batchMarkingService.js:validateSetupData` returning HTTP 400 if criteria sum $\ne$ `max_marks`. | `c3.test.js:34` (`validate setup data rejects invalid max marks or criteria sum mismatch`) |
| **5. Cognitive Overload in Batch Entry:** Entering 7 student answers manually from scratch was tedious and error-prone during live demos. | No pre-configured sample datasets accessible directly in the UI. | Added a one-click `"⚡ Fill Sample Cohort"` button in `LecturerBatchMarkingPage.jsx` loading 7 diverse quality answers. | Verified in live demo runbook. |
| **6. Scanned Answer Confusion:** Users attempted to upload photo attachments or scanned handwriting PDFs to C3. | C3 was conceived as subjective natural language text, but users expected OCR. | Added explicit HTTP 400 rejection in `c3Controller.js:uploadScannedAnswer` with helpful message redirecting to typed answers. | `c3.test.js:16, 17` (`scanned image / OCR upload endpoint explicitly rejects with 400`) |
