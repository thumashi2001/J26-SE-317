# 12 Rapid revision sheet — C3 PP1 viva (read this the morning of the viva)

Everything below is limited to what the audit verified. "V" = I executed or read it. If an examiner pushes past these facts, say "that is planned / not yet evaluated".

## One-page facts
- **Project:** AdaptiveLearnSE (J26-SE-317), four components. **Mine:** Component 3 — AI-Powered Automated Marking and Answer Analysis. C2 → C3 → C1/C4 (C2 gives questions; C3 gives marks, concepts, evidence; C1 updates learner state; C4 uses weak concepts).
- **Research gap (proposal p.26):** no integrated, experimentally validated work that combines rubric-aware semantic marking + concept-level diagnosis + explainable evidence + answer-to-knowledge-map.
- **Method:** Design Science Research + experimental evaluation. Development: Agile.
- **Architecture:** React (5173) → Express/Node (3000: auth, validation, Mongo, lecturer review) → Python FastAPI (8003: the marking pipeline). Pipeline: process → analyse concepts → pick rubric level per criterion → explain → feedback → concept map.
- **Numbers (V):** Python tests 324 pass / 13 xfail (known bugs) / 0 fail; Node 90 = 75 pass + 15 todo (known bugs); live Neo4j 5 pass. Ruff 111 findings, ESLint 13 errors.
- **Dataset (V):** original 167 questions / 1,002 answers (6 variants each). Repaired primary set 96 questions / 576 answers (train 420, val 66, test 90); 355 quarantined; 71 IRRELEVANT controls kept apart.
- **Results (V, repaired test n = 90, MAE in marks):** lexical baseline **1.939**, Condition E **3.544**. The baseline is *better*. Condition E predicts only 0 or full marks in that experiment.
- **Verified demo results:** `arch-full` 4/4, `arch-partial` 2/4, `arch-zero` 0/4, `oop-higher` 3/3, `quality-multi` 2/4.
- **Verified weaknesses:** paraphrase → 0/4; negation → 4/4; keyword stuffing → 4/4; padding does not help.

## 60-second explanation
"My component, C3, automatically marks written software-engineering answers against a lecturer's rubric and explains the mark. A student's answer is cleaned and split into sentences; the system looks for the concepts the question expects, decides for each rubric criterion which level the evidence supports — so a half-correct answer gets partial marks — and returns the mark, the evidence sentences, feedback and a concept map. A lecturer can review, override with a reason, and finalise; the original automated mark is always kept. For PP1 I built the deterministic baseline of this pipeline and I can demonstrate it end to end. It is deliberately simple — it matches words, not meaning — so my next step, planned in the proposal, is to compare it with semantic-model, LLM and retrieval-based approaches on the same data. I have also audited and repaired my synthetic dataset and I report its limitations openly."

## 2-minute explanation
1. **Problem:** manual marking is slow and inconsistent; score-only automated tools give no concept-level insight (proposal p.26 gap).
2. **What C3 does:** five capabilities — answer processing, rubric-aware marking, concept diagnosis, explainable feedback, concept map — plus lecturer verification. Output also feeds C1/C4 (marks, demonstrated and missing concepts).
3. **How (current implementation):** FastAPI pipeline `/c3/assess`: normalise → sentence split → tokenise → per-concept overlap (demonstrated / partial / missing) → for each criterion choose the highest rubric level whose required concepts are evidenced → sum marks → templated explanation/feedback → star-shaped concept map. Express adds login roles, saving, lecturer review (override needs a reason), C1 events.
4. **Evidence:** 324 + 75 automated tests; verified examples 4/4, 2/4, 0/4; dataset audited, defects (literal "nan", flat marks, leakage) found and repaired reproducibly.
5. **Honest status:** baseline-first; no LLM/RAG/semantic-model result yet; C2/C4/CCKG integration not built; synthetic data; the comparison of 2–3 approaches is the planned next phase.

## 5-minute technical explanation
- **Request → response:** React sends question, student answer, rubric (criteria with levels and required concepts), expected concepts. Express authenticates (JWT, roles), calls Python (15 s timeout; Python down → 502, timeout → 504), stores submission + result in Mongo, shows it to the student; lecturer queue → review → accept/override(reason ≥ required)/finalize; finalize also sends a "finalized" event to C1 (provisional events earlier).
- **Python pipeline (files):** `services/preprocessing/text_normalizer.py` (whitespace, sentence split on `.?!`, tokens = words, hyphens kept, no stemming) → `services/semantic/analyzer.py` (concept score = shared tokens ÷ concept tokens; 1.0 demonstrated, >0 partial, 0 not) → `services/marking/criterion_evaluator.py` (levels sorted by marks; first level whose required concepts / evidence rule is satisfied wins; explicit mark per level — never a percentage formula) → `marking_engine.py` (sum) → `services/feedback` (templated strengths, missing areas, next-level hints) → `services/mindmap` (root → concept nodes coloured by status).
- **Why rubric levels:** marks come from lecturer-defined levels, so partial credit is explicit and explainable ("level L2, evidence in sentence 1").
- **Design:** pure core packages (no network/db imports), provider abstraction `BaseLLMProvider` (Gemini/OpenAI/Ollama), cache + retry + rate-limit layer, Neo4j adapter with strict mode, hermetic tests.
- **Evaluation:** metrics MAE, RMSE, Pearson r, within ±2 marks / 10 % of max, bootstrap CIs, failed calls excluded and counted (never scored 0). Proposal also lists QWK/F1/feedback/mind-map metrics — **QWK is not yet implemented**.
- **Dataset story:** found literal "nan" in 252 answers, flat 10-mark labels on 426, wrong rubric keys; built a deterministic hash-verified repair (nothing invented): 576 eligible answers remain; validation still fails ratio-concentration (0.758 > 0.45) and length–mark correlation (0.81) — limitation of researcher-constructed labels.
- **Result and what it means:** baseline MAE 1.939 vs E 3.544 on 90 test answers: on this synthetic set, word-overlap tracks the labels better than my binary-rubric engine; it does *not* show that LLMs or semantic models are better or worse — they were not run.
- **Limits and next steps:** semantic model/LLM/RAG comparison on validation-then-test with fixed seeds; multi-level rubric authoring; QWK; fix security todos; integrate C2/C4/CCKG via the agreed APIs.

## Models: planned vs done (say this if asked "which models?")
- **Planned (Day 22/23):** L0 TF-IDF + classical ML, L1 RoBERTa-base, L2 SBERT, L3 GPT/Llama (conditional), L4 integrated pipeline; BERT and cross-encoder optional. Datasets: EngSAF, ASAP-SAS, Mohler, ASAG2024.
- **Done:** deterministic L4 pipeline (word-overlap evidence + rubric levels); lexical baseline vs Condition E on the repaired synthetic set (1.939 vs 3.544 MAE, baseline wins); earlier TF-IDF+Ridge/GBR trained on defective synthetic labels (v2 MAE 5.994).
- **Not done:** RoBERTa, SBERT, BERT, cross-encoder, any real GPT/Llama run, RAG vs non-RAG, benchmark datasets. Provider code and datasets are ready; quota/compute are the blockers.
- **Next:** EngSAF experiment — TF-IDF vs SBERT vs RoBERTa (+ LLM if quota), select on validation only, test once; report honestly even if TF-IDF wins.
- **XAI claim (careful):** explanation = which rubric level, which concept, which sentence — transparent because rule-based; not a learned-model explanation (no SHAP etc.).

## Key terms (simple English)
- **Rubric:** the marking scheme: criteria, each with levels worth fixed marks.
- **Criterion level:** e.g. L0 = 0, L2 = 2, L4 = 4 marks, each with required concepts.
- **Concept evidence:** sentences in the answer that contain a concept's words.
- **Demonstrated / partial / missing:** all / some / none of a concept's words found.
- **Partial credit:** a middle level (e.g. L2) is awarded when only part of the required concepts are evidenced.
- **Lexical vs semantic:** matching words vs matching meaning.
- **Baseline:** simple method used for comparison. **Condition E:** my deterministic concept-evidence + rubric engine. **A–D, F:** LLM-only, +rubric, +vector RAG, +GraphRAG, full combined — planned, not run.
- **RAG:** the LLM is given retrieved reference text. **CCKG:** shared curriculum knowledge graph (Neo4j).
- **MAE / RMSE:** average / root-mean-square mark error. **QWK:** agreement score for ordinal marks (planned).
- **Leakage:** test data resembling training data, inflating results. **Quarantine:** records removed from evaluation but kept with a reason.
- **Human-in-the-loop:** lecturer has the final word.

## Five strongest defensible contributions
1. Working end-to-end deterministic assessment pipeline with criterion-level evidence and explicit partial credit (V).
2. Lecturer-controlled workflow: original mark preserved, mandatory override reason, finalize (V, with listed defects).
3. Extensible, tested engineering: pure core, provider abstraction, caching/retry/rate limiting, 324 + 75 tests.
4. Transparent research hygiene: a dataset audit that exposed and documented real defects, a reproducible hash-verified repair, and honest metric reproduction (including what did *not* reproduce).
5. Ready-to-run comparison infrastructure (real Gemini/OpenAI providers, preflight, response cache, validation-only fusion fit, live Neo4j) awaiting API quota.

## Five most important limitations (say them first)
1. Matching is lexical: paraphrase scores 0/4, negation and keyword stuffing score 4/4.
2. Data is synthetic and template-like; validation checks fail; no expert labels; baseline beats E on it.
3. The planned model comparison (TF-IDF baseline, SBERT, RoBERTa, GPT/Llama — Day 22/23) has not been run; no benchmark dataset (EngSAF etc.) used; supervisor's multi-candidate comparison NOT yet demonstrated.
4. C2/C4/CCKG integration not built; mind map is a star graph, not concept relationships.
5. Backend security/reliability defects are known and unfixed (client-supplied answer key, ownership, masked save failure, etc.); heavy AI-assisted development must be explained and verified.

## Morning-of checklist
- [ ] Kill anything on ports 8003/3000/5173; start Python (`.venv_c3\Scripts\python.exe -m uvicorn app.main:app --port 8003` in `ai-services/c3`), backend (`npm run dev`), frontend (`npm run dev`).
- [ ] `GET http://127.0.0.1:8003/health` returns `"status":"running"` with an `llm` section (current version).
- [ ] Log in as lecturer and student; run `arch-full`, `arch-partial`, `arch-zero`; open the lecturer queue and review one.
- [ ] Have fallback evidence ready: screenshots, pytest output (324 passed), `reports/c3_pp1_comprehensive_audit`, the repaired dataset card.
- [ ] Re-read: five limitations, the baseline-beats-E answer, the AI-assistance answer, the LO5 pitch.
- [ ] Do not demo MCQ mind map or batch with real data; do not show `.env`.
- [ ] Know where each claim lives in code (file 09 §C).
