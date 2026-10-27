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
- C3 dataset: the authoritative research dataset is the **repaired** `C3-Phase3-v5` set in `ai-services/c3/datasets/c3_phase3_v5_repaired/` (96 eligible questions / 576 answers; 355 answers quarantined, 71 repaired controls kept outside the primary set; see its `DATASET_CARD.md`, `repair_manifest.csv`, `validation_report.json`). The byte-exact original is in `datasets/archive/C3-Phase3-v5-FINAL_original/` (SHA256SUMS; never edit). Repair = `datasets/repair_c3_dataset.py` (deterministic, verifies the archive hash), validate = `datasets/validate_repaired.py <dir> --json`, recompute metrics = `python -m datasets.repair.evaluate_repaired <dir>`. Rules: never generate or reword answers, never assign marks from a tier name, never move records between splits, quarantine with a reason instead of guessing. Known open failure: ratio-concentration 0.758 > 0.45 (inherited from the labels; threshold in `datasets/repair/validation_spec.json`, not to be weakened). The earlier LLM generator (v6) was removed; the free Gemini tier (20 req/day/model) made it infeasible.
- C3 frozen modelling set: `datasets/c3_phase3_v5_repaired_v2/` (derived by `datasets/repair/derive_v2.py`; 558 eligible answers, ratio-concentration still FAILS 0.766 — labels are tier-based). `experiments/model_comparison.py` (TF-IDF / SBERT / RoBERTa + baseline + Condition E; validation-only selection, results in `reports/c3_remediation/`) needs torch/transformers/sentence-transformers (`experiments_requirements_lock.txt`, not in requirements.txt). RoBERTa won on v2 but a length-only model beats TF-IDF/SBERT, so do not claim semantic skill.
- C3 experiments (target the removed v6 release schema; need an adapter to the repaired dataset before use): `experiments/run_experiments.py` runs the lexical baseline and conditions A-F (`framework.py` metrics/prompts, `conditions.py` implementations). Failed model calls are excluded and counted, never scored 0; condition C retrieves from TRAIN references only; F weights are fit on validation only.
- Data: MongoDB (operational data; Atlas via `MONGO_URI`, or local via docker) and Neo4j (shared curriculum concept knowledge graph). No per-component databases. `docker-compose.yml` runs only MongoDB and Neo4j.

- C3 DATA NOTE (found 2026-10-27): `02_controlled_answers_eligible.csv` has an EMPTY `reference_answer` column for every row; the reference answers are in `01_question_bank.csv`. Always load via `experiments.model_comparison.load_answers_with_reference()` / `load()` (regression test: `tests/unit/test_reference_answers_loaded.py`). Model results produced before the fix (report 03, F-lite, `reports/c3_remediation/experiments/extra_answer_only/`) are ANSWER-ONLY and must not be cited as reference-aware.
- C3 extra model comparison: `experiments/model_comparison_extra.py` (phase 1, validation only, saves checkpoints) -> `experiments/final_test_extra.py` (phase 2, scores the held-out split once, refuses a rerun); Colab notebook `experiments/colab_train_models.ipynb`. `experiments/multi_llm_comparison.py` compares 2-3 free LLM providers (groq/openrouter/gemini/... via OpenAI-compatible presets in `services/llm/factory.py`); BLOCKED without keys + `--run-live`.
- C3 advisory AI estimate: `services/ml/scorer.py` loads a fine-tuned transformer from `C3_ML_MODEL_DIR` and `/c3/assess` adds `ai_estimate` (advisory, never changes marks, `needs_review` when it differs from the rubric by >0.25). Off by default; fails soft. Trained on tier-derived labels, so it is not evidence of human-level marking.

- Backend C3 security: `AUTH_SECRET` is mandatory (no fallback). Students send only their answer plus `demo_id` (server bank `modules/c3/data/demoAssessments.js`) or `batch_id`; inline rubric/answer key is rejected for students and allowed for lecturers/admins. Batches are owner-scoped (admin sees all); a failed save returns 503. Tests: 93 (91 pass, 2 todo AUDIT-B9).

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
.venv_c3\Scripts\python.exe datasets\validate_repaired.py datasets\c3_phase3_v5_repaired --json
.venv_c3\Scripts\python.exe datasets\repair_c3_dataset.py --sample   # deterministic; a full run refuses a non-empty output dir
.venv_c3\Scripts\python.exe -m datasets.repair.evaluate_repaired datasets\c3_phase3_v5_repaired
.venv_c3\Scripts\python.exe experiments\run_experiments.py --smoke   # targets the removed v6 schema; needs an adapter
bash database/neo4j/scripts/load_cckg.sh                              # repo root, loads CCKG schema + seeds
```

Notes: known bugs are encoded as strict `xfail` (Python) / `todo` (Node) tests tagged `AUDIT-<id>`; fixing one makes its xfail fail until the marker is removed. `c3_live_microservice.test.js` uses whatever is on :8003 (skips if nothing is). Lint has remaining findings (ruff E501/E402/B905; eslint unused vars) that are reported, not fixed.

## Working rules specific to this repo

- Never fabricate AI outputs, metrics, datasets, or UI results; automated proposed marks must stay distinct from lecturer-verified/overridden marks (lecturer is final authority).
- Start with deterministic baselines before LLM/RAG; there is no mock/simulated LLM anywhere; unit tests may stub HTTP but results must come from real models. Don't commit `.env` files or secrets.
- Preserve provenance and avoid train/test leakage in `ai-services/c3/datasets` and `experiments`.
- Current working branch is a C3 feature branch (`feature/c3-pp1-experiments-…`); don't create extra C3 branches without strong reason.
- Git commits/PRs use only the configured author identity (`Vk-Viman`). Never add a `Co-Authored-By: Claude …` trailer or "Generated with Claude Code" line; the user's instruction overrides any default attribution. Project-local `.claude/settings.local.json` sets `attribution.commit/pr` to empty (do not commit that file).
- C3 Vector RAG (`ai-services/c3/services/rag/{corpus,rag_marking}.py`, local SBERT embeddings via `C3_EMBEDDING_PROVIDER=local`) is a library + experiment harness, not wired into `/c3/assess`. Its corpus is TRAIN-only; marking output is validated and always `pending_review`. LLM RAG-vs-no-RAG evaluation is BLOCKED until credentials/quota exist (`experiments/rag_vs_norag.py --run-live`). Status of every proposed experiment: `reports/c3_remediation/experiment_status_matrix.csv`.
- C3 UI (frontend/src/pages/c3): pages use the shared tokens/classes in `src/index.css` plus `components/c3ui.jsx` (PageHeader, StatusPill, Notice, Dialog/ConfirmDialog, Stepper). No "Component 3"/version labels in user-facing screens. Students only ever send `demo_id`/`batch_id` + their answer; questions come from `GET /c3/assessments` (no keys), lecturer examples from the staff-only `GET /c3/examples`; student submission detail is redacted server-side. Browser tests: `reports/c3_remediation/ui_tests/` (see `13_c3_frontend_ux_audit.md`).
- C3 result views share one renderer (`frontend/src/pages/c3/components/AssessmentResult.jsx` + `analysis.js`): missing analysis is shown as an explicit note, MCQ has no concept diagnosis/map. Students never receive MCQ answer keys (`backend/.../services/redaction.js`, applied to `/assess` and `GET /submissions/:id`). Frontend component tests: `cd frontend && npm test` (fixtures in `frontend/tests/fixtures`, captured from the live service). Restart the backend after pulling route changes (`npm run dev`).
