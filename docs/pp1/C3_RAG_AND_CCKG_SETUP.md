# AdaptiveLearnSE Component 3 — RAG & Shared CCKG Setup Guide
**Project:** AdaptiveLearnSE | **Component:** C3 (Automated Marking & Answer Analysis)  
**Researcher:** T. P. V. K. Edirisinghe (IT23227118)  
**Document Version:** 2.0.0 (PP1 Final Verified)

---

## 1. Architectural Overview

Component 3 integrates two distinct grounding mechanisms for research experiments and automated grading:
1. **Vector-RAG (Unstructured Document Grounding):** Retrieves relevant textual excerpts and slide citations from SLIIT Software Engineering course lecture materials using semantic vector similarity.
2. **GraphRAG / CCKG (Structured Knowledge Graph Grounding):** Traverses the **Co-Evolving Curriculum Knowledge Graph (CCKG)** to retrieve concept prerequisite chains, ontology hierarchies, and syllabus relationships.

```
                               ┌───────────────────────────┐
                               │   Student Submission      │
                               │   (Question + Answer)     │
                               └─────────────┬─────────────┘
                                             │
                      ┌──────────────────────┴──────────────────────┐
                      ▼                                             ▼
        ┌───────────────────────────┐                 ┌───────────────────────────┐
        │       Vector-RAG          │                 │     CCKG / GraphRAG       │
        │  (CurriculumVectorStore)  │                 │    (CCKGGraphAdapter)     │
        └─────────────┬─────────────┘                 └─────────────┬─────────────┘
                      │ Top-k Passages + Citations                  │ Prerequisite Closure
                      ▼                                             ▼
        ┌─────────────────────────────────────────────────────────────────────────┐
        │            Rubric-Aware Grading & Concept Diagnostic Engine             │
        └─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Shared CCKG Foundation in `database/neo4j/`

In collaboration with the research group, the authoritative CCKG schema and initial seed data have been implemented in the shared repository directory:

```
database/neo4j/
├── README.md                                      # Documentation & Cypher execution guide
├── schema/
│   └── 01_cckg_constraints.cypher                # Uniqueness constraints & text indexes
└── cypher/
    ├── 01_seed_curriculum_ontology.cypher        # Modules, topics, concepts & prerequisites
    └── 02_seed_assessment_mappings.cypher        # Exam questions, concept links & citations
```

### Node Labels & Schema Definition
| Node Label | Primary Key | Key Attributes |
| :--- | :--- | :--- |
| `:Module` | `module_id` | `title`, `credits`, `semester` (e.g. `SE3010`, `SE3020`, `SE3030`, `SE3040`) |
| `:SyllabusTopic` | `topic_id` | `name`, `week_number` (e.g. `TOPIC-SE3010-MOD`, `TOPIC-SE3030-COV`) |
| `:Concept` | `concept_id` | `name`, `description`, `bloom_level` (e.g. `high cohesion`, `statement coverage`) |
| `:Question` | `question_id` | `question_text`, `max_marks`, `question_type` |
| `:CurriculumResource` | `resource_id`| `title`, `citation`, `resource_type` (e.g. lecture slides, textbook) |

### Relationship Semantics
- `(:Module)-[:CONTAINS_TOPIC]->(:SyllabusTopic)`
- `(:SyllabusTopic)-[:COVERS_CONCEPT]->(:Concept)`
- `(:Concept)-[:PREREQUISITE_OF]->(:Concept)`: Represents directed dependency (e.g. `Statement Coverage` is a prerequisite of `Branch Coverage`).
- `(:Question)-[:EVALUATES_CONCEPT]->(:Concept)`: Connects exam questions to rubric concepts.
- `(:Concept)-[:CITED_IN]->(:CurriculumResource)`: Provides verifiable syllabus provenance.

---

## 3. CCKG Graph Adapter (`CCKGGraphAdapter`)

Located in `ai-services/c3/services/cckg/graph_adapter.py`.

### Dual-Mode Execution Architecture
1. **Live Neo4j Mode:** When a Neo4j instance is online at `bolt://127.0.0.1:7687`, the adapter executes live Cypher queries using the official `neo4j` Python driver.
2. **Deterministic In-Memory Fallback:** When Neo4j is offline (standard for CI or lightweight viva demos), the adapter automatically switches to a synchronized internal graph mirror without throwing errors or halting execution.

### Key GraphRAG Query Capabilities
- `get_concept(name)`: Retrieves concept definition, prerequisites, and citations.
- `get_prerequisite_closure(concepts)`: Traverses transitive multi-hop prerequisite dependencies via depth-first search.
- `retrieve_graphrag_context(question_id, concepts)`: Formats a complete GraphRAG prompt context string grounding rubric evaluation in curriculum dependencies.

---

## 4. Vector-RAG Curriculum Store (`CurriculumVectorStore`)

Located in `ai-services/c3/services/rag/vector_store.py`.

### Corpus Coverage
Indexes curated lecture excerpts across SLIIT Software Engineering modules:
- **SE3010:** High Cohesion, Loose Coupling, Dependency Inversion, Microservices Bounded Contexts.
- **SE3020:** Relational Normalization (1NF–3NF), ACID Properties & Distributed Transactions.
- **SE3030:** Statement Coverage vs Branch Coverage, Cyclomatic Complexity, MCDC Testing.
- **SE3040:** RESTful API Design & Stateless Architecture, React Component Lifecycle.

### Retrieval Pipeline
1. Input query (concatenation of question and student answer) is vectorized using TF-IDF bigrams.
2. Cosine similarity is computed against all curriculum passages.
3. Relevant passages above threshold (default `0.05`) are returned with slide-level citations.

---

## 5. Verification & Testing

Execute unit tests for both Vector-RAG and CCKG GraphRAG:
```bash
cd ADAPTIVE_LEARN_SE/ai-services/c3
& "..\..\..\.venv\Scripts\python.exe" -m pytest tests/unit/test_cckg_and_rag.py -v
```
All 12 unit tests pass, verifying initialization, passage retrieval, concept lookups, prerequisite traversal, and offline fallback behavior.
