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
