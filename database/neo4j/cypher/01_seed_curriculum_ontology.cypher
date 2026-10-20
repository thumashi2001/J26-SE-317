// ============================================================================
// AdaptiveLearnSE — Co-Evolving Curriculum Knowledge Graph (CCKG)
// Seed Script: Modules, Topics, Concepts, and Prerequisite Relationships
// Location: database/neo4j/cypher/01_seed_curriculum_ontology.cypher
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
MERGE (m1)-[:CONTAINS_TOPIC]->(t1_1)
MERGE (m1)-[:CONTAINS_TOPIC]->(t1_2)
MERGE (m2)-[:CONTAINS_TOPIC]->(t2_1)
MERGE (m2)-[:CONTAINS_TOPIC]->(t2_2)
MERGE (m3)-[:CONTAINS_TOPIC]->(t3_1)
MERGE (m3)-[:CONTAINS_TOPIC]->(t3_2)
MERGE (m4)-[:CONTAINS_TOPIC]->(t4_1);

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
MERGE (t1_1)-[:INTRODUCES_CONCEPT]->(c_coh)
MERGE (t1_1)-[:INTRODUCES_CONCEPT]->(c_coup)
MERGE (t1_2)-[:INTRODUCES_CONCEPT]->(c_micro)
MERGE (t3_1)-[:INTRODUCES_CONCEPT]->(c_stmt)
MERGE (t3_1)-[:INTRODUCES_CONCEPT]->(c_brnc)
MERGE (t3_1)-[:INTRODUCES_CONCEPT]->(c_adeq)
MERGE (t2_1)-[:INTRODUCES_CONCEPT]->(c_norm)
MERGE (t2_2)-[:INTRODUCES_CONCEPT]->(c_acid);

// 6. Prerequisite Relationships (Concept Dependencies)
MERGE (c_coh)-[:PREREQUISITE_OF]->(c_coup)
MERGE (c_coup)-[:PREREQUISITE_OF]->(c_micro)
MERGE (c_stmt)-[:PREREQUISITE_OF]->(c_brnc)
MERGE (c_brnc)-[:PREREQUISITE_OF]->(c_adeq);
