# 04 C3 security fixes (backend; nothing committed)

| ID | Issue | Change | Files |
|---|---|---|---|
| B1 | JWT secret fell back to a source-visible constant when `AUTH_SECRET` unset | `secret()` now throws in every environment; no fallback. Callers (auth, admin, C1, C3 routes) all rely on `.env`; tests already set `AUTH_SECRET`. | `backend/src/middleware/auth.js` |
| B8 | Client-supplied answer key, rubric, max marks, `is_demo` trusted | Students may send only their answer plus `demo_id` (server demo bank) or `batch_id` (lecturer batch setup); configuration fields are rejected with 400, unknown ids 404, non-string ids 400. Lecturers/admins may still send inline configuration (trusted authors, tagged `config_source`). Frontend student page sends only the minimal body. | `services/assessmentConfig.js` (new), `data/demoAssessments.js` (new, generated from `frontend/.../presets.js`), `controllers/c3Controller.js`, `frontend/src/pages/c3/AssessmentPage.jsx` |
| B4 | No batch ownership | `assertBatchAccess`: creator or admin only, on get/validate/mark/finalize-all (403) | `services/batchMarkingService.js`, controller |
| B7 | Operator injection via `setup_id`, `batchId`, `status`, `batchId` filters | `requireStringId` (400 for non-strings); `listSubmissions` rejects non-string filters | same + `submissionService.js` |
| B6 | Persistence failure returned 200 | now 503 with a safe message, server-side log of `err.message` only; success includes `persisted: true`; 4xx errors pass through | controller |
| B2 | Re-posting a batch id reopened finalized work | 409 if the existing submission/result is not `pending_review` | `submissionService.js` |
| B3 / X1 | Override mark unbounded, `"Infinity"` accepted, coercion of arrays/booleans | numeric/finite check, ≤ `total_possible_marks`, reason ≤ 2000 chars | `submissionService.js` |
| B5 | Non-atomic review/finalize | conditional `updateOne({_id, status: {$ne: 'finalized'}})`, 409 if nothing matched; `finalized_by` recorded | `submissionService.js` |

## Not changed (reported)
- Raw proxy endpoints `/analysis`, `/marking`, `/feedback`, `/mindmap` still accept caller-supplied configuration for any authenticated user: they persist nothing and affect no academic record, but are unmetered (rate limiting is a shared-app change).
- AUDIT-B9 (404/error JSON middleware), CORS, login rate limit, Python service authentication, `finalize-all` auto-accepting unreviewed results, review history array: outside the four requested issues or in shared code; remain open.
- Admin may access every batch (documented assumption; policy decision for the owner).
- `backend/seed_users.js` untouched (untracked, hard-coded demo password).
