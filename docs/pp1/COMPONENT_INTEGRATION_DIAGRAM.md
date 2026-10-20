# AdaptiveLearnSE — Component Integration Diagram & Contract Specification

**Document Version:** 2.0.0 (Authoritative PP1 Integration Specification)  
**Target Milestone:** Project Performance 1 (PP1) Evaluation  
**Auditor:** Component 3 Engineer  

---

## 1. Ecosystem Component Integration Matrix

The table below classifies every inter-component connection across AdaptiveLearnSE by its actual implementation status in the codebase:

| Connection ID | Source (Producer) | Target (Consumer) | Purpose & Data Payload | Implementation Status | Real Runtime Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **INT-C3-C1** | **Component 3 (Marking)** | **Component 1 (Cognitive Twin)** | Emits provisional & finalized assessment scores and concept masteries (`demonstrated`, `partial`, `missing`) to update student cognitive twin state. | ✅ **Operational & Verified** | `backend/src/integration/c3-c1/index.js`<br>`c1/services/eventService.js:71`<br>`c3.test.js:18-21, 40` |
| **INT-C2-C3** | **Component 2 (Exam Intel)** | **Component 3 (Marking)** | Delivers structured past-paper questions, syllabus topics, and multi-criterion rubrics for automated evaluation. | 🟡 **Contract Specified; Runtime Pending C2 UI** | `backend/src/integration/c2-c3/README.md`<br>C3 accepts compliant payloads directly via Batch Studio. |
| **INT-C1-C4** | **Component 1 (Cognitive Twin)** | **Component 4 (Adaptive Paths)** | Exports mastery gaps and forgetting curve risks to drive reinforcement-learning study path generation. | ❌ **Proposed Only** | C4 UI is `ComingSoon`; AI service has empty skeleton folders. |
| **INT-C3-C4** | **Component 3 (Marking)** | **Component 4 (Adaptive Paths)** | Feeds concept diagnosis gaps into personalized remedial revision scheduling. | ❌ **Proposed Only** | Blocked by C4 implementation status. |
| **INT-*-CCKG** | **All Components** | **Shared CCKG (Neo4j)** | Bidirectional graph queries for syllabus concept traversal, prerequisite mapping, and question alignment. | ❌ **Proposed Only** | Docker container configured; zero Cypher scripts, schemas, or drivers in code. |

---

## 2. Component-to-Component Architectural Interaction Flow

```mermaid
graph TD
    subgraph C2_Boundary ["Component 2: Exam Intelligence (Teammate Owned)"]
        C2_Extraction["Syllabus & Exam Parser<br>(Python ai-services/c2)"]
        C2_Contract["Contract Specification<br>(backend/src/integration/c2-c3/README.md)"]
    end

    subgraph C3_Boundary ["Component 3: Automated Marking (Candidate Owned)"]
        C3_Batch["Lecturer Batch Studio<br>(Question, Rubric & Answers)"]
        C3_Engine["F1–F4 Automated Evaluation Pipeline<br>(ai-services/c3 Port 8003)"]
        C3_Review["Lecturer Review & Override Engine<br>(Mandatory Reason Enforced)"]
        C3_Bridge["C3 -> C1 Live Integration Bridge<br>(syncC3AssessmentToC1)"]
    end

    subgraph C1_Boundary ["Component 1: Cognitive Digital Twin (Teammate Owned)"]
        C1_Events[("MongoDB: 'learning_events' Collection")]
        C1_Twin["Event Processing & Risk Model<br>(c1/services/eventService.js)"]
        C1_UI["Student Digital Twin Dashboard<br>(/c1/dashboard, /c1/topics)"]
    end

    subgraph C4_Boundary ["Component 4: Adaptive Study Paths (Teammate Owned)"]
        C4_Placeholder["Status: Placeholder<br>(frontend/src/pages/c4 ComingSoon)"]
    end

    subgraph CCKG_Boundary ["Shared CCKG: Neo4j Graph (Unassigned Owner)"]
        CCKG_Placeholder["Status: Proposed Architecture Only<br>(No graph schema or Cypher scripts)"]
    end

    %% Verified Active Connection
    C3_Engine -->|1. Idempotent Upsert (Provisional)| C3_Bridge
    C3_Review -->|2. Idempotent Upsert (Finalized)| C3_Bridge
    C3_Bridge -->|3. Structured Event Record| C1_Events
    C1_Events -->|4. Reads Non-Provisional Events| C1_Twin
    C1_Twin -->|5. Recalculates Topic Mastery & Risk| C1_UI

    %% Specified / Pending Connections
    C2_Extraction -.->|Format Aligned| C2_Contract
    C2_Contract -.->|Pending Runtime Integration| C3_Batch

    %% Blocked / Proposed Connections
    C1_Twin -.->|Proposed Handoff| C4_Placeholder
    C3_Engine -.->|Proposed Concept Gaps| C4_Placeholder
    C1_Twin -.->|Proposed Graph Alignment| CCKG_Placeholder
    C3_Engine -.->|Condition D Planned GraphRAG| CCKG_Placeholder

    classDef verified fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef pending fill:#fff3cd,stroke:#ffc107,stroke-width:2px;
    classDef proposed fill:#f8d7da,stroke:#dc3545,stroke-width:1px,stroke-dasharray: 5 5;

    class C3_Bridge,C1_Events,C1_Twin,C1_UI verified;
    class C2_Contract pending;
    class C4_Placeholder,CCKG_Placeholder proposed;
```

---

## 3. Deep-Dive Specification of the Verified C3-to-C1 Event Contract

The only verified, fully functional cross-component interface in the repository is the **C3-to-C1 Integration Bridge**:

### 3.1 Producer & Consumer Specification
- **Producer:** Component 3 (`backend/src/modules/c3/services/submissionService.js` and `batchMarkingService.js`).
- **Adapter Function:** `syncC3AssessmentToC1` (`backend/src/integration/c3-c1/index.js`).
- **Consumer:** Component 1 Cognitive Digital Twin (`backend/src/modules/c1/services/eventService.js`).
- **Shared Medium:** MongoDB Atlas collection `learning_events`.

### 3.2 Data Schema & Field Contracts

```json
{
  "_id": "6714a8f9c1e2b3a4d5e6f7a8",
  "student_id": "IT21001001",
  "submission_id": "6714a8f9c1e2b3a4d5e6f7a1",
  "question_id": "SE3010-Q01",
  "question_text": "Explain the trade-offs between monolithic architecture and microservices...",
  "type": "c3_finalized_assessment",
  "topic": "sa_patterns_styles",
  "timestamp": "2026-10-20T10:45:00.000Z",
  "lifecycle_stage": "finalized",
  "score": 3.5,
  "total_possible": 4.0,
  "percentage": 87.5,
  "is_passing": true,
  "concepts_demonstrated": ["loose_coupling", "single_responsibility"],
  "concepts_partial": ["microservices"],
  "concepts_missing": ["event_driven"],
  "provisional_score": 4.0,
  "final_score": 3.5,
  "lecturer_decision": "overridden",
  "override_reason": "Awarded 3.5 marks. Strong microservices justification with minor terminology gap.",
  "reviewed_by": "SLIITLEC101"
}
```

### 3.3 Lifecycle States & Consumer Safeguards

1. **Stage 1 — Provisional Assessment (At AI Grading Time):**
   - When C3 evaluates an answer, it immediately emits a record with `lifecycle_stage: 'provisional'`.
   - Consumer Safeguard: In Component 1 (`c1/services/eventService.js:71`), C1 explicitly filters out events where `lifecycle_stage === 'provisional'`. This ensures that unverified AI predictions never prematurely distort the student's authoritative mastery or risk score.
2. **Stage 2 — Finalized Assessment (At Lecturer Sign-off):**
   - When the lecturer reviews or finalizes the cohort, C3 updates the exact same record in-place by `submission_id`.
   - Fields updated: `lifecycle_stage: 'finalized'`, `final_score`, `lecturer_decision`, `override_reason`.
   - C1 now includes this event in history calculations, triggering forgetting updates and GBDT risk prediction.
3. **Idempotency & Retry Guarantee:**
   - Repeated calls to `syncC3AssessmentToC1` for the same `submission_id` update the existing document using MongoDB `$set` rather than appending duplicate rows. This guarantees safe batch retries.
