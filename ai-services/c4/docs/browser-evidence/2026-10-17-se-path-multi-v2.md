# Authenticated se-path-multi-v2 check — 2026-10-17

Student IT12345687, semester Y3S1, existing path `25589bd5-d3e7-48e7-b749-df0a354f3f80`. No tokens or connection strings are stored here.

The Colab export field `serves_students` stays false. Readiness now also returns `artifact_serves_students: false` and `student_plan_integration: requestable`. The plan request below is the observation that this checkpoint was used.

## Model used by the student replan

- Protocol: `se-path-multi-v2`
- Revision: `se-path-multi-v2-coverage-r2`
- Seed: 1
- Checkpoint SHA-256: `71f66525cd161d65805469f9effb55527f2fa848a26df401dc21d1bf60526c07`
- Catalogue: `95aaba520a28a494e9d6fed0c30de5999b6d47f376368424fb211acb434a1622`
- Python `POST /v1/se-path-multi-v2/predict` returned 200

Revision 8 pinned `nosql_big_data` practice (`/c1/practice/nosql_big_data`), a Y3S1 catalogue topic. After that activity was self-reported, revision 9 still named the completed practice, so the sequencer correctly refused to pin it. Completed activity ids are now removed from the action mask before the next call. Revision 10 pinned open Y3S1 practice `communication_stakeholders` (`/c1/practice/communication_stakeholders`), same protocol, seed, revision, and checkpoint hash. `student_plan_requested` was true. `serves_students` and `artifact_serves_students` stayed false. Strategy: `weakest_stored_mastery_v1+se-path-multi-v2_next`.

Completions that remained through refresh, replan, and reload:

- `af_rest_express` — `self_reported`
- `af_framework_selection` — `practice_verified`
- `nosql_big_data` — `self_reported` (not converted to a C1 practice result)

Calendar text stayed `weakest_stored_mastery_v1` / estimate minutes. Coding stayed masked.

## Controlled checks that did not change the live student

- AI unavailable: `pathService.test.js` points the service at `http://127.0.0.1:9`. Create stays `activated: false` and does not label the next activity `se-path-multi-v2`. Port 8004 was not left down.
- Both semester masks: `multiActionContract.test.js` keeps a Y3S2 topic ineligible under Y3S1, masks a completed Y3S1 practice, and keeps the Y3S2 coding block false. The student semester was not changed.

## Screenshots

- `c4-v2-plan-before-replan.png`
- `c4-v2-replan-next-activity.png`
- `c4-v2-selected-practice-launch.png`
- `c4-v2-self-report-distinct.png`
- `c4-v2-reload-persisted.png`
