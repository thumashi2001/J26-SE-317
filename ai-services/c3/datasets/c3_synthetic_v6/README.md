# c3_synthetic_v6 (generated output goes here)

This folder is populated by `python datasets/generate_c3_dataset.py` (run from `ai-services/c3`). Nothing in it is
hand-edited. `_llm_cache/` holds the raw LLM responses so a run can be reproduced (`--resume`) without new API calls.
After a run, `DATASET_CARD.md` and `manifest.json` describe the release; `python datasets/validate_dataset.py` checks it.
Expert validation has NOT been performed: see `expert_review_sample.csv` for the rows to give a human grader.
