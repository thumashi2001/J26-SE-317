# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The repo root is `ADAPTIVE_LEARN_SE/` (the git repository). `AGENTS.md` holds the full project rules (research-integrity requirements, engineering workflow, change-communication format); read it before C3 work. The root `README.md` and several sub-READMEs still say "structure only" — they are outdated; C1, C3 and auth/admin have real code, while C2/C4 backend modules are mostly empty scaffolds.

## Project

AdaptiveLearnSE is an undergraduate research monorepo: C1 Cognitive Digital Twin, C2 Exam Intelligence, C3 Automated Marking & Answer Analysis (the primary focus), C4 RL Adaptive Learning. C3 must preserve three objectives: rubric-aware semantic evaluation, explainable marking, and answer-to-concept mind maps.

## Architecture

- `frontend/` — single React 18 + Vite app (pages grouped by role/component under `src/pages/{admin,lecturer,c1..c4}`). Vite dev server on :5173 proxies `/api` to the backend at `127.0.0.1:3000`.
- `backend/` — **one** Express (ESM) app. `src/app.js` auto-mounts every `src/modules/<name>/routes/index.js` at `/api/v1/<name>`, so a new module needs no edits to `app.js`. Modules (`auth`, `admin`, `c1`–`c4`) are folders in this one server, not separate services. `src/integration/` holds cross-component glue (c1-c2, c2-c3, c3-c1, c1-c4). Backend modules own routing, validation, auth, MongoDB access and orchestration; heavy AI/ML must stay in Python.
- `ai-services/c1`, `ai-services/c3` — FastAPI services (C3 on :8003, C1 on :8001; `C1_AI_URL`/`C3_AI_URL` in `backend/.env`). `c2`/`c4` are placeholders.
- C3 service layout: `app/routes` (analysis, marking, feedback, mindmap, assessment) over `services/{preprocessing,semantic,marking,concepts,feedback,mindmap,assessment,llm,rag,cckg}`. The pipeline is layered: Function 1 (`/analysis/answer`, deterministic lexical baseline) → Function 2 (`/marking/evaluate`, rubric-level selection that reuses Function 1 evidence; marks come only from explicit rubric levels, never from a percentage formula) → feedback, mind map. `services/llm` has a provider factory (`mock` default, `openai`, `local`/Ollama via `C3_LLM_PROVIDER`); `services/rag` the vector store (`C3_VECTOR_BACKEND`); `services/cckg` the Neo4j graph adapter with in-memory fallback. `experiments/` holds reproducible experiment/evaluation scripts and `models/` trained scoring regressors; `GET /health` on :8003 must be preserved.
- Data: MongoDB (operational data; Atlas via `MONGO_URI`, or local via docker) and Neo4j (shared curriculum concept knowledge graph). No per-component databases. `docker-compose.yml` runs only MongoDB and Neo4j.

## Commands

```powershell
# repo root
docker compose up -d mongodb neo4j

# backend/  (copy .env.example to .env; AUTH_SECRET required)
npm install
npm run dev            # node --watch src/server.js
npm test               # node --test src/modules/c3/tests/*.test.js
node --test src/modules/c3/tests/c3.test.js     # single test file
node scripts/seedAdmin.js                        # other seed*/check* scripts live in backend/scripts

# frontend/
npm install
npm run dev
npm run build

# ai-services/c3/  (Python venv: .venv or .venv_c3; copy .env.example to .env)
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
python -m pytest -q
python -m pytest tests/unit/test_marking_engine.py::test_name -q   # single test
```

Note: `ai-services/c3/requirements.txt` is saved as UTF-16 (shows as spaced characters in some tools); re-encode as UTF-8 if pip or an editor has trouble with it. There is no linter configured. `c3_live_microservice.test.js` expects the Python service to be running.

## Working rules specific to this repo

- Never fabricate AI outputs, metrics, datasets, or UI results; automated proposed marks must stay distinct from lecturer-verified/overridden marks (lecturer is final authority).
- Start with deterministic baselines before LLM/RAG; keep the offline `mock` provider the default, and don't commit `.env` files or secrets.
- Preserve provenance and avoid train/test leakage in `ai-services/c3/datasets` and `experiments`.
- Current working branch is a C3 feature branch (`feature/c3-pp1-experiments-…`); don't create extra C3 branches without strong reason.
