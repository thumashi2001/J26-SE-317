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

_Generated from the real service (`POST /c3/assess` with the request above, semantic layer off, no AI estimate) on 2026-10-27, and checked by `tests/integration/test_c2_c3_contract.py` against `AssessmentResponse`. Fields added since: `analysis.concept_matches[].contradicted/conflicting/negated_sentence_ids`, `analysis.contradiction_check`, `feedback.criteria_feedback[].contradicted_concepts`._

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
        "evidence_sentence_ids": [
          1,
          2
        ],
        "supporting_concepts": [
          "atomicity",
          "consistency"
        ],
        "explanation": "Selected rubric level 'Full Understanding' (5 marks) for criterion crit_atomicity_consistency. Supporting concepts: atomicity, consistency. Evidence sentence IDs: 1, 2. The proposed result is based on the rubric requirements and deterministic lexical evidence.",
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
        "explanation": "Selected rubric level 'No Demonstration' (0 marks) for criterion crit_isolation_durability. No higher scoring level was supported by the available deterministic lexical evidence.",
        "warnings": [
          "No positive scoring level was supported for criterion crit_isolation_durability; selected lowest rubric level 'level_none'."
        ]
      }
    ],
    "total_awarded_marks": 5.0,
    "total_possible_marks": 10.0,
    "percentage": 50.0,
    "overall_explanation": "The overall proposed mark is derived by summing the rubric-defined criterion marks: crit_atomicity_consistency=5/5; crit_isolation_durability=0/5. It is a deterministic baseline proposal, not a claim of factual correctness or final lecturer judgment.",
    "warnings": [
      "No positive scoring level was supported for criterion crit_isolation_durability; selected lowest rubric level 'level_none'."
    ],
    "marking_version": "baseline-v1"
  },
  "analysis": {
    "question_id": "IT3020-2023-Q1-a",
    "normalized_answer": "Atomicity means that transactions are all or nothing. Consistency ensures that database constraints are not violated.",
    "sentence_count": 2,
    "token_count": 16,
    "sentences": [
      {
        "sentence_id": 1,
        "text": "Atomicity means that transactions are all or nothing."
      },
      {
        "sentence_id": 2,
        "text": "Consistency ensures that database constraints are not violated."
      }
    ],
    "reference_similarity": 0.23836564731139803,
    "concept_matches": [
      {
        "concept": "atomicity",
        "status": "demonstrated",
        "overlap_score": 1.0,
        "evidence_sentence_ids": [
          1
        ],
        "match_method": "lexical",
        "semantic_score": null,
        "contradicted": false,
        "conflicting": false,
        "negated_sentence_ids": []
      },
      {
        "concept": "consistency",
        "status": "demonstrated",
        "overlap_score": 1.0,
        "evidence_sentence_ids": [
          2
        ],
        "match_method": "lexical",
        "semantic_score": null,
        "contradicted": false,
        "conflicting": false,
        "negated_sentence_ids": []
      },
      {
        "concept": "isolation",
        "status": "not_demonstrated",
        "overlap_score": 0.0,
        "evidence_sentence_ids": [],
        "match_method": "lexical",
        "semantic_score": null,
        "contradicted": false,
        "conflicting": false,
        "negated_sentence_ids": []
      },
      {
        "concept": "durability",
        "status": "not_demonstrated",
        "overlap_score": 0.0,
        "evidence_sentence_ids": [],
        "match_method": "lexical",
        "semantic_score": null,
        "contradicted": false,
        "conflicting": false,
        "negated_sentence_ids": []
      }
    ],
    "warnings": [],
    "analysis_version": "baseline-v1",
    "contradiction_check": "negation-cue-v1"
  },
  "feedback": {
    "question_id": "IT3020-2023-Q1-a",
    "criteria_feedback": [
      {
        "criterion_id": "crit_atomicity_consistency",
        "criterion_description": "Understanding and definition of Atomicity and Consistency",
        "max_marks": 5.0,
        "selected_level_id": "level_full",
        "selected_level_descriptor": "Accurately defines both Atomicity and Consistency with transaction examples.",
        "awarded_mark": 5.0,
        "evidence_sentence_ids": [
          1,
          2
        ],
        "supporting_concepts": [
          "atomicity",
          "consistency"
        ],
        "demonstrated_concepts": [
          "atomicity",
          "consistency"
        ],
        "partial_concepts": [],
        "missing_concepts": [],
        "contradicted_concepts": [],
        "next_level_improvements": [],
        "explanation": "Criterion crit_atomicity_consistency received the proposed mark 5/5 at rubric level 'level_full'. Supporting concepts: atomicity, consistency. Student evidence is referenced by sentence IDs: 1, 2. This explanation reports the existing rubric result and does not create a new mark.",
        "strengths": [
          "Demonstrated concept supported by the answer: atomicity.",
          "Demonstrated concept supported by the answer: consistency."
        ],
        "missing_or_partial_areas": [],
        "improvement_suggestions": [
          "This criterion is at its top rubric level (5/5); keep this standard.",
          "The concepts found in your wording were 'atomicity', 'consistency'.",
          "To go further, support your points with a specific example and say why it matters."
        ],
        "warnings": []
      },
      {
        "criterion_id": "crit_isolation_durability",
        "criterion_description": "Understanding of Isolation and Durability",
        "max_marks": 5.0,
        "selected_level_id": "level_none",
        "selected_level_descriptor": "Fails to explain isolation or durability.",
        "awarded_mark": 0.0,
        "evidence_sentence_ids": [],
        "supporting_concepts": [],
        "demonstrated_concepts": [],
        "partial_concepts": [],
        "missing_concepts": [],
        "contradicted_concepts": [],
        "next_level_improvements": [
          "isolation",
          "durability"
        ],
        "explanation": "Criterion crit_isolation_durability received the proposed mark 0/5 at rubric level 'level_none'. No sentence-level evidence was available, so this explanation does not assert unsupported evidence.",
        "strengths": [],
        "missing_or_partial_areas": [],
        "improvement_suggestions": [
          "No sentence in your answer matched the concepts for this criterion, so the system cannot tell what you did or did not understand. It currently scores 0/5; to reach 'Partial Understanding' (2.5/5), write about 'isolation', 'durability'.",
          "For 'isolation': explain it in your own words and show how it applies to this question.",
          "For 'durability': explain it in your own words and show how it applies to this question.",
          "These suggestions come from matching the rubric's concepts in your wording, not from a check that your explanation is correct, so a correct answer written in different words may not be matched."
        ],
        "warnings": [
          "No positive scoring level was supported for criterion crit_isolation_durability; selected lowest rubric level 'level_none'.",
          "No sentence-level evidence was available for criterion crit_isolation_durability; the explanation is limited to the rubric result."
        ]
      }
    ],
    "overall_feedback": {
      "total_mark": 5.0,
      "total_possible": 10.0,
      "percentage": 50.0,
      "overall_summary": "Function 2 proposed 5 of 10 marks across 2 criterion(s).",
      "overall_strengths": [
        "Demonstrated concept supported by the answer: atomicity.",
        "Demonstrated concept supported by the answer: consistency."
      ],
      "overall_missing_concepts": [],
      "overall_next_level_improvements": [
        "isolation",
        "durability"
      ],
      "overall_improvement_suggestions": [
        "This criterion is at its top rubric level (5/5); keep this standard.",
        "The concepts found in your wording were 'atomicity', 'consistency'.",
        "To go further, support your points with a specific example and say why it matters.",
        "No sentence in your answer matched the concepts for this criterion, so the system cannot tell what you did or did not understand. It currently scores 0/5; to reach 'Partial Understanding' (2.5/5), write about 'isolation', 'durability'.",
        "For 'isolation': explain it in your own words and show how it applies to this question.",
        "For 'durability': explain it in your own words and show how it applies to this question.",
        "These suggestions come from matching the rubric's concepts in your wording, not from a check that your explanation is correct, so a correct answer written in different words may not be matched."
      ]
    },
    "warnings": [
      "No positive scoring level was supported for criterion crit_isolation_durability; selected lowest rubric level 'level_none'.",
      "No sentence-level evidence was available for criterion crit_isolation_durability; the explanation is limited to the rubric result."
    ],
    "feedback_version": "baseline-v1"
  },
  "mindmap": {
    "question_id": "IT3020-2023-Q1-a",
    "root_node_id": "root_it3020-2023-q1-a",
    "title": "Concept Map: IT3020-2023-Q1-a",
    "nodes": [
      {
        "node_id": "root_it3020-2023-q1-a",
        "type": "root",
        "concept": "IT3020-2023-Q1-a",
        "label": "Explain the ACID properties in database transaction management.",
        "source": "system",
        "status": null,
        "evidence_sentence_ids": [],
        "parent_node_id": null,
        "children": [
          "concept_atomicity",
          "concept_consistency",
          "concept_isolation",
          "concept_durability"
        ],
        "relationship_type": null
      },
      {
        "node_id": "concept_atomicity",
        "type": "concept",
        "concept": "atomicity",
        "label": "Atomicity",
        "source": "student_answer",
        "status": "demonstrated",
        "evidence_sentence_ids": [
          1
        ],
        "parent_node_id": "root_it3020-2023-q1-a",
        "children": [],
        "relationship_type": "child"
      },
      {
        "node_id": "concept_consistency",
        "type": "concept",
        "concept": "consistency",
        "label": "Consistency",
        "source": "student_answer",
        "status": "demonstrated",
        "evidence_sentence_ids": [
          2
        ],
        "parent_node_id": "root_it3020-2023-q1-a",
        "children": [],
        "relationship_type": "child"
      },
      {
        "node_id": "concept_isolation",
        "type": "concept",
        "concept": "isolation",
        "label": "Isolation",
        "source": "expected_concept",
        "status": "not_demonstrated",
        "evidence_sentence_ids": [],
        "parent_node_id": "root_it3020-2023-q1-a",
        "children": [],
        "relationship_type": "child"
      },
      {
        "node_id": "concept_durability",
        "type": "concept",
        "concept": "durability",
        "label": "Durability",
        "source": "expected_concept",
        "status": "not_demonstrated",
        "evidence_sentence_ids": [],
        "parent_node_id": "root_it3020-2023-q1-a",
        "children": [],
        "relationship_type": "child"
      }
    ],
    "relationships": [
      {
        "relationship_id": "98a27bd78724e46321181d3aeb70b445",
        "source_node_id": "root_it3020-2023-q1-a",
        "target_node_id": "concept_atomicity",
        "relationship_type": "child",
        "evidence": "Deterministic baseline structural attachment."
      },
      {
        "relationship_id": "b7f10ce2b3de948d4695d4b5c94bfb47",
        "source_node_id": "root_it3020-2023-q1-a",
        "target_node_id": "concept_consistency",
        "relationship_type": "child",
        "evidence": "Deterministic baseline structural attachment."
      },
      {
        "relationship_id": "90e33840b64d8408fac27f0473614fbf",
        "source_node_id": "root_it3020-2023-q1-a",
        "target_node_id": "concept_isolation",
        "relationship_type": "child",
        "evidence": "Deterministic baseline structural attachment."
      },
      {
        "relationship_id": "6b882d4da7bfd3937629b98215a3bd25",
        "source_node_id": "root_it3020-2023-q1-a",
        "target_node_id": "concept_durability",
        "relationship_type": "child",
        "evidence": "Deterministic baseline structural attachment."
      }
    ],
    "summary": {
      "total_nodes": 5,
      "demonstrated_count": 2,
      "partial_count": 0,
      "missing_count": 2
    },
    "warnings": [
      "Mind map contains 2 missing expected concept(s)."
    ],
    "generation_version": "baseline-v1"
  },
  "warnings": [
    "No positive scoring level was supported for criterion crit_isolation_durability; selected lowest rubric level 'level_none'.",
    "No sentence-level evidence was available for criterion crit_isolation_durability; the explanation is limited to the rubric result.",
    "Mind map contains 2 missing expected concept(s)."
  ],
  "pipeline_version": "integrated-v1",
  "ai_estimate": null
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


## 4. Verified status (2026-10-27)

Checked against the repository, not against a running C2 service.

| Question | Finding |
| :--- | :--- |
| How does C2 hand questions over? | `ai-services/c2/services/question_repository.py::build_question_repository(paper)` returns records (`question_id`, `paper_id`, `module_code`, `question_text`, `context`, `marks`, `marks_status`, `topic`, ...). There is **no HTTP route** on the C2 side (`backend/src/modules/c2/*` holds only `.gitkeep`; `ai-services/c2/app/routes` is empty). |
| Does C2 supply a rubric, reference answer or expected concepts? | **No.** Those must come from the lecturer. `ai-services/c3/services/integration/c2_adapter.py` keeps what C2 provides, uses `marks` only when `marks_status` is `extracted`/`calculated`, never invents a rubric, and lists what the lecturer must supply. |
| Does C3 accept the request in 2.1? | Yes: `POST /c3/assess` returns 200 (checked by `tests/integration/test_c2_c3_contract.py` and a live call to the running service). Unknown C2 fields (`assessment_id`, `paper_id`, `module_code`, ...) are ignored. |
| Input validation | Missing rubric, blank concepts, wrong `answer_type` and a non-numeric or non-positive `max_marks` return HTTP 422. **New:** a `max_marks` that differs from the rubric total is rejected (422); `max_marks` is optional and never computes a mark. |
| Authentication | The Python service has no authentication of its own; the Node backend (`/api/v1/c3/*`) enforces JWT roles. A C2 caller must go through the backend. No C2-to-backend credentials or endpoint are defined in the repository: **requires agreement with the C2 owner**. |
| Response example in 2.2 | Replaced with real output of the running service; it is validated against `AssessmentResponse` by the contract test (the earlier example had an out-of-date shape). |
