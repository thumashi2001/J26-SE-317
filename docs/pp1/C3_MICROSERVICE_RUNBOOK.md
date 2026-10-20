# AdaptiveLearnSE Component 3 — Microservice Runbook & Operations Guide
**Project ID:** J26-SE-317 | **Academic Module:** IT4010 Research Project  
**Component:** Component 3 (C3) — AI-Powered Automated Marking & Answer Analysis System  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Runbook Version:** 2.0.0 | **Audit Date:** 2026-10-20

---

## 1. System Requirements & Architecture Overview

AdaptiveLearnSE Component 3 operates as a coordinated multi-service system:
- **Service 1: Python FastAPI AI Service** (Listening on `http://127.0.0.1:8003`)
- **Service 2: Node.js Express Backend** (Listening on `http://localhost:3000`)
- **Service 3: React Vite Frontend** (Listening on `http://localhost:5173`)
- **Database: MongoDB Atlas Database** (Configured via `MONGO_URI`)
- **Knowledge Graph: Shared CCKG Ontology** (Neo4j on port 7687, or automatic in-memory fallback)

---

## 2. Step-by-Step Service Startup Guide

### Step 1: Start the Python FastAPI AI Service (Port 8003)
Open a terminal in the project root:
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3
& "..\..\..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload
```
**Verification:**
Open `http://127.0.0.1:8003/health` in your browser. Expected response:
```json
{
  "service": "component-3-ai-service",
  "status": "running",
  "version": "0.1.0"
}
```

---

### Step 2: Start the Node.js Express Backend (Port 3000)
Open a second terminal:
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\backend
npm run dev
```
**Verification:**
Open `http://localhost:3000/health` in your browser. Expected response:
```json
{
  "status": "ok",
  "service": "backend"
}
```

---

### Step 3: Start the React Frontend Application (Port 5173)
Open a third terminal:
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\frontend
npm run dev
```
**Verification:**
Navigate to `http://localhost:5173/` in your browser. The AdaptiveLearnSE login portal will load.

---

## 3. Demonstration & Role Authentication Accounts

The local development database includes pre-seeded demonstration accounts:

| User Role | Username / ID | Password | Landing Route | Intended Demonstration Feature |
| :--- | :--- | :--- | :--- | :--- |
| **Student** | `IT10000001` | `password123` | `/c3` | Typed answer submission, MCQ, rubric marks, concept pills, SVG mind map. |
| **Lecturer** | `SLIITLEC101` | `password123` | `/lecturer/c3` | Submissions review queue, mark override with academic reason, finalization. |
| **Admin** | `admin1` | `password123` | `/admin` | Cross-system administration and approval management. |

*To re-seed test accounts at any time, run: `node backend/seed_users.js`.*

---

## 4. Test Execution & Quality Assurance Runbook

### 1. Execute Python AI Service Unit & Integration Tests (119 Tests)
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3
& "..\..\..\.venv\Scripts\python.exe" -m pytest tests -v
```
*Expected: 119 passed, 0 failed in ~2.0s.*

### 2. Execute Express Backend & Live Microservice Tests (47 Tests)
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\backend
npm test
```
*Expected: 47 passed (41 unit + 6 live microservice boundary tests), 0 failed in ~1.0s.*

### 3. Execute Frontend Production Build
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\frontend
npm run build
```
*Expected: 112 modules transformed, 0 errors in ~5.5s.*

### 4. Re-Execute Research Benchmark Experiment Suite (Suites 1–7)
```powershell
cd c:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE
& ".venv\Scripts\python.exe" ai-services/c3/experiments/run_all_experiments.py
```
*Expected: Executes Condition E, Condition F v2.0, 6-Case Diagnostics, Exp 1, Exp 2, Exp 3, Exp 4, Exp 5 in ~1.1s.*

---

## 5. Troubleshooting & Operational Recovery

### Issue A: "C3 AI service unreachable at http://127.0.0.1:8003" (HTTP 502)
- **Cause:** The Python FastAPI microservice is not running, or is listening on an unexpected port.
- **Remedy:** Ensure the FastAPI service is started in terminal 1. Check `netstat -ano | findstr 8003`. Confirm `C3_AI_URL=http://127.0.0.1:8003` in `backend/.env`.

### Issue B: "C3 AI service request timed out after 15000ms" (HTTP 504)
- **Cause:** Large neural model or local LLM inference took longer than the default 15-second timeout.
- **Remedy:** Increase `C3_AI_TIMEOUT_MS=30000` in `backend/.env` if running local inference via Ollama.

### Issue C: Neo4j Connection Refused / Bolt Offline
- **Cause:** Neo4j desktop or Docker container is not active on port 7687.
- **Remedy:** Component 3 includes an automatic in-memory curriculum ontology fallback (`NEO4J_ENABLED=false`). The service transparently uses the verified in-memory graph DAG with zero downtime.

### Issue D: Port Collisions (Port 3000, 8003, or 5173 occupied)
- **Remedy:** Terminate orphaned processes using PowerShell:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8003).OwningProcess | Stop-Process -Force
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process -Force
```
