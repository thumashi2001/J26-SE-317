# AdaptiveLearnSE — Co-Evolving Curriculum Knowledge Graph (CCKG)

The **Co-Evolving Curriculum Knowledge Graph (CCKG)** provides the shared conceptual backbone for the AdaptiveLearnSE ecosystem:
- **Component 1 (Cognitive Digital Twin):** Tracks student concept mastery, prerequisite readiness, and personalized learning paths.
- **Component 2 (Exam Intelligence):** Maps exam past-paper question patterns, syllabus coverage, and cognitive complexity.
- **Component 3 (Automated Assessment):** Performs GraphRAG retrieval of prerequisite concepts, syllabus definitions, and curriculum citations to ground rubric marking and concept mind maps.
- **Component 4 (Adaptive Learning Path):** Traverses prerequisite chains to recommend remedial materials.

---

## 1. Directory Structure

```
database/neo4j/
├── README.md                                 # Architecture, schema, and usage guide
├── schema/
│   └── 01_cckg_constraints.cypher           # Uniqueness constraints and text indexes
└── cypher/
    ├── 01_seed_curriculum_ontology.cypher    # Modules, Topics, Concepts, and Prerequisite edges
    └── 02_seed_assessment_mappings.cypher    # Questions, CurriculumResources, and Evidence edges
```

---

## 2. Graph Data Model & Ontology

```
 (:Module) ──[:CONTAINS_TOPIC]──> (:SyllabusTopic) ──[:INTRODUCES_CONCEPT]──> (:Concept)
                                                                                  │
  (:Question) ──[:EVALUATES_CONCEPT]──────────────────────────────────────────────┤
                                                                                  │
                                                      [:PREREQUISITE_OF]─────────┘
                                                              │
                                                              ▼
                                                   (:Concept) ──[:CITED_IN]──> (:CurriculumResource)
```

### Core Node Labels
1. **`:Module`**: Course module units (`SE3010`, `SE3020`, `SE3030`, `SE3040`).
2. **`:SyllabusTopic`**: Top-level curricular subject areas within a module.
3. **`:Concept`**: Granular software engineering learning concepts (`high cohesion`, `loose coupling`, `statement coverage`, `branch coverage`).
4. **`:Question`**: Assessment examination questions.
5. **`:CurriculumResource`**: Lecture slide decks, textbook chapters, and syllabus references.

### Core Relationship Types
- `(:Module)-[:CONTAINS_TOPIC]->(:SyllabusTopic)`
- `(:SyllabusTopic)-[:INTRODUCES_CONCEPT]->(:Concept)`
- `(:Concept)-[:PREREQUISITE_OF]->(:Concept)`
- `(:Question)-[:EVALUATES_CONCEPT {weight}]->(:Concept)`
- `(:Concept)-[:CITED_IN]->(:CurriculumResource)`

---

## 3. Initializing & Seeding Neo4j

### Using Docker Compose
Neo4j is provisioned in `docker-compose.yml` on ports `7474` (HTTP) and `7687` (Bolt):
```bash
docker compose up -d neo4j
```

### Executing Cypher Scripts
Connect via `cypher-shell` or Neo4j Browser (`http://localhost:7474`):
```bash
cypher-shell -u neo4j -p change-me-in-development -f schema/01_cckg_constraints.cypher
cypher-shell -u neo4j -p change-me-in-development -f cypher/01_seed_curriculum_ontology.cypher
cypher-shell -u neo4j -p change-me-in-development -f cypher/02_seed_assessment_mappings.cypher
```

---

## 4. Component 3 GraphRAG Integration
Component 3 accesses the CCKG via the graph adapter service at [`ai-services/c3/services/cckg/`](../../ai-services/c3/services/cckg/).
When Neo4j is offline or in standalone test environments, the adapter seamlessly falls back to a deterministic, in-memory ontology store to ensure 100% test reproducibility.
