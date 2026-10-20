# AdaptiveLearnSE Component 3 — Live Demonstration Contingency & Recovery Plan

**Document Version:** 2.0.0 (PP1 Disaster Recovery & High-Availability Plan)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Objective:** Guaranteed zero-downtime demonstration regardless of network or hardware faults.  

---

## 1. Quick-Action Disaster Recovery Runbook

| Failure Symptom | Immediate Diagnostic Step | Rapid Recovery Command (30-Second Fix) | Backup Fallback if Fix Fails |
| :--- | :--- | :--- | :--- |
| **`502 Bad Gateway` on Marking Request** | Python FastAPI process died or was not started on port 8003. | Open Terminal 1 and run:<br>`cd ai-services/c3`<br>`.\.venv_c3\Scripts\python.exe -m uvicorn app.main:app --port 8003` | Open `ss/05_batch_marking_results.png` to demonstrate live results while service boots. |
| **`MongoServerSelectionError` / DB Timeout** | University Wi-Fi dropped or current IP is not whitelisted in Atlas. | 1. Enable Mobile 4G/5G Hotspot.<br>2. Reconnect laptop Wi-Fi to hotspot.<br>3. Whitelist IP in Atlas dashboard. | Switch to seeded local test mock server (`node src/modules/c3/tests/c3.test.js`). |
| **`EADDRINUSE` (Port 3000, 5173, or 8003 Conflict)** | Background process already running on target port. | Run in PowerShell:<br>`Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -ErrorAction SilentlyContinue \| Stop-Process -Force` | Change port in `.env` (e.g. `PORT=3001`). |
| **`403 Forbidden` on Batch Setup Page** | Logged in with student account instead of lecturer. | Click Logout. Log in with:<br>Username: `SLIITLEC101`<br>Password: `password123` | N/A (Standard RBAC behavior). |
| **Complete Browser / Machine Freeze** | Out of memory or hardware hang. | Hard reboot machine. Restart the 3 terminal commands from `DEMO_RUNBOOK.md`. | Deploy pre-recorded 2-minute backup video (`ss/videos/c3_pp1_two_minute_demo.mp4`) and static evidence HTML (`frontend/public/evidence_evaluation_results.html`). |

---

## 2. Tiered Demonstration Continuity Architecture

```
[Tier 1: Full Multi-Tier Live Demo] ◄── PRIMARY MODE
  ├── React Vite Frontend (:5173)
  ├── Express Backend Gateway (:3000)
  ├── Python FastAPI NLP Engine (:8003)
  └── MongoDB Atlas Cloud Database
           │
           ▼ (If Network or Cloud DB Fails)
[Tier 2: Offline Mock Demonstrator] ◄── FAIL-SAFE MODE 1
  ├── Automated Test Runner (`npm test` in backend)
  ├── Pytest Suite (`python -m pytest tests/` in ai-services/c3)
  └── 140 Passing Tests with In-Process Mock AI Server
           │
           ▼ (If Local Node / Python Fails)
[Tier 3: Visual & Video Evidence Fallback] ◄── FAIL-SAFE MODE 2
  ├── Authoritative 12 High-Res Screenshots in `ss/`
  ├── Standalone Offline Results Dashboard (`evidence_evaluation_results.html`)
  └── 2-Minute Full Workflow Video Backup (`ss/videos/c3_pp1_two_minute_demo.mp4`)
```

---

## 3. Pre-Flight Diagnostic Script for Viva Day

Execute this quick 3-line diagnostic check in PowerShell 10 minutes before entering the viva room:

```powershell
# 1. Check all required ports are active
Get-NetTCPConnection -LocalPort 3000, 5173, 8003 -ErrorAction SilentlyContinue | Select-Object LocalPort, State

# 2. Check Python FastAPI health endpoint
Invoke-RestMethod -Uri "http://localhost:8003/health"

# 3. Check Express Backend health endpoint
Invoke-RestMethod -Uri "http://localhost:3000/api/v1/auth/health" -ErrorAction SilentlyContinue
```
- If all three return healthy HTTP 200, proceed with Tier 1 live demo with 100% confidence.
