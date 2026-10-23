# 24. Stage 2 label audit (milestone 2a)

Status: reproducible, read-only audit of `datasets/c3_phase3_v5_repaired_v2`. Nothing in the dataset, its labels, splits,
thresholds or ledgers was changed. The figures below are inserted from the audit output by the generator of this report,
and `tests/unit/test_label_audit.py` fails if the machine-generated block at the end stops matching a live run.

Reproduce: `python -m datasets.repair.label_audit datasets/c3_phase3_v5_repaired_v2` (from `ai-services/c3`; prints the JSON,
writes nothing). Each section of that JSON carries its sample size and a `method` sentence; the methods are summarised here.

## What is audited
558 eligible answers on 93 questions (test 90, train 402, validation 66);
93 answers per tier. Mark ratio = `expected_mark / max_marks`.

## Findings

### 1. How marks relate to tiers (n = 93 questions with all six tiers)
Method: group answers by question and tier, compare mark ratios per question (tolerance 1e-9).
- FULL has ratio 1.0 in 93 of 93 questions; IRRELEVANT has ratio 0.0 in 93 of 93.
- MOSTLY_CORRECT, MISSING_CONCEPT and MISCONCEPTION have the **same mark in 93 of 93 questions**.
  Mean ratio per tier: FULL 1.0, IRRELEVANT 0.0, MISCONCEPTION 0.7961, MISSING_CONCEPT 0.7961, MOSTLY_CORRECT 0.7961, PARTIAL 0.6173.
- PARTIAL is below MOSTLY_CORRECT in 82 of 93 questions and at or below MISSING_CONCEPT in 85.

What this shows: the marks within a question take one of at most four distinct values across the six tiers, and three tiers with
different recorded concept content share one value. It does not show how the marks were produced.

### 2. Demonstrated, missing and incorrect concepts
Method: concept counts are the lengths of the JSON lists; the demonstrated fraction is demonstrated / (demonstrated + missing +
incorrect), defined when that sum is above zero (n = 465); r is Pearson against the mark ratio.
- Mean counts (demonstrated / missing / incorrect): FULL 5.5161/0.0/0.0; IRRELEVANT 0.0/0.0/0.0; MISCONCEPTION 4.4086/0.0/1.129; MISSING_CONCEPT 4.4086/1.129/0.0; MOSTLY_CORRECT 4.4086/1.129/0.0; PARTIAL 3.2258/2.3441/0.0.
- Pearson(demonstrated fraction, mark ratio) = 0.929 (n = 465).
- Demonstrated + missing + incorrect equals the length of the question's `expected_concepts` (question bank) for
  454 of 558 answers. The answers file's own `expected_concepts` column is empty in
  558 rows.

What this shows: the recorded concept lists agree with the question's concept list for 454 of the 465 answers
that have any recorded concepts (none of the IRRELEVANT answers do), and the mark ratio tracks the demonstrated fraction closely. A correlation does not establish that marks were computed
from concept counts. MISCONCEPTION answers carry incorrect concepts and receive the same mark as MISSING_CONCEPT answers.

### 3. Rubrics (eligible questions, n = 93)
Method: rubric rows of the eligible questions in `03_rubric_criteria.csv`.
- Criteria per question: {'1': 93}. Criterion text: {'Question-level rubric criterion (retain source rubric allocation)': 93}.
- Columns naming levels or descriptors: none. Rows with expected concepts:
  0; rows with evidence requirements: 0.
- Rubric status: {'researcher_constructed; pending final content review': 93}.

What this shows: the dataset's rubrics are one placeholder criterion per question without levels, descriptors or concepts, so
they cannot drive the marking engine's `Rubric -> criteria -> scoring levels` structure.

### 4. Criterion identifiers (n = 558 answers)
Method: `criterion_marks` is parsed as a JSON list of `{criterion_id, mark}`; ids are compared with the `criterion_id` column
of the eligible questions' rubric rows, and with the rows of `criterion_id_map.csv` for the eligible questions.
- Answers with parsable criterion marks: 558; criteria per answer (2: 6, 3: 48, 4: 30, 5: 306, 6: 144, 7: 18, 9: 6); marks
  summing to the answer's `expected_mark`: 558.
- Referenced criterion ids: 2850; exact matches to a rubric criterion id: 0
  (rubric has 93 ids).
- Id map rows for eligible questions: 475; status {'RESOLVED': 93, 'UNRESOLVED': 382}; among resolved rows, marks agree:
  {'False': 93}.

What this shows: every answer has criterion-level marks that add up, but they refer to criteria the rubric file does not define, so
no criterion-level mark can be tied to a rubric descriptor.

### 5. Answer length
Method: words = whitespace-separated tokens of `student_answer`; Pearson against the mark ratio on the named subset.
- Mean words by tier: FULL 75.7, IRRELEVANT 12.0, MISCONCEPTION 77.5, MISSING_CONCEPT 73.5, MOSTLY_CORRECT 60.8, PARTIAL 43.1.
- Pearson(words, mark ratio): all tiers 0.8321 (n = 558); without IRRELEVANT
  0.611 (n = 465); the four middle tiers only
  0.7349 (n = 372).

What this shows: length and mark are strongly associated overall and still associated among the middle tiers; the association is
not only the very short IRRELEVANT answers. Note on an earlier interpretation: an interim summary written before this audit (not in the repository) said length "does not
rank the middle tiers". The figure above (r = 0.7349) contradicts that, and this report
replaces it. The data cannot say whether length drives the marks or both follow the tier recipe.

### 6. Ratio concentration (threshold 0.45, read from `validation_spec.json`)
Method: among answers with 0 < ratio < 1 (3 d.p.), the share on the 7 most frequent ratios.
- Answers 558; anchors at 0 or 1: 186; inner labels: 372;
  distinct inner ratios: 37.
- Top-7 ratios: 0.8 x160, 0.6 x52, 0.85 x24, 0.84 x18, 0.667 x12, 0.55 x10, 0.9 x9. **Share on the top 7 = 0.766129, which exceeds the threshold: True.**
- Most common ratio per tier (ratio, count): {'MISCONCEPTION': [0.8, 52], 'MISSING_CONCEPT': [0.8, 52], 'MOSTLY_CORRECT': [0.8, 52], 'PARTIAL': [0.6, 43]}.

This reproduces the failure recorded in `validation_report.json`. The threshold was not changed.

## What these figures do not establish
- Descriptive statistics only: a correlation or an equal-marks count shows how the labels are structured, not how or why they were assigned.
- The dataset is synthetic and author-labelled; none of these figures measures agreement with an independent marker.
- Concept lists and criterion marks are taken as recorded in the CSVs; this audit does not judge whether they are right.
- Pearson r is computed on the stated subset only and is sensitive to a few extreme groups (see the per-subset values).

## Machine-generated audit output
Generated by `python -m datasets.repair.label_audit datasets/c3_phase3_v5_repaired_v2`. The test suite compares this block with a
live run.

```json
{
  "caveats": [
    "Descriptive statistics only: a correlation or an equal-marks count shows how the labels are structured, not how or why they were assigned.",
    "The dataset is synthetic and author-labelled; none of these figures measures agreement with an independent marker.",
    "Concept lists and criterion marks are taken as recorded in the CSVs; this audit does not judge whether they are right.",
    "Pearson r is computed on the stated subset only and is sensitive to a few extreme groups (see the per-subset values)."
  ],
  "concepts": {
    "concept_accounting": {
      "answers_checked": 558,
      "demonstrated_plus_missing_plus_incorrect_equals_question_expected_concepts": 454
    },
    "demonstrated_fraction_vs_mark_ratio": {
      "n": 465,
      "pearson_r": 0.929
    },
    "expected_concepts_column_empty_in_answers_file": 558,
    "method": "Concept counts are the lengths of the JSON lists in demonstrated/missing/incorrect_concepts. The 'demonstrated fraction' is demonstrated / (demonstrated + missing + incorrect), defined only when that sum is above zero; r is Pearson against the mark ratio over those answers. Concept accounting compares that sum with the length of the question's expected_concepts list in 01_question_bank.csv (the answers file's own expected_concepts column is empty, see the count below).",
    "per_tier_mean_counts": {
      "FULL": {
        "demonstrated": 5.5161,
        "incorrect": 0.0,
        "missing": 0.0
      },
      "IRRELEVANT": {
        "demonstrated": 0.0,
        "incorrect": 0.0,
        "missing": 0.0
      },
      "MISCONCEPTION": {
        "demonstrated": 4.4086,
        "incorrect": 1.129,
        "missing": 0.0
      },
      "MISSING_CONCEPT": {
        "demonstrated": 4.4086,
        "incorrect": 0.0,
        "missing": 1.129
      },
      "MOSTLY_CORRECT": {
        "demonstrated": 4.4086,
        "incorrect": 0.0,
        "missing": 1.129
      },
      "PARTIAL": {
        "demonstrated": 3.2258,
        "incorrect": 0.0,
        "missing": 2.3441
      }
    },
    "unparsable_cells": {
      "demonstrated_concepts": 0,
      "incorrect_concepts": 0,
      "missing_concepts": 0
    }
  },
  "criterion_ids": {
    "answers": 558,
    "answers_with_parsable_criterion_marks": 558,
    "criteria_per_answer": {
      "2": 6,
      "3": 48,
      "4": 30,
      "5": 306,
      "6": 144,
      "7": 18,
      "9": 6
    },
    "criterion_marks_sum_equals_expected_mark": 558,
    "exact_match_to_a_rubric_criterion_id": 0,
    "map_resolved_marks_agree": {
      "False": 93
    },
    "map_rows_for_eligible_questions": 475,
    "map_status": {
      "RESOLVED": 93,
      "UNRESOLVED": 382
    },
    "method": "criterion_marks is a JSON list of {criterion_id, mark} per answer. 'exact id match' compares each id with the criterion_id column of the rubric rows of the eligible questions; the map section counts criterion_id_map.csv rows of the eligible questions (its own normalised matching rule).",
    "referenced_criterion_ids": 2850,
    "rubric_criterion_ids": 93
  },
  "dataset": "c3_phase3_v5_repaired_v2",
  "length": {
    "length_vs_mark_ratio": {
      "all_tiers": {
        "n": 558,
        "pearson_r": 0.8321
      },
      "four_middle_tiers_only": {
        "n": 372,
        "pearson_r": 0.7349
      },
      "without_IRRELEVANT": {
        "n": 465,
        "pearson_r": 0.611
      }
    },
    "method": "words = number of whitespace-separated tokens of student_answer; r is Pearson(words, mark ratio) on the named subset.",
    "per_tier_words": {
      "FULL": {
        "mean": 75.7,
        "median": 74,
        "n": 93,
        "sd": 18.3
      },
      "IRRELEVANT": {
        "mean": 12.0,
        "median": 12,
        "n": 93,
        "sd": 0.0
      },
      "MISCONCEPTION": {
        "mean": 77.5,
        "median": 76,
        "n": 93,
        "sd": 17.3
      },
      "MISSING_CONCEPT": {
        "mean": 73.5,
        "median": 72,
        "n": 93,
        "sd": 17.5
      },
      "MOSTLY_CORRECT": {
        "mean": 60.8,
        "median": 59,
        "n": 93,
        "sd": 16.9
      },
      "PARTIAL": {
        "mean": 43.1,
        "median": 44,
        "n": 93,
        "sd": 10.4
      }
    }
  },
  "ratio_concentration": {
    "anchor_answers_ratio_0_or_1": 186,
    "answers": 558,
    "distinct_inner_ratios": 37,
    "exceeds_threshold": true,
    "inner_answers_by_tier": {
      "MISCONCEPTION": 93,
      "MISSING_CONCEPT": 93,
      "MOSTLY_CORRECT": 93,
      "PARTIAL": 93
    },
    "inner_label_answers": 372,
    "method": "Same definition as the validator: among answers with 0 < ratio < 1 (ratios rounded to 3 d.p.), the share that sits on the 7 most frequent ratios. Threshold is read from validation_spec.json.",
    "most_common_ratio_by_tier": {
      "MISCONCEPTION": [
        0.8,
        52
      ],
      "MISSING_CONCEPT": [
        0.8,
        52
      ],
      "MOSTLY_CORRECT": [
        0.8,
        52
      ],
      "PARTIAL": [
        0.6,
        43
      ]
    },
    "share_on_top7": 0.766129,
    "threshold": 0.45,
    "top7_ratios": [
      [
        0.8,
        160
      ],
      [
        0.6,
        52
      ],
      [
        0.85,
        24
      ],
      [
        0.84,
        18
      ],
      [
        0.667,
        12
      ],
      [
        0.55,
        10
      ],
      [
        0.9,
        9
      ]
    ]
  },
  "rubric": {
    "columns_naming_levels_or_descriptors": [],
    "criteria_per_question": {
      "1": 93
    },
    "criterion_texts": {
      "Question-level rubric criterion (retain source rubric allocation)": 93
    },
    "eligible_questions": 93,
    "method": "Rubric rows of the eligible questions, from 03_rubric_criteria.csv.",
    "questions_with_rubric_rows": 93,
    "rows_with_evidence_requirements": 0,
    "rows_with_expected_concepts": 0,
    "rubric_status": {
      "researcher_constructed; pending final content review": 93
    }
  },
  "sizes": {
    "answers_by_split": {
      "test": 90,
      "train": 402,
      "validation": 66
    },
    "answers_by_tier": {
      "FULL": 93,
      "IRRELEVANT": 93,
      "MISCONCEPTION": 93,
      "MISSING_CONCEPT": 93,
      "MOSTLY_CORRECT": 93,
      "PARTIAL": 93
    },
    "eligible_answers": 558,
    "eligible_questions": 93
  },
  "tier_marks": {
    "method": "mark ratio = expected_mark / max_marks per answer. Per-question comparisons use only questions that have all six tiers.",
    "per_question": {
      "full_ratio_is_1": 93,
      "irrelevant_ratio_is_0": 93,
      "mostly_missing_misconception_equal": 93,
      "partial_at_or_below_missing": 85,
      "partial_below_mostly": 82
    },
    "per_tier": {
      "FULL": {
        "distinct_ratios": 1,
        "max": 1.0,
        "mean_ratio": 1.0,
        "min": 1.0,
        "n": 93
      },
      "IRRELEVANT": {
        "distinct_ratios": 1,
        "max": 0.0,
        "mean_ratio": 0.0,
        "min": 0.0,
        "n": 93
      },
      "MISCONCEPTION": {
        "distinct_ratios": 19,
        "max": 0.9143,
        "mean_ratio": 0.7961,
        "min": 0.6,
        "n": 93
      },
      "MISSING_CONCEPT": {
        "distinct_ratios": 19,
        "max": 0.9143,
        "mean_ratio": 0.7961,
        "min": 0.6,
        "n": 93
      },
      "MOSTLY_CORRECT": {
        "distinct_ratios": 19,
        "max": 0.9143,
        "mean_ratio": 0.7961,
        "min": 0.6,
        "n": 93
      },
      "PARTIAL": {
        "distinct_ratios": 24,
        "max": 0.88,
        "mean_ratio": 0.6173,
        "min": 0.5,
        "n": 93
      }
    },
    "questions_with_all_six_tiers": 93
  }
}
```
