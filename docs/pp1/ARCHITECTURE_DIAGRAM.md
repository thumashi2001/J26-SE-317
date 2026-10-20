# AdaptiveLearnSE — Master System Architecture & Runtime Topology

**Document Version:** 2.0.0 (Authoritative PP1 Architecture)  
**System Milestone:** Project Performance 1 (PP1) Evaluation  
**Target Date:** 22, 23, and 26 October 2026  
**Scope:** Full Ecosystem Architecture with Component 3 (C3) Deep Dive  

---

## 1. High-Level Ecosystem Architecture

AdaptiveLearnSE operates as a multi-tier, micro-service-oriented platform consisting of a unified Single Page Application (SPA), an Express API Gateway / Application Server, dedicated Python AI microservices per component, and shared database systems.

```mermaid
graph TD
    subgraph Client_Layer ["Client Layer (React 18 + Vite | Port 5173)"]
        UI_Student["Student Portal<br>(/c1, /c3 Sandbox)"]
        UI_Lecturer["Lecturer Portal<br>(/lecturer/c1, /lecturer/c3/batch)"]
        UI_Admin["Admin Dashboard<br>(/admin)"]
    end

    subgraph Gateway_Layer ["Application & Gateway Layer (Node.js / Express | Port 3000)"]
        AUTH["Auth & RBAC Middleware<br>(JWT, Roles: student, lecturer, admin)"]
        MOD_C1["C1 Controller & Services<br>(Cognitive Digital Twin & Mastery)"]
        MOD_C2["C2 Controller & Routes<br>(Exam Intelligence - Stub/Proxy)"]
        MOD_C3["C3 Controller & Services<br>(Automated Marking & Batch Studio)"]
        MOD_C4["C4 Routes<br>(Placeholder / ComingSoon)"]
        BRIDGE_C3_C1["C3 -> C1 Integration Bridge<br>(syncC3AssessmentToC1)"]
    end

    subgraph AI_Microservices_Layer ["Python AI Engine Layer"]
        AI_C1["C1 AI Service (Port 8001/8000)<br>• Forgetting Curve Model<br>• Risk Predictor (GBDT)<br>• Topic Adaptation"]
        AI_C2["C2 AI Service<br>• Syllabus Topic Extraction<br>• Candidate Ranking & Quality Filter"]
        AI_C3["C3 AI Engine (FastAPI | Port 8003)<br>• F1: Preprocessing & Concept Match<br>• F2: Rubric-Aware Marking Engine<br>• F3: Explainable Feedback Generator<br>• F4: Mind-Map DAG Synthesizer"]
        AI_C4["C4 AI Service<br>(Planned RL Engine - Skeletons only)"]
    end

    subgraph Data_Persistence_Layer ["Persistence Layer"]
        MONGO[("MongoDB Atlas<br>(adaptivelearnse_dev)<br>• users, learning_events<br>• c3_submissions, c3_batch_setups<br>• c3_results, mastery_state")]
        NEO4J[("Neo4j Graph Database<br>(Intended for CCKG)<br>⚠️ Status: Docker provisioned only<br>No graph schema / Cypher active")]
    end

    %% Client to Gateway
    UI_Student -->|REST / JWT| AUTH
    UI_Lecturer -->|REST / JWT| AUTH
    UI_Admin -->|REST / JWT| AUTH

    AUTH --> MOD_C1
    AUTH --> MOD_C2
    AUTH --> MOD_C3
    AUTH --> MOD_C4

    %% Internal Gateway to Services
    MOD_C1 -->|Internal HTTP| AI_C1
    MOD_C3 -->|Internal HTTP :8003| AI_C3
    MOD_C3 -->|In-Process Event Call| BRIDGE_C3_C1
    BRIDGE_C3_C1 -->|Idempotent Event Emission| MONGO

    %% DB Persistence
    MOD_C1 --> MONGO
    MOD_C3 --> MONGO
    AI_C1 -.->|Feature Queries| MONGO
```

---

## 2. Component 3 (C3) Runtime Topology & Internal Architecture

Component 3 is divided cleanly between an asynchronous Node.js orchestrator and an in-process, high-efficiency Python FastAPI NLP evaluation service.

```mermaid
sequenceDiagram
    autonumber
    actor Lecturer as Lecturer (Browser)
    participant Front as React Vite Frontend (:5173)
    participant Express as Node.js C3 Controller (:3000)
    participant DB as MongoDB Atlas
    participant PyAI as Python AI Service (:8003)
    participant C1Bridge as C3-C1 Bridge (learning_events)

    Lecturer->>Front: 1. Setup Question & Rubric (SE3010-Q01)
    Front->>Express: POST /api/v1/c3/batch/setup
    Express->>DB: Upsert into 'c3_batch_setups'
    Express-->>Front: Setup Locked & Saved

    Lecturer->>Front: 2. Import Cohort Answers (CSV / Dynamic Grid)
    Lecturer->>Front: 3. Click "Validate Answers"
    Front->>Express: POST /api/v1/c3/batch/validate
    Express-->>Front: Pre-validation Report (flags duplicates, empty rows)

    Lecturer->>Front: 4. Click "Mark Valid Cohort (AI)"
    Front->>Express: POST /api/v1/c3/batch/mark
    loop For each valid student answer
        Express->>PyAI: POST /c3/assess (question, answer, rubric)
        Note over PyAI: F1: Preprocessing & Regex Token Match<br>F2: Rubric Scoring Level Assignment<br>F3: Feedback & Missing Concepts<br>F4: Concept Mind-Map DAG Synthesis
        PyAI-->>Express: Awarded marks, criteria spans, DAG nodes, feedback
        Express->>DB: Idempotent Upsert into 'c3_submissions' & 'c3_results'
        Express->>C1Bridge: syncC3AssessmentToC1(lifecycle: 'provisional')
        C1Bridge->>DB: Upsert 'learning_events' (provisional_score)
    end
    Express-->>Front: Batch Results Table (Marks, AI Proposed)

    Lecturer->>Front: 5. Inspect Evidence & Mind Map DAG
    Front-->>Lecturer: Interactive SVG DAG + Criterion Evidence Cards

    Lecturer->>Front: 6. Submit Score Override (e.g. 3.5 / 4.0 + Reason)
    Front->>Express: POST /api/v1/c3/submissions/:id/review
    Express->>DB: Update 'c3_submissions' (final_mark: 3.5, reason: "...")
    Express-->>Front: Status: 'reviewed'

    Lecturer->>Front: 7. Click "Finalize All Submissions"
    Front->>Express: POST /api/v1/c3/batch/:id/finalize-all
    Express->>DB: Transition status to 'finalized'
    Express->>C1Bridge: syncC3AssessmentToC1(lifecycle: 'finalized')
    C1Bridge->>DB: Update 'learning_events' (final_score, lecturer_decision)
    Express-->>Front: 100% Finalized Audit State
```

---

## 3. Component Boundaries & Ownership Status

| Component | Official Project Scope | Responsible Owner | Implementation Reality in Repository | Runtime Status for PP1 |
| :--- | :--- | :--- | :--- | :--- |
| **Component 1 (C1)** | Cognitive Digital Twin, Learning State, Risk Prediction, Practice Engine | Teammate (Protected) | Fully functional backend (`modules/c1/`), active UI pages (`DashboardPage`, `TopicInsightsPage`, `ClassInsights`), GBDT model, and pilot analysis. | ✅ **Operational & Tested** |
| **Component 2 (C2)** | Exam Intelligence, Past Paper Ingestion, Syllabus Topic Extraction | Teammate (Protected) | Python syllabus topic candidate extraction, quality filters, and ranking repository implemented in `ai-services/c2/`. Frontend UI is `ComingSoon`. | ⚠️ **AI Services Active; UI Placeholder** |
| **Component 3 (C3)** | AI-Powered Automated Marking, Rubric Evaluation, Mind Map Synthesis, Lecturer Governance | **Candidate (Candidate Owned)** | Fully functional: Batch Studio wizard, deterministic MCQ engine, rubric subjective evaluator, SVG DAG generator, MongoDB persistence, C1 bridge, 140 passing tests, 12 verified screenshots. | ✅ **Authoritative, Complete & PP1 Ready** |
| **Component 4 (C4)** | Reinforcement-Learning Adaptive Study Paths & Recommendation | Teammate (Protected) | Directory skeletons only (`ai-services/c4/`, `frontend/src/pages/c4/` contain `.gitkeep`). UI routes render `ComingSoon`. | ❌ **Deferred / Skeletons Only** |
| **Shared CCKG** | Co-Evolving Curriculum Knowledge Graph (Neo4j) | **Shared Architecture (Unassigned Owner)** | Docker Compose provisions a basic Neo4j:5 container. No Cypher scripts, graph schemas, or backend connection drivers exist in the codebase. | ❌ **Proposed Architecture Only (Unimplemented)** |

---

## 4. Security, Authentication & Role-Based Authorization (RBAC)

1. **Authentication:** Stateless JSON Web Tokens (JWT) signed using `JWT_SECRET`. Tokens are transmitted via the standard HTTP `Authorization: Bearer <token>` header.
2. **Role Authorization Hierarchy:**
   - **Student (`role: 'student'`):** Restricted to `/c1/*` and `/c3` student sandbox. Forbidden (HTTP 403) from accessing `/lecturer/*`, batch marking setup, lecturer review endpoints, or override endpoints.
   - **Lecturer (`role: 'lecturer'`):** Authorized to access `/lecturer/*`, configure batch rubrics, mark cohorts, view evidence, apply score overrides, and finalize submissions. Cannot impersonate other students.
   - **Admin (`role: 'admin'`):** Inherits all lecturer privileges plus access to `/admin` dashboard.
3. **Audit Trail & Provenance:**
   - The system tracks provenance (`student`, `pp1_demo`, `test_fixture`).
   - Every score override requires a non-empty `override_reason` string, preserving the original AI proposed mark (`automated_mark`) alongside the authoritative `final_mark` and `reviewed_by` timestamp.
