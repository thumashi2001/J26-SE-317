# 08 PP1 readiness verdict and prioritised gaps

Labels: **V** verified (read or executed by me), **R** reported (document/earlier report, not reproduced), **I** inferred, **B** blocked. Feature status: IMPLEMENTED / PARTIAL / MOCKED / PLANNED / BLOCKED / NOT IMPLEMENTED.
Snapshot: branch `feature/c3-pp1-experiments-20261020`, HEAD `8fdbdbd`, identical to `origin` (V). Nothing in the repo was modified by this audit.

## 1. The verdict (read this first)
**C3 is conditionally ready to demonstrate at PP1, and not ready to claim a validated research result.**
- **PP1 viva demonstrability — CONDITIONALLY READY.** A real, tested, deterministic pipeline exists and works end to end: answer → processing → rubric-aware marking with criterion evidence and partial credit → concept diagnosis → templated explanation/feedback → concept map → lecturer review/override/finalize. Python 324 tests pass, Node 75 pass (V). It is conditional on: both services running the current code, a reachable Mongo and existing accounts (B: cannot be verified from here), and you staying inside the verified claims below.
- **Research validity — NOT READY for strong claims.** The only compared candidates are a token-recall baseline and a deterministic engine, on synthetic template-like data whose own validation fails (ratio-concentration 0.758 > 0.45; length–mark correlation 0.81; a train/test near-duplicate pair at cosine 0.903). On the repaired test split the **baseline beats Condition E** (MAE 1.939 vs 3.544). No LLM, RAG, semantic-model or multi-model result exists. No expert validation.
- **Production readiness — NOT READY.** Verified defects: client-supplied answer key/rubric trusted, forgeable token secret fallback, no batch ownership check, masked persistence failure, finalized results reopenable (AUDIT-B1…B9).
- **Against the "100 % of the approved individual component" expectation — NO.** The deterministic core of all five proposed capabilities exists, but the proposal's semantic-model comparison, LLM/RAG experiments, CCKG/C2/C4 integration and mind-map *relationships* are not delivered (table §3). The mark sheet itself only asks for "approximately 50 % where applicable" for the Excellent completion band, so you are ahead of the formal bar but behind your own panel's expectation. Say this plainly if asked.

## 2. What you can demonstrate reliably (verified outputs, executed offline)
Strongest two functions (the two "guaranteed" key functions in the team execution document §7.3; they also have the strongest test evidence):
1. **Rubric-aware marking with criterion evidence (and partial credit)** — `services/marking/{marking_engine,criterion_evaluator}.py`, `POST /c3/assess`. Verified results on the built-in presets:
   | Preset | Result | Why |
   |---|---|---|
   | `arch-full` | **4 / 4**, level L4 | all three concepts (high-level structure, components, relationships) found |
   | `arch-partial` | **2 / 4**, level L2 | only "high-level structure" found; components/relationships `not_demonstrated` |
   | `arch-zero` | **0 / 4**, level L0 | answer about cooking pasta, no concept found |
   | `oop-higher` | **3 / 3**, level L3 | polymorphism + runtime dispatch found |
   | `quality-multi` | **2 / 4** (C1 = L2, C2 = L0) | access control found, fault tolerance missing: two criteria scored independently |
2. **Answer processing + concept-level analysis** — `services/preprocessing`, `services/semantic/analyzer.py`: normalisation, sentence split, tokenisation, per-concept status (demonstrated / partial / not_demonstrated) with evidence sentence ids.
Third strongest (stretch, but heavily tested): **lecturer review / override / finalize** (`backend/src/modules/c3/services/submissionService.js`, UI `LecturerReviewPage.jsx`): original `automated_mark` preserved, mandatory override reason.

## 3. Feature status against the approved scope
| Capability (proposal) | Status | Evidence / gap |
|---|---|---|
| Answer processing | IMPLEMENTED (lexical) | `text_normalizer.py`; no OCR (explicitly rejected, HTTP 400) |
| Semantic answer analysis | **PARTIAL** | Runtime "semantic" analysis is token overlap; no embedding/transformer on the `/c3/assess` path (V). `reference_similarity` is computed but unused in marking |
| Rubric-aware marking + partial credit | IMPLEMENTED | verified table above; known bugs AUDIT-M1/M4/M5 (strict xfail tests) |
| Concept identification (demonstrated/partial/missing) | IMPLEMENTED (lexical) | blind to paraphrase and negation (below) |
| Explainable marking evidence | IMPLEMENTED | per-criterion level, supporting concepts, evidence sentence ids, templated explanation |
| Feedback generation | IMPLEMENTED (rule-based) | templated strings, no generative model |
| Answer-derived mind map | **PARTIAL** | star graph: root → each concept (type `child`), coloured by status; no concept↔concept relationships, no CCKG |
| Lecturer support & verification | IMPLEMENTED with defects | AUDIT-B2/B3/B5, no history array, overwrites on re-review |
| Result storage / traceability | IMPLEMENTED | Mongo; persistence failure masked as 200 (B6) |
| MCQ deterministic marking | IMPLEMENTED (in **Node**) | a second marking engine outside Python; answer key supplied by client (B8) |
| C1 integration | PARTIAL | direct DB event write (provisional/finalized), not an API contract |
| C2 / C4 integration | NOT IMPLEMENTED | spec README only; Node `c2`/`c4` folders empty |
| CCKG / Neo4j | PARTIAL (infrastructure) | live Neo4j + 5 passing live tests, but not on the marking path |
| RAG / LLM / multi-LLM | PARTIAL code, **never executed on the dataset**; BLOCKED by API quota/credits | providers real (Gemini/OpenAI/Ollama); former mock experiments are MOCKED and invalid as evidence |
| Experimental evaluation vs human/reference | PARTIAL | baseline vs E on synthetic labels; **no QWK anywhere** (proposal's first-listed metric); no human gold |

## 4. Verified limitations to know cold (executed offline on `arch-full`)
| Probe | Result | Meaning |
|---|---|---|
| Correct paraphrase, no shared words | **0 / 4** | lexical matching misses synonyms |
| "Does **not** define … nothing to do with components" | **4 / 4** | negation not detected (AUDIT-S1) |
| Keywords listed with no explanation | **4 / 4** | keyword stuffing rewarded |
| Correct answer + long irrelevant padding | 4 / 4 | length itself is not rewarded (good) |
| Empty answer | 0 / 4 | handled |
These are the honest reason a semantic model / LLM / evidence-aware condition is research-worthy — present them as the motivation for the comparison work, not as hidden defects.

## 5. Original model plan vs reality, and the supervisor's multi-model instruction — status: **NOT DEMONSTRATED** (infrastructure PARTIAL)
**Where the instruction is written (V):** Day 22 (candidate comparison), Day 23 (final selection + experimental hierarchy), Day 23 Experimental Design, Day 25 ("Candidate model comparison before final selection", "RAG vs non-RAG under matched conditions"), proposal §3.3/§3.5/SO6 and Table 4. None says "2–3" or fixes PP1 vs later; "2–3 candidates" is your verbal report (R).

**What the original plan said (Day 23 hierarchy):**
| Level | Planned candidate | Role |
|---|---|---|
| L0 | TF-IDF + classical ML | transparent baseline |
| L1 | RoBERTa-base | contextual encoder for marking |
| L2 | SBERT | semantic comparison with reference answer |
| L3 | GPT- or Llama-family (conditional) | structured marking evidence + feedback |
| L4 | integrated C3 pipeline | proposed system |
| optional | BERT, cross-encoder | extra baselines |
Planned datasets: EngSAF (0/1/2 labels, unseen-answer and unseen-question splits), ASAP-SAS, Mohler, ASAG2024. All four exist on your disk (`Desktop\Reserach\Data sets\`) but **none was used**.

**What actually exists (V, git grep + history):**
| Candidate | Status |
|---|---|
| L0 TF-IDF + Ridge/GBR | PARTIAL: trained on the *synthetic* set (scripts deleted from HEAD; `f21dba4`, `c57e553`); v1 MAE 0.017 (length leakage, suspect), v2 MAE 5.994, r 0.282; never re-run on repaired data |
| RoBERTa / BERT / cross-encoder | NOT IMPLEMENTED (no code, no torch/transformers) |
| SBERT | NOT IMPLEMENTED (remote Gemini/OpenAI embeddings only, for RAG; never run) |
| GPT / Llama | PARTIAL code (OpenAI, Gemini, Ollama providers, cache, preflight); never run on the dataset; BLOCKED by quota/credits. Earlier "GPT-4o/Claude/Llama" results were **MOCK** |
| L4 pipeline | IMPLEMENTED (lexical core), executed offline |
| RAG vs non-RAG | code only; never run |
| Extra, executed | lexical token-recall baseline (MAE 1.939) and Condition E (3.544) on repaired test n = 90 |

**Verdict:** no valid comparison of the *planned* candidates has been run, and no documented evidence-based "best model" selection exists. The only valid executed comparison is two deterministic methods on a synthetic set, and the simpler one wins. DEC-06 (synthetic data instead of benchmarks) contradicts proposal §3.2 / Day 23 and is self-recorded, not supervisor-signed.

**Required for PP1?** Repo documents (COM-07, DEC-07, proposal "Should Have") defer LLM/RAG comparison to Phase 4; no written supervisor decision makes it a PP1 deliverable. Ask the supervisor to confirm in writing.

**Honest answer to say aloud:** "My Day 22–23 plan was TF-IDF baseline, SBERT, RoBERTa and a GPT/Llama model, compared on EngSAF and other benchmarks. For PP1 I built and verified the deterministic pipeline and audited my own dataset. The transformer and LLM comparison is not yet run; here is the protocol."

**Next-experiment plan (plan only, nothing executed; needs approval for installs/downloads/compute):** primary task = EngSAF answer-correctness (0/1/2), secondary = repaired synthetic set. Candidates: C1 TF-IDF + logistic/ridge, C2 SBERT embeddings + classifier, C3 RoBERTa-base (fine-tune if GPU, else frozen features), optional C4 LLM judge when quota exists. Same preprocessing/labels/splits; choose on **validation only** with a pre-registered rule (Macro-F1, ties → QWK); evaluate unseen-answer and unseen-question test sets once; paired bootstrap over questions; record seeds, library versions, checkpoints; report if TF-IDF wins. Then feed the winning semantic score into concept-status evidence while marks still come from rubric levels.

## 6. Twelve readiness categories (no averaged percentage)
| # | Category | Status | Key evidence / gap | Minimum before viva |
|---|---|---|---|---|
| 1 | Proposal & mark-sheet compliance | Conditionally ready | LO1 strong; LO2 needs technology justification; LO3 mixed; LO5 thin (no market evidence) | rehearse LO-by-LO answers (file 02) |
| 2 | Core functional requirements | Conditionally ready | deterministic core works; semantic/relationship gaps | state "baseline-first" honestly |
| 3 | Novelty & methodology | Conditionally ready | DSR + experiments planned; experiments incomplete | explain what is done vs planned |
| 4 | Dataset validity | **Not ready** for strong claims | 0.758, 0.81, 0.903 pair, templated text, DEC-06 conflicts with proposal §3.2 | disclose; do not claim generalisation |
| 5 | Evaluation reproducibility | Conditionally ready | baseline/E reproduce offline; legacy 5.609 baseline does not; no QWK | present only reproducible numbers |
| 6 | Architecture & integration | Conditionally ready | C3 internals sound; C2/C4/CCKG not integrated | show boundary diagram, say "planned" |
| 7 | SOLID & maintainability | Conditionally ready | strong pure core + provider abstraction; god components, Node MCQ engine, singletons | prepare honest SOLID answers (file 04) |
| 8 | Security & reliability | Not ready (production); acceptable for PP1 demo | B1–B9 | do not demo with real data; mention as known issues |
| 9 | Automated testing | Ready for PP1 | 324 py + 75 node + 5 live Neo4j; ruff 111, ESLint 13; green ≠ end-to-end | quote counts exactly |
| 10 | Demo & UI workflow | Conditionally ready | needs Python:8003, Node:3000, Mongo, accounts (B) | pre-flight checklist (file 11) |
| 11 | Documentation & traceability | Conditionally ready | ~29 stale docs; contradictory counts; DEC/COM provenance internal only | use only file 09/12 numbers |
| 12 | Viva explanation & defence | Ready if you study files 09–12 | five hardest questions below | rehearse aloud |

## 7. Top five likely examiner criticisms (with the honest answer)
1. **"Where is the AI/semantic model?"** The runtime pipeline is lexical and rule-based (V). Answer: deliberate baseline-first design; the abstractions for embeddings/LLMs/RAG exist and are tested with stubs; real runs are blocked by quota and deferred by COM-07; the paraphrase/negation probes show exactly why they are the next step.
2. **"Why should we trust your evaluation?"** Synthetic template-like data, failing ratio check, a leaking pair, baseline beats E, no QWK, no human labels. Answer with the audit's own findings and the validation-only/test-once protocol you will follow.
3. **"You promised to compare models/approaches."** Only baseline vs E done; comparison planned (Phase 4); say what is done, what is missing, and the plan.
4. **"Is it integrated with C1/C2/C4/CCKG?"** C1 partial (event bridge), C2/C4 not, CCKG not on the path. Do not claim otherwise.
5. **"Did you write this? How did you verify AI help?"** Large parts were AI-assisted (29 commits carry a Claude co-author trailer, V). You must explain every module you show, name what AI did, and how you verified it (tests, audits, executed probes). Prepare the AI-use record (lecture slide 19/21).
Also likely: commercialisation evidence (LO5) and "partial credit — show me".

## 8. What not to claim
"Fully repaired/validated/ALL PASS"; "semantic understanding"; "E beats the baseline" or "17.3 % better"; "LLM/RAG/GraphRAG results"; "mind map shows relationships" (star graph only); "integrated with C2/C4/CCKG"; "expert-validated"; "QWK = …"; "100 % complete"; "secure/production-ready".

## 9. Minimum preparation before the viva (ordered)
1. Start both services from the current code and run the verified presets once (kill any stale process on port 8003 — an older version was listening earlier in this session).
2. Confirm Mongo connectivity and that student + lecturer accounts exist (B).
3. Rehearse file 12 (60 s / 2 min / 5 min) and the 10 hardest questions in file 10 aloud.
4. Prepare the AI-use record and a one-slide business-potential pitch (LO5).
5. Prepare screenshots/logs for the fallback path (file 11).
6. Ask your supervisor to confirm in writing: (a) the multi-model comparison timing, (b) synthetic data as primary data, (c) A–F scope.

## 10. Deferred safely until after PP1
Real LLM/RAG/multi-LLM runs; scoring-level authoring for B–F; QWK; backend security fixes; adapter for the repaired dataset; CCKG population; C2/C4 contracts; doc clean-up.
