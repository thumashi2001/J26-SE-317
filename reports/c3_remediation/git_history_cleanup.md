# Git history cleanup — Claude co-author trailer removal

Branch: `feature/c3-pp1-experiments-20261020` · Repo `thumashi2001/J26-SE-317` · Date 2026-10-21

## Result
| Item | Value |
|---|---|
| Original HEAD (local = origin) | `8fdbdbdb7be97cc80880a96110518e590d595d0a` |
| Rewritten HEAD (local = origin) | `0817e185b4506c0586982817b3a457823cabb326` |
| Commits on branch | 207 (unchanged) |
| Trailer commits found | 38 = 29 by Vk-Viman + 9 by Thumashi Nawanjana |
| Rewritten | **29 (all Vk-Viman)**; 178 commits keep their original hash |
| Trailer left | 9 Thumashi commits (see below) |
| Remote update | `git push --force-with-lease=<branch>:8fdbdbd` succeeded; only this ref changed |

## Why 29 and not 38
The 9 Thumashi-authored commits (also present in `origin/Development` and ~30 other remote branches) were deliberately left untouched, as decided. GitHub will therefore still show "claude" as co-author on those 9 commits. Removing it would change hashes in Development and the component branches and needs team coordination.

## Method
1. Backup: `_git_backups/c3-pp1-experiments-pre-rewrite.bundle` (verified with `git bundle verify`; contains the branch and local `feature/c3-pp1-final-integration-20261020`), local branch `backup/c3-pp1-experiments-20261020-pre-trailer-rewrite` at `8fdbdbd`, ref snapshots `refs_before.txt`, `ls_remote_before.txt`, `commits_before.txt`, `status_before.txt` (all in `C:\Users\M S I\Desktop\Reserach\DEVELOPMENT\_git_backups\`).
2. Rewrite performed in an isolated clone (`_git_backups/rewrite_clone`) so the working tree was never touched. `git filter-branch --commit-filter` (`_git_backups/commitfilter.sh`): a commit is recreated only if its author is Vk-Viman and it has the exact line `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (or a parent was rewritten); every other commit is returned unchanged. A first attempt with `--msg-filter` rewrote all 207 commits (it drops GitHub `gpgsig` signatures) and was discarded before any push.
3. Pre-push check: GitHub branch still `8fdbdbd`; push used force-with-lease against that value. Other GitHub refs differ from the backup snapshot only by teammates' own activity (`main` moved, new `component_1_model_code_comments`/PR 42) — not by this operation.

## Verification (all executed)
- Tip tree identical: `69822a4c920967a6362c5144505441fa9cfc7cad` before and after; every one of 207 commits matched old↔new by tree + author + committer + date + subject (`commit_map_old_new.csv`).
- Message diff for all 29 rewritten commits: only the Claude trailer line (and trailing blank line) removed.
- 0 Claude trailers on Vk-Viman commits; 9 on Thumashi commits remain. Author name/email/dates and committer fields unchanged.
- No originally signed commit was rewritten (0 of 29), so no signature was lost.
- After push: re-fetched; `origin/<branch>` = `0817e18`; only that ref changed between pre-push and post-push `ls-remote`.
- Local repo: `git reset --mixed origin/<branch>` (trees identical) so the uncommitted `.gitignore` edit and untracked files are unchanged; the 49 protected-file hashes still match; `git status` equals the earlier state.
- Identity unchanged: `user.name=Vk-Viman`, `user.email=electrusgreen@gmail.com`.

## Backup recovery
`git clone C:\...\_git_backups\c3-pp1-experiments-pre-rewrite.bundle` (or `git fetch` from it) restores the original branch at `8fdbdbd`. Local branch `backup/c3-pp1-experiments-20261020-pre-trailer-rewrite` also points there.

## Future commits
Mechanism: Claude Code's built-in commit/PR attribution (no hook, template or gpgsign involved; Git author config is separate). Installed version 2.1.305 supports the `attribution` setting. Added project-local, untracked `.claude/settings.local.json` with `attribution.commit = ""` and `attribution.pr = ""`, plus a rule in `CLAUDE.md`. Global Claude/Git settings untouched.

## Caveats / for collaborators
- Local branch `feature/c3-pp1-final-integration-20261020` (`b1b148b`) is still based on the old hashes; left as is. To move it later: `git rebase --onto 0817e18 8fdbdbd feature/c3-pp1-final-integration-20261020` (after a backup).
- Anyone who pulled the old branch should fetch, keep a backup branch, and rebase their own commits onto the new tip with `git rebase --onto origin/feature/c3-pp1-experiments-20261020 8fdbdbd <their-branch>`; no destructive reset needed.
- Old commit URLs/PR references to the 29 rewritten hashes no longer resolve on that branch (map in `commit_map_old_new.csv`).
