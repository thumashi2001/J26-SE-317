# 10 Viva questions and model answers (56 Q&A, 10 groups)

Format: **Q** → *Spoken answer* (say this) → Evidence (where to point) → Caveat/follow-up. All numbers verified at commit `8fdbdbd` unless marked R (reported) or I (inference). Keep answers short; offer detail only if asked.

---
## Group 1 — Problem, gap, objectives
**1. What problem does C3 solve?** *Marking written answers is slow and inconsistent, and a bare score does not tell students which ideas they missed. C3 proposes a mark against a lecturer rubric, shows the evidence, lists demonstrated/partial/missing concepts, writes feedback and a concept map; the lecturer decides.* Evidence: proposal pp.3, 13, 26. Caveat: survey (App. 7) is about learning progress, not marking.

**2. What is your research gap?** *No integrated, experimentally validated work that combines rubric-aware semantic marking, concept-level diagnosis, explainable evidence and automatic conversion of answers to structured knowledge.* Evidence: proposal p.26 (exact wording).

**3. State your objectives.** *One main objective and six specific ones: semantic analysis, rubric-aware marking with evidence, concept-level analysis, explainable feedback, mind-map generation, and experimental evaluation against baselines.* Evidence: proposal p.27. Caveat: SO6 (evaluation) is the least complete.

**4. What are your research questions?** *The proposal states a research direction without numbered RQs; my Day 2 and Day 18/23 documents define RQ1–RQ6 and hypotheses H1–H5 (accuracy vs human marking, semantic vs keyword, RAG effect, LLM comparison, concept-level correctness, usefulness of maps).* Evidence: Day 2 pp.6–7; Day 23 design doc. Caveat: say this openly — the proposal itself lists none.

**5. Which two functions are you demonstrating for PP1?** *(1) Answer processing + semantic analysis; (2) rubric-aware marking with evidence. Concept diagnosis, feedback and the map build on them.* Evidence: team execution doc §7.3 (not in the proposal). Caveat: the choice comes from a team document.

**6. What is novel here?** *Not the models. The contribution is an explainable, lecturer-supervised pipeline connecting answer → rubric criterion → concept evidence → knowledge map, together with a rigorous evaluation protocol and dataset audit.* Evidence: Day 23 ("not claiming model novelty"). Caveat: novelty is of integration, and integration with C2/C4/CCKG is not built.

---
## Group 2 — Scope, requirements, decisions
**7. How many requirements do you have and which count is authoritative?** *The proposal lists 46 functional and 30 non-functional requirements; my Day 6 catalogue lists 96 finer-grained FRs. The proposal numbers are the formal ones.* Evidence: proposal pp.40–49; Day 6. Caveat: the two systems are not cross-referenced (03).

**8. Why is OCR excluded?** *In the repo OCR is excluded and image upload returns HTTP 400. The proposal lists OCR as Should-Have, so I treat it as deferred, not removed.* Evidence: `c3Controller.js:51-69`; proposal p.49. Caveat: decision COM-05 is internal; the TAF contains no such comment.

**9. Who approved your decisions (COM-xx, DEC-xx)?** *They are recorded in my project's decision log. I do not have signed minutes; the supervisor meeting sheet has blank decision fields.* Evidence: `PROPOSAL_COMMENT_RESPONSE_MATRIX.md`; Downloads supervisor sheet. Caveat: never say "the panel approved" without a record.

**10. Why synthetic data instead of the benchmarks in your proposal?** *Synthetic data lets me control answer quality for SE topics, but I accept it conflicts with proposal p.30, which says synthetic data will not replace real benchmark evidence. EngSAF, ASAP-SAS, Mohler and ASAG2024 are on disk and are the next experiment.* Evidence: DEC-06; proposal p.30; `Data sets\`. Caveat: this is the weakest research-design point.

**11. Is 100 % of the component complete?** *No. The deterministic core of all five capabilities works end to end. The model-comparison layer and C2/C4/CCKG integration are not done. The mark sheet's completion criterion says about 50 %.* Evidence: 08 §3; mark sheet. Caveat: do not say "100 %".

**12. What did the supervisor ask you for?** *To compare candidate models before choosing one (documented in Day 22/23/25 and proposal §3.3). I did not run it for PP1 because LLM/RAG conditions were deferred (COM-07), and here is the protocol I will follow.* Evidence: 08 §5. Caveat: "2–3 models" is my recollection of a verbal instruction (R).

---
## Group 3 — Model selection and comparison (expect these)
**13. Which models did you plan?** *TF-IDF + classical ML baseline, RoBERTa-base, SBERT, and a GPT- or Llama-family model; BERT and a cross-encoder as options.* Evidence: Day 23 hierarchy L0–L4.

**14. Which did you train or test?** *Only the baseline family: TF-IDF with Ridge/gradient boosting on my synthetic data, plus a lexical token-recall baseline and my deterministic Condition E. Transformers and LLMs are not run.* Evidence: git `f21dba4`, `c57e553`; `evaluate_repaired.py`. Caveat: the TF-IDF models were trained on labels later found defective; they were never re-run.

**15. Why SBERT rather than BERT?** *BERT gives token-level representations and is awkward for comparing two texts; SBERT is trained to give one sentence vector so similarity is a cheap cosine. For "does this answer match the reference idea" SBERT is the natural tool.* Evidence: proposal lit. review (SBERT [12]); Day 22. Caveat: not yet benchmarked by me.

**16. Why RoBERTa?** *It is an improved BERT (more data, better training), so it is the stronger encoder to fine-tune for correct/partial/incorrect.* Evidence: Day 23 L1.

**17. Why a GPT or Llama model?** *They generate structured marking evidence and feedback in natural language. Llama is open-weight (privacy, no per-call fee); GPT is stronger but paid. Choice depends on access, cost and reproducibility.* Evidence: Day 23 "conditional select"; providers in `services/llm/`.

**18. How would you choose the best model?** *Same dataset, preprocessing, labels and splits for all candidates; choose on the validation set only with a rule fixed beforehand (Macro-F1, ties by QWK); evaluate on the test sets once; paired bootstrap over questions; report even if TF-IDF wins.* Evidence: 08 §5.

**19. Which model is best right now?** *I cannot honestly name one — that comparison is not run. The only executed comparison is my lexical baseline versus my rubric engine on synthetic data, and the baseline is better.* Evidence: `metrics_report.json` (1.939 vs 3.544).

**20. Isn't it a problem that your system loses to a baseline?** *It is a finding, not a failure to hide: my engine emits only 0 or full marks in that experiment because the dataset has no scoring levels, so it cannot match the graded labels. It shows exactly what to fix: multi-level rubrics.* Evidence: 06; `criterion_evaluator.py:21-32`.

**21. Why not just use ChatGPT?** *A single LLM score is not explained by the rubric, can vary between runs, is costly, and sends student data out. I plan LLMs as one candidate within a controlled comparison, and the lecturer keeps authority.* Evidence: proposal pp.14, 28. Caveat: no LLM result of mine exists.

**22. Where did the earlier "GPT-4o / Claude / Llama" numbers come from?** *They came from mock simulations in an earlier phase and are not evidence. I removed the mock provider and never cite them.* Evidence: git `8cad340`; `C3_REAL_VS_MOCK_MODEL_INVENTORY.md` (superseded).

---
## Group 4 — How the system works
**23. Walk me through one answer.** *Clean text → sentences → words; for each expected concept count matching words; for each rubric criterion pick the highest level whose required concepts are evidenced; add marks; write feedback; draw the map.* Evidence: 09 Part C/D.

**24. Is it semantic?** *Not yet. It matches words, which is a lexical proxy. Paraphrase scores 0/4 and negation can score full. Semantic comparison (SBERT/RoBERTa/LLM) is planned.* Evidence: probes on `arch-full`; `semantic/analyzer.py`. Caveat: the module is named "semantic" — be explicit.

**25. How are partial marks decided?** *By the rubric's explicit levels: the highest level whose required concepts are evidenced. Marks are never a percentage formula.* Evidence: `criterion_evaluator.py:155-184`; `arch-partial` = 2/4.

**26. What exactly is "explainable" about it?** *It states the selected level, the concept evidence, the sentence ids and a reason; the lecturer sees AI mark and final mark separately. It is transparent because it is rule-based, not because it explains a neural model.* Evidence: criterion explanation template `criterion_evaluator.py:132-152`.

**27. What happens if the rubric is wrong?** *A cross-field invalid rubric currently returns HTTP 500 instead of 422 on `/c3/assess` (known bug AUDIT-A1).* Evidence: `test_api_audit.py:76-93`. Caveat: a one-handler fix is planned.

**28. How does the mind map work?** *A root node for the question and one node per concept coloured by status, joined root→concept.* Evidence: `relationship_builder.py`. Caveat: it is a star, not relationships between concepts; relationships need CCKG.

**29. Where do LLM and RAG fit?** *They are experiment conditions A–D/F, not on the live path. Provider code, caching and preflight exist; quota blocked any run.* Evidence: `experiments/conditions.py`; Gemini free tier ≈20 requests/day.

**30. What is Condition E?** *My deterministic rubric engine: concept evidence + rubric levels. It is the PP1 baseline and also what the live endpoint runs.* Evidence: `AGENTS.md:57`.

---
## Group 5 — Data and validity
**31. Describe your dataset.** *167 questions and 1,002 answers over software-engineering topics, six quality variants per question, researcher-constructed. After audit, 96 questions / 576 answers are eligible.* Evidence: `DATASET_CARD.md`.

**32. What was wrong with it?** *Literal "nan" in 252 answers, 426 answers with flat 10-mark labels, and wrong rubric keys. I repaired them deterministically with hashes, quarantining rather than guessing.* Evidence: `repair_manifest.csv`.

**33. Is the dataset validated?** *No. It still fails ratio-concentration (0.758 > 0.45), mark correlates with length (0.81), and one near-duplicate question pair spans train and test.* Evidence: `validation_report.json`; `reports/read_only_audit/03`.

**34. Is there data leakage?** *One known near-duplicate pair (PP-SE3080-099 train / 107 test, cosine 0.903) and 9 unflagged duplicate answers across questions. Not removed, because I do not change splits without approval.* Evidence: audit 03.

**35. Who labelled the data?** *The labels are researcher-constructed from answer quality tiers; there is no expert annotation.* Evidence: dataset card. Caveat: never call it ground truth.

**36. Why only 90 test answers?** *The eligible test split shrank after quarantine, from 15 questions × 6 answers; results are indicative only.* Evidence: `metrics_report.json`.

**37. Could you use real student data?** *Not without ethics approval and SLIIT permission (proposal p.30). Benchmarks are the lawful interim.* 

---
## Group 6 — Evaluation and metrics
**38. Which metrics do you use?** *MAE, RMSE, correlation and within-tolerance now; the proposal also lists QWK, accuracy, precision/recall, Macro-F1, feedback and map quality.* Evidence: proposal Table 5. Caveat: QWK is not implemented anywhere.

**39. What is MAE here?** *The average absolute difference between the system's mark and the labelled mark, in marks; baseline 1.939, rubric engine 3.544 on 90 answers.*

**40. What is QWK and why do you need it?** *Quadratic weighted kappa measures agreement on ordered scores, penalising big disagreements more; it is the standard for graded marks and will be added.*

**41. Why do your numbers differ from older documents?** *The older documents used the defective labels and a run where 15 failed calls were scored 0. I could reproduce one legacy figure only that way and could not reproduce 5.609 at all (got 5.369). I report the recomputed numbers.* Evidence: audit 04.

**42. How do you know the repair did not tune results?** *The repair never looks at the system output; it is rule-based, hash-verified, and the archive of the original is kept.* Evidence: `SHA256SUMS`; `repair_c3_dataset.py`.

**43. What would a fair comparison look like?** *08 §5: same splits, validation-only selection, single test run, fixed seeds, versions recorded.*

---
## Group 7 — Software engineering quality (SOLID, testing)
**44. Does the code follow SOLID?** *The core is strong on dependency inversion: marking, feedback and map packages import only schemas and each other, and LLM providers sit behind an abstract class. Weaknesses: duplicated helpers, a long orchestrator function, singletons, and a second marking engine in Node.* Evidence: 04.

**45. Show a SOLID problem you know about.** *`assess_answer` (95 lines) re-implements `mark_answer` and has a self-comparing "authority" check; the `_analysis_request` helper exists three times.* Evidence: `orchestrator.py:49-143`, `:17`, `marking_engine.py:14`, `generator.py:25`.

**46. How do you know it works?** *324 Python tests, 75 Node tests pass; known bugs are encoded as strict xfail/todo tests; 5 live Neo4j tests pass; plus my hand-verified demo outputs.* Evidence: pytest/npm output.

**47. Why are there failing/expected-fail tests?** *They document known defects (AUDIT-id). If I fix one, its test starts passing and the marker must go — that prevents silent regressions.*

**48. What about lint?** *Ruff 111 findings (101 are line length) and ESLint 13 errors are reported, not fixed.*

---
## Group 8 — Security, reliability, lecturer control
**49. Who can mark or override?** *Only lecturer/admin roles; override requires a reason; the automated mark is stored separately.* Evidence: `routes/index.js:19-20`; `submissionService.js:332-413`.

**50. Can a student cheat the system?** *Today the browser supplies the answer key and rubric, so a student could self-grade an MCQ (known AUDIT-B8). Results still need lecturer review.* Evidence: `c3Controller.js:59-99`. Caveat: fix = server-side question bank.

**51. Other known security issues?** *Token secret fallback when AUTH_SECRET is unset, no batch ownership check, operator injection through batch id, persistence failures masked as success, override unbounded.* Evidence: `auth.js:12-21`; AUDIT-B1–B9, X1. Caveat: unfixed, not hidden.

**52. Is student data protected?** *Roles and hashing exist; no logging of answers in the Python service; but there is no rate limiting and CORS is open.* Evidence: 05.

---
## Group 9 — Integration, commercialisation, AI use, future
**53. Does C3 talk to the other components?** *C3→C1 events work (direct database write, provisional then finalised). C2→C3, C3→C4 and the CCKG are documented contracts only.* Evidence: `integration/c3-c1`; `integration/c2-c3/README.md`.

**54. What is the business case?** *B2B institutional SaaS for universities with large cohorts: lecturers save marking time, students get concept-level feedback; subscription plus optional usage pricing; human-supervised. I have no market data yet — pilots and interviews would provide it.* Evidence: proposal pp.51–59. Caveat: descriptive only.

**55. What AI assistance did you use and how did you verify it?** *I used Claude Code for implementation and audits, and ChatGPT for planning/drafting (proposal Table 33). I verified by running the test suites, reproducing numbers, and reading the main files; I decide scope and I can explain each stage.* Evidence: git trailers on 29 commits. Caveat: be truthful and calm.

**56. What will you do next?** *Run the EngSAF experiment (TF-IDF vs SBERT vs RoBERTa, optional LLM), select on validation, test once; build multi-level rubrics; add QWK; fix the security todos; integrate C2/C4 via the agreed APIs.* Evidence: 08 §5, §9.
