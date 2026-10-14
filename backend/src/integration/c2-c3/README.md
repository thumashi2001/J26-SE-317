# C2 → C3 Integration Contract & Data Interchange Specification

## 1. Overview & Architectural Boundary

In the **AdaptiveLearnSE** architecture:
- **Component 2 (Exam Intelligence):** Ingests, parses, and structures examination papers and past papers into standardized question records and topic taxonomies.
- **Component 3 (Automated Marking & Answer Analysis):** Consumes structured question definitions, rubrics, and student answers to execute the F1–F4 evaluation pipeline (Answer Preprocessing, Rubric-Aware Marking, Explainable Feedback, Mind Map Generation) followed by Human-In-The-Loop Lecturer Verification.

```
+-------------------------------------------------------+
| Component 2 (Exam Intelligence)                       |
|   Past Paper PDFs -> Structured Question Repository   |
+---------------------------+---------------------------+
                            |
                            | (Question Metadata + Rubrics)
                            v
+-------------------------------------------------------+
| Component 3 (Automated Marking Pipeline)              |
|   F1: Answer Processing & Concept Matching            |
|   F2: Rubric-Aware Marking Engine                     |
|   F3: Evidence-Grounded Feedback                      |
|   F4: Concept-Based Mind Map                          |
|   Lecturer Verification & C1 Sync                     |
+-------------------------------------------------------+
```

---

## 2. Shared Data Contract

### 2.1 Request Payload (C2 Assessment Context -> C3 Assessment Engine)

When an assessment session evaluates a student answer for a question sourced from C2, the payload matches C3's Pydantic schema (`ai-services/c3/app/schemas/assessment.py`):

```json
{
  "assessment_id": "IT3020-2023-EXAM-01",
  "question_id": "IT3020-2023-Q1-a",
  "paper_id": "IT3020-2023-a1b2c3d4",
  "module_code": "IT3020",
  "module_name": "Distributed Systems",
  "question_number": 1,
  "part_id": "(a)",
  "question_text": "Explain the ACID properties in database transaction management.",
  "context": "Assume a distributed relational banking database system.",
  "topic": "ds_components_formats",
  "answer_type": "short",
  "max_marks": 10.0,
  "reference_answer": "Atomicity ensures all-or-nothing execution. Consistency preserves database invariants. Isolation guarantees serializable execution. Durability guarantees committed transactions survive failures.",
  "expected_concepts": [
    "atomicity",
    "consistency",
    "isolation",
    "durability"
  ],
  "rubric": {
    "rubric_id": "RUBRIC-ACID-001",
    "title": "ACID Properties Evaluation Rubric",
    "criteria": [
      {
        "criterion_id": "crit_atomicity_consistency",
        "description": "Understanding and definition of Atomicity and Consistency",
        "max_marks": 5.0,
        "required_concepts": ["atomicity", "consistency"],
        "scoring_levels": [
          {
            "level_id": "level_full",
            "label": "Full Understanding",
            "mark": 5.0,
            "descriptor": "Accurately defines both Atomicity and Consistency with transaction examples.",
            "required_concepts": ["atomicity", "consistency"]
          },
          {
            "level_id": "level_partial",
            "label": "Partial Understanding",
            "mark": 2.5,
            "descriptor": "Defines either Atomicity or Consistency, but omits key aspects.",
            "required_concepts": ["atomicity"]
          },
          {
            "level_id": "level_none",
            "label": "No Demonstration",
            "mark": 0.0,
            "descriptor": "Fails to explain atomicity or consistency.",
            "required_concepts": []
          }
        ]
      },
      {
        "criterion_id": "crit_isolation_durability",
        "description": "Understanding of Isolation and Durability",
        "max_marks": 5.0,
        "required_concepts": ["isolation", "durability"],
        "scoring_levels": [
          {
            "level_id": "level_full",
            "label": "Full Understanding",
            "mark": 5.0,
            "descriptor": "Accurately defines Isolation and Durability with persistence guarantees.",
            "required_concepts": ["isolation", "durability"]
          },
          {
            "level_id": "level_partial",
            "label": "Partial Understanding",
            "mark": 2.5,
            "descriptor": "Defines either Isolation or Durability.",
            "required_concepts": ["durability"]
          },
          {
            "level_id": "level_none",
            "label": "No Demonstration",
            "mark": 0.0,
            "descriptor": "Fails to explain isolation or durability.",
            "required_concepts": []
          }
        ]
      }
    ]
  },
  "student_id": "IT10000001",
  "student_answer": "Atomicity means that transactions are all or nothing. Consistency ensures that database constraints are not violated."
}
```

### 2.2 Response Payload (C3 Assessment Output)

```json
{
  "question_id": "IT3020-2023-Q1-a",
  "total_awarded_marks": 5.0,
  "total_possible_marks": 10.0,
  "percentage": 50.0,
  "marking": {
    "question_id": "IT3020-2023-Q1-a",
    "criteria_results": [
      {
        "criterion_id": "crit_atomicity_consistency",
        "criterion_description": "Understanding and definition of Atomicity and Consistency",
        "selected_level_id": "level_full",
        "selected_level_label": "Full Understanding",
        "rubric_descriptor": "Accurately defines both Atomicity and Consistency with transaction examples.",
        "awarded_mark": 5.0,
        "max_marks": 5.0,
        "evidence_sentence_ids": [1, 2],
        "supporting_concepts": ["atomicity", "consistency"],
        "explanation": "Awarded 5.0/5.0: The response demonstrated all required concepts ('atomicity', 'consistency') supported by sentences 1, 2.",
        "warnings": []
      },
      {
        "criterion_id": "crit_isolation_durability",
        "criterion_description": "Understanding of Isolation and Durability",
        "selected_level_id": "level_none",
        "selected_level_label": "No Demonstration",
        "rubric_descriptor": "Fails to explain isolation or durability.",
        "awarded_mark": 0.0,
        "max_marks": 5.0,
        "evidence_sentence_ids": [],
        "supporting_concepts": [],
        "explanation": "Awarded 0.0/5.0: Insufficient evidence for isolation or durability.",
        "warnings": []
      }
    ],
    "total_awarded_marks": 5.0,
    "total_possible_marks": 10.0,
    "percentage": 50.0,
    "overall_explanation": "Evaluated 2 criteria. Total score: 5.0/10.0 (50.0%).",
    "warnings": [],
    "marking_version": "f2-rubric-v1"
  },
  "analysis": {
    "question_id": "IT3020-2023-Q1-a",
    "normalized_answer": "atomicity means that transactions are all or nothing. consistency ensures that database constraints are not violated.",
    "sentence_count": 2,
    "token_count": 18,
    "sentences": [
      { "sentence_id": 1, "text": "Atomicity means that transactions are all or nothing." },
      { "sentence_id": 2, "text": "Consistency ensures that database constraints are not violated." }
    ],
    "reference_similarity": 0.62,
    "concept_matches": [
      { "concept": "atomicity", "status": "demonstrated", "overlap_score": 1.0, "evidence_sentence_ids": [1] },
      { "concept": "consistency", "status": "demonstrated", "overlap_score": 1.0, "evidence_sentence_ids": [2] },
      { "concept": "isolation", "status": "not_demonstrated", "overlap_score": 0.0, "evidence_sentence_ids": [] },
      { "concept": "durability", "status": "not_demonstrated", "overlap_score": 0.0, "evidence_sentence_ids": [] }
    ],
    "warnings": [],
    "analysis_version": "baseline-v1"
  },
  "feedback": {
    "question_id": "IT3020-2023-Q1-a",
    "awarded_mark": 5.0,
    "max_marks": 10.0,
    "percentage": 50.0,
    "strengths": [
      "Demonstrated accurate understanding of 'atomicity' in sentence 1.",
      "Demonstrated accurate understanding of 'consistency' in sentence 2."
    ],
    "areas_for_improvement": [
      "Missing key concepts: 'isolation', 'durability'. Explain persistence and concurrency control to achieve full marks."
    ],
    "guidance": "Review transaction isolation levels (Read Committed, Serializable) and Write-Ahead Logging (WAL) for durability.",
    "criterion_feedback": [
      {
        "criterion_id": "crit_atomicity_consistency",
        "awarded_mark": 5.0,
        "max_marks": 5.0,
        "feedback_text": "Excellent explanation of atomicity and consistency."
      },
      {
        "criterion_id": "crit_isolation_durability",
        "awarded_mark": 0.0,
        "max_marks": 5.0,
        "feedback_text": "Neither isolation nor durability was addressed in the response."
      }
    ],
    "feedback_version": "f3-explainable-v1"
  },
  "mindmap": {
    "root_concept": "ACID Properties",
    "nodes": [
      { "id": "node_root", "label": "ACID Properties", "status": "partial", "level": 0 },
      { "id": "node_atomicity", "label": "Atomicity", "status": "demonstrated", "level": 1 },
      { "id": "node_consistency", "label": "Consistency", "status": "demonstrated", "level": 1 },
      { "id": "node_isolation", "label": "Isolation", "status": "missing", "level": 1 },
      { "id": "node_durability", "label": "Durability", "status": "missing", "level": 1 }
    ],
    "relationships": [
      { "source": "node_root", "target": "node_atomicity", "label": "includes" },
      { "source": "node_root", "target": "node_consistency", "label": "includes" },
      { "source": "node_root", "target": "node_isolation", "label": "includes" },
      { "source": "node_root", "target": "node_durability", "label": "includes" }
    ],
    "mindmap_version": "f4-mindmap-v1"
  },
  "warnings": [],
  "pipeline_version": "integrated-v1"
}
```

---

## 3. Contract Status & Open Decisions

| Item | Current C2 Status | Current C3 Status | Status & Decision |
| :--- | :--- | :--- | :--- |
| **Question Extraction** | Implemented via `build_question_repository()` (`ai-services/c2/services/question_repository.py`) | Ingests `question_id`, `question_text`, `context`, `marks`, `topic` | **Aligned**: C3 directly maps `question_id` and `question_text`. |
| **Domain Topics** | Classified via `services/topic_taxonomy.py` (e.g. `ds_components_formats`, `sa_patterns_styles`) | Mapped in `submissionService.js` and `syncC3AssessmentToC1` | **Aligned**: Topics conform to the 8-module taxonomy. |
| **Rubric Extraction** | C2 currently parses question mark totals (`marks: float`). Rubric criteria breakdown (scoring levels, descriptors) is not yet extracted from raw examination PDFs by C2. | C3 requires structured `rubric` criteria with scoring levels. Preset rubrics exist for standard questions. | **Decision Required**: When C2 exposes dynamic question papers without explicit multi-level rubric criteria, C3 will fall back to its structured single-criterion or topic-standard default rubric until C2 introduces marking-scheme PDF parsing. |
| **OCR / Scanned Answers** | C2 operates on electronic examination PDFs. | C3 operates on typed natural language answers. Scanned answer sheets explicitly reject with HTTP 400. | **Aligned**: No unsupported fake OCR claimed. |
