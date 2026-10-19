# C3 Research Report — Final Dataset

The final C3 dataset contains 167 written-answer questions and 1,002 controlled answer
records. Each question has six controlled response conditions: FULL, MOSTLY_CORRECT, PARTIAL,
MISSING_CONCEPT, MISCONCEPTION and IRRELEVANT. The question-level split contains 117 training,
25 validation and 25 testing questions, with all variants of a question kept in the same split.

The dataset is intentionally focused on short-answer and essay-answer automated assessment.
Questions whose original tasks depended primarily on diagram construction, visual structure
manipulation or code implementation were replaced with researcher-designed written questions
covering the relevant conceptual area. Original IDs and replacement rationale are preserved.

All automated structural and scope QA checks passed. The dataset is researcher-constructed
controlled data, not authentic student response data, and the reference standard is not
claimed to be independently expert-validated.

The dataset supports the planned experimental conditions:
A. LLM-only
B. LLM + Rubric
C. LLM + Rubric + Vector-RAG
D. LLM + Rubric + GraphRAG
E. Concept Evidence + Rubric
F. Full Combined Approach

No condition is assumed to outperform another; performance must be established empirically.
