# C4 learning-path API examples

Base: `/api/v1/c4` (auto-mounted). All routes require `Authorization: Bearer <JWT>`.

Student identity is taken from the token via `resolveStudentId`. Students must not
pass another student’s id. Lecturers must pass `studentId`.

## Create (idempotent active path)

```http
POST /api/v1/c4/paths
Content-Type: application/json

{
  "clientRequestId": "optional-retry-key",
  "horizon": 8,
  "goal": { "label": "Y3S2 revision" },
  "forceNew": false
}
```

Returns the existing active path when one already exists (`reused: true`) unless
`forceNew: true`. Same `clientRequestId` always returns the same stored path.

## List / active / detail

```http
GET /api/v1/c4/paths
GET /api/v1/c4/paths/active
GET /api/v1/c4/paths/<pathId>
```

Lecturer: append `?studentId=IT20261234`.

## Self-reported progress (no C1 mastery write)

```http
POST /api/v1/c4/paths/<pathId>/progress
Content-Type: application/json

{
  "activityId": "c1_practice:file_organization_indexing",
  "status": "self_reported_complete"
}
```

Duplicate posts are safe. This does **not** create a correct-answer event.
Assessed performance still goes through `POST /api/v1/c1/practice/answer`.

## Replan (preserves completed)

```http
POST /api/v1/c4/paths/<pathId>/replan
Content-Type: application/json

{ "horizon": 8 }
```

Archives the prior revision into `c4_learning_path_revisions`, rebuilds pending
order from a fresh C1 twin/insights snapshot, keeps `self_reported_complete` items.

## Refresh / revisions

```http
POST /api/v1/c4/paths/<pathId>/refresh
GET  /api/v1/c4/paths/<pathId>/revisions
```

Refresh re-reads C1 twin/insights and may mark `practice_verified` from C1 sessions/events.

Create/replan accept schedule prefs: `studyStartDate`, `examDate`, `dailyMinutesBudget`,
`studyDays` (0=Sun…6), `planDayCount`, `estimatedMinutesPerActivity`.

## Mock quizzes (C4 practice-bank)

```http
GET  /api/v1/c4/exams/sources
POST /api/v1/c4/exams
GET  /api/v1/c4/exams
GET  /api/v1/c4/exams/<attemptId>
POST /api/v1/c4/exams/<attemptId>/answers
POST /api/v1/c4/exams/<attemptId>/submit
```

`source=c2_past_paper` returns **503** until C2 exposes an HTTP API.

## Feedback

```http
POST /api/v1/c4/feedback
GET  /api/v1/c4/feedback
```

## Synthetic simulation demo (v1) — no DB writes

Python base URL is **server-only** (`C4_AI_URL`, default `http://127.0.0.1:8004`).
Browser never supplies a target host.

```http
GET  /api/v1/c4/simulation/v1/ready
GET  /api/v1/c4/simulation/v1/scenarios
GET  /api/v1/c4/simulation/v1/path/ready
GET  /api/v1/c4/simulation/v1/path/catalogue
POST /api/v1/c4/simulation/v1/path/predict
GET  /api/v1/c4/simulation/v1/supervised/ready
POST /api/v1/c4/simulation/v1/supervised/response
POST /api/v1/c4/simulation/v1/supervised/exam-score
POST /api/v1/c4/simulation/v1/supervised/pass
```

Prefer labelled scenarios from `GET .../scenarios` (full `request` payloads), or
`{ "use_synthetic_scenario": true, ... }` knobs on predict routes. Responses include
`demo_not_persisted: true`. Not student readiness; operational path remains heuristic.
