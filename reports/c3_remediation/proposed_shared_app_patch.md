# Proposed change to the shared `backend/src/app.js` (DOCUMENTATION ONLY — NOT APPLIED)

`backend/src/app.js` is shared by C1–C4 and auth/admin, so it was not modified. This document lists the unresolved issues found in the C3 security audit and a proposed patch for the owners to approve.

## Unresolved issues (all demonstrated over real HTTP on an isolated local stack)
| # | Issue | Evidence | Affects |
|---|---|---|---|
| A1 | Malformed JSON body → HTML 400 page (Express default error page) | `POST /c3/assess` with `{"x":` → `text/html`; tests `AUDIT-B9b` (todo) | every module |
| A2 | Unknown non-C3 path → HTML 404 | `GET /api/v1/anything-else` | every module |
| A3 | `cors()` allows every origin | `app.js:10` | every module |
| A4 | `express.json()` default 100 kB limit only; no per-route limits | `app.js:11` (C3 enforces its own field limits since this audit) | every module |
| A5 | No security headers (helmet) | not present | every module |
| A6 | No rate limit on login | `auth` module; C3 has its own limiter on C3 routes only | auth |
| A7 | Encoded traversal path (`/c3/submissions/../../etc/passwd`) is normalised before routing and answered by the shared HTML 404 | probe | every module |

## Proposed patch (`backend/src/app.js`)
```diff
 const app = express();
-app.use(cors());
-app.use(express.json());
+// Allowed browser origins come from CORS_ORIGINS (comma separated); unset keeps today's open behaviour.
+const origins = (process.env.CORS_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
+app.use(cors(origins.length ? { origin: origins } : undefined));
+app.use(express.json({ limit: process.env.JSON_BODY_LIMIT || '200kb' }));
@@
     console.log(`Mounted /api/v1/${name}`);
   }
 }

+// JSON answers for unknown paths and body-parser errors (no HTML pages, no stack traces).
+app.use((req, res) => res.status(404).json({ error: 'Not found' }));
+app.use((err, req, res, next) => {
+  if (res.headersSent) return next(err);
+  if (err?.type === 'entity.parse.failed') return res.status(400).json({ error: 'Invalid JSON body' });
+  if (err?.type === 'entity.too.large') return res.status(413).json({ error: 'Request body too large' });
+  console.error('[app] unhandled error:', err?.message);
+  res.status(err?.status >= 400 && err.status < 500 ? err.status : 500).json({ error: err?.status < 500 ? err.message : 'The request could not be completed' });
+});
+
 export default app;
```
Optional (needs a new dependency, so a separate approval): `app.use(helmet())`; login throttling in `modules/auth` using the same fixed-window approach as `modules/c3/middleware/rateLimit.js`.

## Impact and risks
- Every module's HTML error pages become JSON. Any client that parses an HTML error body would change (none known in the frontend; the frontend reads `error` from JSON).
- `CORS_ORIGINS` unset keeps the current behaviour, so existing dev setups are unaffected; setting it blocks other origins (the Vite dev server uses a proxy, so same-origin).
- A 200 kB JSON limit is larger than the current C3 payloads (answers ≤ 20 000 chars, batches ≤ 500 rows may approach it; raise `JSON_BODY_LIMIT` if needed).
- Tests that would change: `AUDIT-B9a` and `AUDIT-B9b` in `backend/src/modules/c3/tests/c3_audit.test.js` can be converted from `todo` to normal tests. C1/C2/C4 suites must be re-run (the C4 suite is 73 tests).
- Rollback: revert the single file.

## Status
BLOCKED pending approval from the owner(s) of the shared application file. No shared file was modified.
