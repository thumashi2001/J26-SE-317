# Lecturer review fixes: "Change the mark" reason box and floating "Sample" badge (2026-10-21)

C3-owned files only. Nothing staged or committed; no shared file changed (one root cause lies in a shared file and was worked around inside C3, see Bug 2).

## Bug 1: the Reason textarea loses focus on every keystroke
**Root cause (reproduced).** `Dialog` in `frontend/src/pages/c3/components/c3ui.jsx` ran its focus set-up in an effect that depended on `[onClose]`. The review page passes an inline `onClose={() => !busy && setOverrideOpen(false)}`, a new function on every render. Each keystroke in Reason updates state, re-renders the page, re-runs the effect and moves focus to the `data-autofocus` field (New mark); the cleanup also restored focus to the opener first. The mark field looked fine because it is the field that takes focus. The batch review dialog uses the same `Dialog`, so it was affected too.
**Reproduction before the fix** (real keystrokes, `keys_check` script, isolated stack): typing "Checked each criterion by hand" into Reason produced the value `"C"` and left focus on `ov-mark`. **After the fix:** the full text, focus stays on `ov-reason`.
**Fix.** `Dialog` keeps the latest `onClose` in a ref (`closeRef`) and the effect runs once per open (`[]`). Escape, backdrop click and the Close button call `closeRef.current`. No other behaviour changed.
**Already correct and verified, not changed:** controlled `value`/`onChange`; `maxLength` 2000; validation message "Give a reason. It is saved with the result." plus mark range validation; the original automatic mark is stored separately (`automated_mark` vs `final_mark`, `override_reason`, `reviewed_by`); the draft lives in page state, so it survives Escape/Cancel and re-render and is replaced by the saved reason on reload; the student sees the final mark with the adjustment notice and reason.

## Bug 2: floating "Sample" label
**Root cause (reproduced in Chrome).** The queue renders the label as `<span class="chip">`. `frontend/src/pages/auth.css:25` (shared, login page) defines a **global** `.chip { position: absolute; z-index: 1; … animation: orbfloat … }` for decorative login chips, and Vite bundles all CSS globally, so every `.chip` in the app becomes absolutely positioned and animated. Measured before: computed `position: absolute; z-index: 1` for the queue's Sample chips. The review page had no Sample label at all.
**Fix (C3 only).** New `SourceBadge`/`sourceKind` in `c3ui.jsx` (single source of truth for sample / test / student) with its own class `.c3-source-badge` in `c3.css` (`position: static`, inline). The queue uses it beside the student id; the review page shows it in the header next to the status for sample and test submissions only. Real-student rows show no badge; legitimate sample identification is preserved. The shared `auth.css` rule was **not** changed: it should be scoped (for example `.auth-art .chip`) by its owner; any other page using `.chip` is exposed to the same problem. Measured after, at 1280/768/375 px: the badge is `position: static`, inside its table row, one per page on the review view, never outside the viewport.

## Tests
| Test | Type | What it proves |
|---|---|---|
| Browser L28 | real keystrokes (`keyboard.type`), isolated stack | Full multi-word reason, Enter newline, paste (`insertText`), select-all replace, focus stays in Reason, Tab stays inside the dialog, Escape keeps the draft, save persists, reopened page shows reason, adjustment notice and automatic mark, stored `automated_mark` ≠ `final_mark` |
| Browser L28b | student view | Finalized adjusted mark, adjustment notice and reason visible to the student |
| Browser L29 | computed styles / geometry at 1280, 768, 375 px | Badge static and inside its row, no stray "Sample" text, no global `.chip` inside the C3 page, review badge in viewport, nothing overlaps the reason box |
| `analysis.test.mjs` (2 new) | component/static | `sourceKind` mapping, badge renders only for sample/test, uses no `.chip` class, CSS rule is static without animation; static guard that `Dialog` uses `closeRef` and no `[onClose]` dependency (the behavioural proof is L28 because server rendering cannot run effects) |
**Does the new test catch the bug?** Yes: with the fix temporarily reverted, the keystroke check produced `"C"` with focus on `ov-mark` (failure); with the fix restored (byte-identical to the saved copy) it passed.
Fresh results: browser suite 103/103 (API matrix 35/35); frontend component tests 10/10; backend `npm test` 115 tests: 112 pass, 0 fail, 3 todo; `vite build` succeeds. The earlier Playwright `.fill` steps could not detect Bug 1; they remain but are no longer the only coverage.

## Files changed
`frontend/src/pages/c3/components/c3ui.jsx` (Dialog ref fix; `SourceBadge`, `sourceKind`), `LecturerQueuePage.jsx`, `LecturerReviewPage.jsx`, `c3.css`, `frontend/tests/analysis.test.mjs`, `reports/c3_remediation/ui_tests/e2e.mjs`.

## Not changed / open
Shared `pages/auth.css` `.chip` rule (owner decision; proposed scoping above). Keyboard checks cover Tab (focus stays inside the dialog), Escape and typing focus, and only in Chrome; no screen-reader or cross-browser test.
