# 01 Initial state and backup (2026-10-21)

| Item | Value |
|---|---|
| Repo / branch | `ADAPTIVE_LEARN_SE`, `feature/c3-pp1-experiments-20261020` |
| HEAD at start | `8fdbdbd` (local = origin) |
| Working tree at start | uncommitted: `.gitignore` (user edit), untracked `backend/seed_users.js`, `frontend/public/evidence_*.html` (4), `scratch/`, `scripts/generate_evidence_screenshots.py`, `scripts/sync_verified_screenshots.py`, `reports/` |
| Audit reports reused | `reports/c3_pp1_comprehensive_audit/` (14 files) and `reports/read_only_audit/` (10 files); every finding below was re-verified against the current files |
| Git backup | `_git_backups/c3-pp1-experiments-pre-rewrite.bundle` (verified), branch `backup/c3-pp1-experiments-20261020-pre-trailer-rewrite`, ref/ls-remote snapshots (see `git_history_cleanup.md`) |
| Original dataset | `ai-services/c3/datasets/archive/C3-Phase3-v5-FINAL_original/` + `SHA256SUMS`, untouched; `datasets/c3_phase3_v5_repaired/` untouched (v2 is a new directory) |
| Protected files | 49 protected hashes re-checked after git cleanup: no difference |
| Remediation commit/push state | **nothing committed or pushed** (as instructed) |

Order executed: (1) Git history cleanup, (2) dataset diagnosis and v2 derivation, (3) C3 security fixes + tests, (4) model experiments, (5) regression and integration verification, (6) reports.
