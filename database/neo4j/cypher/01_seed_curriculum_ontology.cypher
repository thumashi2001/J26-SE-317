// ============================================================================
// AdaptiveLearnSE — Co-Evolving Curriculum Knowledge Graph (CCKG)
// Seed Script: Modules, Topics, Concepts, and Prerequisite Relationships
// Location: database/neo4j/cypher/01_seed_curriculum_ontology.cypher
//
// NOTE: cypher-shell runs each ";"-terminated statement separately, so variables are NOT shared
// between statements. Relationship sections therefore MATCH their endpoints by id (an earlier
// version re-used unbound variables and created empty unlabelled nodes).
// ============================================================================

// 1. Core Modules (SLIIT Year 3 Curriculum)
MERGE (m1:Module {module_id: "SE3010", code: "SE3010", title: "Software Architecture & Design Patterns", credits: 4})
MERGE (m2:Module {module_id: "SE3020", code: "SE3020", title: "Database Systems & Distributed Storage", credits: 4})
MERGE (m3:Module {module_id: "SE3030", code: "SE3030", title: "Software Quality Assurance & Metrics", credits: 4})
MERGE (m4:Module {module_id: "SE3040", code: "SE3040", title: "Enterprise Application Development", credits: 4});

// 2. Syllabus Topics
MERGE (t1_1:SyllabusTopic {topic_id: "TOPIC-SE3010-MOD", name: "Modular Abstraction & Decomposition", module_id: "SE3010"})
MERGE (t1_2:SyllabusTopic {topic_id: "TOPIC-SE3010-PAT", name: "Architectural Patterns & Styles", module_id: "SE3010"})
MERGE (t2_1:SyllabusTopic {topic_id: "TOPIC-SE3020-NORM", name: "Relational Schema Normalization", module_id: "SE3020"})
MERGE (t2_2:SyllabusTopic {topic_id: "TOPIC-SE3020-TRAN", name: "Transaction Isolation & ACID Properties", module_id: "SE3020"})
MERGE (t3_1:SyllabusTopic {topic_id: "TOPIC-SE3030-COV", name: "Structural Coverage & Control Flow Testing", module_id: "SE3030"})
MERGE (t3_2:SyllabusTopic {topic_id: "TOPIC-SE3030-MET", name: "Software Metrics & Quality Standards", module_id: "SE3030"})
MERGE (t4_1:SyllabusTopic {topic_id: "TOPIC-SE3040-API", name: "RESTful Service Design & Microservices", module_id: "SE3040"});

// 3. Link Modules to Topics
MATCH (t:SyllabusTopic)
MATCH (m:Module {module_id: t.module_id})
MERGE (m)-[:CONTAINS_TOPIC]->(t);

// 4. Learning Concepts
MERGE (c_coh:Concept {concept_id: "C-COHESION", name: "high cohesion", description: "Internal module coherence where all elements collaborate to perform a single well-defined task."})
MERGE (c_coup:Concept {concept_id: "C-COUPLING", name: "loose coupling", description: "Minimizing inter-module dependencies to permit independent evolution and testing."})
MERGE (c_micro:Concept {concept_id: "C-MICROSERVICES", name: "microservices", description: "Distributed architectural pattern organizing applications into autonomous, independently deployable services."})
MERGE (c_stmt:Concept {concept_id: "C-STMT-COV", name: "statement coverage", description: "Metric measuring the proportion of executable statements executed by a test suite."})
MERGE (c_brnc:Concept {concept_id: "C-BRNC-COV", name: "branch coverage", description: "Metric measuring whether each decision branch outcome (true/false) has been exercised."})
MERGE (c_adeq:Concept {concept_id: "C-TEST-ADEQ", name: "test adequacy", description: "Criteria determining whether test suites sufficiently exercise program logic and failure modes."})
MERGE (c_norm:Concept {concept_id: "C-NORMALIZATION", name: "relational normalization", description: "Systematic decomposition of relations to eliminate anomalies and redundancy (1NF, 2NF, 3NF, BCNF)."})
MERGE (c_acid:Concept {concept_id: "C-ACID", name: "acid transactions", description: "Database transaction guarantees: Atomicity, Consistency, Isolation, and Durability."});

// 5. Link Topics to Concepts
UNWIND [
  ["TOPIC-SE3010-MOD", "C-COHESION"],
  ["TOPIC-SE3010-MOD", "C-COUPLING"],
  ["TOPIC-SE3010-PAT", "C-MICROSERVICES"],
  ["TOPIC-SE3030-COV", "C-STMT-COV"],
  ["TOPIC-SE3030-COV", "C-BRNC-COV"],
  ["TOPIC-SE3030-COV", "C-TEST-ADEQ"],
  ["TOPIC-SE3020-NORM", "C-NORMALIZATION"],
  ["TOPIC-SE3020-TRAN", "C-ACID"]
] AS pair
MATCH (t:SyllabusTopic {topic_id: pair[0]})
MATCH (c:Concept {concept_id: pair[1]})
MERGE (t)-[:INTRODUCES_CONCEPT]->(c);

// 6. Prerequisite Relationships (Concept Dependencies)
UNWIND [
  ["C-COHESION", "C-COUPLING"],
  ["C-COUPLING", "C-MICROSERVICES"],
  ["C-STMT-COV", "C-BRNC-COV"],
  ["C-BRNC-COV", "C-TEST-ADEQ"]
] AS pair
MATCH (a:Concept {concept_id: pair[0]})
MATCH (b:Concept {concept_id: pair[1]})
MERGE (a)-[:PREREQUISITE_OF]->(b);
