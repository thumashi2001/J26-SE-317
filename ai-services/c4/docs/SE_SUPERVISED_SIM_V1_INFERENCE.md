# SE supervised simulation v1 inference (isolated)

Protocol: **`se-supervised-sim-v1`**. Does **not** replace
`/v1/se-supervised-simulation/*` (v0). Does **not** feed `se-path-sim-v1`.

## Bundle

```text
runtime-artifacts/se_supervised_sim_v1/train_full_se-supervised-sim-v1_20261014T002241.664Z/export_bundle/
```

- Catalogue: 46 topics; SHA-256 `95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622`
- Response features: **54**; exam features: **98**
- Selected models: response=`hist_gradient_boosting_classifier`,
  exam_score=`ridge_regression`, pass=`logistic_regression`

## Thresholds (not institutional rules)

| Constant | Value | Role |
|---|---|---|
| `PASS_THRESHOLD` | **0.55** | Synthetic exam-score **label** cutoff for `y_pass` |
| `CLASSIFICATION_PROB_THRESHOLD` | **0.5** | Hard-class accuracy only (separate) |

## Startup

```powershell
cd ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
# optional: $env:C4_SE_SUPERVISED_V1_BUNDLE_DIR = "...\export parent..."
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

## Endpoints

| Method | Path |
|---|---|
| GET | `/v1/se-supervised-simulation-v1/ready` |
| POST | `/v1/se-supervised-simulation-v1/response` |
| POST | `/v1/se-supervised-simulation-v1/exam-score` |
| POST | `/v1/se-supervised-simulation-v1/pass` |

Missing/invalid artifacts → **503** for these routes only. Missing features /
non-finite values → **400**. No imputation; no silent v0 fallback.

## Sample requests

Feature names must match saved schemas exactly (see ready payload
`feature_schema_response` / `feature_schema_exam`).

```powershell
# Response (topic one-hot must sum to 1)
$body = @{
  protocol = 'se-supervised-sim-v1'
  features = @{
    difficulty = 0.0
    topic_prior_attempts = 4.0
    topic_prior_correct = 2.0
    topic_prior_accuracy = 0.5
    topic_prior_streak = 1.0
    global_prior_attempts = 12.0
    global_prior_accuracy = 0.5
    learner_step = 12.0
    # plus topic_oh_<id> for all 46 topics with exactly one 1.0
  }
} | ConvertTo-Json -Depth 5
# Prefer building the full dict in Python (see tests/test_se_supervised_v1_inference.py)
```

Exam-score responses include `exam_score_raw` and optional
`exam_score_clipped_display` (clip to [0,1] for display only).

Pass responses include `p_pass`, `pass_threshold=0.55`, and
`classification_prob_threshold=0.5`, plus `real_exam_validation=false`.

## Authenticated Node proxy (demo UI)

Node (`C4_AI_URL`, default `http://127.0.0.1:8004`) exposes:

- `POST /api/v1/c4/simulation/v1/supervised/response`
- `POST /api/v1/c4/simulation/v1/supervised/exam-score`
- `POST /api/v1/c4/simulation/v1/supervised/pass`

Synthetic labelled scenarios: `GET /api/v1/c4/simulation/v1/scenarios`.
Live C1 mapping: [`LIVE_INPUT_COMPATIBILITY_V1.md`](LIVE_INPUT_COMPATIBILITY_V1.md).

## Limitations

- Simulation-only; not real-exam validation.
- The 55% synthetic pass-label cutoff is **not** an institutional rule.
- Not wired into the RL simulator or the operational heuristic student path.
- Demo UI only; predictions are not student readiness.
