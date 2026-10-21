# C3 dataset repair — Phase 1 baseline (read-only inspection)

Scope: repair the **existing** C3 research dataset (`C3-Phase3-v5-FINAL`); no replacement dataset, no new questions or answer variants.
All numbers below were computed from the files by a read-only script on 2026-10-21 and are labelled **verified by execution**.

## 1. Which files are authoritative

| Version | Location | Status |
|---|---|---|
| Original `C3-Phase3-v5-FINAL` | git `f21dba4` `ai-services/c3/datasets/synthetic/*`; byte-exact copy in `datasets/archive/C3-Phase3-v5-FINAL_original/` (SHA256SUMS.txt) | **Authoritative source.** The committed blobs and the pre-repair backup are identical after line-ending normalisation. |
| Earlier in-place repair (never committed) | `datasets/archive/earlier_inplace_repair_20261020.zip` | **Not authoritative.** It rewrote 436 answers and invented marks (see §4). Kept for audit only. |
| Derived artefacts | `controlled_answers_{train,validation,test}.csv`, `question_bank_{train,validation,test}.csv` | Derived from the master files; ids verified identical to the master per split. |
| QA/summary files | `04_ORIGINAL_63_REPLACEMENT_AUDIT.csv`, `05_FINAL_QA_RESULTS_ALL_PASS.csv`, `06_FINAL_SUMMARY.csv`, `00_MANIFEST.json` | Documentation of the original; the "ALL PASS" claims are not supported (§3). |

## 2. Actual counts (original) — documentation counts of 169/1,014 are wrong

167 questions · 1,002 answers (exactly 6 per question: FULL, MOSTLY_CORRECT, PARTIAL, MISSING_CONCEPT, MISCONCEPTION, IRRELEVANT) · 230 rubric rows · splits (question-disjoint): train 117 q / 702 a, validation 25 q / 150 a, test 25 q / 150 a.
Answer columns (31): ids, question/rubric text, `marks`, `expected_mark`, `reference_answer`, `criterion_marks`, `student_answer`, `answer_quality`, concept lists (`demonstrated/missing/incorrect_concepts`), `evidence_spans`, provenance (`generation_method`, `variant_rationale`, `dataset_version`, `annotation_status`, `content_qa_status`, `validation_claim`), `split`.

The data falls into three groups with very different quality:

| Group | Questions | Answers | train/val/test answers | State |
|---|---|---|---|---|
| **Canonical** (47 past-paper + 49 native synthetic) | 96 | 576 | 420 / 66 / 90 | Marks vary by tier and equal the sum of per-criterion marks. Mostly usable. |
| **Replacement block A** (63 replaced diagram questions, `04_ORIGINAL_63_REPLACEMENT_AUDIT.csv`) | 63 | 378 | 252 / 78 / 48 | Defective: literal `nan` in 252 answers, flat 10.0 mark on all six tiers, constant sentences. |
| **Replacement block B** (8 more `SYN-REPL-*`) | 8 | 48 | 30 / 6 / 12 | Defective: placeholder concepts (“conceptual understanding; supporting evidence…”), flat 10.0 marks, constant sentences, rubric rows keyed to the wrong ids. |

## 3. Findings (original files) — each verified against the data

| # | Concern | Affected | Evidence | Recoverable? |
|---|---|---|---|---|
| F1 | **Literal `nan` answers**: 63 FULL answers are exactly `"nan"`; 63 MOSTLY_CORRECT start with `nan `; 63 PARTIAL and 63 MISSING_CONCEPT contain `nan` where a concept name should be | 252 answers, all in block A | The concept slot was empty in the source (`demonstrated_concepts` is also `"nan"` in 189 rows). No other file contains the lost text. | **No.** The original FULL answer text does not exist anywhere; reconstructing it from the reference answer would be fabrication. → quarantine. |
| F2 | **Flat marks**: all six tiers of every replacement question have `expected_mark = 10.0` (incl. IRRELEVANT and MISCONCEPTION); `criterion_marks` is positional text `5,5` for all six | 426 answers (71 questions) | MISCONCEPTION ratio distribution: 1.0 ×71; IRRELEVANT non-zero ×71 | **IRRELEVANT only**: documented label policy (card + README: IRRELEVANT = 0) and the answer text itself states it is off-topic. Other tiers: no rubric/answer evidence supports any specific mark → quarantine. |
| F3 | **Rubric ↔ question key mismatch**: 8 rubric rows keyed `PP-SE3020-035`, … `SYN-SE3040-019` while the questions are `SYN-REPL-PP-SE3020-035`, …; 8 questions have no rubric rows | 8 questions / 8 rubric rows | `source_replaced_question_id` of each `SYN-REPL-X` equals the rubric row key `X` | **Yes** (id re-key, evidence-backed). |
| F4 | **Criterion ids in `criterion_marks` do not exist in the rubric file** | 576 canonical answers (487 distinct ids) | answer ids `PP-SE3040-001-C01`; rubric file `R-PP-SE3040-001-v2-C01`; only 92 match after an `R-` prefix; the rubric file holds one row per canonical question but answers carry up to 7 criteria | **Partly**: id naming is mappable where it matches; the missing criterion descriptions are **not recoverable** (document as a limitation, do not invent). |
| F5 | `nan` inside list fields (`expected_relationships`: 4 questions, 20 answers, 5 rubric rows) | 29 cells | element `"nan"` in a JSON list | **Yes**: drop the empty element (no content lost), record original. |
| F6 | Identical answer text with different/ambiguous labels inside one question | 4 answers (PP-SE3010-089 MOSTLY=PARTIAL text; PP-SE3080-102 FULL=PARTIAL text; both pairs carry the same mark 20) | `duplicated(question_id, student_answer)` | Not repairable without inventing text → **review queue**. |
| F7 | Constant sentences (intentional template controls?): IRRELEVANT ×96 and ×71 (2 strings), MISCONCEPTION ×71 (1 string), plus per-tier strings with `nan`/placeholders | 535 answers share 17 strings; 15 strings span splits | Documented as controlled variants, but the IRRELEVANT strings are the only text of the class | Keep as **flagged template controls** (not removed, not moved between splits); report as a validity limitation. |
| F8 | Ordering is not uniform: PARTIAL < MISSING_CONCEPT in 83 questions, MOSTLY < PARTIAL in 10, MISCONCEPTION = MISSING in all 167 | all | pivot of `expected_mark` per question | **Not a defect to “fix”** (no rule requires ordering); informational only. |
| F9 | `marks` column is overloaded (equals `expected_mark` for non-FULL canonical rows, 0 for IRRELEVANT) | 479 rows | `marks != question marks` | Add a derived `max_marks` column; keep `marks` unchanged. |
| F10 | Placeholder concept annotations (“one supporting detail”, “accurate causal relationship”, “inverted technical rule”, “conceptual understanding”) | 95 rows | string match | Not recoverable; flag `placeholder_concepts`, do not edit. |
| F11 | `reference_answer` empty for all 576 canonical answers; question-bank references are generic templates | 576 | empty-string count | Not recoverable; document. |
| F12 | Scope: several past-paper items need code/diagrams (e.g. PP-SE3040-001/002 are “develop a web application” with 100 marks) | ≥ 2 confirmed (LLM scope probe on PP-SE3040-001/002 returned `requires_code`); others unverified | trial run 2026-10-21 | Flag `scope_review`, never silently drop. |
| F13 | Validation claims: manifest/QA file say “ALL PASS”; the data fail checks above | — | §3 | Regenerate QA results from the real checks. |

Other verified facts: no empty answers; no duplicate question text; all answer splits equal their question's split; answer-length vs mark Pearson r = 0.089 (original) — the earlier repair raised it to 0.698; ratio-concentration (top-7 inner labels, definition in `tier_spec.json`, threshold 0.45) = **0.758** on the original and 0.832 after the earlier repair, so the dataset **fails** the provisional threshold before any repair.

## 4. What the earlier in-place repair did (and why it is not carried over)

446 manifest rows: **426** `RECONSTRUCTED_GROUND_TRUTH_AND_RUBRIC_TIER` — assigned fixed marks by tier name (10/8.5/5/5/2.5/0 × marks) and replaced the `nan` sentences with generic template text; **20** `RECONSTRUCTED_DOMAIN_GROUNDED_ANSWER_VARIANT` — wrote new answer texts for 10 canonical past-paper answers. Both contradict the new rules (marks must come from the rubric/evidence, not the tier name; no new answer variants; no generic filler). Side effects measured: criterion-sum mismatches (0 → 7), answer-length/mark correlation 0.089 → 0.698, duplicate strings spanning splits 15 → 31, mixed `dataset_version`. Only its IRRELEVANT→0 outcome is consistent with documented policy.

## 5. Not verified
Whether the remaining canonical past-paper questions are answerable as written text (only 2 probed); whether canonical criterion allocations match the original exam mark schemes (no source available); any expert validation (none exists; `expert_validation: false`).
