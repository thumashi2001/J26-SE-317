# Component 2: AI Exam Intelligence

Component 2 (C2) is the AI Exam Intelligence subsystem of the AdaptiveLearnSE platform. It provides automated past-paper extraction, exam question structuring, topic classification, and past-paper / mock-examination practice workflows for SLIIT 3rd Year Software Engineering undergraduate students.

## Research Objectives

1. **Authentic Historical Examination Ingestion & Structuring:** Automated extraction of unstructured past-paper PDFs into structured question repositories preserving marks, hierarchies, subquestions, and provenance.
2. **Topic Classification & Curriculum Mapping:** AI-driven mapping of examination questions to curriculum topics with strict confidence thresholds, explicit abstention for ambiguous queries, and lecturer verification safeguards.
3. **Dual-Mode Student Practice:** Strict separation between **Authentic Past-Paper Practice** (grounded exclusively in lecturer-verified historical exam papers) and **Synthetic Practice (Experimental)** (grounded in M16 synthetic questions for exploratory training without polluting authentic data).

---

## Directory Structure

```text
ai-services/c2/
├── app/                  # FastAPI prediction & question-bank endpoints
├── config/               # Configuration settings & environment variables
├── datasets/
│   ├── authentic/        # [GIT-IGNORED] Source authentic past-paper PDFs
│   ├── curriculum/       # Canonical module definitions & curriculum topics
│   ├── m16_synthetic/    # Synthetic questions for offline ML training & practice
│   └── processed/        # [GIT-IGNORED] Extracted questions, papers & reports
├── models/               # [GIT-IGNORED] Trained topic classifier model binaries
├── scripts/              # Ingestion, training, evaluation, and export scripts
├── services/             # Core extraction, parsing, ML, and bank services
└── tests/                # Comprehensive unit, integration, and regression tests
```

---

## Git Safety & Intellectual Property Compliance

Examination papers contain restricted institutional assessment material and copyright-protected text. Strict Git policies are enforced:

- **Source PDFs:** All authentic PDF files in `datasets/authentic/` (including all subfolders) are recursively ignored via `.gitignore` (`datasets/authentic/**/*.pdf`). Under no circumstances should source PDFs be force-added to version control.
- **Processed Question Repositories:** Extracted question data (`datasets/processed/questions.json`, `papers.json`, `topic_classifications.json`) is Git-ignored by default to prevent leaking restricted examination content into version control.
- **Model Binaries & Temporary Artifacts:** Trained model files (`models/*.joblib`, `models/*.onnx`), cache files (`.pytest_cache/`, `__pycache__/`), and evaluation outputs are excluded from Git.

---

## Reproducible Authentic Dataset Regeneration

Because authentic examination files are excluded from Git, each developer or deployment environment must regenerate the local repository from authorized local PDF files.

### Regeneration Instructions

1. **Place Authorized PDFs:**
   Copy the authorized SLIIT 3rd Year past-paper PDF files into:
   ```text
   ai-services/c2/datasets/authentic/
   ```
   Subfolders by module or year (e.g., `datasets/authentic/SE3080/`) are supported and scanned recursively.

2. **Activate the Python Virtual Environment:**
   ```powershell
   cd ai-services/c2
   .\.venv\Scripts\Activate.ps1
   # Or on macOS/Linux: source .venv/bin/activate
   ```

3. **Execute the Ingestion Pipeline:**
   ```powershell
   python scripts/ingest_authentic_dataset.py
   ```

4. **Ingestion Operations Performed:**
   - **Recursive PDF Discovery:** Scans all subdirectories and validates file signatures.
   - **Provenance & Duplicate Checking:** Computes SHA-256 hashes to detect and prevent duplicate paper processing.
   - **Scanned Document Quarantining:** Automatically identifies non-searchable or scanned bitmap PDFs (lacking a text layer) and quarantines them into `datasets/processed/quarantined_papers.json` without failing the pipeline.
   - **Heading & OCR Normalization:** Handles OCR imperfections (such as corrupted headings like `Q!!stion`) and multi-part structures (including Part A MCQs).
   - **Nested Subquestion Parsing:** Accurately decomposes questions into nested subquestions (Roman numerals `(i)`, alphabetic `(a)`, and numbered parts `(1)`) using strict sequence validation and mark constraints to prevent splitting code snippets or lists.
   - **Mark Extraction:** Parses marks `[X marks]` / `(X marks)` and flags questions with ambiguous or unstated marks as `ambiguous`.
   - **Topic Classification Pipeline:** Applies M17 topic classification models, abstaining or leaving questions unclassified until verified by a lecturer.
   - **Repository Outputs:** Atomically writes:
     - `datasets/processed/questions.json` (Structured flat question bank)
     - `datasets/processed/papers.json` (Paper-level metadata and hash provenance)
     - `datasets/processed/topic_classifications.json` (Topic predictions and abstention records)
     - `datasets/processed/quarantined_papers.json` (List of scanned/unreadable papers)
     - `datasets/processed/processing_report.json` (Detailed execution metrics)

5. **Verify the Dataset:**
   ```powershell
   python -m pytest tests/test_batch_paper_ingestion.py -q
   ```

---

## Missing-Dataset Safeguard Policy

The `StudentQuestionBank` service implements a strict guard against missing datasets:

- If `datasets/processed/questions.json` or `topic_classifications.json` has not yet been generated, `StudentQuestionBank` raises a descriptive `FileNotFoundError` explaining that the authentic dataset is not generated and instructing the user to run `python scripts/ingest_authentic_dataset.py`.
- **No Silent Fallback:** The system will **never** silently substitute synthetic questions into authentic past-paper practice. Synthetic practice is only accessible via the explicitly labeled **Synthetic Practice (Experimental)** mode.

---

## Running Tests and Services

```powershell
# Run all C2 Python tests
python -m pytest

# Run FastAPI development server
uvicorn app.main:app --reload --port 8000
```
