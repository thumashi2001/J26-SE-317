# 28 — Optional semantic concept matching (FR-C3-09), result: built, no measured gain (2026-10-27)

## What was built
`services/semantic/semantic_matcher.py` + hook in `services/semantic/analyzer.py`. With `C3_SEMANTIC_MATCH=local` each expected
concept is embedded (pretrained all-MiniLM-L6-v2, local, not trained here) and compared with every answer sentence; a concept the word
matcher did not fully find is upgraded to `demonstrated` when the best cosine >= `C3_SEMANTIC_THRESHOLD` (0.5, chosen on TRAIN). Upgrades
are flagged `match_method="semantic"` with `semantic_score`; `analysis_version` becomes `semantic-v1`. Off by default; fails soft;
marks still come only from rubric levels (7 unit tests; suite 596 passed, 13 xfailed).

## Evaluation (`experiments/semantic_concept_eval.py`, results in `experiments/semantic/`)
Concept detection per (answer, concept): positives = `demonstrated_concepts`, negatives = `missing_concepts` (tier-derived synthetic
annotations, not human). Threshold from TRAIN only; test scored once.

| Split | Live lexical rule F1 | Lexical any-overlap F1 | Semantic F1 |
|---|---|---|---|
| Train (n=1751) | 0.949 | – | 0.960 (threshold fitted here) |
| Validation (n=364) | 0.856 (recall 0.79) | 0.925 | 0.906 (recall 0.88) |
| Test (n=356, 61 negatives) | **0.967** | 0.951 | 0.959 (CI 0.941–0.973) |

## Honest reading
- The semantic layer improved the strict lexical rule on validation but **not on test** (0.959 vs 0.967, intervals overlap). No
  measurable benefit is claimed.
- The dataset's answers mostly contain the concept words (that is why lexical F1 is already ~0.95), so it contains almost no true
  paraphrases; this evaluation cannot show whether semantic matching helps on them.
- A direct probe with the real model (concepts "components", "interfaces"; answer "The parts of the system talk to each other through
  agreed contracts.") was **not** upgraded: cosines 0.30 and 0.20 against the 0.5 threshold. Single-word concepts versus whole
  sentences give low similarities, so FR-C3-09's own example is still unresolved.
- The test split is spent for this protocol. A better method (e.g. compare answer sentences with reference-answer sentences that contain
  the concept) must be tuned on validation only and needs a fresh paraphrase set (human-written) to be evaluated honestly.

Status: FR-C3-09 stays PARTIAL; the layer is available but not recommended on until a paraphrase benchmark exists.
