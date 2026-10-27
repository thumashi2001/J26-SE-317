# 27 — Extra model comparison, a reference-answer data defect, and the advisory AI estimate (2026-10-27)

## 1. Defect found: every model so far saw the student answer only
`02_controlled_answers_eligible.csv` has an EMPTY `reference_answer` column for all 558 rows (test: `tests/unit/test_reference_answers_loaded.py`).
The reference answers are in `01_question_bank.csv`. `model_comparison.load()` read the empty column, so the (reference, answer) pair of
RoBERTa, the cosine-to-reference features of TF-IDF/SBERT, F-lite and the LLM harnesses carried **no reference**.
Consequences: report 03 and F-lite describe "reference + answer" inputs but are really **answer-only**; they must not be cited as
reference-aware. The deterministic rubric engine is not affected (it reads the question bank). Fixed 2026-10-27:
`load_answers_with_reference()` joins the question bank; `multi_llm_comparison.py` and `rag_vs_norag.py` use it.

## 2. Answer-only results (kept as an ablation: `experiments/extra_answer_only/`)
Phase 1 (validation) then one test scoring, protocol unchanged. nMAE, lower is better; test CI = question bootstrap.

| Model | val nMAE | test nMAE [95% CI] | test QWK |
|---|---|---|---|
| DistilRoBERTa | 0.0359 | 0.0380 [0.030, 0.046] | 0.982 |
| BERT-base | 0.0374 | 0.0432 [0.036, 0.052] | 0.975 |
| RoBERTa-base | 0.0377 | 0.0382 [0.030, 0.047] | 0.980 |
| MiniLM cross-encoder | 0.0676 | 0.0613 [0.056, 0.067] | 0.965 |
| mpnet features + ridge | 0.0818 | 0.0776 [0.067, 0.089] | 0.935 |
| MiniLM features + random forest | 0.0860 | 0.0762 [0.071, 0.081] | 0.931 |
| MiniLM features + SVR | 0.0939 | 0.0809 [0.071, 0.093] | 0.931 |
Length-only diagnostic: validation nMAE 0.0748, QWK 0.955 (earlier test: 0.067).
Reading: an answer-only transformer scores 0.038 on tier-derived labels, so the labels are largely recognisable from the answer text alone
(tiers differ in wording/length). This is not evidence of agreement with human markers.

## 3. Corrected, reference-aware comparison
Re-run with the reference answer supplied (same protocol: validation-only selection, one test scoring afterwards) into `experiments/extra/`.
Completed 2026-10-27 (one seed; files in `experiments/extra/`). Validation selected RoBERTa-base; the test split was then scored once.

| Model | val nMAE | test nMAE | test QWK | answer-only test nMAE |
|---|---|---|---|---|
| RoBERTa-base | 0.0273 | **0.0277** | 0.988 | 0.0382 |
| DistilRoBERTa | 0.0363 | 0.0350 | 0.984 | 0.0380 |
| BERT-base | 0.0309 | 0.0401 | 0.979 | 0.0432 |
| MiniLM features + SVR | 0.0508 | 0.0608 | 0.960 | 0.0809 |
| MiniLM features + random forest | 0.0613 | 0.0634 | 0.954 | 0.0762 |
| MiniLM cross-encoder | 0.0671 | 0.0636 | 0.964 | 0.0613 |
| mpnet features + ridge | 0.0738 | 0.0643 | 0.961 | 0.0776 |

Reading: supplying the reference answer improves the models that compare answer and reference (RoBERTa, SVR, forest, ridge); the
cross-encoder and DistilRoBERTa barely change. Caveats: tier-derived labels (not human marks), one seed, 90 test answers / few questions.

## 4. Advisory AI estimate in the product
`services/ml/scorer.py` + `ai_estimate` in `/c3/assess`: off unless `C3_ML_MODEL_DIR` is set; never changes marks; flagged for lecturer
review when it differs from the rubric ratio by more than 0.25; fails soft (6 unit tests). The validation-selected RoBERTa-base checkpoint (reference-aware) is deployed locally in
`ai-services/c3/models/c3_scorer` (git-ignored, ~500 MB; enable with `C3_ML_MODEL_DIR=models/c3_scorer`). End-to-end check through
`orchestrator.assess_answer` on all 90 test rows: `ai_estimate` present, advisory, model roberta-base, nMAE vs labels 0.0277 (identical to
the phase-2 result). That check used a generic single-criterion rubric, so it validates the plumbing and the model, not rubric agreement.
The backend stores the whole response, so `ai_estimate` is saved. Staff view: `AssessmentResult.jsx` shows an "AI second opinion
(advisory)" panel with the estimate, the rubric mark and a consistent/differs pill. Student view: `redaction.js` removes `ai_estimate`
and its warning server-side (backend test added; stored record untouched). The panel was built and the frontend build passes, but it
has not been looked at in a browser with a live estimate.

## 5. LLM evidence so far
Live Gemini pilot, 5 validation answers x {no RAG, RAG} = 10 real calls, all valid (`experiments/multi_llm_pilot/`): nMAE 0.093 in both
conditions, identical marks (retrieval returned other questions' references; with n=5 nothing can be concluded). Groq/OpenRouter keys
are not configured, so the 2-3-provider comparison remains BLOCKED beyond Gemini.
