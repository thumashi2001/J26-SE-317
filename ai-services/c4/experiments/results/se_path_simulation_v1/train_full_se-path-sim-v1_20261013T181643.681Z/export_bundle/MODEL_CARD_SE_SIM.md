# Model card — SE path simulation (se-path-sim-v0)

**Simulation only.** Not measured SE student behaviour. No readiness/pass-probability claims.

- Protocol: `se-path-sim-v0`
- Selected (validation): `maskable_ppo`
- Actions: 12 C1 practice topics (see topic_catalogue.json)
- Observation dim: 28 (mastery×12 + availability×12 + 4)
- Forgetting: **none** (explicit v0 default)
- Max episode steps: 40

Do not integrate automatically into production. Heuristic Node path remains separate.

