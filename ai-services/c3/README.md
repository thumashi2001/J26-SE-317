# Component 3: AI-Powered Automated Marking and Answer Analysis

C3 is responsible for the research and future implementation of:

- Answer Processing System
- Automated Marking Engine
- Concept-Level Answer Analysis
- Explainable Feedback Generation
- Answer-to-Concept Mind Map Generation
- Lecturer Support and Verification
- Experimental comparison of semantic, LLM, and RAG configurations

C3 receives assessment context from C2 and provides structured assessment evidence to C1 and C4. The service is separated from the Node/Express application so that AI/ML processing, experiments, models, and evaluation can use appropriate Python tooling.

## Function 1: Answer Processing and Baseline Semantic Analysis

Function 1 provides a deterministic first-stage analysis through `POST /analysis/answer`.
It normalizes whitespace, extracts sentences, tokenizes answers, calculates lexical
token-frequency cosine similarity against an optional reference answer, and reports
basic expected-concept token overlap with sentence evidence.

The lexical similarity and concept overlap are transparent research baselines. They
do not establish true semantic understanding, correctness, or a student mark. They
are retained so later embedding, transformer, LLM, or RAG approaches can be compared
against a reproducible baseline.

The endpoint returns structured evidence only. Rubric-aware marking, criterion
scoring, feedback, mind-map generation, persistence, and lecturer verification are
outside Function 1.

### Example request

```json
{
  "question_id": "SE3010-Q01",
  "question_text": "Explain the concept of software architecture.",
  "student_answer": "Software architecture describes the high-level structure of a software system.",
  "reference_answer": "Software architecture defines the high-level structure of a software system.",
  "expected_concepts": ["high-level structure", "components", "relationships"],
  "answer_type": "short"
}
```

### Example response shape

```json
{
  "question_id": "SE3010-Q01",
  "normalized_answer": "Software architecture describes the high-level structure of a software system.",
  "sentence_count": 1,
  "token_count": 9,
  "sentences": [{"sentence_id": 1, "text": "Software architecture describes the high-level structure of a software system."}],
  "reference_similarity": 0.9166666667,
  "concept_matches": [{
    "concept": "high-level structure",
    "status": "demonstrated",
    "overlap_score": 1.0,
    "evidence_sentence_ids": [1]
  }],
  "warnings": [],
  "analysis_version": "baseline-v1"
}
```

The exact similarity value depends on the token-frequency vectors. It is not a
research result or a final assessment score.

## Running Function 1

From `ai-services/c3/` with the C3 virtual environment active:

```powershell
python -m pytest -q
uvicorn app.main:app --reload --port 8003
```

The existing `GET /health` endpoint remains available. Interactive API documentation
is available at `/docs`, and the OpenAPI document is available at `/openapi.json`.

## Function 2: Deterministic Rubric-Aware Marking Baseline

Function 2 provides `POST /marking/evaluate`. It accepts the Function 1 answer
fields plus a lecturer-defined rubric containing criteria and explicit scoring
levels. The marking engine reuses Function 1 preprocessing, lexical similarity,
concept statuses, and sentence evidence.

Each criterion is evaluated independently. The engine selects the highest scoring
level whose required concepts and evidence requirements are supported by the
available deterministic lexical evidence. The awarded mark is the exact mark from
that rubric level. It never converts a percentage of concept overlap into marks and
does not use a universal partial-credit formula.

The overall proposed mark is derived only by summing criterion marks. Each result
contains the selected level, rubric descriptor, awarded mark, evidence sentence IDs,
supporting concepts, explanation, and warnings. This remains a proposed baseline
result, not a claim of factual correctness, true semantic understanding, or final
lecturer judgment.

Function 2 deliberately does not implement LLMs, RAG, advanced transformer models,
feedback generation, mind maps, lecturer dashboards, persistence, CCKG integration,
or Node.js orchestration.

Run the complete C3 test suite from `ai-services/c3/` with:

```powershell
python -m pytest -q
```

The current suite covers rubric validation, criterion-level selection, explicit
partial levels, aggregation, explanations, warnings, API validation, and regression
checks for `/health` and `/analysis/answer`.

### C3-010: Machine-readable evidence rules

Scoring levels may include an `evidence_rule` with type
`required_concept_count`. The rule can require a minimum number of demonstrated
concepts and, when explicitly enabled, a minimum number of partial concepts:

```json
{
  "type": "required_concept_count",
  "minimum_demonstrated": 1,
  "minimum_partial": 0,
  "allow_partial": false
}
```

The evaluator uses these fields against Function 1 concept statuses. It never parses
the human-readable descriptor and never derives marks from percentages. The selected
level's exact rubric mark is returned. For example, a level requiring one
demonstrated concept can award its explicit mark when one concept is demonstrated
and another is partial, while a level requiring two demonstrated concepts is not
supported by that evidence.
