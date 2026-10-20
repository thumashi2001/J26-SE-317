# AdaptiveLearnSE Component 3 — PP1 Demonstration Runbook & Viva Script
**Project:** AdaptiveLearnSE | **Project ID:** J26-SE-317  
**Component:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Document Version:** 2.0.0 (PP1 Final Verified)  
**Viva Dates:** 22, 23 & 26 October 2026

---

## 1. Pre-Demonstration Service Startup

Open three terminal windows to launch the full-stack system:

### Terminal 1: Python AI Microservice (Port 8003)
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3
& "..\..\..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```
*Health verification:* Open `http://localhost:8003/health` -> `{"status":"ok","component":"c3"}`.

### Terminal 2: Node.js Express Backend (Port 3000)
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\backend
npm start
```
*Health verification:* Open `http://localhost:3000/api/v1/c3/health` -> `{"status":"ok"}`.

### Terminal 3: React Frontend (Port 5173)
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\frontend
npm run dev
```
*Access interface:* Open `http://localhost:5173` in Google Chrome.

---

## 2. Demonstration Persona Credentials

| Persona | Role | Email | Password | Allowed Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Kasun Perera** | Student | `student@adaptivelearnse.lk` | `Student@123` | Submit subjective answers, take MCQs, view feedback & mind maps, view own submission history. |
| **Dr. Nimal Silva** | Lecturer | `lecturer@adaptivelearnse.lk` | `Lecturer@123` | View class submissions, override marks with mandatory reason, finalize grades, batch marking. |

---

## 3. Step-by-Step Viva Demonstration Script (10–12 Minutes)

### Step 1: Role Authentication & RBAC (1 min)
1. Navigate to `http://localhost:5173/login`.
2. Log in as **Kasun Perera** (`student@adaptivelearnse.lk`).
3. Explain to the panel: *"Component 3 enforces role-based access. Students have access only to their assigned assessments and personalized feedback."*

### Step 2: Subjective Assessment Submission (2 mins)
1. Navigate to **Assessment** -> Question `PP-SE3010-001` (*"Explain the difference between statement coverage and branch coverage in software testing"*).
2. Note the displayed rubric: 2 criteria, maximum 10 marks total.
3. Paste the controlled demonstration response:
   > *"Statement coverage measures the percentage of executable statements exercised by tests. Branch coverage measures whether every decision branch (true/false) has been evaluated. Statement coverage alone is insufficient because a single path can execute 100% of statements without testing edge branches."*
4. Click **Submit for Evaluation**.

### Step 3: Real-Time Automated Marking & Rubric Breakdown (2 mins)
1. Show the evaluation results screen:
   - **Total Awarded Mark:** `10.0 / 10.0 (100%)`
   - **Criterion Breakdown:**
     - `Criterion 1 (Statement Coverage)`: `5.0 / 5.0` (Proficient)
     - `Criterion 2 (Branch Coverage)`: `5.0 / 5.0` (Proficient)
2. Explain to the panel: *"Notice how our criterion evaluator ties marks directly to evidence quotes from the student's text, strictly bounding scores within rubric limits."*

### Step 4: Demonstrated Concepts & Mind Map DAG (2 mins)
1. Scroll down to the **Concept Analysis** card:
   - **Demonstrated Concepts:** `Statement Coverage`, `Branch Coverage`, `Decision Branch`.
   - **Missing Concepts:** `None`.
2. Inspect the **Concept Mind Map Visualizer**:
   - Show the interactive Directed Acyclic Graph (DAG).
   - Point out the green nodes representing verified concepts and directed edges illustrating the prerequisite relationship (`Statement Coverage` -> `Branch Coverage`).

### Step 5: Explainable Formative Feedback (1 min)
1. Highlight the **Formative Feedback** section.
2. Explain to the panel: *"Unlike black-box LLM scoring, our feedback explicitly cites the student's statements and explains why full marks were awarded, offering actionable pedagogical guidance."*

### Step 6: Deterministic MCQ Evaluation (1 min)
1. Navigate to **MCQ Assessment**.
2. Select question `MCQ-SE3040-001` (*"Which HTTP method is idempotent?"*).
3. Select `PUT` and submit.
4. Point out to the panel: *"MCQ marking is strictly deterministic, executing in under 2ms without LLM latency or non-deterministic variance."*

### Step 7: Lecturer Review, Mark Override & Finalization (2 mins)
1. Log out and log in as **Dr. Nimal Silva** (`lecturer@adaptivelearnse.lk`).
2. Navigate to **Lecturer Review Dashboard** (`http://localhost:5173/lecturer/submissions`).
3. Click on Kasun Perera's submission.
4. Demonstrate a mark adjustment: change mark to `9.5` and enter reason: *"Minor formatting improvement noted."*
5. Click **Save Override**.
6. Show the panel the **Audit Trail**:
   - `Original AI Mark: 10.0 / 10.0`
   - `Lecturer Final Mark: 9.5 / 10.0`
   - `Reason: Minor formatting improvement noted.`
   - `Lecturer ID: Dr. Nimal Silva`
7. Click **Finalize Assessment**. Explain that this transitions status to `FINALIZED` and dispatches the authoritative learning event to Component 1.

### Step 8: Shared CCKG Foundation & Research Experiment Evidence (2 mins)
1. Open the project repository and show `database/neo4j/`:
   - `database/neo4j/schema/01_cckg_constraints.cypher`
   - `database/neo4j/cypher/01_seed_curriculum_ontology.cypher`
2. Show the test execution evidence:
   - **119 Python unit & integration tests passing.**
   - **41 Node.js backend tests passing.**
   - **Frontend Vite build with 112 modules (0 errors).**
3. Open `docs/pp1/evidence/results/master_research_summary.json` and present the benchmark matrix comparing Token Baseline (5.609 MAE), Condition E (4.640 MAE), Condition F (Length-bias corrected), and Multi-LLM comparisons across 3 model classes.

---

## 4. Contingency & Fallback Protocol

If the university network or external services are restricted during the viva:
1. **Zero External Dependency:** The entire C3 system is configured with `C3_LLM_PROVIDER=mock` and internal CCKG ontology fallback, meaning 100% of the demonstration operates locally without internet access.
2. **Deterministic Responses:** The calibrated mock provider returns pre-calculated, verified scoring distributions matching the approved synthetic benchmark.
3. **Prepared Evidence Backup:** All test logs, prediction CSVs, and screenshots are pre-compiled in `ADAPTIVE_LEARN_SE/docs/pp1/evidence/`.
