# 07 Git history verification

| Check | Result |
|---|---|
| Original / rewritten HEAD | `8fdbdbd` → `0817e18` (local = origin) |
| Commits | 207 before and after |
| Rewritten | 29 (all Vk-Viman); 178 keep their hash (no signatures lost: 0 of the rewritten commits were signed) |
| Tree of every commit equals its original; tip tree `69822a4c…` identical; `git diff old-tip new-tip` empty | yes |
| Message diff of the 29 | only the Claude trailer line (+ trailing blank) removed |
| Claude trailers left | 0 on Vk-Viman commits; 9 on Thumashi commits (by decision) |
| Author/committer name, email, dates | unchanged |
| Remote | pre-push branch == `8fdbdbd`; `--force-with-lease` push; post-push `ls-remote` differs only on this branch; re-fetched and re-read |
| Other branches / tags | untouched (local `feature/c3-pp1-final-integration-20261020` still on old hashes by request) |
| Backup | verified bundle + local backup branch (recoverable) |
| Working tree | uncommitted files preserved (mixed reset to a tree-identical commit); 49 protected hashes unchanged |
| Tests after rewrite | Python 324 pass / Node 91 pass (run after the security changes) |
