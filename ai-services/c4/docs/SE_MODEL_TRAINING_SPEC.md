# SE model training specification (evidence-based)

Status: **compatibility decision recorded 2026-10-13** (pre-training gate).  
Student `/c4` remains the **heuristic** PathPage. ASSISTments and all SE `*-v0`
artefacts stay intact. **No catalogue size (22 vs 46) is approved merely by
appearing in an earlier draft of this file.**

---

## A. Compatibility decision (executive)

| Question | Decision |
|---|---|
| Can frozen SE v0 policies/features be **verified-adapted** onto live C1 topic IDs? | **No** — 0 exact ID overlaps; no lecture-content–verified 1:1 map; several v0 topics have no discrete successor |
| Must every model be retrained because strings changed? | **No** — see §E per model. ASSISTments and heuristic need no SE-catalogue retrain; v0 SE models remain valid **only** on the frozen v0 synthetic contract |
| May training start now? | **No** — catalogue **scope still unresolved** (§D). Do not start Colab full runs until Suwani/team signs scope |
| Student Adaptive path | Keep heuristic; do **not** wire SE RL/supervised until a signed v1 catalogue + eval |

---

## B. Proposal PDF access

| Attempt | Result |
|---|---|
| Workspace / Softedge / agent stores / C4 backup zip | **No** `.pdf` matching Muthumali / AdaptiveLearnSE / J26 C4 proposal |
| `Downloads\Proposal.pdf`, mini-project proposals, `softprodetailseng.pdf` | Opened and text-extracted; **not** the C4 SoftEdge proposal (wrong titles / no Muthumali·C4 markers) |

**Limitation:** The actual Muthumali C4 proposal PDF was **not accessible** in this
environment. **No proposal verification** is claimed. Mapping below uses
**repository code + user-stated themes + confirmed Y3S1/Y3S2 lecture-batch intent**
only. When the PDF is placed on disk, reconcile §D/§F against it before training.

User-stated themes (not PDF-verified): RL adaptive paths; daily study activities;
dynamic exam simulation using C2 content; readiness / pass-probability when labels
exist; progress/feedback.

---

## C. Source pins and live C1 contract (read-only)

Audited at HEAD `11c4920a8f5e5ddbd9031a2deb76e07a2b47863e`
(`feature/c4-adaptive-learning`).

| File | Role | Git blob SHA-1 |
|---|---|---|
| `backend/src/modules/c1/data/practiceQuestions.js` | Practice bank export | `047185d3840a74ea113c886e6ffbc82f4c82064e` |
| `backend/src/modules/c1/data/content/index.js` | Module registry → topics | `a7c3014434a815aeee32e650b04a6f1db476a063` |
| `frontend/src/utils/topicLabels.js` | Labels / module / lectures / semester | `db3bc9e29065b802b36791c659ae6a0c05134738` |
| `ai-services/c4/training_se/catalogue.py` | Frozen SE v0 12-topic order | `997e87634a7239006baa507fffc80642d30e5233` |
| `ai-services/c2/config/exam_structures.json` | C2 exam structure config | `0284bcf0d780001a6f86b74107f9e972cec650f1` |
| `ai-services/c2/config/modules.json` | C2 module registry (often incomplete) | `b6f43de902ebf691cc0d28d7cb020a89843f421e` |

**Live practice facts**

- **46** `PRACTICE_QUESTIONS` keys; each content bank has **10** items.
- Semesters: **Y3S1 = 28** topics (SE3070, SE3080, SE3050, SE3060, SE3040);
  **Y3S2 = 18** (SE3020, SE3030, SEPQM).
- Exact ID overlap with frozen v0 catalogue: **0**.
- Practice start (`practiceService.startSession`): diagnostic completed **and**
  topic key present on twin mastery **and** practice questions exist.
- Eligibility today: `students.semester` drives diagnostic pool;
  `enrolled_modules` exists but registers as **`[]`** — do not treat as populated.
- **Missing mastery ≠ observed zero:** live ranking must omit / mark unavailable;
  v0 obs schema notes `available=0` with `mastery=0` as *unavailable encoding* —
  product builders must keep an availability channel and must not present missing
  as known-zero competence.

**Lecture batch:** User confirmed supplied Y3S1/Y3S2 lecture ZIPs are the intended
batch. Match materials by **module code + content**, not ZIP folder semester
labels alone. (ZIP files were not re-ingested in this task.)

---

## D. Training catalogue scope (not auto-chosen)

### D.1 What is **not** approved

- Choosing **22** topics solely because a prior draft of this doc listed them.
- Choosing **all 46** solely because they exist in C1.

### D.2 Evidence that bounds a future choice

| Evidence | Implication |
|---|---|
| Heuristic PathPage sequences any live practiseable topic on the twin | Product path already spans the **full practiseable registry** |
| Intended lecture batch covers **both** Y3S1 and Y3S2 | Excluding SE3020/SE3030/SEPQM/SE3040 needs an explicit product reason, not “v0 didn’t have them” |
| Frozen v0 covered only SE3050/3060/3070/3080 (old IDs) | Continuity argument for a **legacy-module pack** is optional engineering staging, **not** ratified scope |
| Proposal PDF unread | Cannot confirm which modules/activities C4 must train |

### D.3 Proposed design pending sign-off (recommendation)

**Proposed (unsigned) catalogue design for the next protocol:**

1. **Registry** = all **46** current practiseable IDs (ordered as
   `content/index.js` `MODULES` insertion: csse → spm → uee → ds → dsys → sa →
   sepqm → af). Reference hash of
   `{"catalogue_id":"c1-practice-full-2026.10","topics":[…46…],"topic_modules":{…}}`
   (sort_keys, compact): `e853414d711e0375a795ac6a728c256d910256e9ab5d1b514db46ea9470bf0aa`.
2. **Episode action mask** = registry ∩ practiseable ∩ twin-eligible ∩
   **semester-eligible** (and module enrolment **if/when** `enrolled_modules`
   is populated). Missing mastery → unavailable, not zero.
3. **Do not train** until Suwani confirms one of:
   - **S1:** Registry=46 with semester masking (recommended default to discuss),
   - **S2:** Explicit module pack (list modules), or
   - **S3:** Other proposal-driven subset.

A **22-topic legacy-module pack** remains an optional *smoke staging* idea only
(hash previously computed `b14db0cb…` for documentation) — **not** the signed
scope.

---

## E. Definitive compatibility table (frozen v0 → current C1)

**Legend — equivalence status**

| Status | Meaning |
|---|---|
| `exact_id` | Same string in live `PRACTICE_QUESTIONS` |
| `verified_equivalent` | Same ID **or** lecture-content / proposal evidence establishing 1:1 succession |
| `unverified_label_candidate` | Same module + overlapping human title words only — **insufficient** to remap actions |
| `restructured_no_1to1` | Module rebuilt; no single successor ID |
| `removed_as_discrete` | No current discrete practice key covering that v0 label |

**None of the 12 rows are `exact_id` or `verified_equivalent`.**  
Candidates must **not** be used as silent remaps.

Required learner data (all rows that could be practised live):  
`diagnostic_completed=true`; twin `mastery[topic]` entry present; finite ranking
score preferred from insights `estimatedNow` else `storedScore` else twin
`score` — if none finite → **unavailable** (unknown), not 0.

| Old C4 (v0) topic | Current C1 topic(s) | Module (v0 → live) | Equivalence evidence | Status | Supported practice route | Eligible semester (live metadata) |
|---|---|---|---|---|---|---|
| `usability_heuristics` | *candidate* `ux_testing_heuristics` (also related UX bank: `ux_foundations_process`, …) | SE3050 → SE3050 | Label overlap (“heuristics” / UX testing); **no** lecture-slide diff or proposal map | `unverified_label_candidate` | `/c1/practice/ux_testing_heuristics` if twin has that key | Y3S1 |
| `user_research_methods` | *candidate* `user_research_synthesis` | SE3050 → SE3050 | Title overlap only | `unverified_label_candidate` | `/c1/practice/user_research_synthesis` | Y3S1 |
| `prototyping` | *candidates* `structuring_prototyping`, `visual_design_accessibility` | SE3050 → SE3050 | Split/narrowing possible; no 1:1 proof | `unverified_label_candidate` / likely split | `/c1/practice/<candidate>` | Y3S1 |
| `normalization` | *no discrete successor*; bank has `object_relational_db`, … | SE3060 → SE3060 | ORDB/PLSQL ≠ proven “normalization” topic | `restructured_no_1to1` | none for old ID | Y3S1 (live DB topics) |
| `indexing` | *candidate* `file_organization_indexing` | SE3060 → SE3060 | Title contains “Indexing”; no content verification | `unverified_label_candidate` | `/c1/practice/file_organization_indexing` | Y3S1 |
| `query_optimization` | *candidate* `query_processing_tuning` | SE3060 → SE3060 | Title overlap only | `unverified_label_candidate` | `/c1/practice/query_processing_tuning` | Y3S1 |
| `case_analysis_techniques` | SE3070 now: `interaction_functional_design`, `code_quality_solid`, `refactoring_best_practices`, `unit_integration_testing`, `debugging_profiling_config` | SE3070 → SE3070 | Module topic list replaced | `restructured_no_1to1` | none for old ID | Y3S1 |
| `industry_case_studies` | — | SE3070 → SE3070 | No matching practice key | `removed_as_discrete` | none | — |
| `lessons_learned` | — | SE3070 → SE3070 | No matching practice key | `removed_as_discrete` | none | — |
| `risk_management` | *candidate* `project_risk_management` | SE3080 → SE3080 | Title overlap only | `unverified_label_candidate` | `/c1/practice/project_risk_management` | Y3S1 |
| `estimation` | *partial lexical link* `schedule_cost_management` (EVM) | SE3080 → SE3080 | Scope likely broader/different | `restructured_no_1to1` | none trusted for old ID | Y3S1 |
| `agile_planning` | — | SE3080 → SE3080 | No matching practice key | `removed_as_discrete` | none | — |

**Current topics with no v0 counterpart:** all Y3S2 banks (SE3020/SE3030/SEPQM) and
SE3040 AF, plus expanded SE3050–SE3080 keys not listed as candidates above —
**new** relative to v0 (not “renames”).

---

## F. Model-by-model: adapter vs new version

| ID | Artefact | Verified adapter to live C1? | Retrain / new version? | Concrete reason |
|---|---|---|---|---|
| **M1** | ASSISTments response | N/A (math skills) | **No** | Different domain; catalogue change irrelevant |
| **M2** | ASSISTments RL | N/A | **No** | Same |
| **M3** | ASSISTments research serve | N/A | **No** | Keep `/v1/research/*` |
| **M4** | Heuristic `weakest_stored_mastery_v1` | **Already live** | **No** | Reads current `PRACTICE_QUESTIONS` via `supportedTopics.js`; not a frozen 12-ID policy |
| **M5** | SE MaskablePPO `se-path-sim-v0` | **No** for live C1 | **New version only if** targeting current catalogue / live features | Action indices and obs slots are bound to the 12 retired IDs (`observation_schema.json` order). Unverified rename would change action semantics. **Preserve v0** for synthetic-v0 replay/demo without adapter |
| **M6** | SE next-attempt model v0 | **No** for live C1 features | **New version if** training/serving on current topic one-hots / attempt columns | `feature_schema_response.json` columns `topic_oh_<v0_id>`; swapping names without verified equivalence corrupts features. Keep v0 for v0-synthetic eval only |
| **M8** | Mock exam score/pass v0 | **No** for live C1 aggregates | **New version if** using current topic attempt/accuracy features | Same ID-bound feature schema; pass-score cutoff ≠ probability threshold (keep distinction) |
| **M7** | Dynamic exam assembly | N/A (not built) | Not a retrain of v0 | See §G — C2 interface status |

**Summary:** Topic-string drift alone does not force ASSISTments or M4 retrain.
It **does** block a *verified* adapter from v0 SE nets → live C1. Any live- or
current-catalogue-facing SE learner requires a **new protocol version** after
scope sign-off — not an overwrite of v0.

---

## G. Remaining proposal features (separate from catalogue mismatch)

| Feature theme | Catalogue blocker? | Repo evidence | Ownership / next dependency |
|---|---|---|---|
| Daily planning / study path | Partially (IDs) | Heuristic path + C1 practice links work on live IDs | C4 Node/UI; trained policy blocked on §D |
| Activity choices beyond `c1_practice` | Not mainly catalogue | Only practice deep-links exist | Product + content; no lab/lecture-revision actions in code |
| Progress / feedback | No | Self-reported path progress; C1 practice answers write twin | Keep assessed vs self-reported distinct |
| Mock exams / exam simulation | **Not solely catalogue** | C2 has module registry, exam structure validator, coverage tracker, synthetic rules; most structures `unverified` / `null`; `modules.json` topics `[]`; DB sample paper only (`M4_DATASET_PREPARATION.md`) | **C2 owns paper/structure/question datasets.** C4 may *consume* a future C2 API for item selection / mock delivery — **do not declare “exam assembly impossible”**; declare **C2 not ready / contract undefined for C4**. C4 readiness models still need outcome labels |
| Readiness / pass probability | Labels > catalogue | Synthetic M8 only; no real exam scores in workspace | C4 supervised **after** labels + signed feature catalogue; C1 forecast ≠ exam label |

---

## H. Implementation handoff

### H.1 Catalogue — **S1 selected**

- **Signed implementation scope:** full **46** registry + **semester masks** (§D.3 S1).
- Frozen file: `catalogues/c1_practice_full_2026_10.py` (`catalogue_id=c1-practice-full-2026.10`).
- Not a claim that the proposal PDF was verified.
- **22-topic pack:** not used.

### H.2 Retraining decisions

| Model | Action now |
|---|---|
| M1–M3 | Preserve; no work |
| M4 | Preserve heuristic as student flow (no model wiring yet) |
| M5–M6–M8 v0 | Preserve artefacts; no overwrite; no live adapter |
| M5–M6–M8 v1 | Additive `training_se_v1` / `training_se_supervised_v1` + notebooks 07/08 |
| M7 | Specify C2→C4 item API when C2 structures verified — outside this edit set |

### H.3 Delivered C4 v1 packages

Under `ai-services/c4/`:

- `catalogues/c1_practice_full_2026_10.py`
- `training_se_v1/` → protocol `se-path-sim-v1`
- `training_se_supervised_v1/` → protocol `se-supervised-sim-v1`
- `docs/SE_PATH_SIM_V1.md`, `docs/SE_SUPERVISED_SIM_V1.md`
- `experiments/07_se_path_simulation_v1.ipynb`, `08_se_supervised_simulation_v1.ipynb`
- ZIPs: `c4-se-v1-source-colab.zip`, `c4-se-supervised-v1-source-colab.zip`

Under `backend/src/modules/c4/` / `frontend/src/pages/c4/`: **no model wiring**;
heuristic student flow unchanged.

### H.4 Colab runs

- Local: catalogue / mask / leakage / fixture smoke only (gates False).
- Colab: v1 smoke → (optional) full train → freeze selection → final test.
- Never write into v0 result folders (`se_path_sim_v0`, `se_supervised_sim_v0`).

### H.5 Browser checks (heuristic — when local services up)

1. Student login → sidebar **Adaptive path** → `/c4` renders PathPage (not ComingSoon).
2. Without diagnostic → 409 messaging + link to `/c1/diagnostic`.
3. After diagnostic with twin topics → Create path → activities use **current**
   topic labels; Open practice → `/c1/practice/<live_id>`.
4. Mark done → self-reported only; replan keeps completed.
5. Confirm no call to SE RL / supervised inference from PathPage (`c4Api.js`
   path APIs only).

*(Not executed in this task: no local frontend/backend services assumed.)*

---

## I. Explicit non-claims

- Proposal PDF contents were not verified.
- Unverified label candidates ≠ approved remaps.
- Prior “22-topic” draft ≠ approved scope.
- ASSISTments success ≠ SE classroom efficacy.
- C2 partial tooling ≠ finished exam assembly for C4.
- Synthetic v0 metrics ≠ validation on current C1 IDs.
