# AdaptiveLearnSE Component 3 — Research Datasets

This directory contains the dataset infrastructure for **Component 3: AI-Powered Automated Marking & Answer Analysis System**.

---

## Directory Organization

```
ai-services/c3/datasets/
├── README.md                      # This comprehensive specification and architecture document
├── __init__.py                    # Python package entry point exposing loader utilities
├── loader.py                      # Offline programmatic dataset loader for research & experiments
├── processed/                     # Placeholder (.gitkeep) for intermediate experimental artifacts
├── raw/                           # Placeholder (.gitkeep) for raw source files
├── samples/                       # Placeholder (.gitkeep) for tiny smoke test samples
└── synthetic/                     # Canonical C3-Phase3-v5-FINAL research benchmark package
    ├── 00_MANIFEST.json           # Canonical dataset manifest & metadata
    ├── 01_FINAL_question_bank.csv # 167 written-answer assessment questions & reference models
    ├── 02_FINAL_controlled_answers.csv # 1,002 controlled student answers (6 variants / question)
    ├── 03_FINAL_rubric_criteria.csv # 230 detailed rubric criteria with concept mappings
    ├── 04_ORIGINAL_63_REPLACEMENT_AUDIT.csv # Audit trace of diagram/code replacement questions
    ├── 05_FINAL_QA_RESULTS_ALL_PASS.csv # 17 automated structural and scope QA checks (ALL PASS)
    ├── 06_FINAL_SUMMARY.csv       # Summary metrics and quality breakdown
    ├── 07_DATASET_README.md       # Package README summarizing version v5-FINAL
    ├── 08_RESEARCH_REPORT_DATASET_SECTION_FINAL.md # Research report section on methodology
    ├── question_bank_train.csv    # 117 training questions
    ├── question_bank_validation.csv # 25 validation questions
    ├── question_bank_test.csv     # 25 test questions
    ├── controlled_answers_train.csv # 702 training answers (117 * 6)
    ├── controlled_answers_validation.csv # 150 validation answers (25 * 6)
    └── controlled_answers_test.csv # 150 test answers (25 * 6)
```

---

## 1. Dataset Origin and Provenance

- **Dataset Version:** `C3-Phase3-v5-FINAL`
- **Scope:** Short-answer and essay-answer assessment questions derived from university software engineering curriculum materials (modules: `SE3010`, `SE3020`, `SE3040`, `SE3060`, `SE3070`).
- **Focus:** Conceptual understanding, architectural trade-offs, testing concepts, distributed systems, database paradigms, and agile engineering practices.
- **Exclusion of Code/Diagrams:** All tasks primarily requiring diagram construction, visual manipulation, or raw programming code were audited and replaced with researcher-designed written conceptual questions (71 replacement questions, documented in `04_ORIGINAL_63_REPLACEMENT_AUDIT.csv`).

---

## 2. Generation Methodology & Controlled Answer Conditions

Each of the 167 questions includes exactly **6 controlled answer variants** (1,002 answers total) to evaluate marking precision, explainability, and error diagnosis:

| Condition | Description | Expected Marks | Demonstrated Concepts |
| :--- | :--- | :--- | :--- |
| **`FULL`** | Complete, high-quality answer meeting all rubric criteria. | 100% of rubric marks | All target concepts present |
| **`MOSTLY_CORRECT`** | Strong answer with minor supporting details omitted. | ~80–90% of marks | Most concepts present, 1 minor detail omitted |
| **`PARTIAL`** | Addresses approximately half of the rubric criteria. | ~40–60% of marks | Core concepts present, secondary omitted |
| **`MISSING_CONCEPT`** | Answer discusses topic but completely omits a required core concept. | Deducted for missing criterion | Explicitly lacking target concept |
| **`MISCONCEPTION`** | Answer contains an explicit factual error or inverted relationship. | 0 marks on affected criterion | Misconception concept flagged |
| **`IRRELEVANT`** | Answer is entirely off-topic or discusses unrelated material. | 0 marks (0.0) | Empty demonstrated concepts |

---

## 3. Train / Validation / Test Split Hygiene

- **Question-Level Splitting:** Splits are performed strictly at the question level to guarantee **zero question leakage**:
  - **Train:** 117 questions / 702 answers (70.1%)
  - **Validation:** 25 questions / 150 answers (15.0%)
  - **Test:** 25 questions / 150 answers (15.0%)
  - **Total:** 167 questions / 1,002 answers (100.0%)
- All 6 variants of each question reside in the exact same split as their parent question.

---

## 4. Ground-Truth Limitations & Academic Integrity

> [!IMPORTANT]
> **Ground-Truth Limitations:**
> This dataset is **researcher-constructed controlled synthetic data**, not authentic student exam scripts. The reference marks and expected scores are researcher-designed assessment targets for controlled benchmarking.
> 
> The dataset is **NOT** claimed to be an independently expert-validated or lecturer-validated gold standard (`expert_validation: false` in manifest and summary). It is explicitly designed for controlled comparative experiments.

---

## 5. Strict Separation of Research Data from Production

- **No Auto-Ingestion:** This research dataset is **never** automatically ingested into MongoDB Atlas collections (`submissions`, `evaluations`, `learning_events`).
- **Isolation:** Evaluation benchmarks remain strictly within the `ai-services/c3/` Python service layer for offline experimental scripts and evaluation runs.
- **Application UI:** The application frontend and lecturer queues display live student submissions and verified PP1 demo benchmarks (`provenance: 'pp1_demo'`), clearly decoupled from offline research files.

---

## 6. Programmatic Python Loader Usage

Researchers can access the dataset using `datasets.loader`:

```python
from datasets.loader import (
    load_manifest,
    load_question_bank,
    load_controlled_answers,
    load_rubric_criteria,
    get_question_bundle,
    get_dataset_summary
)

# 1. Summary
summary = get_dataset_summary()
print(f"Loaded {summary['total_questions']} questions, {summary['total_answers']} answers.")

# 2. Load train questions with parsed concepts
train_questions = load_question_bank(split="train")
print("First question concepts:", train_questions[0]["expected_concepts_parsed"])

# 3. Load test answers under MISCONCEPTION condition
misconceptions = load_controlled_answers(split="test", quality="MISCONCEPTION")

# 4. Get complete question bundle (question + rubrics + all 6 variants)
bundle = get_question_bundle("PP-SE3040-001")
```

---

## 7. Supported Research Conditions

The dataset is prepared for benchmarking the following planned experimental conditions:

- **Condition A:** LLM-only Baseline
- **Condition B:** LLM + Criterion-Level Rubric
- **Condition C:** LLM + Rubric + Vector-RAG
- **Condition D:** LLM + Rubric + GraphRAG (Neo4j CCKG)
- **Condition E:** Concept Evidence + Rubric Analysis
- **Condition F:** Full Combined Approach (Rubric + Semantic + Evidence + Mind Map)
