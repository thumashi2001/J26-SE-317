# AdaptiveLearnSE — Inter-Component Integration Handoffs

**Document Version:** 2.0.0 (PP1 Group Integration Specification)  
**Author:** Component 3 Engineer  
**Purpose:** Precise integration specifications and actionable handoffs for teammate components.  

---

## 1. Handoff for Component 1 Owner (Cognitive Digital Twin)

### Current Integration Status: ✅ **OPERATIONAL & VERIFIED**
The C3-to-C1 live integration bridge (`backend/src/integration/c3-c1/index.js`) is implemented and tested. It writes structured events to MongoDB `learning_events` with stable `submission_id` keys, lifecycle stages (`provisional` vs. `finalized`), domain topic mappings, and concept arrays (`concepts_demonstrated`, `concepts_partial`, `concepts_missing`).

### Verification & Mutual Contract:
- **Producer:** `syncC3AssessmentToC1` (Component 3).
- **Consumer:** `backend/src/modules/c1/services/eventService.js:71`.
- **Consumer Logic:** C1 filters out `lifecycle_stage === 'provisional'` during risk calculations. Only `lifecycle_stage === 'finalized'` triggers forgetting curve updates and GBDT risk prediction.

### Actionable Next Steps for C1 Owner:
1. **Frontend Class Insights Display:** Ensure that finalized C3 assessments are reflected in the lecturer Class Insights view (`ClassInsights.jsx`), specifically updating class-wide topic averages for `sa_patterns_styles` and `ds_components_formats`.
2. **Concept-Level Remediation:** Utilize C3's `concepts_missing` array to highlight granular knowledge gaps on the student's `TopicInsightsPage.jsx`.

---

## 2. Handoff for Component 2 Owner (Exam Intelligence)

### Current Integration Status: 🟡 **CONTRACT DEFINED; RUNTIME PENDING C2 UI**
The formal data interchange specification between C2 and C3 is documented in `backend/src/integration/c2-c3/README.md`. Component 3's Batch Marking Studio (`/lecturer/c3/batch`) is designed to consume structured question definitions, multi-criterion rubrics, and answer keys directly.

### Actionable Next Steps for C2 Owner:
1. **Question Export Endpoint:** Implement an endpoint in C2 (e.g., `GET /api/v1/c2/questions/:id/export-c3`) that serializes C2's structured past-paper questions into the standard C3 rubric format:
   ```json
   {
     "question_id": "SE3010-2023-Q01",
     "question_text": "...",
     "max_marks": 4.0,
     "rubric": {
       "rubric_id": "RUB-01",
       "criteria": [
         {
           "criterion_id": "crit_1",
           "description": "...",
           "max_marks": 2.0,
           "scoring_levels": [...]
         }
       ]
     }
   }
   ```
2. **Direct Dispatch Button:** On C2's question inspection UI, add a button `"Send to C3 Batch Marking Studio"`, redirecting the lecturer to `/lecturer/c3/batch?preset=SE3010-2023-Q01` with pre-filled question and rubric metadata.

---

## 3. Handoff for Component 4 Owner (Adaptive Learning Paths)

### Current Integration Status: ❌ **DEFERRED / SKELETONS ONLY**
Component 4 currently consists of directory skeletons in `ai-services/c4/` and placeholder routes in `frontend/src/pages/ComingSoon.jsx`.

### Actionable Next Steps for C4 Owner:
1. **Initialize Core AI Service:** Implement the reinforcement-learning service in `ai-services/c4/app/main.py`.
2. **Consume Concept Gaps:** Define an ingestion endpoint (e.g., `POST /api/v1/c4/study-plan/generate`) that accepts student learning states from C1 and diagnostic concept gaps (`concepts_missing`) from C3.
3. **Adaptive Path UI:** Replace the `ComingSoon` placeholder at `/c4` and `/lecturer/c4` with an interactive study path recommendation view.

---

## 4. Handoff for Shared CCKG Owner / Group Lead

### Current Integration Status: ❌ **PROPOSED ARCHITECTURE ONLY**
Neo4j is provisioned in `docker-compose.yml`, but no Cypher schemas, constraints, or application connection drivers exist in the repository.

### Actionable Next Steps for CCKG Owner / Group Lead:
1. **Assign Clear Ownership:** Formally assign CCKG implementation responsibility to a named team member or establish shared commit protocols.
2. **Define Cypher Ontology:** Create schema scripts in `database/neo4j/scripts/` defining node labels (`(:Module)`, `(:Topic)`, `(:Concept)`, `(:Question)`) and relationship types (`[:PREREQUISITE_OF]`, `[:COVERS_CONCEPT]`).
3. **Add Neo4j Driver to Node Backend:** Install `neo4j-driver` in `backend/package.json` and configure connection pooling in `backend/src/config/neo4j.js`.
