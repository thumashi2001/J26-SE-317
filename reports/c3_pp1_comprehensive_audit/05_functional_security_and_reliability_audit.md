# 05 Functional, security and reliability audit

Static code reading plus the executed offline probes below; no dynamic security testing, no external calls. Severity = my judgement. "Fix" lines are proposals only and wait for approval.

## 1. Executed functional probes (V; FastAPI TestClient, `/c3/assess`, no network)
| Case | Result |
|---|---|
| `arch-full` | 4/4 (L4) |
| `arch-partial` | 2/4 (L2) |
| `arch-zero` | 0/4 (L0) |
| `oop-higher` | 3/3 (L3) |
| `quality-multi` | 2/4 (C1 = L2, C2 = L0) |
| Paraphrase of full answer | **0/4** (no shared words) |
| Negated statement | **4/4** (words present, meaning ignored) |
| Keyword stuffing | **4/4** |
| Long irrelevant padding | 4/4 (padding neither rewarded nor penalised) |
| Empty answer | 0/4 |
MCQ presets are handled in Node (not probed here).

## 2. Functional defects (named, most are encoded as xfail/todo tests)
- AUDIT-A1 cross-field invalid rubric → 500 (high, `routes/assessment.py:10-13`).
- AUDIT-M1 unsupported answer gets lowest positive level when no zero level (medium).
- AUDIT-M4 criterion concepts merged into every level → partial level unreachable; in the dataset experiment this makes Condition E binary (high).
- AUDIT-M5 single shared token satisfies a multi-word evidence requirement; no stop-words (medium).
- Mind map: star graph; node-id collision ("User Auth" vs "user_auth") (low).
- Node MCQ result → mind-map component likely crashes (I, high for demo, avoid).
- Persistence failure returns HTTP 200 with the AI result but no `submission_id` (AUDIT-B6).
- Batch marking is sequential, up to 15 s per item; failed rows are not persisted.

## 3. Security findings (separate from functional correctness)
| ID | Finding | Evidence | Severity | Proposed fix |
|---|---|---|---|---|
| B1 | JWT secret falls back to `dev-only-secret-change-me` when `AUTH_SECRET` unset and `NODE_ENV` ≠ production → forgeable lecturer/admin tokens | `middleware/auth.js:12-21` | high | refuse to start without secret outside tests |
| B8/N04 | Client supplies rubric, answer key, `max_marks`, `is_demo`; a student can self-grade an MCQ | `c3Controller.js:59-99`; `mcqMarkingService.js:126` | high | server-side question bank |
| B4 | No batch ownership check on read/mark/finalize | `batchMarkingService.js:250-258,343-347,460-468,553-557` | high | `created_by` check |
| B7b/c | `setup_id` `{"$ne":null}` operator injection matches any setup | `parseId` 14–20 | high (with B4) | reject non-strings |
| B7a | `?status[$ne]=x` operator in query | `submissionService.js:193-195` | low | type check |
| B6 | Persistence failure masked | `c3Controller.js:93-99` | high | 503 / `persisted:false` |
| B2 | Re-posting a batch id reopens a finalized result with stale `final_mark` | `submissionService.js:89-111` | medium | reject if finalized |
| B3/X1 | Override has no upper bound; `"Infinity"` passes | `:366-373` | medium | finite and ≤ total |
| B5 | Review/finalize read-then-write (non-atomic) | `:426-449` | medium | conditional update |
| B9 | No 404/error middleware (HTML errors) | `app.js:9-26` | medium | JSON handlers |
| — | Open CORS, no helmet, no rate limit on login or `/assess` | `app.js:10` | medium | limits |
| — | Python service unauthenticated; no max sizes on payloads (O(C×S×T) CPU) | `aiClient.js:11-14`; schemas | medium | shared secret + `max_length` |
| — | `backend/seed_users.js` untracked with hard-coded demo password | file | medium | keep untracked; do not commit |
| — | `finalize-all` auto-accepts unreviewed results; no `finalized_by`; no history | `batchMarkingService.js:575-599` | medium | audit trail |
Positives: scrypt, uniform login error, no `innerHTML`/`eval`, student answers not logged by Node or Python, API keys only in headers, `.env` ignored.

## 4. Reliability
Timeouts mapped (502/504/400); retry/backoff/rate-limit layer is solid; `/health` offline; no unique DB indexes (idempotency only in application code); the C1 bridge swallows errors; Python first-call latency can exceed the 15 s default.

## 5. Viva handling
Say: "I know these defects; each is a named test, none is hidden; the highest-risk four (B1, B8, B4, B6) are my first fixes after the viva." Do not demo a student editing the answer key.
