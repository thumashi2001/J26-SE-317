# Model card — SE path simulation (se-path-sim-v0)

**Simulation only.** Not measured SE student behaviour. No readiness/pass-probability claims.

- Protocol: `se-path-sim-v0`
- Selected (validation): `maskable_ppo`
- Actions: 12 C1 practice topics (see topic_catalogue.json)
- Observation dim: 28 (mastery×12 + availability×12 + 4)
- Forgetting: **none** (explicit v0 default)
- Max episode steps: 30

Do not integrate automatically into production. Heuristic Node path remains separate.

## Validation return (mean ± sample SD across seeds)
- `maskable_ppo`: 7.7707 ± 0.2510
- `random_valid`: 6.7160 ± 0.1749
- `recent_performance`: 6.4920 ± 0.1220
- `weakest_stored_mastery_v1_sim`: 6.1560 ± 0.2963

