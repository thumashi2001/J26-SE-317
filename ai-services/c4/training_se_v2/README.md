# se-path-sim-v2 (Colab training package)

**Status: PAUSED — do not train or activate.**  
Files are preserved for a future authorized train only. Live serving continues on **se-path-sim-v1** with assumed `prior_strength=0.45`. Do **not** load v2 weights under the v1 observation schema (or vice versa).

## Why v2 exists

`se-path-sim-v1` observation slot `prior_strength` is a **simulator latent** with no authorized C1 field. Live serving v1 therefore fills it with an explicit protocol constant (`0.45`) and records `episode_init_mean_mastery` separately without injecting it into the v1 vector.

**v2 replaces that slot** with an observable freeze:

| Slot (index extras[3]) | v1 | v2 |
|---|---|---|
| Feature name | `prior_strength` | `episode_init_mean_mastery` |
| Training meaning | Latent used to init synthetic mastery | Mean mastery over available topics at episode start (frozen) |
| Live source | Protocol constant 0.45 | Same freeze already stored on `c4_learning_paths.live_model_episode.episode_init_mean_mastery` |

All other slots stay identical: mastery×46, available×46, mean, frac, `elapsed_env_step_frac` (one practice attempt per step).

**Protocol id:** `se-path-sim-v2`  
**Obs dim:** still 96  
**Catalogue:** same 46-topic hash as v1 (must match serving before import)

## Attempt / step contract (shared with live-serving)

- One env step = one practice attempt.
- Live: deduplicated `quiz_answer` events (`session_id`+`question_id`), exclude abandoned sessions, bound by episode `created_at`.
- **Never** count Mark done / self-reported completion as an attempt.
- Partial sessions: answered questions count; abandoned sessions do not.

## Colab execution order

1. Locally: `python scripts/package_se_v2_colab_zip.py` → writes `experiments/colab_zips/se_path_sim_v2_colab.zip`
2. Upload ZIP to Colab (or Drive).
3. Open `experiments/notebooks/v2/01_se_path_simulation_v2.ipynb`
4. Run cells in order:
   - Install deps
   - Unzip / `sys.path` bootstrap
   - Catalogue hash assert
   - Observation schema assert (`episode_init_mean_mastery` name)
   - Env smoke (random + baselines)
   - `RUN_FULL_TRAINING = False` until intentional
   - Full train → export under `MyDrive/AdaptiveLearnSE/c4_runs/se_path_sim_v2/`
5. Import artifacts into the repo with a **new** loader path (`se-path-sim-v2`); keep v1 untouched.

## What this package does **not** claim

- No executed full-train metrics until Colab completes.
- No replacement of live v1 inference until a matching artifact is imported and catalogue/schema checks pass.
- Synthetic data only unless authorized real learner traces are supplied separately (no student IDs in the ZIP).

## Local smoke

```bash
cd ai-services/c4
python -c "from training_se_v2.observation import observation_schema; print(observation_schema()['protocol'], observation_schema()['extras_names'])"
```

Expected: `se-path-sim-v2` and extras ending with `episode_init_mean_mastery`.
