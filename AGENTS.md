# AdaptiveLearnSE Agent Guide

## Project focus

AdaptiveLearnSE is an undergraduate research monorepo. Component 3 (C3), the AI-Powered Automated Marking and Answer Analysis System, is the primary development focus. Preserve these approved research objectives in every C3 change:

1. Rubric-aware semantic evaluation
2. Explainable AI-based marking
3. Conversion of natural-language student answers into structured or hierarchical concept-based mind maps

The project is on the `component_3` branch. Do not create another C3 branch unless there is a strong technical reason.

## Architecture boundaries

- `frontend/` is the single React application.
- `backend/` is the single Node.js/Express application. Component folders under `backend/src/modules/` are modules in that server, not separate backend services.
- `ai-services/c3/` is the C3 Python/FastAPI service for NLP, preprocessing, semantic analysis, marking, concept analysis, feedback, mind-map generation, experiments, and evaluation.
- `backend/src/modules/c3/` owns C3 application-facing API routes, validation, authentication/authorization, database access, orchestration, and integration. Keep heavy AI/ML logic in `ai-services/c3/`.
- MongoDB Atlas is for operational/application data. Neo4j is for the shared Curriculum Concept Knowledge Graph (CCKG). Do not create per-component databases or duplicate the Node backend.
- C3 currently exposes `GET /health` at `http://127.0.0.1:8003`; preserve it.

Useful implementation context: [root README](README.md), [C3 Python README](ai-services/c3/README.md), [C3 backend README](backend/src/modules/c3/README.md), [backend README](backend/README.md), [frontend README](frontend/README.md), [MongoDB notes](database/mongodb/README.md), and [Neo4j notes](database/neo4j/README.md).

## Verified development commands

Run commands from the directory shown:

```powershell
# Repository root: start only the database containers
docker compose up -d mongodb neo4j
docker compose down

# backend/
npm install
npm run dev
npm start

# frontend/
npm install
npm run dev
npm run build
npm run preview

# ai-services/c3/ (Python 3.13.15)
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
python -m pytest
```

The current repository is mainly structural. Do not describe a command, endpoint, model, dataset, or test as implemented unless the files and an executed check support that claim. Docker Compose provisions MongoDB and Neo4j only; it does not run the application services.

## Research and data integrity

- Develop in this order unless a documented reason changes it: answer processing, semantic analysis, rubric-aware marking, criterion scoring, partial credit, explainable evidence, concept diagnosis, feedback, mind maps, lecturer verification, Express integration, persistence, CCKG integration, model comparisons, LLM/RAG experiments, and evaluation.
- Start with a deterministic, defensible baseline before adding LLM or RAG approaches. Record alternatives, limitations, configuration, and evaluation plans.
- Never fabricate AI outputs, metrics, model performance, datasets, or completed functionality for a UI.
- Keep automated proposed results distinct from lecturer-verified and lecturer-overridden results. Lecturer review is the final authority over marks.
- Preserve provenance and prevent train/test leakage. Evaluation records should retain the question, reference answer, rubric, expected concepts, student answer, predicted and ground-truth marks, criterion scores, evidence, concepts, feedback, model/configuration, and dataset version where applicable.
- Prefer reproducible, explainable, traceable, auditable, and versioned research artifacts. Use the pattern `Claim -> Evidence -> Decision` for important design choices and maintain decision records in the appropriate documentation area.
- Use synthetic student-answer data and permitted institutional or past-paper material as the main research data sources. Do not silently substitute public benchmark data as the project dataset.

## Engineering workflow

For meaningful changes, follow `Design -> Implement -> Test -> Review -> Commit`. Before changing an interface or architecture, inspect its current implementation and explain the reason. Prefer typed schemas, validation, meaningful exceptions, structured logging, environment variables, small modules, and focused tests. Do not add unnecessary services, dependencies, abstractions, hard-coded secrets, or mock results presented as real research functionality.

Every meaningful implementation needs relevant unit tests, API/integration tests where applicable, edge-case checks, and a regression check for existing behavior. Run the narrowest relevant command first and report exactly what was executed. Do not claim tests passed unless they were run.

Use small meaningful commits when the user requests commits; never claim a commit or push that did not succeed. Avoid overwriting unrelated working changes.

## Change communication

When explaining a code change, name the exact folder and file, state exactly what changes, give the command needed to verify it, and explain the purpose and rationale. If repository files contradict an assumption, inspect and adapt to the existing implementation rather than creating a parallel structure. State uncertainty explicitly.
