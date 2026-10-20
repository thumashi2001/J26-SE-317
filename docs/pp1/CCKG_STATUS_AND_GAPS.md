# AdaptiveLearnSE — Co-Evolving Curriculum Knowledge Graph (CCKG) Status & Gap Audit

**Document Version:** 2.0.0 (Authoritative PP1 Architectural Audit)  
**Target Milestone:** Project Performance 1 (PP1) / Viva Evaluation (22, 23, and 26 October 2026)  
**Evaluator:** Component 3 Engineer  
**Overall CCKG Status:** ❌ **PROPOSED ARCHITECTURE ONLY (Unimplemented)**  

---

## 1. Executive Summary & Honest Classification

In project proposals and architecture slides, the **Co-Evolving Curriculum Knowledge Graph (CCKG)** is envisioned as the shared conceptual spine connecting syllabus modules, topics, learning concepts, past-paper exam questions, and student learning paths.

Following a comprehensive audit of the complete codebase, Git history, Docker configuration, and service dependencies:
- **Formal Status Classification:** **PROPOSED ARCHITECTURE ONLY**
- **Ownership:** **UNASSIGNED / REQUIRES CONFIRMATION**
- **Operational Reality:** While Docker Compose declares a container for Neo4j (`neo4j:5`), **no Neo4j driver is installed, no connection code exists, no Cypher schema or migration scripts exist, and no application component currently executes queries against Neo4j**.

---

## 2. Ten-Dimension Technical Audit

| Dimension | Audit Check | Observed Codebase Reality | Status |
| :--- | :--- | :--- | :--- |
| **1. Graph Schema & Entities** | Are node types (`:Module`, `:Topic`, `:Concept`, `:Question`) defined? | No Cypher schema, graph DDL, or entity definitions exist anywhere in the repository. | ❌ **Missing** |
| **2. Relationship Types** | Are semantic relationships (`:PREREQUISITE_OF`, `:CONTAINS`, `:EVALUATES`) defined? | No relationship models or ontology specifications exist in code. | ❌ **Missing** |
| **3. Constraints & Indexes** | Are uniqueness constraints or schema indexes configured? | No `.cypher` constraint files exist. | ❌ **Missing** |
| **4. Data Ingestion & Seeding** | Is there seed data, a synthetic graph generator, or a curriculum loader? | `database/neo4j/README.md` explicitly states: *"No graph schema or Cypher scripts are implemented yet."* | ❌ **Missing** |
| **5. Neo4j Connection & Config** | Is Neo4j connection code configured in Express or Python? | `backend/package.json` does **not** include `neo4j-driver`. `ai-services/*/requirements.txt` do **not** include `neo4j` or `py2neo`. | ❌ **Missing** |
| **6. Query Services & APIs** | Do RESTful API endpoints exist to query or mutate the graph? | No graph controller, service, or repository exists in `backend/` or `ai-services/`. | ❌ **Missing** |
| **7. Curriculum Coverage** | Are SLIIT SE3010–SE3040 course topics mapped into a graph? | Course topics are represented as flat JavaScript arrays in C1 (`data/content/*.js`) and CSVs in C3, not in Neo4j. | ❌ **Missing** |
| **8. Graph Persistence** | Is live data written to or updated in Neo4j during user sessions? | Zero runtime writes to Neo4j occur during any student or lecturer workflow. | ❌ **Missing** |
| **9. Component Consumption** | Does C1, C2, C3, or C4 consume graph data in real workflows? | No component makes graph queries. C3's Condition D (Neo4j GraphRAG) is accurately documented as deferred. | ❌ **Missing** |
| **10. Automated Tests** | Are graph queries, schema constraints, or graph traversals covered by unit tests? | Zero tests exist for Neo4j across backend Node.js and Python pytest suites. | ❌ **Missing** |

---

## 3. CCKG Evidence in the Codebase

1. **`docker-compose.yml` (Lines 10–23):**
   ```yaml
   neo4j:
     image: neo4j:5
     container_name: adaptivelearnse-neo4j
     ports:
       - "7474:7474"
       - "7687:7687"
     environment:
       NEO4J_AUTH: neo4j/change-me-in-development
     volumes:
       - neo4j_data:/data
   ```
   *Analysis:* Provisions a stock Neo4j 5 community image. It provides the database infrastructure container, but contains no custom application logic or preloaded graph state.
2. **`database/neo4j/README.md` (Lines 1–6):**
   ```markdown
   # Neo4j Curriculum Knowledge Graph

   Neo4j is intended for the shared Curriculum Knowledge Graph (CCKG), including curriculum concepts and their relationships across the integrated ecosystem.

   No graph schema or Cypher scripts are implemented yet.
   ```
   *Analysis:* Truthfully and explicitly documents that CCKG remains unimplemented.

---

## 4. Candidate Viva Defense Position on CCKG

During the PP1 viva, examiners may ask about Neo4j or the CCKG:

> **Examiner Question:** *"You show a Curriculum Concept Knowledge Graph (CCKG) using Neo4j in your architecture slides. Can you show me the live Neo4j database or Cypher queries running right now?"*
>
> **Defensible Candidate Response:**  
> *"In our high-level architecture, CCKG is designed as the shared curriculum ontology connecting syllabus concepts across all four components, and Neo4j is provisioned in our Docker Compose infrastructure. However, for this Project Performance 1 (PP1) milestone, CCKG remains classified as **Proposed Architecture**. No Cypher schema, graph loader, or database driver has been implemented yet, and ownership across the four group members is currently unassigned.*  
> *For my individual Component 3 responsibility, I implemented and evaluated Condition E—a deterministic concept evidence and rubric-aware engine using hierarchical Directed Acyclic Graphs (DAGs) rendered directly via SVG. Condition D, which incorporates Neo4j GraphRAG, is documented as a planned research condition for post-PP1 Phase 4 once the shared CCKG ontology is formally implemented by the team."*

---

## 5. Actionable Roadmap for Post-PP1 Group Work

1. **Clarify Ownership:** The group supervisor and team lead must assign formal ownership of the CCKG to a specific teammate or define joint milestones.
2. **Define Cypher Schema:** Implement `database/neo4j/schema.cypher` creating indexes and node labels.
3. **Ingest Curriculum Data:** Write a Python ingestion script in `database/neo4j/seed_curriculum.py` translating SLIIT SE course specifications into nodes and prerequisite edges.
4. **Connect Node.js Backend:** Install `neo4j-driver` and expose a read-only endpoint `/api/v1/cckg/concepts/:topic`.
