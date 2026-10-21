# 10 PP2 experiment plan (unfinished conditions, in execution order)

COM-07 stays in force for PP1: no uncalibrated LLM numbers are shown. Everything below is plan only; nothing here has been run unless 09 says so.

## Order and dependencies
| Step | Work | Depends on | Output |
|---|---|---|---|
| 0 | Supervisor policy decision: synthetic-only vs benchmarks (DEC-06 vs proposal p.30); confirm "2–3 candidate models" in writing | supervisor | signed note |
| 1 | LLM readiness test (below) | credentials/quota or local Ollama | `preflight.json`, 1-call-per-provider smoke result |
| 2 | Multi-level rubric authoring for the 96 eligible questions (scoring levels) so Conditions B/E/F are meaningful; mark `rubric_status` human-reviewed | lecturer time (2–5 days) | `rubric_levels_v3.csv` |
| 3 | Human-marked reference scores: at least 2 markers on a stratified sample (≥150 answers), agreement (QWK) reported | markers, ethics approval for real student data | `human_marks.csv` |
| 4 | Conditions A and B (LLM no-RAG, rubric-prompted) on validation, then test once | 1, 2 | predictions + cache |
| 5 | Vector RAG marking (`rag_vs_norag.py --run-live`) | 1, retrieval ablations | A vs C table |
| 6 | Multi-LLM comparison | 1, 4 | per-model table |
| 7 | CCKG readiness test, then GraphRAG (Condition D) | CCKG built | D table |
| 8 | Proposal Condition F, then external datasets | 4–7, step 0 | F table; cross-dataset table |

## LLM conditions
Verify before any grading: provider class (`services/llm/*`) and `CachedLLMProvider`; keys read from `.env` only (never printed); preflight of exact model ids; request handling (timeout 90 s, retries with backoff, rate limiter); structured JSON validated against the rubric (`validate_output` / `parse_level_selection`); failures excluded and counted, never scored 0; deterministic settings (temperature 0); response cache + run metadata (model id, prompt hash, git commit, seed) for reproducibility. Calibration: fit any score mapping on the training split, check on validation, apply once to test. Budget guard: dry-run call counter before a live run (2 × 90 test answers per model + validation).

## Vector RAG ablations (after the first live run)
Corpus variants (reference answers only / + expected concepts), top-k 1/3/5, similarity threshold 0/0.2/0.3, embeddings (local MiniLM vs a second SBERT model), random-retrieval control, "oracle" same-topic control, retrieval removed. Metrics: marking nMAE/QWK vs no-RAG on identical answers, retrieval hit rate (needs human relevance labels), evidence-support correctness by lecturer sample, latency and tokens. Constraints: corpus from training questions only; own question excluded; no student answers or marks indexed.

## GraphRAG / CCKG readiness test (must pass before grading)
1. Neo4j reachable in strict mode (`C3_CCKG_STRICT=1`). 2. Schema loaded (`database/neo4j/scripts/load_cckg.sh`) with Course/Topic/Concept nodes and PREREQUISITE/RELATED edges. 3. Coverage: ≥ 80 % of eligible expected-concept strings resolve to a CCKG concept (today ≈ 5 of 541). 4. Every retrieved neighbour carries a source id; no fabricated nodes (hash of seed files recorded). 5. Spot-check 30 retrievals by a lecturer. Only then run Condition D against Condition C with identical prompts.

## Multi-LLM comparison protocol
Same inputs (question, reference, rubric, answer), same prompt template and JSON schema, temperature 0, same scoring scale (normalised mark), same train/validation/test split, models chosen before seeing results (e.g. one OpenAI, one Gemini, one open-weight via Ollama), failures counted per model. Selection on validation by the pre-registered rule (nMAE, ties → QWK); test once; bootstrap CIs by question; report cost and latency.

## Condition F (proposal) 
Required component scores per answer: E (with multi-level rubric), embedding similarity (SBERT), LLM rubric score. Fit fusion weights on training + validation predictions only (grid or NNLS), freeze, evaluate once on test. Compare with its best single component and with F-lite. Resolve the three conflicting definitions in docs first.

## Additional datasets
Prerequisites: supervisor policy (DEC-06 vs proposal p.30), licence check per dataset, score-scale mapping (EngSAF 0/1/2 → ordinal, ASAP-SAS 0–3, Mohler 0–5, ASAG2024 continuous), no mixing of incompatible scales without a documented normalisation, human-marked reference scores for any claim about agreement with markers, SLIIT data only with ethics approval. Keep source train/val/test splits; unseen-question split for generalisation.

## Integrity rules (unchanged)
Held-out test untouched for selection; ratio-concentration failure (0.766) and tier-label limits stated in every report; length-only diagnostic reported next to every learned model; multiple seeds for learned models; no mock output as evidence.
