# 09 Complete viva explanation (simple English first, then technical, then exact evidence)

Rule used throughout: **Simple** = what you can say to anyone; **Technical** = how it works; **Evidence** = where to point (file:line or command). Labels: V verified, R reported, I inference. Planned work is never described as done.

---
## Part A — What the project is and why it matters
**Simple.** Lecturers spend a long time marking written answers, and a plain score does not tell a student *what* they misunderstood. My component, C3, reads a written answer, compares it to a lecturer's rubric, gives a proposed mark, shows *which sentences* support it, says which ideas are present/partly present/missing, writes feedback and draws a concept map. The lecturer stays in charge and can override.

**Technical.** C3 is one of four components: C2 supplies questions/rubrics, C3 marks and diagnoses, C1 (digital twin) and C4 (adaptive learning) consume marks and weak concepts. Proposal gap (p.26): no integrated, experimentally validated work combining rubric-aware semantic marking + concept diagnosis + explainable evidence + answer-derived knowledge map. Method: Design Science Research with experimental evaluation (p.28); Agile development (p.34).

**Evidence.** Proposal pp.3, 13, 26–27; five functions p.35; TAF pp.11–13.

---
## Part B — What exists today (the honest status)
| Capability | Status | One-line truth |
|---|---|---|
| Answer processing | IMPLEMENTED (V) | cleans text, splits sentences, tokenises |
| Semantic analysis | IMPLEMENTED as **word overlap**, not meaning (V) | "semantic" is a label for lexical concept matching |
| Rubric-aware marking, partial credit | IMPLEMENTED (V) | marks come from lecturer-defined rubric levels |
| Concept diagnosis | IMPLEMENTED (V) | demonstrated / partial / missing per concept |
| Explainable feedback | IMPLEMENTED, templated (V) | evidence sentences + fixed sentence templates |
| Mind map | PARTIAL (V) | star graph root→concepts; no concept-to-concept links |
| Lecturer review/override/finalise | IMPLEMENTED with known defects (V) | original mark kept, override needs a reason |
| MCQ marking | IMPLEMENTED in Node only (V) | deterministic key compare |
| LLM / RAG / GraphRAG / multi-model comparison | **NOT DEMONSTRATED** | provider code exists; never run on the dataset |
| C2 / C4 / CCKG integration | NOT IMPLEMENTED | C1 bridge exists (direct DB write) |
| OCR | NOT IMPLEMENTED | rejected with HTTP 400 |

---
## Part C — How a request flows (text architecture)
```
Browser (React :5173)
   │  POST /api/v1/c3/assess  {question, student_answer, rubric, expected_concepts}
   ▼
Express backend (:3000)  auth (JWT roles) → validation → [MCQ? handled here in Node]
   │  POST /c3/assess  (15 s timeout; Python down → 502, timeout → 504)
   ▼
FastAPI C3 service (:8003)  orchestrator.assess_answer
   1 preprocessing/text_normalizer   normalise → sentences → tokens
   2 semantic/analyzer               per concept: shared tokens ÷ concept tokens
   3 marking/rubric_validator        check rubric consistency
   4 marking/criterion_evaluator     choose highest level whose required concepts are evidenced
   5 marking/marking_engine          sum criterion marks
   6 feedback/*                      strengths, missing, next-level hints (templates)
   7 mindmap/*                       root → concept nodes coloured by status
   ▼  JSON result
Express saves c3_submissions + c3_results (status pending_review) → C1 provisional event
   ▼
Lecturer queue → review page → accept / override (+reason) → finalize → C1 finalized event
```
No LLM, RAG or graph database is on this path (V: `services/assessment/orchestrator.py` imports only schemas + marking/feedback/mindmap/semantic). The pipeline **is** "Condition E" of the experiments.

---
## Part D — The algorithms in plain words, with worked examples
### D1 Text processing (`services/preprocessing/text_normalizer.py`)
Simple: tidy the text, cut into sentences, cut into words (lower-case). Technical: whitespace collapsed; sentence split after `.`/`!`/`?`; tokens by regex keeping hyphenated words; **no stemming, no stop-word list** ("coupled" ≠ "coupling").

### D2 Concept check (`services/semantic/analyzer.py`, `baseline.py:29-39`)
Simple: for each expected concept, count how many of its words appear in the answer. All → *demonstrated*, some → *partial*, none → *missing*.
Example: concept "loose coupling"; answer "Modules should be loosely coupled. Coupling matters." → words {loose, coupling}; only "coupling" appears → 1/2 → **partial**, evidence sentence 2.
Limit: order and meaning are ignored; "of/the" can create a "partial" (no stop-words).

### D3 Choosing the rubric level (`services/marking/criterion_evaluator.py:155-184`)
Simple: a rubric criterion has levels, e.g. L0 = 0, L2 = 2, L4 = 4 marks. Try the highest level first; give the first one whose required concepts are all evidenced.
Example (verified `arch-partial`): the answer evidences some, not all, required concepts → L2 → **2/4**. `arch-full` → L4 → **4/4**; `arch-zero` → **0/4**.
Marks come only from explicit levels — never from a percentage formula (V; CLAUDE.md rule). Known bugs (strict xfail tests): AUDIT-M1 lowest positive level awarded when there is no zero level; M4 criterion concepts leak into every level so partial levels can be unreachable; M5 a single shared word satisfies a multi-word evidence requirement.

### D4 Feedback and mind map
Feedback: fixed templates filled with the demonstrated/missing concepts and next-level hints. Mind map: root = question, one node per concept coloured by status, one edge root→concept. Simple: it is a checklist drawn as a star, not a real concept web.

### D5 Lecturer workflow (`backend/src/modules/c3/services/submissionService.js:332-491`)
Student submits → status `pending_review` with the AI mark stored as `automated_mark` (never overwritten) → lecturer accepts or overrides (reason required) → finalise → event to C1. Known defects: no upper bound on override, finalised result can be reopened by re-posting a batch id, no history array (AUDIT-B2/B3/B5).

---
## Part E — The original research plan versus what was built (be ready for this)
**Simple.** On Day 22–23 I planned a ladder of methods and said the best would be chosen *by evidence*: (L0) TF-IDF + classical ML as a simple baseline, (L1) RoBERTa-base, (L2) SBERT, (L3) a GPT- or Llama-family model, (L4) my integrated C3 pipeline; BERT and a cross-encoder optional. I planned to test on EngSAF, ASAP-SAS, Mohler and ASAG2024. For PP1 I built the integrated pipeline's deterministic core and audited my dataset; the transformer/LLM comparison is **not run yet**.

**Technical / evidence.** Day 23 "Final Experimental Hierarchy"; experimental groups A lexical, B BERT/RoBERTa, C SBERT/cross-encoder, D structured LLM, E hybrid; RQ1–6, H1–H5; metrics per dataset (Accuracy/Precision/Recall/Macro-F1 for EngSAF 0/1/2 labels; MAE/QWK for ordinal scores). Datasets exist on disk but unused: `Desktop\Reserach\Data sets\{engsaf, asap, mohler, ASAG2024}`. Code check (V by grep): no RoBERTa/BERT/cross-encoder/SBERT code; TF-IDF+Ridge/GradientBoosting existed only in deleted scripts (git `f21dba4`, `c57e553`) trained on defective synthetic labels (v2 MAE 5.994, r 0.282; v1 MAE 0.017 with length leakage). Earlier "GPT-4o/Claude/Llama" results were **mock** simulations and are not evidence.

**Why those candidates (Day 22–23 reasoning, restated simply).**
- *TF-IDF + classical ML*: cheap, transparent baseline; if it wins, report it.
- *SBERT*: turns a sentence into a vector so meaning-similar sentences are close; good for "does the answer match the reference idea" even with different words; needs a scoring/evidence layer on top.
- *BERT/RoBERTa*: read the whole answer with context; fine-tuned to predict correct/partial/incorrect; RoBERTa is the stronger, better-trained successor of BERT, so BERT was deprioritised.
- *GPT/Llama*: generate structured marking evidence and feedback text; costly, variable, need prompt control; Llama is open-weight (privacy, no per-call fee), GPT is stronger but paid.
- *Cross-encoder*: reads question+answer pair together; accurate but slower; optional.

**Supervisor's "compare 2–3 candidate models and choose the best" instruction.** Written support exists (Day 22/23, Day 25 "Candidate model comparison before final selection", proposal §3.3/§3.5/SO6); the number "2–3" is your verbal report (R). Status: **NOT DEMONSTRATED**. The only executed comparison is token-recall baseline vs Condition E, both deterministic, on the repaired synthetic test set (n = 90): MAE 1.939 vs 3.544 — the *simpler* method wins; this is a limitation of the binary rubric adapter (E emits only 0 or full marks), not a claim that rubric marking is worse.

**What to say if asked "so which model is best?"** "I cannot honestly name one yet. I have a protocol: same data, same split, choose on validation only, test once, report even if TF-IDF wins. My next step is that experiment (08 §5)."

---
## Part F — Explainability (XAI) and original contribution
- **What is explainable now (V):** for every criterion the system names the rubric level, the concepts used, the evidence sentence ids and a text explanation; the lecturer sees the AI mark separately from the final mark. This is *transparent by construction* because the logic is rule-based.
- **What is not (V):** no learned-model explanation (no SHAP/attention/LIME) because no learned model is in the live path; explanation templates are fixed text; evidence sentences can be hit by a single shared word.
- **Original contribution (I, defensible wording):** not a new model. The contribution is an *integrated, explainable, lecturer-supervised pipeline* that ties one answer to rubric criteria, concept status, evidence sentences and a knowledge map, plus a rigorous dataset audit/repair and an evaluation protocol. Do not claim novelty of RoBERTa/SBERT/LLM use (Day 23 says the same).
- **Where it is still weak:** meaning-level evidence needs SBERT/RoBERTa/LLM; relationships in the map need CCKG; both are in the next phase.

---
## Part G — Evidence and honesty (data, results, limits)
- Dataset: original synthetic set 167 questions / 1,002 answers → audit found literal "nan" (252 answers), flat 10-mark labels (426), wrong rubric keys → deterministic repair: **576 eligible answers / 96 questions** (train 420, val 66, test 90), 355 quarantined, 71 controls held aside (576+355+71 = 1,002). Nothing was invented or reworded.
- Open failures (V): ratio-concentration 0.758 > 0.45 (val 1.0, test 0.917); length–mark Pearson 0.81; near-duplicate pair PP-SE3080-099 (train) / 107 (test), cosine 0.903; 391 of 487 criterion ids have no description.
- Results (V, test n = 90): lexical baseline MAE 1.939; Condition E 3.544; E emits only 0/full marks. Older claims (E 17.3 % better; baseline 5.609) do **not** reproduce — say so before an examiner finds out.
- Tests: Python 324 pass / 13 xfail / 0 fail; Node 90 = 75 pass + 15 todo; Neo4j live 5 pass; ruff 111 findings; ESLint 13 errors.
- Verified weaknesses: paraphrase of a full answer → 0/4; negation → 4/4; keyword stuffing → 4/4; padding gains nothing; empty → 0/4.

---
## Part H — Responsible AI use and what you must be able to explain
- Much of the code and the audits were produced with AI assistance (Claude Code; 29 commits carry a co-author trailer; proposal Table 33 discloses ChatGPT for planning/drafting). The lecture's five questions include "what AI assistance did I use and how did I verify it?" Answer truthfully: AI drafted code and reports; you verified by running 324+75 tests, reproducing numbers, and reading the key files; you decide scope.
- You must be able to walk through: `orchestrator.assess_answer`, `criterion_evaluator.evaluate_criterion`, `semantic/analyzer`, `reviewSubmission`, and the dataset repair idea. 09 Part D is your script.
- Never claim: validated dataset, LLM results, model comparison done, semantic understanding, supervisor approval of anything not signed, 100 % completion.
