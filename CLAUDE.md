# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The repo root is `ADAPTIVE_LEARN_SE/` (the git repository). `AGENTS.md` holds the full project rules (research-integrity requirements, engineering workflow, change-communication format); read it before C3 work. The root `README.md` and several sub-READMEs still say "structure only" — they are outdated; C1, C3 and auth/admin have real code, while C2/C4 backend modules are mostly empty scaffolds.

## Project

AdaptiveLearnSE is an undergraduate research monorepo: C1 Cognitive Digital Twin, C2 Exam Intelligence, C3 Automated Marking & Answer Analysis (the primary focus), C4 RL Adaptive Learning. C3 must preserve three objectives: rubric-aware semantic evaluation, explainable marking, and answer-to-concept mind maps.

## Architecture

- `frontend/` — single React 18 + Vite app (pages grouped by role/component under `src/pages/{admin,lecturer,c1..c4}`). Vite dev server on :5173 proxies `/api` to the backend at `127.0.0.1:3000`.
- `backend/` — **one** Express (ESM) app. `src/app.js` auto-mounts every `src/modules/<name>/routes/index.js` at `/api/v1/<name>`, so a new module needs no edits to `app.js`. Modules (`auth`, `admin`, `c1`–`c4`) are folders in this one server, not separate services. `src/integration/` holds cross-component glue (c1-c2, c2-c3, c3-c1, c1-c4). Backend modules own routing, validation, auth, MongoDB access and orchestration; heavy AI/ML must stay in Python.
- `ai-services/c1`, `ai-services/c3` — FastAPI services (C3 on :8003, C1 on :8001; `C1_AI_URL`/`C3_AI_URL` in `backend/.env`). `c2`/`c4` are placeholders.
- C3 service layout: `app/routes` (analysis, marking, feedback, mindmap, assessment) over `services/{preprocessing,semantic,marking,feedback,mindmap,assessment,llm,rag,cckg}`. Pipeline: Function 1 (`/analysis/answer`, deterministic lexical baseline) -> Function 2 (`/marking/evaluate`, rubric-level selection; marks come only from explicit rubric levels, never a percentage formula) -> feedback, mind map. `/health` on :8003 must be preserved (it makes no network calls).
- C3 AI providers are REAL only (the mock LLM was deleted): `services/llm` has `gemini` (default), `openai`, `local` (Ollama), chosen with `C3_LLM_PROVIDER`; an unknown provider raises. `CachedLLMProvider` stores real responses in a JSONL cache for reproducible reruns. `services/rag` holds real embeddings (`C3_EMBEDDING_PROVIDER`) and a vector store that takes an explicit corpus (`dense` or an explicitly-labelled `tfidf` baseline). `services/cckg` is the Neo4j adapter; `C3_CCKG_STRICT=1` (or `strict=True`) forbids the in-memory fallback.
- C3 dataset: `datasets/source/questions_source.csv` (167 verbatim exam questions) -> `datasets/generate_c3_dataset.py` (LLM-generated, rubric-targeted, labels = sum of targeted rubric-level marks) -> `datasets/c3_synthetic_v6/` release (manifest with sha256) -> `datasets/validate_dataset.py` (41 checks, `datasets/generator/tier_spec.json` is the single spec) -> `datasets/loader.py::load_release`. The previous dataset was deleted for documented defects; never hand-edit a release.
- C3 experiments: `experiments/run_experiments.py` runs the lexical baseline and conditions A-F (`framework.py` metrics/prompts, `conditions.py` implementations). Failed model calls are excluded and counted, never scored 0; condition C retrieves from TRAIN references only; F weights are fit on validation only.
- Data: MongoDB (operational data; Atlas via `MONGO_URI`, or local via docker) and Neo4j (shared curriculum concept knowledge graph). No per-component databases. `docker-compose.yml` runs only MongoDB and Neo4j.

## Commands

```powershell
# repo root
docker compose up -d mongodb neo4j

# backend/  (copy .env.example to .env; AUTH_SECRET required)
npm install
npm run dev            # node --watch src/server.js
npm test               # node:test: c3 + middleware tests; `todo` tests are known bugs (AUDIT-*)
npm run test:coverage; npm run lint
node --test src/modules/c3/tests/c3.test.js     # single test file
node scripts/seedAdmin.js                        # other seed*/check* scripts live in backend/scripts

# frontend/
npm install
npm run dev
npm run build

# ai-services/c3/  (venv: .venv_c3; copy .env.example to .env and add GEMINI_API_KEY / OPENAI_API_KEY)
.venv_c3\Scripts\python.exe -m pip install -r requirements-dev.txt   # always `python -m` (exe shims are blocked)
.venv_c3\Scripts\python.exe -m uvicorn app.main:app --reload --port 8003
.venv_c3\Scripts\python.exe -m pytest -q --cov                      # default: offline, no keys
.venv_c3\Scripts\python.exe -m pytest -m live_llm -q                # real Gemini/OpenAI calls
.venv_c3\Scripts\python.exe -m pytest -m neo4j -q                   # needs docker neo4j + load_cckg.sh
.venv_c3\Scripts\python.exe -m ruff check .
.venv_c3\Scripts\python.exe datasets\generate_c3_dataset.py --dry-run   # then --limit 3, then full (--resume)
.venv_c3\Scripts\python.exe datasetsalidate_dataset.py
.venv_c3\Scripts\python.exe experimentsun_experiments.py --smoke
bash database/neo4j/scripts/load_cckg.sh                              # repo root, loads CCKG schema + seeds
```

Notes: known bugs are encoded as strict `xfail` (Python) / `todo` (Node) tests tagged `AUDIT-<id>`; fixing one makes its xfail fail until the marker is removed. `c3_live_microservice.test.js` uses whatever is on :8003 (skips if nothing is). Lint has remaining findings (ruff E501/E402/B905; eslint unused vars) that are reported, not fixed.

## Working rules specific to this repo

- Never fabricate AI outputs, metrics, datasets, or UI results; automated proposed marks must stay distinct from lecturer-verified/overridden marks (lecturer is final authority).
- Start with deterministic baselines before LLM/RAG; there is no mock/simulated LLM anywhere; unit tests may stub HTTP but results must come from real models. Don't commit `.env` files or secrets.
- Preserve provenance and avoid train/test leakage in `ai-services/c3/datasets` and `experiments`.
- Current working branch is a C3 feature branch (`feature/c3-pp1-experiments-…`); don't create extra C3 branches without strong reason.
