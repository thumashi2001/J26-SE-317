// ============================================================================
// AdaptiveLearnSE — Co-Evolving Curriculum Knowledge Graph (CCKG)
// Shared Schema Constraints & Uniqueness Indexes
// Database: Neo4j 5.x
// Location: database/neo4j/schema/01_cckg_constraints.cypher
// ============================================================================

// 1. Module Constraints
CREATE CONSTRAINT cckg_module_id_unique IF NOT EXISTS
FOR (m:Module) REQUIRE m.module_id IS UNIQUE;

// 2. Syllabus Topic Constraints
CREATE CONSTRAINT cckg_topic_id_unique IF NOT EXISTS
FOR (t:SyllabusTopic) REQUIRE t.topic_id IS UNIQUE;

// 3. Learning Concept Constraints
CREATE CONSTRAINT cckg_concept_id_unique IF NOT EXISTS
FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE;

// 4. Assessment Question Constraints
CREATE CONSTRAINT cckg_question_id_unique IF NOT EXISTS
FOR (q:Question) REQUIRE q.question_id IS UNIQUE;

// 5. Curriculum Resource Constraints
CREATE CONSTRAINT cckg_resource_id_unique IF NOT EXISTS
FOR (r:CurriculumResource) REQUIRE r.resource_id IS UNIQUE;

// 6. Text indexes for fast lexical and GraphRAG search
CREATE INDEX cckg_concept_name_idx IF NOT EXISTS
FOR (c:Concept) ON (c.name);

CREATE INDEX cckg_topic_name_idx IF NOT EXISTS
FOR (t:SyllabusTopic) ON (t.name);
