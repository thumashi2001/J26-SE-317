# C4 authenticated browser verification

No credentials or tokens recorded here.  
Evidence folder: `docs/evidence/pp1-browser-20261015/screenshots/`  
Operator account: authorized test student (Cursor IDE browser panel).  
Verification date: **2026-10-16**.

---

## Browser workflows (verified)

| ID | Workflow | Status | Screenshots |
|---|---|---|---|
| 1 | Study plan load → Upcoming → Replan (rev 4→5) → Reload | **Pass** | `02`–`05`, `19` |
| 2 | Practice link → C1 → partial → Refresh → `practice_observed` | **Pass** | `06`–`08` |
| 3 | Finish full C1 session → Refresh → `practice_verified` + session evidence | **Pass** | `16`–`18` |
| 4 | Replan / Reload keep completed (verified + self-reported) | **Pass** | `17`, `19` |
| 5 | Mock quiz create → freeze estimate → save → resume → submit → review | **Pass** | `09`–`12`, `20` |
| 6 | Feedback “PP1 test” → list → reload persistence | **Pass** | `13`–`15` |
| 7 | Heuristic schedule vs experimental model reco kept distinct | **Pass** | `04`, `07`, `19` |
| Defect | `/c4` was ComingSoon; wired to `PathPage` | **Fixed** | `01` |

---

## Completion kinds (browser-proven)

| Kind | How produced | UI label | Evidence |
|---|---|---|---|
| **self_reported** | Progress → **Mark done** | Marked done (self-reported) | RESTful Web Services… `17`, `19` |
| **practice_observed** | Answer ≥1 C1 item, leave unfinished → Refresh | Practice in progress (not complete) / `practice_observed` | Framework… before finish `07`–`08` |
| **practice_verified** | Finish all C1 session items → Refresh | Verified practice (session finished) | Framework… `17`–`18`; Progress shows `Linked C1 session: … · 7/7 answered` |

Self-reported and verified remain **distinct** on Completed and Progress after replan (revision 5: “Completed items were kept”).

---

## Persistence evidence

- **Plan:** Reload saved plan after replan → prefs + Completed list intact (`19`).
- **Quiz:** Save answers → hard navigate away → reopen `in_progress` → Answered 1/3 restored (`11`); submit → `submitted 66.7%` (`12`, `20`).
- **Feedback:** Submit with “PP1 test…” → appears in list → full page reload → same entry (`15`).

---

## Model / UI claims (16% vs 66.7%)

On the submitted 3-Q attempt (`20`):

- Pre-exam block: **“Experimental simulation-trained readiness (clipped display): 16% — not a forecast of this quiz’s observed score”** (frozen at attempt start).
- Observed score: **66.7% (2/3)** from this practice-bank quiz only.
- Copy states the 16% estimate is **not** validated real-student model accuracy.

Operational daily cards use heuristic `weakest_stored_mastery_v1`. Experimental next-topic card uses `se-path-sim-v1` with serving-assumption disclosure. These are not interchangeable.

---

## Lecturer access status

**Shared `App.jsx` change already made** (no further shared edits):

- Student: `/c4` + `/c4/*` → `PathPage` (replaced ComingSoon).
- Lecturer: `/lecturer/c4` + `/lecturer/c4/*` → `LecturerPathPage` (replaced ComingSoon).

**Authorization:** Shared `resolveStudentId` still treats lecturer + `studentId` as identification only (no roster). C4-owned `resolveC4StudentId` **fails closed** (403 `lecturer_scope_unavailable`) for lecturer roles on path/exam/feedback APIs. `LecturerPathPage` shows **Unavailable** — does not invent roster membership. See `backend/src/modules/c4/docs/APP_JSX_ROUTE_PATCH.md`.

---

## Targeted automated checks (not full suite)

Re-run 2026-10-16:

- `c4StudentAccess.test.js` — lecturer fail-closed
- `examService.test.js` — timeout finalize + duplicate submit/save safety  
- `authOwnership.test.js` — shared student ownership unchanged  

**Sim isolation:** `simDemoController` / `simScenarioBuilder` are synthetic-only (no path/progress writes). Demo UI states inputs are not the C1 twin. Live predict buttons may stay disabled if C4 AI readiness is down; that does not affect real progress.

---

## Remaining limitations (not marked complete)

- **C2 past papers:** unavailable (no authorized delivery/answer-key API).
- **Next-answer response model:** blocked (no C1 item difficulty).
- **Lecturer roster UX:** unavailable until product-owned scope exists.
- **Live path/exam models:** experimental / simulation-trained; assumed `prior_strength`; not real-student validated accuracy.

---

## Two-minute demo sequence (verified)

1. Login as authorized test student → **Adaptive path** (`/c4`).
2. Study plan: show Today / Completed; note heuristic chip vs experimental next-practice card.
3. Open Progress: point at **Verified practice** + linked session (`7/7`) vs **Marked done (self-reported)**.
4. Mock quizzes: open the `66.7%` attempt → expand pre-exam estimate → contrast **16% experimental readiness** with **observed 66.7%**.
5. Feedback: show “PP1 test” entry still listed after reload.
6. (Optional) Say aloud: C2 papers and lecturer roster remain unavailable; sim demo does not write student progress.
