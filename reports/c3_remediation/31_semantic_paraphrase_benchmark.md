# 31 — Semantic paraphrase benchmark v1: annotation-ready, no human labels yet (2026-10-27)

## Honest status (read first)
| Thing | State |
|---|---|
| Item texts (82 items, 10 groups) | **AI-drafted** (Claude, 2026-10-27). Each item carries `draft.proposed_label`, the drafter's intent. That is **not ground truth**. |
| Human labels | **None exist.** Every item is `draft_unreviewed`. Annotators, rationales, disagreements and adjudication must come from people. |
| Benchmark results (lexical vs semantic) | **Not produced.** The dev and held-out phases refuse to run (exit code 3) until every item of the split has >= 2 human annotations. |
| Pipeline check on draft labels | Run once to exercise the code. Stamped `NOT EVIDENCE`. |
| Architecture-case re-measurement | Done (model observation, needs no labels). Scores unchanged. |

A software test passing shows the harness behaves as specified; it does not show that the semantic layer detects concepts better.

## What was built (all under `ai-services/c3`, production marking untouched)
| Deliverable | Location |
|---|---|
| Versioned dataset | `datasets/semantic_paraphrase_benchmark_v1/items.json` (content hash in the integrity report) |
| Schema | `.../schema.json` (documentation); enforced by `datasets/paraphrase_benchmark/validate.py` |
| Annotation guidelines and label definitions | `.../ANNOTATION_GUIDELINES.md` (labels: demonstrated / partial / missing / contradicted) |
| Dataset and split integrity report | `.../INTEGRITY_REPORT.md` (generated: `python -m datasets.paraphrase_benchmark.validate --write`) |
| Blind sheets and return ingestion | `datasets/paraphrase_benchmark/sheets.py` |
| Evaluation script | `experiments/semantic_paraphrase_eval.py` (`dev`, `heldout`, `pipeline-check`) |
| Tests | `tests/unit/test_semantic_paraphrase_benchmark.py` (35) |
| Architecture-case observation | `reports/c3_remediation/experiments/paraphrase_benchmark/architecture_case_observation.json` |

## Design
- **Distinct from earlier work.** `experiments/semantic_matching` (author-labelled fixtures, report 16) and `semantic_concept_eval.py` (tier-derived labels, report 28) are untouched and their results are not reused or merged.
- **Contents:** 6 dev groups (50 items), 4 held-out groups (32). Per group one concept and eight answers across seven categories: paraphrase (two), partial, related-incorrect, missing, negation, technical alternative, keyword trap. Both splits contain every category. The historical architecture answer and its two other concepts sit in **dev** (an already-observed failure must not be in the held-out split).
- **Leakage controls:** groups never straddle splits; cross-split word-set Jaccard >= 0.8 and exact duplicates are rejected; the dataset hash is frozen with the threshold and a changed dataset is refused.
- **Label provenance:** status is derived from annotation records; a hand-typed status or `final_label` without annotators fails validation; annotator ids must be pseudonyms (`ANN01`, `ADJ01`); an adjudicator cannot be an annotator of that item; blind sheets omit category, split and the draft label.
- **Protocol:** truth positive = `demonstrated`. Threshold chosen on **dev only** (grid 0.20-0.90, best macro-F1, ties to the higher value), frozen with the dataset hash, held-out scored once (rerun refused). Reported: per-concept and macro P/R/F1, confusion matrices (binary and human label x system status), false positives/negatives, per-category results, layer off vs on (chosen and default 0.5 thresholds), threshold sensitivity (missed vs wrongly detected).
- **Not done:** no bootstrap interval (4 held-out groups is too few), no kappa until annotations exist, no change to `services/semantic`.

## Execution results (exact)
| Run | Result |
|---|---|
| `pytest tests/unit/test_semantic_paraphrase_benchmark.py` | 35 passed |
| Full C3 suite | see the final section (run after the last edit) |
| `python -m datasets.paraphrase_benchmark.validate` | valid; 82 items; 0 item problems; 0 split problems; 0 human-labelled |
| `python -m experiments.semantic_paraphrase_eval dev ...` | exit 3 `NO HUMAN LABELS` (verified by test) |
| `pipeline-check` (real MiniLM, AI-draft labels) | ran; selection on dev picked 0.30 with dev macro-F1 0.4179 vs 0.2083 lexical. **NOT EVIDENCE:** the labels are drafts and the threshold was chosen on them. Do not quote. |

The tests that touch metrics use hand-counted rows and a deterministic fake analyzer. They do not assert that the model returns expected labels. The test labels used to exercise the protocol are marked as fixtures inside the test file and are not benchmark data.

## Error analysis: the architecture paraphrase
Re-measured today with the same MiniLM model (single-sentence answer; model observation, no labels involved):
| Item | Concept | Lexical | Best cosine | Threshold 0.5 |
|---|---|---|---|---|
| PB1-G01-P1 | components | not_demonstrated | 0.3112 | not reached |
| PB1-G01-P1-INT | interactions | not_demonstrated | 0.1884 | not reached |
| PB1-G01-P1-ORG | organisation | demonstrated (word match) | 0.4339 | n/a |
The historical values (0.31, 0.19, threshold 0.5) are **unchanged**; they are kept in the item record as history, not as labels.

Observations (one answer, so hypotheses, not findings):
1. The concept is a single word compared with a whole sentence. The same answer scores 0.5802 against the longer phrase "the components of a system" but 0.2409 against "parts" and 0.2406 against "building blocks". The score depends strongly on how the concept is written.
2. Same-model scores in G01 do not separate meaning from vocabulary: the keyword trap ("electronic components ... circuit board") scores 0.7099 and the negation item 0.4648, both above the genuine paraphrases (0.31 and 0.36). Both also pass the lexical rule already, so a cosine threshold can not remove them. Negations and traps need a different mechanism.
3. A threshold low enough to accept the paraphrase (<= 0.31) would also sit below the scores of several non-demonstrating answers in this group (0.22-0.28), i.e. trading misses for false detections. Whether that trade is acceptable is exactly what the held-out benchmark must measure.

## What still requires humans
1. Two independent annotators label all 82 items from blind sheets (guidelines in the dataset folder); an adjudicator settles disagreements.
2. Record the annotation method, pseudonym map custody, dates and agreement in a manifest; agree any acceptance threshold **before** running the dev phase.
3. Review the AI-drafted item texts for naturalness and any wrong or ambiguous items (annotators may flag items instead of forcing a label).

## Recommended next steps (based on measured evidence only)
1. Obtain the human labels, then run `dev` and `heldout` once each; report macro-F1, per-category and sensitivity results as they come out, including a negative result.
2. Only if held-out results justify it, propose a semantic-layer change **separately**, for example comparing a concept description rather than a bare name, with its own evidence. Observation 1 is a lead, not a justification.
3. Negation and keyword traps are not addressed by similarity thresholds; treat them as a separate requirement (the contradicted class from the FRS audit).
4. Increase held-out groups (4 is small) before drawing any conclusion about categories.
