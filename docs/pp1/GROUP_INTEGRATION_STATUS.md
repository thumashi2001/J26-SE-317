# AdaptiveLearnSE — Group Integration Status & System Overview

**Document Version:** 2.0.0 (Authoritative PP1 Assessment Audit)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Candidate Ownership:** Component 3 (AI-Powered Automated Marking & Answer Analysis System)  

---

## 1. Shared Group Vision & Overall Solution Architecture

The examiners evaluate AdaptiveLearnSE as an **integrated ecosystem**, not four disconnected student projects. The candidate must be prepared to articulate how all four components interconnect to realize the shared cognitive digital twin vision:

```
                  ┌──────────────────────────────────────────────┐
                  │             SHARED CCKG (Neo4j)              │
                  │   (Co-Evolving Curriculum Knowledge Graph)   │
                  │   * Proposed Unifying Conceptual Graph *    │
                  └──────┬──────────────┬──────────────┬─────────┘
                         │              │              │
        ┌────────────────┘              │              └────────────────┐
        ▼                               ▼                               ▼
┌───────────────┐               ┌───────────────┐               ┌───────────────┐
│  COMPONENT 2  │               │  COMPONENT 3  │               │  COMPONENT 4  │
│     (Exam     │ Questions &   │  (Automated   │ Concept Gaps  │   (Adaptive   │
│ Intelligence) │ Rubrics       │   Marking)    │ & Diagnostic  │  Study Paths) │
│               ├──────────────►│  [Candidate]  ├──────────────►│               │
└───────────────┘               └───────┬───────┘               └───────▲───────┘
                                        │                               │
                                        │ Verified Event Sync           │
                                        ▼ (learning_events)             │ Mastery
                                ┌───────────────┐                       │ State &
                                │  COMPONENT 1  │                       │ Risk
                                │  (Cognitive   ├───────────────────────┘
                                │ Digital Twin) │
                                └───────────────┘
```

### Functional Synergy Across Components:
1. **Component 2 (Input Pipeline):** Ingests university past papers and syllabus lecture notes, extracting structured questions, topics, and multi-criterion rubrics.
2. **Component 3 (Evaluation Pipeline — Candidate Owned):** Assesses student responses against rubrics, extracts sentence evidence, diagnoses concept mastery, generates concept mind maps, and enforces lecturer human-in-the-loop review.
3. **Component 1 (Cognitive Modeling Engine):** Receives verified C3 learning events, updates topic mastery, applies Ebbinghaus forgetting curves, and predicts academic risk using GBDT machine learning models.
4. **Component 4 (Adaptive Recommendation):** Uses C1 cognitive states and C3 concept gaps to generate personalized reinforcement-learning revision schedules.
5. **Shared CCKG (Knowledge Spine):** Intended to ground all components in a formal curriculum ontology linking prerequisite concepts and syllabus learning outcomes.

---

## 2. Actual Repository Implementation Reality vs. Planned Architecture

To uphold academic integrity, the candidate must distinguish between what is **genuinely operational in the repository** versus what is **partially implemented, placeholder, or proposed**:

| Component / Subsystem | Responsible Teammate | Actual Codebase Reality | Real Evidence & Paths | PP1 Integration Status |
| :--- | :--- | :--- | :--- | :--- |
| **Component 1 (C1)**<br>Cognitive Digital Twin | Teammate (Protected) | Complete backend service (`modules/c1/`), active UI pages (`DashboardPage`, `TopicInsightsPage`, `ClassInsights`), GBDT model, Google Forms pilot analysis. | `backend/src/modules/c1/`<br>`frontend/src/pages/c1/`<br>`docs/c1-question-method.md` | ✅ **Operational & Tested** |
| **Component 2 (C2)**<br>Exam Intelligence | Teammate (Protected) | Active Python services for syllabus candidate extraction, quality filtering, and ranking. Frontend UI routes currently render `ComingSoon` placeholder. | `ai-services/c2/services/`<br>`ai-services/c2/tests/`<br>`frontend/src/pages/c2/.gitkeep` | 🟡 **AI Engine Active; UI Placeholder** |
| **Component 3 (C3)**<br>Automated Marking Engine | **Candidate (Candidate Owned)** | 100% complete and verified: Batch Studio wizard, deterministic MCQ engine, rubric subjective evaluator, SVG DAG generator, MongoDB persistence, C1 bridge, 140 passing tests, 12 verified screenshots. | `backend/src/modules/c3/`<br>`frontend/src/pages/c3/`<br>`ai-services/c3/`<br>`ss/01`–`12_*.png` | ✅ **Authoritative, Complete & PP1 Ready** |
| **Component 4 (C4)**<br>Adaptive Learning Paths | Teammate (Protected) | Directory skeletons only (`ai-services/c4/` and `frontend/src/pages/c4/` contain `.gitkeep`). UI routes render `ComingSoon` placeholder. | `frontend/src/pages/ComingSoon.jsx`<br>`ai-services/c4/requirements.txt` | ❌ **Deferred / Skeletons Only** |
| **Shared CCKG**<br>Neo4j Curriculum Graph | **Shared Architecture (Unassigned Owner)** | Docker Compose provisions a basic Neo4j:5 container. Zero Cypher scripts, graph schemas, or backend connection drivers exist in the codebase. | `docker-compose.yml`<br>`database/neo4j/README.md` | ❌ **Proposed Architecture Only (Unimplemented)** |

---

## 3. Strict Ownership Boundaries for the Candidate

1. **Candidate Coding Authority:**
   - Candidate is strictly responsible for **Component 3**.
   - Candidate has full authority to audit, modify, test, and demonstrate C3 backend services, C3 Python engine, C3 frontend views, C3 evaluation benchmarks, and the C3-to-C1 adapter.
2. **Teammate Code Protection Policy:**
   - The candidate **must not modify, refactor, or overwrite** C1, C2, C4, or CCKG code.
   - If an integration connection is missing because another component has not implemented their endpoint, the candidate must **not** create a fake or competing implementation of that teammate's component.
   - Instead, the candidate documents the exact contract, runtime findings, and produces a clean handoff in `docs/pp1/INTEGRATION_HANDOFFS.md`.
3. **Viva Defense Position:**
   - When asked about the group project: Candidate presents the shared vision and overall architecture.
   - When asked about individual contribution: Candidate articulates the complete C3 workflow, empirical evaluation, 140 automated tests, and the operational C3-to-C1 live event bridge.
