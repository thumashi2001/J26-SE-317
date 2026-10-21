# 05 Test, lint and integration report (commands audited before running; none wrote to tracked/protected files)

Raw outputs were captured to the session scratchpad (`audit/pytest_default_raw.txt`, `pytest_neo4j_raw.txt`, `node_test_raw.txt`, `eslint_raw.txt`, `ruff_configured_raw.txt`). Command audit: pytest tests write only to pytest temp dirs (`tmp_path_factory`); `tests/conftest.py` blocks all real HTTP and strips API keys; the default `-m 'not live_llm and not neo4j'` deselects paid/DB tests; `-p no:cacheprovider` used; ruff run with `--no-cache` and without `--fix`. **Not run (side effects/cost): `pytest --cov` (writes `.coverage`), `-m live_llm` (paid APIs), `datasets/repair_c3_dataset.py`, `python -m datasets.repair.evaluate_repaired` (write into the dataset dir), any install.** After all runs `git status` and the ignored-file list were identical to the start (V).

| Suite | Command | Result | Label |
|---|---|---|---|
| Python unit/integration (offline) | `python -m pytest -p no:cacheprovider -ra` (ai-services/c3) | **324 passed, 13 xfailed, 9 deselected, 0 failed, 0 skipped**, 2 warnings, 15 s; 337 collected (324 + 13). Matches the claimed 324. | V |
| Xfails | strict `xfail` tagged AUDIT-A1, M1, M4, M5, MM1–MM3, N1, S1 | 13 known product bugs encoded as expected failures (not "passes") | V |
| Deselected | markers `live_llm` (4), `neo4j` (5) | not part of the 324 | V |
| Live Neo4j | `python -m pytest -m neo4j` (container already up; read-only `MATCH` queries) | 5 passed – the adapter is genuinely live and the seeded graph has no blank nodes | V |
| Live LLM | `-m live_llm` | **NOT RUN** (external, paid) | B |
| Ruff, project configuration | `python -m ruff check . --no-cache` | **111 findings, exit 1** (101 E501 line-too-long, 8 E402, 2 W293). The narrower rule selection (`--select E,F,I,B,UP --ignore E501,E402,B905`) used in my commits passes ("All checks passed"); that subset is not the configured set. | V |
| Backend unit | `npm test` (backend) | 90 tests: **75 pass, 15 todo, 0 fail** (todo = known bugs AUDIT-B1…B9, X1). Uses an in-memory fake DB and a mock AI HTTP server; one test probes `127.0.0.1:8003` if something listens. | V |
| ESLint | `npm run lint` | **13 errors**, 0 warnings (unused variables in C3 services, an irregular-whitespace error, `no-useless-assignment`) | V |
| Coverage (reported earlier) | not run | Python 88 %, Node line 76 % are REPORTED, not reproduced | R |
| Frontend build / e2e / Mongo-backed integration | – | not run; no frontend or e2e tests exist | B |

## What the green results do and do not establish
- They show the repair pipeline is deterministic, the accounting identity holds on the real archive, the validator catches injected defects, and the offline evaluation runs. They do **not** show end-to-end operation (Express → FastAPI → Mongo → lecturer review), live LLM behaviour, or that any marking engine is accurate.
- `test_validator_report_on_real_output_is_honest` and `…manifest_qa_is_real` assert that the repaired dataset FAILS the ratio check; the suite is green *because* it encodes the known failure.

## Coverage of required topics (INFERRED from test names)
Reconciliation/provenance ✔ (`test_accounting_invariant_on_real_archive`, hash tests) · eligibility & six-variant rule ✔ (validator per-question coverage) · quarantine isolation/fidelity ✔ · label & mark consistency ✔ (score range, criterion sums, IRRELEVANT=0) · cross-split leakage ✔ (injected split/question leakage) · rubric referential integrity ✔ (missing rubric injected; id map never invents) · failed-prediction handling ◐ (only that `not_evaluable` is empty; no test that a failed marking call is excluded not zeroed) · metric reproducibility ◐ (`evaluate_repaired` test asserts counts/seed, not metric values or the 4.640 reproduction) · API contracts ◐ (FastAPI route tests; Express↔FastAPI only against a mock or a locally running service) · regression after generator removal ✔ (suite green, grep shows no live import of removed modules; stale references remain in `.env.example:18`, `datasets/loader.py:22`).
