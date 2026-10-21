# Post-merge browser check — 2026-10-18

This note is separate from `docs/browser-evidence/2026-10-17-se-path-multi-v2.md`. The older screenshots do not verify this merged tree.

Opening `http://localhost:5173/c4` redirected to `/login`. No authorized student, lecturer, or admin session was present. No plan, replan, quiz, or feedback action was performed.

Screenshot: `c4-post-merge-login-required.png`.

C4 inference readiness at the same time: protocol `se-path-multi-v2`, selected seed 1, `student_plan_integration` requestable, artifact `serves_students` false. That is service readiness, not an observed student request.
