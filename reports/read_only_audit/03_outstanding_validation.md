# 03 Outstanding validation issues and the 71 IRRELEVANT controls

Labels: V verified (recomputed), R reported, I inferred, B blocked. Recomputation scripts: scratchpad `audit/independent.py`, `independent2.py`; delegated partial results `audit/agentA/*.csv` were cross-checked against them.

## 0. The 71 repaired IRRELEVANT controls
| Check | Result | Label |
|---|---|---|
| Policy defines IRRELEVANT = 0 | `datasets/README.md` (git `f21dba4`) line 57: "IRRELEVANT … 0 marks (0.0)"; old card: "0%" | V |
| Texts are meta-statements without domain content | all 71 are one sentence ("The response discusses an unrelated software topic and does not address the concepts requested in the question."); content-word overlap with the question/concepts: 0 words for 53 of 71 rows, 1–2 generic words ("software", "question") for the other 18; no technical content | V |
| Original text/label/split preserved | `repaired_ineligible_controls.csv` differs from the original only in `marks`, `expected_mark`, `criterion_marks`, `dataset_version` (71 each; 284 field diffs) | V |
| Repaired mark = 0 | 71/71 are 0.0 with zero criterion marks | V |
| Leak into eligible train/val/test | 0 (disjoint ids) | V |
| 96 canonical IRRELEVANT rows | all 0.0; a single constant sentence | V |
| Rule "contains *unrelated* ⇒ IRRELEVANT" | original: precision 0.994, recall 1.0 (167 TP, 1 FP among 1,002); eligible set: 0.990 / 1.0. It is a data pattern, not implemented as a rule in code. The one false positive is a non-IRRELEVANT answer containing the word. | V |
| Conflicts found | none requiring a label change. Caveat: the control text is a label-like string, not realistic off-topic prose (INFERRED limitation). | V/I |

## A. Ratio-concentration (hard check, FAILING)
- Definition (V): `datasets/repair/common.py::ratio_concentration` – labels `expected_mark/max_marks` rounded to 3 dp, only values with 0 < r < 1, share of those on the 7 most frequent values. Threshold 0.45 in `datasets/repair/validation_spec.json` (copied unchanged from the removed `tier_spec.json`); implemented as a **hard** check in `validate_repaired.py`.
- Recomputed (V): eligible n = 576, n_inner = 380 (99 labels at 0, 97 at 1), 37 distinct inner values, top-7 = 0.8 (163), 0.6 (52), 0.85 (24), 0.84 (18), 0.667 (12), 0.55 (10), 0.9 (9) → **0.7579**. Per split: train 0.728, validation **1.000** (44 inner labels), test **0.917** (60 inner labels). Original all-1,002: 0.7579 (identical, because the replacement block's labels are all 0 or 1 and excluded). So the repair neither caused nor fixed it.
- Meaningfulness (I): the metric rewards spread; mark schemes here come from criterion allocations, so labels cluster (0.8 = a one-criterion deduction in a 5-criterion allocation). A uniformly random integer-mark scheme would itself give ≈0.51–0.65 (agent simulation), so 0.45 is strict even for a spread-out scheme. It is a distribution diagnostic dressed as a hard integrity check.
- Recommendation: do not change the number or labels without approval. Present it as a documented statistical limitation of researcher-constructed labels (decision row 1).

## B. Answer length vs mark (spec limit 0.4)
- Definition (V): words = `len(student_answer.split())`; y = `expected_mark/max_marks`.
- Recomputed (V): Pearson **0.8107**, Spearman 0.793; vs raw mark Pearson 0.615. Without IRRELEVANT (all 12 words, mark 0): 0.576. Without the two flagged 100-mark questions: 0.826 (delegated: with all three 100-mark questions 0.842). Mean within-question Pearson 0.918. Tier means: FULL 75.5 words / 1.00; MOSTLY 60.8 / 0.787; PARTIAL 43.1 / 0.623; MISSING 73.4 / 0.787; MISCONCEPTION 77.3 / 0.787; IRRELEVANT 12.0 / 0.0.
- Interpretation (I): the correlation is a construction artefact: PARTIAL answers are short but MISSING/MISCONCEPTION (long, low-ish marks) share MOSTLY's marks; the IRRELEVANT constant sentence is the shortest and scores 0. It is also present in the original canonical data (0.811), so the repair did not create it. A length-aware baseline (lexical overlap) will look strong for this reason. No record was removed to improve it.

## C. Cross-split similar questions
- Validator method (TfidfVectorizer on the 96 eligible question texts) reproduces **0.9034** for `PP-SE3080-099` (train) vs `PP-SE3080-107` (test); with English stop-words 0.9037; with unigram+bigram 0.8336 (V). Next pairs: 0.644 (`PP-SE3060-015` train / `-045` validation), 0.602, 0.601.
- The pair: same "Company XYZ owns an ERP system…" scenario, both 25 marks, identical expected concepts `["Java RMI","remote object","RMI registry"]`, token Jaccard 0.742, and near-identical templated FULL answers (V). **Near duplicate with train/test leakage risk (I: high)**. Not an exact duplicate. Records preserved; reassigning requires approval (decision row 5).

## D. Rubric criterion ids
- Recomputed (V): 487 distinct criterion ids in eligible answers; **96 resolve, 391 do not**. All 96 resolved ids are the single question-level `…-C01` row; **all 391 unresolved are sub-criteria C02–C09** (C02 95, C03 94, C04 86, C05 80, C06 29, C07 5, C08 1, C09 1; 205 synthetic, 186 past-paper).
- The rubric file holds exactly one row per eligible question (96/96, V) with the full allocation; for 96/96 FULL answers the sum of criterion marks equals that rubric total (V). 95 of 96 questions have more than one criterion in their answers; marks per criterion exist but their descriptions do not.
- The 8 re-keyed rows map `X → SYN-REPL-X` correctly by `source_replaced_question_id` (V) but keep `rubric_id`/`criterion_id` of the replaced original (e.g. `R-PP-SE3040-007-v2-C01`) and its allocation (does not sum to the replacement's 10 marks): all on ineligible questions.
- Consumers: `datasets/repair/validate_repaired.py` (criterion_id_map, reported as WARN) and `evaluate_repaired.py` (uses only the single question-level criterion). **Criterion-level (rubric-aware) evaluation is NOT trustworthy now:** only total marks are supported (I, strong).

## E. Duplicate-text review queue
Four answers (V): `PP-SE3010-089` MOSTLY_CORRECT and PARTIAL (identical text, both 20.0; FULL 25); `PP-SE3080-102` FULL and PARTIAL (identical text, both 20.0; siblings MOSTLY/MISSING/MISCONCEPTION = 0). All in train. Same-text/same-mark pairs are label-consistent, but `PP-SE3080-102` is internally inconsistent (PARTIAL = FULL, MOSTLY = 0). Flagged `needs_review`, kept; no rewriting (decision row 6).

## F. Scope review
`PP-SE3040-001` (validation) and `-002` (train): 100 marks, "develop a web application" with UI, REST services, unit test and coding-quality marks → require code (V from text). Flags correct. **`PP-SE3040-009` (100 marks) matches the same pattern but is not flagged** (V keyword evidence: "implementation of", "unit test"). Other eligible questions with code/diagram keywords (I, keyword evidence only): `PP-SE3040-003` ("given code"), `PP-SE3060-013`, `-050` (XQuery), `PP-SE3070-028`, `PP-SE3010-085` ("code snippet", 74 marks), `-087`, `-088`, `PP-SE3010-095` (unit test). The scope flag set is incomplete (decision row 7).
