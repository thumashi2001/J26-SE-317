# AdaptiveLearnSE Component 3 — Live Demonstration Runbook (PP1 Viva)

**Document Version:** 2.0.0 (Authoritative Live Demonstration Runbook)  
**Target Milestone:** Project Performance 1 (PP1) Viva (22, 23, and 26 October 2026)  
**Allocated Demonstration Time:** Exactly 10 Minutes  
**Demonstrator:** Component 3 Engineer  
**Live Ports:** Frontend: `http://localhost:5173` | Backend: `http://localhost:3000` | Python AI: `http://localhost:8003`  

---

## 1. Pre-Demonstration Checklist (Complete 15 Minutes Before Session)

1. **Terminal 1 — Python AI Service (Port 8003):**
   ```powershell
   cd ai-services/c3
   .\.venv_c3\Scripts\python.exe -m uvicorn app.main:app --port 8003
   # Output: Uvicorn running on http://127.0.0.1:8003
   ```
2. **Terminal 2 — Node.js Express Backend (Port 3000):**
   ```powershell
   cd backend
   npm start
   # Output: MongoDB connected: adaptivelearnse_dev | Backend listening on http://localhost:3000
   ```
3. **Terminal 3 — React Vite Frontend (Port 5173):**
   ```powershell
   cd frontend
   npm run dev
   # Output: Local: http://localhost:5173/
   ```
4. **Browser Setup:** Open Chrome/Edge in incognito mode at `http://localhost:5173/login`.
5. **Credentials Ready:** Lecturer account `SLIITLEC101` / `password123`.

---

## 2. Minute-by-Minute 10-Minute Live Demo Script

```
[00:00 - 01:00] Step 1: Lecturer Login & Navigation
[01:00 - 02:30] Step 2: Assessment Setup (Question & Multi-Criterion Rubric)
[02:30 - 04:00] Step 3: Cohort Ingestion & Pre-Marking Validation (Duplicate Detection)
[04:00 - 05:30] Step 4: Automated Batch Marking Execution (AI Proposed Marks)
[05:30 - 07:00] Step 5: Deep Inspection — Sentence Evidence & Interactive Mind Map DAG
[07:00 - 08:30] Step 6: Lecturer Review & Override with Mandatory Justification
[08:30 - 09:30] Step 7: Batch Finalization & C1 Digital Twin Event Emission
[09:30 - 10:00] Step 8: Persistence Proof & Q&A Transition
```

---

## 3. Step-by-Step Live Execution Instructions

### Step 1: Lecturer Login & Role Authorization (0:00 – 1:00)
1. In the browser, navigate to `http://localhost:5173/login`.
2. Enter username `SLIITLEC101` and password `password123`. Click **Login**.
3. **Spoken Cue:** *"I am logging in with the authorized lecturer account SLIITLEC101. Notice the role-based navigation bar where Component 3 provides the Batch Marking Studio."*
4. In the sidebar menu, click **Batch marking** (navigating to `/lecturer/c3/batch`).

### Step 2: Configure Question & Rubric Setup (1:00 – 2:30)
1. Point to **Step 1: Assessment Setup** on the wizard:
   - Module: `SE3010` (Software Architecture)
   - Question ID: `SE3010-Q01`
   - Title: `Software Architecture Principles — Modular Abstraction`
   - Max Marks: `4`
2. Show the multi-criterion rubric:
   - **Criterion 1 (C1):** `Understanding of High Cohesion and Single Responsibility` (Max Marks: 2; Levels: Full [2.0], Partial [1.0], None [0.0]).
   - **Criterion 2 (C2):** `Understanding of Loose Coupling & Architecture Patterns` (Max Marks: 2; Levels: Full [2.0], Partial [1.0], None [0.0]).
3. Click **"Save & Continue to Answers ->"**.
4. **Spoken Cue:** *"The lecturer defines the question and rubric criteria once. It is immediately locked and persisted into MongoDB collection c3_batch_setups."*

### Step 3: Cohort Ingestion & Pre-Marking Validation (2:30 – 4:00)
1. Point to **Step 2: Enter Student Answers**.
2. Click the button **"⚡ Fill Sample Cohort"**.
3. Point out the loaded synthetic cohort of 7 answers:
   - `IT21001001`: Strong answer (cohesion, single responsibility, loose coupling).
   - `IT21001002`: Partial answer (explains cohesion, omits coupling details).
   - `IT21001003`: Partial answer (mentions microservices and message queues).
   - `IT21001004`: Weak answer (general definition only).
   - `IT21001005`: Empty response row (testing edge cases).
   - `IT21001006`: Irrelevant answer (discusses database normalization).
   - `IT21001001`: Duplicate submission row (testing duplicate detection).
4. Click **"Validate Answers ->"**.
5. Observe **Step 3: Preview & Validation**:
   - Total Rows: `7` | Valid Rows: `5` | Validation Issues: `2`.
   - Highlight the warning cards: Duplicate student ID `IT21001001` flagged; empty row `IT21001005` flagged.
6. **Spoken Cue:** *"Our pre-validation engine safeguards the marking pipeline by blocking corrupted rows and duplicate student submissions before executing AI evaluation."*

### Step 4: Automated Batch Marking Execution (4:00 – 5:30)
1. Click **"Mark Valid Cohort (AI) ->"**.
2. Watch the cohort marks table populate in real time (within 1 second):
   - `IT21001001`: `4.0 / 4.0` (100.0%) — `AI Proposed`
   - `IT21001002`: `2.0 / 4.0` (50.0%) — `AI Proposed`
   - `IT21001003`: `2.0 / 4.0` (50.0%) — `AI Proposed`
   - `IT21001004`: `0.0 / 4.0` (0.0%) — `AI Proposed`
   - `IT21001006`: `0.0 / 4.0` (0.0%) — `AI Proposed`
3. **Spoken Cue:** *"Notice that student IT21001006, who submitted a verbose but completely irrelevant database response, was awarded 0.0 marks. Pure token-overlap models hallucinate marks on common keywords; our rubric evaluator strictly bounds marks by verified evidence."*

### Step 5: Deep Inspection — Evidence & Interactive Mind Map DAG (5:30 – 7:00)
1. Click **"Inspect Evidence & Mind Map"** on student `IT21001001`.
2. In the inspector modal, highlight:
   - **Criterion Breakdown:** Sentence numbers linked to criteria (e.g. Sentence 1 supports Criterion 1).
   - **Formative Feedback:** Strengths, missing concepts, and actionable advice.
   - **Interactive SVG Mind Map:** Directed Acyclic Graph (DAG) visualizing demonstrated concepts (green nodes) connected to the root question.
3. **Spoken Cue:** *"Instead of a black-box grade, Component 3 provides transparent evidence tracing and a concept mind map showing the student's conceptual structure at a glance."*

### Step 6: Lecturer Review & Override with Mandatory Justification (7:00 – 8:30)
1. In the modal, scroll to **Lecturer Review & Score Override**.
2. Enter score `3.5`. Leave the justification reason field blank. Click **"Apply Lecturer Override"**.
3. Observe the validation warning: System rejects the adjustment because a justification is mandatory.
4. Now enter justification: `"Awarded 3.5 marks. Strong microservices justification with minor terminology gap."` Click **"Apply Lecturer Override"**.
5. Observe the status transition to **`Reviewed`**. Show that `automated_mark` (4.0) is preserved while `final_mark` (3.5) is recorded.
6. **Spoken Cue:** *"To satisfy university governance, final marks require lecturer authority. The system enforces an audit trail by requiring a written reason for every score override."*

### Step 7: Batch Finalization & C1 Digital Twin Event Emission (8:30 – 9:30)
1. Close the modal and click **"⚡ Finalize All Submissions"**.
2. Confirm the dialogue. All cohort statuses transition to **`Finalized`**.
3. **Spoken Cue:** *"Finalization transitions the entire batch to the finalized audit state and emits learning events into MongoDB's learning_events collection for Component 1's cognitive digital twin."*

### Step 8: Persistence Proof & Transition (9:30 – 10:00)
1. Refresh the browser page (`F5`).
2. Show that all finalized marks, overrides, and batch statistics reload from MongoDB Atlas.
3. Conclude: *"This concludes the live demonstration of Component 3. We have demonstrated assessment configuration, cohort ingestion, duplicate prevention, automated grading, explainable evidence, mind-map generation, lecturer override governance, and cross-component event emission."*
