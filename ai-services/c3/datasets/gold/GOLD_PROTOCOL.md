# Gold-standard protocol for Component 3 (draft v1)

## Status and limits

This is a **design**, not a record of anything that has happened.

- It has not been operationally validated. Nobody has followed it end to end, no pilot has been run, and passing the unit
  tests in `tests/unit/test_gold_rubric.py` only shows that the tooling in this directory behaves as described.
- No human marks exist. No marker has marked any answer, no lecturer has approved any rubric, and no agreement statistic has
  been measured. Nothing in this repository should be described as gold-standard labels until the steps below are completed
  and sealed.
- It does not change the existing v2 dataset, its labels, its splits, the 0.45 ratio-concentration threshold, or any historical
  experiment result. The ratio-concentration failure stays recorded.
- Acceptance thresholds (for example the agreement a marker pair must reach) are **not** set here. The researchers and
  supervisor choose them and record them in the study plan before any marking starts; choosing them afterwards would let the
  data pick its own bar.

## Purpose

The v2 marks follow a tier template (report `24_stage2_label_audit.md`): three tiers with different recorded concept content
share one mark in every question, the rubrics are one placeholder criterion per question, and the criterion-level marks refer
to criteria no rubric defines. The author wrote both the answers and the marks, so agreement between a model and those marks
says little about marking quality. This protocol describes how to obtain marks that a person made from a rubric alone, without
seeing the tier, so that (a) the validity of the existing tier labels can be measured and (b) models can be evaluated against
an independent target.

## Roles

| Role | Does | Must not |
|---|---|---|
| Rubric drafter | Drafts multi-level rubrics (a lecturer, or an AI tool whose use is declared) | Mark answers in the gold set |
| Rubric validator | A lecturer who reviews a drafted rubric and records the review | Be the person who drafted it |
| Markers (at least 2) | Mark every answer independently, blind, using only the rubric | See tiers, existing marks, other markers' marks, or model output |
| Adjudicator | Resolves disagreements between the two markers on an item | Be one of the two markers on that item |
| Custodian | Generates the sheets and keeps the key that maps sheet ids back to dataset ids | Mark, or hand the key to a marker |
| Analyst | Computes agreement and evaluates models after sealing | Alter labels or sheets |

One person may hold several roles across different items only where the "must not" column is respected for each item. The
roles and the pseudonyms used for them are recorded in the sealed manifest.

## Evaluation subset

- **Unit and source.** The unit is the question. Draw questions only from the eligible questions of the v2 **validation and
  test splits**: the models compared so far were not trained on them, and new human marks are a new target, so the existing
  models can be scored on them without leakage. Training-split questions are not used.
- **Selection.** A deterministic script, run with a fixed seed that is written down before any model output is looked at,
  selects questions stratified by module and by question marks. It outputs question ids only: no marks, tiers or answers.
  Selection is question-disjoint by construction.
- **Size.** The intended size is decided in the study plan from marker availability; the audit figures show that the present
  15-question test split gives wide intervals. A larger subset narrows them but multiplies marking work.
- **Answers.** The answers to be marked are the existing v2 eligible answers of the selected questions. They are synthetic
  tier-recipe text, so the independence achieved is independence of the **marks**, not of the answer text. This remains a
  limitation (see Open decisions).
- **Template controls.** The IRRELEVANT tier uses one constant string across questions, so a marker would recognise it at once.
  Whether to leave those answers out of the sheets and report them separately is an open decision.

## Rubrics

- A gold rubric is a document `{format, question_id, provenance, rubric}` (`rubric_template.json`). The `rubric` object is the
  marking engine's own schema (`app/schemas/marking.py`): rubric, criteria, scoring levels. Marks come only from the `mark`
  of a level.
- Every criterion has at least three levels, including a 0-mark level and a level worth the criterion's `max_marks`; level
  marks, labels and descriptors are distinct; descriptors are specific enough for a marker to apply them; positive levels name
  required concepts so the same rubric can later run through the engine; criterion `max_marks` add up to the question's marks.
- `python -m datasets.gold.rubric_check <file> --dataset <v2 dir>` checks all of this with the engine's schema and its
  `validate_rubric`, and also checks that the question exists, is eligible, and has matching marks. `--require-gold` fails
  unless the provenance claims lecturer validation.
- The checker confirms the record is complete and consistent. It cannot confirm that a review took place.

## AI-drafted and lecturer-validated

- `ai_drafted`: an AI tool wrote or helped write the rubric. It is useful as a starting point and is **not** usable as gold. It
  must not carry `validated_by` or `validated_on`.
- `lecturer_validated`: a lecturer other than the drafter has reviewed the rubric, edited it where needed, and recorded their
  name and review date. Only these rubrics enter the gold set.
- A validating review covers at least: do the concepts cover what the question asks; do the level descriptors separate the
  levels in a way a marker can apply; do the marks add up; is anything in the rubric wrong for the subject.
- Not validation: the AI reviewing its own draft; the researcher confirming an AI draft; the checker passing. If lecturers can
  validate only some rubrics, the gold set contains only those questions. The bar is not lowered to keep the numbers up.
- Results report how many rubrics were AI-drafted and then validated, and how many were rejected or rewritten.

## Blind marking

- **Markers receive** the question text, the validated rubric, and one answer at a time. Nothing else.
- **Hidden from markers:** the answer tier (`answer_quality`), `expected_mark`, `criterion_marks` and its criterion ids, the
  concept lists (`demonstrated`, `missing`, `incorrect`), evidence spans, `split`, `source_type`, `generation_method`, and every
  dataset identifier. Question ids and answer ids are replaced by opaque random sheet ids, because the dataset ids contain the
  module and the tier.
- **Order.** Each marker gets their own independent random order of items. Answers to the same question are not grouped by
  tier. No marker sees another marker's marks, and the markers do not discuss items until both have submitted.
- **Not shown:** any model prediction, any earlier result, or the purpose of any individual item.
- **Pilot.** Before the full run, a small pilot on a few questions checks that the rubrics and sheets are clear and measures
  marking time. Pilot items are excluded from the gold set.

## Scoring

- A marker chooses, for each criterion, one of the rubric's allowed `level_id`s. Markers do not type free marks: the mark is
  looked up from the chosen level, and the total is the sum, so a mark outside the rubric cannot be recorded.
- A marker may flag an item "cannot mark" with a short reason (for example the rubric is ambiguous for this answer). Flags are
  counted and reported; they are not silently dropped.
- Each return records marker pseudonym, sheet id, per-criterion level ids, optional comment, and time stamp.

## Agreement

Computed after both returns are in, before adjudication, on the original marks:

- Per-criterion exact agreement on `level_id`, and weighted kappa on the level order for a marker pair.
- Krippendorff's alpha (ordinal) when more than two markers mark an item.
- For the total mark ratio: mean absolute difference between markers and an intraclass correlation.
- Intervals come from a bootstrap that resamples **questions**, not answers, because answers to one question are not
  independent.

Limitations that must be stated with the results:

- Agreement is not validity: two markers using the same rubric can agree and both be wrong, or share a bias from the rubric.
- Kappa and alpha behave badly when almost all marks fall on a few levels (the ratio-concentration problem in another form), so
  raw percentage agreement is reported next to them.
- With few questions the intervals are wide; a single figure without its interval is not reported.
- The answers are synthetic tier-recipe text, so agreement here may not carry over to real student answers.

## Adjudication

- Any criterion on which the two markers chose different levels goes to the adjudicator, who sees the question, rubric,
  answer and both choices with their comments, and still not the tier, the existing marks or any model output.
- The adjudicator picks a level and writes a reason. Marks are never averaged. Both original returns are kept.
- An item that stays unresolved is excluded and counted. The number of adjudicated and excluded items is reported together with
  the agreement figures.

## Sealing

Two seals, each a SHA-256 over a canonical list of file hashes, stored with the study plan (the preparation tooling produces the
first; the second is not yet automated, see Tooling):

1. **Pre-marking seal:** the selected question ids with the selection seed and rule, the hash of the v2 `manifest.json`, every
   validated rubric document, and every generated sheet.
2. **Post-marking seal:** the marker returns, the adjudication records, the final per-criterion labels, and the key file.

Rules: models are evaluated against the final labels only after the post-marking seal; predictions are produced without access
to the labels; the evaluation is run once per frozen configuration; any later change creates a new version with a new seal
and leaves the old one in place. The key file is kept apart from the sheets and never given to a marker. The existing
experiment results are not edited; they stay pinned to the dataset hashes they recorded.

## Ethics and provenance

- The answers are synthetic, researcher-constructed text, not student work, and carry no personal data. Authentic student
  scripts stay prohibited until institutional ethics clearance is obtained (`docs/pp1/CLAIM_EVIDENCE_DECISION_LOG.md`, DEC-06).
- Markers and the adjudicator take part voluntarily and are told what the exercise is. Their names are not stored in the
  sheets; results use pseudonyms.
- Provenance recorded in the manifest: v2 dataset version and manifest hash, the selection seed and script version, each
  rubric's `provenance` block (drafter, AI use, validator, dates), the sheet generator version, and the dates of each step.
- The v2 labels and answers came from an automated pipeline (`generation_method = existing_phase3_v2_controlled_variant`,
  `annotation_status = retained_from_Phase3-v2; automated QA passed`). That is stated wherever results are reported.

## Analysis plan (outline)

1. Tier-label validity: how far the human marks agree with the tier-template marks, per tier and per criterion.
2. Model evaluation against the sealed human labels, with question-level bootstrap intervals, including the length-only and
   lexical baselines, as already done on the v2 marks.
3. A report of everything above including failures, exclusions and flags.

## Tooling, custody and security limits

Preparation tooling exists in this directory. It has been tested only on simulated toy fixtures; no real sheet has been
generated, no marker has used it, and none of it has been operationally validated.

| Module | Does |
|---|---|
| `sampling.py` | Deterministic question ids: the final set from the eligible validation and test questions, a separate pilot from the training split, disjoint by construction; refuses a request larger than the pool. Output holds ids, splits, modules, question marks and counts only. `validate_plan` re-checks a plan file against the dataset (eligibility, splits, disjointness, marks), because a plan can be edited. |
| `sheets.py` | Blind sheets per marker, a return template, a separate key and a pre-marking seal. Re-validates the plan, scans every text a marker will see (and the marker pseudonyms) for dataset ids and tier names, and refuses unsafe output locations. Guarded: see below. |
| `returns.py` | Validates a marker's return against that marker's sheet and turns chosen levels into marks. With `--seal` (or `expected_sheet_sha256`) it also checks the sheet against its sealed hash. |
| `agreement.py` | Exact agreement, quadratic weighted kappa, ordinal Krippendorff alpha, intraclass correlation, question-level bootstrap; rejects mismatched lengths, out-of-range ranks and ragged matrices; `--seal` checks both sheets against the seal. |
| `adjudication.py` | Lists disagreements, a blank decision template, and the final labels; excluded items are counted and carry no label. |

**What the current dataset allows.** The eligible validation and test splits hold exactly 26 questions (11 and 15), with 156
answers. Leaving out the 26 constant-string IRRELEVANT controls gives 130 answers to mark. The final set therefore cannot be
larger than 26 without using training questions, which the existing models were trained on. The 4-question pilot is drawn from
the 67 eligible training questions (20 answers to mark), so it cannot take questions from the final set; pilot material may be
used to refine rubrics and the procedure and is never part of the held-out evaluation. Training-split answers may be analysed
separately for tier validity, not for held-out model evaluation. Seeds are chosen by the team and recorded in the plan before
any model output is looked at.

**Simulated versus real.** Every sheet, return, report and label set carries an `origin`. `toy_fixture` material is simulated:
reports built from it say so, state that it contains no human marks, and the command line needs `--allow-simulated` to compute
on it. The command line cannot produce `toy_fixture` sheets. Origin `gold` needs a `lecturer_validated` rubric for every
question, so real gold sheets cannot be produced until lecturers have validated rubrics; origin `pilot` accepts structurally
valid rubrics, including AI drafts. The `origin` label is a statement by whoever ran the tool: the tools cannot verify who
marked what.

**Security limits.**

- Hashes and the seal give tamper evidence (they show a file changed after sealing). They do not control who can read or write
  anything.
- Opaque ids are a hash of the salt and the answer id. Anyone holding the salt and the dataset can recompute the mapping, and a
  short or reused salt can be guessed. The tool only enforces a minimum length of 16 characters, which is not a measure of
  entropy. The salt must be random, secret, and used for one study.
- The answer key is a plain JSON file. Nothing here encrypts it, authenticates users, or logs access.
- Blinding hides identifiers and labels. It does not hide style: answer length and wording may still hint at a tier.
- Markers receive identical text, so nothing prevents them from comparing notes.
- The generator refuses to write sheets or the key inside a git working tree, but that only protects against accidental commits.
- Only the pre-marking seal has tooling. The post-marking seal described under Sealing (returns, adjudication records, final
  labels, key) must be produced by hand until tooling exists, and the returns themselves are not hashed by these scripts. A return
  is bound to its sheet by the sheet hash it names; checking that hash against the seal needs `--seal` and a seal stored where the
  people being checked cannot rewrite it.
- Someone who can rewrite both a sheet and its return can make them consistent with each other; only the seal, held in custody,
  exposes that. The `origin` label can likewise be rewritten in both files; it is a statement, not a proof.
- Agreement statistics reject malformed input but assume the returns are honest; they say nothing about who marked.

**Where real arrangements are required before any real use.** (1) Access-controlled storage, outside the repository, for the
salt, the key, the plan and the seals, with a named custodian. (2) A channel for sending sheets to markers and receiving returns
that is private to each marker. (3) A pseudonym register held by the custodian. (4) Consent and role records for markers and the
adjudicator. (5) Lecturers who can validate the rubrics. None of these exists yet.

## Open decisions

These need an answer from the research team before real sheets are generated:

1. Who the two markers and the adjudicator are, and how many hours each can give.
2. Who drafts the rubrics, who validates them, and how many rubrics validators can review.
3. The subset size, given the answers to 1 and 2.
4. Whether the constant-string IRRELEVANT controls are left out of the sheets.
5. The acceptance thresholds for agreement and for the proportion of items that may be excluded.
6. Where the key and the sealed artefacts are stored and who holds them.
7. Whether markers also write short answers, to reduce dependence on tier-recipe text (a larger change that this protocol
   does not assume).

## Files

- `rubric_template.json`: the authoring template; unfilled, it is rejected by the checker.
- `rubric_check.py`: the checker (`python -m datasets.gold.rubric_check`).
- `common.py`, `sampling.py`, `sheets.py`, `returns.py`, `agreement.py`, `adjudication.py`: the preparation tooling described
  above. Tests: `tests/unit/test_gold_sampling_and_sheets.py`, `tests/unit/test_gold_returns_and_agreement.py`, with toy data in
  `tests/unit/gold_toy_data.py`.
