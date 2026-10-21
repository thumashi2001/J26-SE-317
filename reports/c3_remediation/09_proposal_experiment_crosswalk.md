# 09 Proposal ↔ Day 18/22/23 ↔ code experiment crosswalk (verified 2026-10-21)

Sources read: proposal Table 4 and §3.3/§3.5 (pp.28–33), Day 18 methodology (conditions A–F), Day 22/23 model plan (L0–L4; groups A–E), Day 25 evaluation list, COM-07/DEC-07 (`PROPOSAL_COMMENT_RESPONSE_MATRIX.md`, `EXPERIMENT_A_TO_F_TRACEABILITY.md`), `experiments/conditions.py`, `experiments/model_comparison.py`, `reports/c3_remediation/*`.
Status labels (only these): `BUILT_AND_TESTED`, `BUILT_NOT_EVALUATED`, `PARTIALLY_IMPLEMENTED`, `BLOCKED`, `NOT_IMPLEMENTED`, `DEFERRED_TO_PP2`.
Evidence classes used below: **U** component/unit/integration tests; **E** controlled research evaluation (fixed split, saved predictions); **L** real LLM inference. A condition is only "tested" when its evidence class is named.

## 1. Name crosswalk
| # | Proposal (Table 4 / §3.3) | Day 18 | Day 22/23 | Code identifier | Actual implementation |
|---|---|---|---|---|---|
| 1 | Deterministic answer-key marking (MCQ baseline) | – (MCQ = functional feature) | – | Node `mcqMarkingService.evaluateMcqAnswer` | implemented in Node only |
| 2 | Keyword/rule-based marking (non-semantic baseline) | "lexical baseline" | Experiment A (lexical) / L0-simple | `baseline` in `conditions.py` (cosine×max) and `R1_lexical_token_recall_baseline` (set recall×max) in `model_comparison.py` | two different formulas; R1 is the one evaluated on v2 |
| 3 | (not in Table 4) | – | L0 TF-IDF + classical ML | `A1_tfidf_ridge`, `A2_tfidf_cosine_overlap_gbr`; history `train_semantic_model*.py` (deleted) | A1/A2 trained on v2 |
| 4 | Semantic-model approach | – | L2 SBERT; group C | `B0_sbert_cosine_isotonic`, `B1_sbert_features_ridge`; `LocalSentenceTransformerEmbedding` (RAG) | all-MiniLM-L6-v2 |
| 5 | Semantic-model approach (contextual) | – | L1 RoBERTa-base; group B | `C_roberta_base_finetuned` | fine-tuned on v2 (BERT, cross-encoder optional: not built) |
| 6 | Proposed integrated approach | Condition E "Concept Evidence + Rubric" | L4 integrated pipeline; group E | Condition `E` = `services/marking` (also `/c3/assess`); `R2_condition_E_binary_rubric` | deterministic; binary on v2 |
| 7 | LLM without RAG | Condition A (LLM-only) | group D (structured LLM) | `conditions.py` `A`; `rag_marking.rag_assess(use_rag=False)` | code only, never run |
| 8 | (rubric-aware LLM) | Condition B (LLM + rubric) | group D | `conditions.py` `B` (needs scoring levels) | code only, never run |
| 9 | LLM + RAG | Condition C (+ Vector RAG) | "RAG vs non-RAG" (Day 25) | `conditions.py` `C`; new `services/rag/{corpus,rag_marking}.py`, `rag_retrieval_eval.py`, `rag_vs_norag.py` | retrieval implemented and evaluated; LLM marking never run |
| 10 | – (GraphRAG only in literature review) | Condition D (+ GraphRAG over CCKG) | – | `conditions.py` `D`, `services/cckg/graph_adapter.py` | adapter + 5 live Neo4j tests; no populated CCKG |
| 11 | Multiple LLMs under equivalent conditions | LLM comparison (H1) | L3 GPT *or* Llama | `services/llm/{gemini,openai,local}_provider.py`; experiments `--provider` | providers only; never run |
| 12 | – | Condition F "full combined" (secondary) | – | `conditions.py` `F` (E + similarity + LLM, grid-fitted on validation) and DEC-07's "gradient-boosted regressor F" | needs LLM; three incompatible definitions in the repo; new **F-lite** (no LLM) is separate |
| 13 | Public datasets (Mohler, ASAP-SAS, SciEntsBank, ASAG2024); SLIIT data if approved; robustness | Tier 1–4 data, cross-dataset | EngSAF, ASAP-SAS, Mohler, ASAG2024 | none (files on disk, unused); probes in audit only | not used (DEC-06 makes synthetic primary) |

## 2. Per-condition record
| # | Requirement source | RQ/H | Files & dependencies | Complete? Runs end to end? | Real inference/training | Valid dataset | Reproducible | Evidence (class) | Missing | PP1/PP2 | **Status** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 MCQ | proposal p.28, FR-C3-04 | – | `mcqMarkingService.js`; Node only | yes / yes | deterministic | – (no MCQ dataset) | yes | U: 11 MCQ subtests; E: none | Python parity, MCQ dataset, UI mind-map shape bug | PP1 | `BUILT_AND_TESTED` (U only) |
| 2 Keyword/rule | Table 4 | H baseline | `evaluate_repaired.py:88`, `model_comparison.py` REF | yes / yes | none needed | v2 (caveats) | yes | E: test nMAE 0.112, MAE 1.939 marks | formula consolidation | PP1 | `BUILT_AND_TESTED` (E) |
| 3 TF-IDF+ML | Day 23 L0 | RQ2 | `model_comparison.py`, scikit-learn | yes / yes | trained | v2 (caveats) | yes (seed) | E: A1 test nMAE 0.081; A2 0.248 | benchmark data, multi-seed | PP1 | `BUILT_AND_TESTED` (E) |
| 4 SBERT | Day 23 L2 | RQ2 | sentence-transformers, torch | yes / yes | pretrained + ridge/isotonic | v2 | yes | E: B1 0.084; B0 0.135 | cross-encoder, benchmarks | PP1 | `BUILT_AND_TESTED` (E) |
| 5 RoBERTa | Day 23 L1 | RQ2 | transformers, torch (CPU) | yes / yes | fine-tuned 5 epochs | v2 | partly (single seed, checkpoint not saved) | E: test nMAE 0.038, QWK 0.98 | seeds, checkpoint, human labels | PP1 | `BUILT_AND_TESTED` (E, provisional) |
| 6 Condition E | proposal "integrated", COM-07 | RQ1/H5 | `services/marking`, `/c3/assess` | yes / yes | deterministic | v2 (no multi-level rubric) | yes | U: 324 py tests; E: test nMAE 0.209 (binary) | scoring levels, semantic evidence | PP1 | `BUILT_AND_TESTED` (U+E) |
| 7 LLM no-RAG | Day 18 A; COM-07 | H1 | `conditions.py` A, `rag_assess(use_rag=False)`, provider code | code yes / **not run** | none | – | – | U: provider & prompt tests with stubs; L: none | quota/credits, calibration, v2 loader adapter | **PP2** (COM-07: no uncalibrated LLM numbers in PP1) | `DEFERRED_TO_PP2` |
| 8 Rubric LLM | Day 18 B | H2 | `conditions.py` B | not on v2 (no scoring levels) | none | – | – | none | rubric levels authoring (O4), quota | PP2 | `DEFERRED_TO_PP2` |
| 9 Vector RAG | Day 18 C; Day 25; proposal RAG | H3, RQ3 | `services/rag/*`, local MiniLM, train-only corpus | retrieval yes; LLM marking **not run** | local embeddings (real SBERT) | v2 train-only corpus | yes (retrieval) | U: 10 offline tests; E(retrieval only): hit@1 0.77 vs TF-IDF 0.54 vs random 0.11 (26 queries, module-match proxy); L: none | LLM access, relevance labels, ablations | retrieval PP1 / marking PP2 | `BUILT_NOT_EVALUATED` |
| 10 GraphRAG/CCKG | Day 18 D | H4 | `graph_adapter.py`, Neo4j | adapter yes; graph **not populated** | none | – | – | U: 5 live Neo4j tests (infrastructure only) | CCKG schema + seeds, concept coverage ≈5/541 | PP2 | `BLOCKED` |
| 11 Multi-LLM | proposal Table 4, Day 22/23 L3 | H1 | provider code | not run | none | – | – | none | credentials/quota, equal-input protocol | PP2 | `DEFERRED_TO_PP2` |
| 12a Condition F (proposal) | Day 18 F; DEC-07 | H5/H6 | `conditions.py` F | needs E + L + embeddings; **not run** | none | – | – | none | LLM predictions | PP2 | `DEFERRED_TO_PP2` |
| 12b F-lite (new, non-LLM) | derived from Day 18 F | exploratory | `hybrid_f_lite.py`, `results_*.json` | yes / yes | NNLS on validation preds | v2 | yes | E: test nMAE 0.0375 vs RoBERTa 0.0382 (weights E .03, A1 .05, B1 0, C .92) | different from proposal F | PP1 (exploratory) | `BUILT_AND_TESTED` (E; not the proposal's F) |
| 13a Benchmarks / cross-dataset | proposal p.30, Day 23 §12 | RQ1–6 | none | – | none | EngSAF etc. on disk | – | none | policy (DEC-06 vs p.30), permissions, score mapping, human-marked scores | PP2 | `NOT_IMPLEMENTED` |
| 13b Robustness tests | Day 18/23 error analysis | – | probes run manually in audit (paraphrase 0/4, negation 4/4, stuffing 4/4) | not a suite | – | – | script in session only | none as tests | automated robustness suite | PP2 | `PARTIALLY_IMPLEMENTED` |

## 3. Integrity checks re-verified (this session)
- Ratio-concentration on v2 = **0.766 > 0.45 → FAIL** (v1 0.758); not relaxed. Three tiers share one mark per question; FULL = 1, IRRELEVANT = 0.
- Length–mark Pearson 0.832; **length-only ridge reaches test nMAE 0.067**, better than TF-IDF/SBERT/baseline (`experiments/diagnostics.json`).
- Splits question-disjoint (validator `split_question_disjoint` pass); the 0.903 train/test near-duplicate pair is removed in v2 (max cross-split cosine 0.648); test split (90 answers, 15 questions) unchanged since the first evaluation and not used for any selection.
- RoBERTa: single seed (20261021), checkpoint not saved, labels are researcher tiers → **not validated against human markers**.
- F-lite inputs verified: prediction lengths 66/90, no failed/missing values; weights fit on validation only.
- RAG retrieval corpus verified train-only/eligible-only by tests (`test_rag_pipeline.py`).

## 4. COM-07 / PP1 boundary
PP1 = Condition E + baselines + offline learned models + retrieval. Not shown as PP1 results: any LLM number, RAG-vs-no-RAG marking, GraphRAG, proposal-F. This follows COM-07 ("do not present uncalibrated zero-shot LLM numbers during PP1").
