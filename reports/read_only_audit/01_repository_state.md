# 01 Repository state (read-only audit, 2026-10-21)

Labels: **V** verified by execution/inspection · **R** reported by documentation, not reproduced · **I** inferred · **B** blocked.

| Item | Result | Label |
|---|---|---|
| Working directory | `…/DEVELOPMENT/ADAPTIVE_LEARN_SE` | V |
| Branch | `feature/c3-pp1-experiments-20261020` | V |
| HEAD | `8fdbdbdb7be97cc80880a96110518e590d595d0a` ("docs: update CLAUDE.md for the repaired dataset workflow") | V |
| `origin/feature/c3-pp1-experiments-20261020` | identical (`git ls-remote` + `rev-list --left-right --count` = 0 / 0). The claimed push is reflected on the remote. | V |
| Working tree at start and at end | only the protected untracked items: `backend/seed_users.js`, `scratch/`, `frontend/public/evidence_{feedback,integration,mcq_result,model_training}.html`, `docs/pp1/screenshots/`, `docs/pp1/evidence/{screenshots,recordings}/` | V |
| Python / Node | 3.14.7 (venv `ai-services/c3/.venv_c3`) / v24.21.0 | V |
| Key dependency pins | numpy 2.5.4, pandas 3.0.6, scikit-learn 1.9.1, pydantic 2.13.5, fastapi 0.141.1, pytest 9.1.1 (`ai-services/c3/requirements.txt`) | V (file) |
| Docker | container `adaptivelearnse-neo4j` up 10 h | V |

## Commits since `84f7e7d` (66 commits)
- 37 are other authors' C1/C2 commits merged from `Development`.
- **29 are commits made in this session (f21dba4 merge → 8fdbdbd); every one carries `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`** (V). Author is `Vk-Viman` on all of them.
- The six commits that completed the repair: `11ff410` (archive), `83b063e` (Phase 1 audit docs), `460ad63` (repair pipeline), `c3cde9d` (repaired dataset), `50d3f5a` (generator removal), `488089c`/`ecc4c90`/`8fdbdbd` (docs, banners, CLAUDE.md).

## Removals actually verified
`datasets/generator`, `generate_c3_dataset.py`, `validate_dataset.py`, `c3_synthetic_v6`, `trial_c3_v6_*`, `datasets/source` are absent from `git ls-files` (V). Retained tests: `test_llm_preflight.py`, `test_llm_cache_and_limits.py`, `test_dataset_repair.py`, `test_experiment_framework.py` (V).

## Snapshot comparison (end of audit)
Branch and HEAD unchanged; `git status` identical; 49 protected-file hashes identical; sha256 of 318 tracked dataset/doc/test/code files identical; ignored-file listing identical. (Re-checked after the reports were written; see §10 of the chat summary.)
