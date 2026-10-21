# Shared frontend mount patch

**Status (2026-10-16):** Applied for **student** and **lecturer** routes in `frontend/src/App.jsx`.

## Exact shared `App.jsx` change already made

```jsx
import PathPage from './pages/c4/PathPage.jsx';
import LecturerPathPage from './pages/c4/LecturerPathPage.jsx';

// student area (replaced ComingSoon):
<Route path="/c4" element={<PathPage />} />
<Route path="/c4/*" element={<PathPage />} />

// lecturer area (replaced ComingSoon):
<Route path="/lecturer/c4" element={<LecturerPathPage />} />
<Route path="/lecturer/c4/*" element={<LecturerPathPage />} />
```

`frontend/src/config/menus.js` was **not** edited (Adaptive path / Adaptive paths entries already existed).

No further shared-file changes were made for lecturer authorization. Access policy is enforced in **C4-owned** code only (below).

## Lecturer access — fail closed (C4-owned)

Shared `resolveStudentId` (`backend/src/middleware/auth.js`) still returns any lecturer-supplied `studentId` **as identification only** — no roster check.

C4 APIs now use `resolveC4StudentId` (`backend/src/modules/c4/services/c4StudentAccess.js`) in path, exam, and feedback controllers:

- **Student:** own token identity (shared rules).
- **Lecturer:** **403** `lecturer_scope_unavailable` — clear message that access is unavailable until an approved class-roster / assignment scope exists.
- **UI:** `LecturerPathPage` shows an **Unavailable** panel; it does **not** offer student lookup or invent roster membership.

Do not claim safe cross-student lecturer browsing until a product-owned scope store exists (shared auth or verified assignment). C4 must not invent that roster.

## Do not change for this heuristic flow

- Do not wire ASSISTments `/v1/research/*` or SE simulation `/v1/se-*` into the student Adaptive path page as operational scheduling.
- Live prediction gaps remain mainly required input semantics (`prior_strength`, env-step fraction, item difficulty, etc.) — see `LIVE_INPUT_COMPATIBILITY_V1.md`.
