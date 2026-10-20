# AdaptiveLearnSE Component 3 — Live Demonstration Runbook (PP1 Viva)

**Document Version:** 1.0.0  
**Target Date:** 22 October 2026 (Viva Evaluation)  
**Demonstration Scope:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)

---

## 1. Prerequisites & Environment Setup

Ensure the following runtimes and services are accessible:
- **Node.js:** v20.x or higher
- **Python:** 3.13 / 3.14 with virtual environment initialized at `ai-services/c3/.venv_c3`
- **MongoDB Atlas:** Connection string configured in `backend/.env`
- **Modern Web Browser:** Google Chrome, Microsoft Edge, or Firefox

### Service Startup Procedure (Execute in 3 Terminal Windows):

#### Terminal 1 — Python AI Service (Port 8003)
```powershell
cd ai-services/c3
.\.venv_c3\Scripts\python.exe -m uvicorn app.main:app --port 8003
# Expected output: Uvicorn running on http://127.0.0.1:8003
```

#### Terminal 2 — Node.js Express Backend (Port 3000)
```powershell
cd backend
npm start
# Expected output: MongoDB connected: adaptivelearnse_dev | Backend listening on http://localhost:3000
```

#### Terminal 3 — React Vite Frontend (Port 5173)
```powershell
cd frontend
npm run dev
# Expected output: Local: http://localhost:5173/
```

---

## 2. End-to-End Live Demonstration Workflow

### Step 1: Lecturer Login & Navigation
1. Open `http://localhost:5173/login` in the browser.
2. Sign in with the authorized lecturer account (`SLIITLEC101` / `password123`).
3. Click **Login**. The browser redirects to `/lecturer`.
4. In the left navigation menu, click **Batch Marking** (or navigate to `http://localhost:5173/lecturer/c3/batch`).

### Step 2: Assessment Setup (Step 1 of Wizard)
1. Point out the Assessment Setup form:
   - Module: `SE3010` (Software Architecture)
   - Question ID: `SE3010-Q01`
   - Assessment Title: `Software Architecture Principles — Modular Abstraction`
   - Answer Type: `Short Answer`
   - Max Marks: `4`
2. Show the multi-criterion rubric:
   - **Criterion 1 (C1):** `Understanding of High Cohesion and Single Responsibility` (Max Marks: 2, Levels: None [0], Basic [1], Proficient [2])
   - **Criterion 2 (C2):** `Understanding of Loose Coupling & Architecture Patterns` (Max Marks: 2, Levels: None [0], Basic [1], Proficient [2])
3. Click **"Save & Continue to Answers ->"**. The setup document is locked in MongoDB (`c3_batch_setups`).

### Step 3: Enter Student Cohort Answers (Step 2 of Wizard)
1. In Step 2, click the **"⚡ Fill Sample Cohort"** button to populate student responses:
   - `IT21001001`: Strong response (high cohesion, single responsibility, loose coupling, microservices).
   - `IT21001002`: Partial response (mentions modules do one thing; loose coupling prevents breaking).
   - `IT21001003`: Borderline response (mentions microservices and message queues).
   - `IT21001004`: Weak response (only general definition).
   - `IT21001005`: Empty response (testing edge cases).
   - `IT21001006`: Irrelevant response (discusses relational database normalization).
   - `IT21001001`: Duplicate submission row (testing duplicate detection).
2. Click **"Validate Answers ->"**.

### Step 4: Inspect Pre-Marking Validation (Step 3 of Wizard)
1. Observe the pre-validation summary cards:
   - Total Rows: `7`
   - Valid Rows: `5`
   - Validation Issues: `2`
2. Point out the detected validation warnings:
   - Duplicate student identifier `IT21001001` flagged and blocked from duplicate grading.
   - Empty answer row for `IT21001005` flagged with row reference.
3. Click **"Mark Valid Cohort (AI) ->"** to execute automated grading.

### Step 5: Review Batch Results Table (Step 4 of Wizard)
1. Observe the cohort marks table populated in real time:
   - `IT21001001`: `4 / 4` (100.0%) — `AI Proposed`
   - `IT21001002`: `2 / 4` (50.0%) — `AI Proposed`
   - `IT21001003`: `2 / 4` (50.0%) — `AI Proposed`
   - `IT21001004`: `0 / 4` (0.0%) — `AI Proposed`
   - `IT21001006`: `0 / 4` (0.0%) — `AI Proposed`
2. Show that irrelevant answer `IT21001006` received 0 marks without hallucinated credit.

### Step 6: Detailed Evidence & Mind Map Inspection
1. Click **"Inspect Evidence & Mind Map"** on student `IT21001001`.
2. In the inspector modal, highlight:
   - **Criterion Breakdown Cards:** Exact scoring levels selected and sentence-level evidence references.
   - **Explainable Feedback:** Automated summary, demonstrated strengths, and actionable suggestions.
   - **Interactive Mind Map Graph:** Directed acyclic graph (DAG) visualizing demonstrated concepts (green) and relationships linked to the root question.

### Step 7: Demonstrate Lecturer Override with Mandatory Justification
1. In the modal, scroll down to the **"Lecturer Review & Score Override"** section.
2. Demonstrate accountability enforcement:
   - Attempt to submit an override without entering a reason -> system rejects the action.
3. Enter new score `3.5` and enter reason: `"Awarded 3.5 marks. Strong microservices justification with minor terminology gap."`
4. Click **"Apply Lecturer Override"**.
5. Observe the status change to **`Reviewed`**. Show that `automated_mark` (4.0) remains preserved while `final_mark` (3.5) is recorded.

### Step 8: Finalize Cohort & Verify C1 Digital Twin Integration
1. Close the modal and click **"⚡ Finalize All Submissions"**.
2. Confirm the action. All cohort statuses transition to **`Finalized`**.
3. Explain that C3 has emitted idempotent learning events to Component 1 (`learning_events` collection in MongoDB).
4. Reload the page to prove data persistence across sessions.

---

## 3. Troubleshooting & Recovery Precautions

| Symptom | Cause | Rapid Resolution |
| :--- | :--- | :--- |
| `502 Bad Gateway: C3 AI service unreachable` | FastAPI is not running on port 8003 | Check Terminal 1 and restart `uvicorn app.main:app --port 8003`. |
| `MongoDB connection error` | IP whitelist or network disconnect | Ensure IP address is whitelisted in MongoDB Atlas dashboard. |
| `403 Forbidden on Batch Setup` | Logged in as student instead of lecturer | Sign out and sign in with lecturer account `SLIITLEC101`. |
| Duplicate rows in database | Rerunning marking | No action needed. System updates existing records in-place. |
