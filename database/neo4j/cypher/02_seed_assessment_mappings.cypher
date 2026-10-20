// ============================================================================
// AdaptiveLearnSE — Co-Evolving Curriculum Knowledge Graph (CCKG)
// Seed Script: Questions, Curriculum Resources & GraphRAG Evidence Links
// Location: database/neo4j/cypher/02_seed_assessment_mappings.cypher
// ============================================================================

// 1. Assessment Questions (Sample Exam Questions from SE3010 and SE3030)
MERGE (q1:Question {
  question_id: "SE3010-Q01",
  code: "SE3010-Q01",
  text: "Explain the architectural significance of high cohesion and loose coupling in software design. Cite architectural patterns that promote them.",
  max_marks: 4.0,
  module_id: "SE3010"
})
MERGE (q2:Question {
  question_id: "DIAG-SE3010-001",
  code: "DIAG-SE3010-001",
  text: "Explain the difference between statement coverage and branch coverage in software testing, and explain why statement coverage alone may be insufficient.",
  max_marks: 10.0,
  module_id: "SE3030"
});

// 2. Curriculum Resources (Lecture Slides & Chapter Notes)
MERGE (r1:CurriculumResource {
  resource_id: "RES-SE3010-L03",
  title: "Lecture 03: Architectural Modularity & Clean Architecture",
  resource_type: "lecture_slide",
  module_id: "SE3010",
  citation: "SLIIT SE3010 Lecture 03 (Modularity), Slide 14-22"
})
MERGE (r2:CurriculumResource {
  resource_id: "RES-SE3030-L04",
  title: "Lecture 04: Control Flow Graph & Structural Coverage Testing",
  resource_type: "lecture_slide",
  module_id: "SE3030",
  citation: "SLIIT SE3030 Lecture 04 (White-Box Testing), Slide 08-19"
});

// 3. Connect Questions to Concepts They Evaluate
MATCH (q1:Question {question_id: "SE3010-Q01"}), (c1:Concept {concept_id: "C-COHESION"})
MERGE (q1)-[:EVALUATES_CONCEPT {weight: 0.5}]->(c1);

MATCH (q1:Question {question_id: "SE3010-Q01"}), (c2:Concept {concept_id: "C-COUPLING"})
MERGE (q1)-[:EVALUATES_CONCEPT {weight: 0.5}]->(c2);

MATCH (q2:Question {question_id: "DIAG-SE3010-001"}), (c3:Concept {concept_id: "C-STMT-COV"})
MERGE (q2)-[:EVALUATES_CONCEPT {weight: 0.3}]->(c3);

MATCH (q2:Question {question_id: "DIAG-SE3010-001"}), (c4:Concept {concept_id: "C-BRNC-COV"})
MERGE (q2)-[:EVALUATES_CONCEPT {weight: 0.4}]->(c4);

MATCH (q2:Question {question_id: "DIAG-SE3010-001"}), (c5:Concept {concept_id: "C-TEST-ADEQ"})
MERGE (q2)-[:EVALUATES_CONCEPT {weight: 0.3}]->(c5);

// 4. Connect Concepts to Curriculum Resources
MATCH (c1:Concept {concept_id: "C-COHESION"}), (r1:CurriculumResource {resource_id: "RES-SE3010-L03"})
MERGE (c1)-[:CITED_IN]->(r1);

MATCH (c2:Concept {concept_id: "C-COUPLING"}), (r1:CurriculumResource {resource_id: "RES-SE3010-L03"})
MERGE (c2)-[:CITED_IN]->(r1);

MATCH (c3:Concept {concept_id: "C-STMT-COV"}), (r2:CurriculumResource {resource_id: "RES-SE3030-L04"})
MERGE (c3)-[:CITED_IN]->(r2);

MATCH (c4:Concept {concept_id: "C-BRNC-COV"}), (r2:CurriculumResource {resource_id: "RES-SE3030-L04"})
MERGE (c4)-[:CITED_IN]->(r2);
