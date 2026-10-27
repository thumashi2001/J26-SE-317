# ANSWER-ONLY runs (superseded input, kept as an ablation)

These results (phase 1 and the single test scoring) were produced on 2026-10-27 BEFORE a data-loading defect was found:
`02_controlled_answers_eligible.csv` has an empty `reference_answer` column, so every model saw the student answer only
(the reference slot was empty). They are valid only as "answer-only" results. The corrected comparison (reference answer
supplied from `01_question_bank.csv`) is in `../extra/`. Do not cite these as reference-aware models.
