# AdaptiveLearnSE Component 3 — Dataset Card: C3-Phase3-v5-FINAL
**Dataset Version:** `C3-Phase3-v5-FINAL` | **Release Date:** October 2026  
**Curator:** T. P. V. K. Edirisinghe (IT23227118) | **Project:** AdaptiveLearnSE C3  
**Approved Scope:** Primary Synthetic Evaluation Benchmark (Per Supervisor Directive COM-07)

---

## 1. Dataset Summary & Purpose

The `C3-Phase3-v5-FINAL` dataset is a curated, purpose-built synthetic benchmark designed specifically for evaluating automated subjective marking, rubric alignment, concept extraction, and diagnostic robustness in university software engineering examinations.

### Key Dataset Statistics
- **Total Questions:** 169 software engineering examination questions
- **Total Controlled Answers:** 1,014 student response variants (6 per question)
- **Total Rubric Criteria:** 350+ criterion descriptors with mark allocations
- **Software Engineering Modules Covered:**
  - `SE3010`: Software Architecture & Design Patterns
  - `SE3020`: Database Systems & Distributed Storage
  - `SE3030`: Software Quality Assurance & Metrics
  - `SE3040`: Enterprise Application Development

---

## 2. Dataset Split & Zero-Leakage Architecture

Partitioning is strictly enforced at the **question level**. No question appearing in the test split appears in the train or validation splits.

| Split | Question Count | Answer Count | Module Distribution | Leakage Audit Result |
| :--- | :--- | :--- | :--- | :--- |
| **Train Split** | 120 Questions | 720 Answers | SE3010 (30), SE3020 (30), SE3030 (30), SE3040 (30) | **0% Question Overlap** |
| **Validation Split** | 24 Questions | 144 Answers | SE3010 (6), SE3020 (6), SE3030 (6), SE3040 (6) | **0% Question Overlap** |
| **Held-Out Test Split** | 25 Questions | 150 Answers | SE3010 (6), SE3020 (6), SE3030 (6), SE3040 (7) | **0% Question Overlap (FROZEN)** |
| **Total** | **169 Questions** | **1,014 Answers** | Balanced across 4 curriculum modules | **100% Partition Integrity** |

---

## 3. Controlled Quality Conditions

Each question is paired with exactly 6 controlled student response variants:

| Variant Quality Label | Expected Mark Allocation | Construction Rule | Evaluation Purpose |
| :--- | :--- | :--- | :--- |
| `FULL` | 100% of maximum marks | Addresses all rubric criteria accurately with relevant terminology. | Upper-bound recall & calibration |
| `MOSTLY_CORRECT` | 75% – 85% of maximum marks | Complete answer missing exactly one minor secondary criterion. | Precision of partial credit |
| `PARTIAL` | 40% – 60% of maximum marks | Substantial answer demonstrating only half of required concepts. | Middle-range scoring fidelity |
| `MISSING_CONCEPT` | 20% – 35% of maximum marks | Answer addresses scenario but omits core technical concepts. | Diagnostic concept omission check |
| `MISCONCEPTION` | 0% – 20% of maximum marks | Uses keywords with inverted or technically incorrect logic. | Logical reasoning sensitivity |
| `IRRELEVANT` | Exactly 0.00 marks | Distractor or out-of-domain essay (e.g. Roman Empire history). | Zero-credit & length-bias rejection |

---

## 4. File Manifest & Structure

Located in `ADAPTIVE_LEARN_SE/ai-services/c3/datasets/synthetic/`:

```
ai-services/c3/datasets/synthetic/
├── 00_MANIFEST.json                               # Cryptographic hashes and split metadata
├── 01_FINAL_question_bank.csv                     # Full 169 question repository
├── 02_FINAL_controlled_answers.csv                # Full 1,014 controlled answer variants
├── 03_FINAL_rubric_criteria.csv                   # Criterion breakdowns and marks
├── controlled_answers_train.csv                   # Train split answers (N=720)
├── controlled_answers_validation.csv              # Val split answers (N=144)
├── controlled_answers_test.csv                    # Held-out test split answers (N=150)
├── question_bank_train.csv                        # Train questions (N=120)
├── question_bank_validation.csv                   # Val questions (N=24)
└── question_bank_test.csv                         # Test questions (N=25)
```

---

## 5. Schema & Field Definitions

### `controlled_answers_test.csv` Core Columns
- `question_id`: Stable identifier (e.g. `PP-SE3040-006`, `SYN-SE3010-012`)
- `answer_id`: Unique variant identifier (e.g. `SA-PP-SE3040-006-FULL`)
- `module_code`: Associated SLIIT curriculum module code
- `question_text`: Complete problem statement
- `student_answer`: Typed student submission text
- `reference_answer`: Model answer (linked from question bank)
- `marks`: Maximum marks available
- `expected_mark`: Target ground-truth mark
- `answer_quality`: Quality condition (`FULL`, `PARTIAL`, etc.)
- `demonstrated_concepts`: JSON array of concepts present in the answer
- `missing_concepts`: JSON array of concepts missing from the answer
- `rubric_id`: Identifier of the associated marking rubric

---

## 6. Academic Integrity & Ethics Statement

1. **Synthetic Nature:** All 1,014 answers in `C3-Phase3-v5-FINAL` are researcher-constructed synthetic stimuli. They DO NOT represent authentic student exam submissions.
2. **Supervisor Guidance (COM-07):** In response to formal proposal feedback, the supervisor directed that initial research benchmarking and PP1 prototype validation be conducted on a purpose-built synthetic dataset to ensure controlled variant testing and avoid privacy/ethics violations.
3. **No Fabricated Human Validation:** Ground-truth scores are rule-constructed reference labels. No independent expert panel or lecturer validation is falsely claimed.
4. **Generalization Limitation:** High accuracy on synthetic templates does not guarantee identical performance on authentic student handwriting or idiosyncratic phrasing. Authentic student data collection is scheduled for the post-PP1 deployment phase.
