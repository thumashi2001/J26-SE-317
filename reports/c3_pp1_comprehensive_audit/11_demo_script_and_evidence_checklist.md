# 11 Demo script and evidence checklist

Only functions I verified are in the script. Reliability order (most to least): lecturer review > lecturer queue > student `arch-full` (needs Python warm on :8003, 15 s timeout) > batch MCQ > batch subjective > MCQ mind map (likely to crash — do not show).

## A. Before you start (10 min)
1. Docker: `docker compose up -d mongodb neo4j` (Neo4j only needed if you mention it).
2. Python: in `ai-services/c3` → `.venv_c3\Scripts\python.exe -m uvicorn app.main:app --port 8003`; check `http://127.0.0.1:8003/health` shows `"status":"running"`.
3. Backend (`backend/`, `.env` with `AUTH_SECRET` set): `npm run dev`. Frontend: `npm run dev` → :5173.
4. Log in as student and as lecturer (lecturers need admin approval unless seeded — test this at home, not in the room; never show `.env` or `seed_users.js`).
5. **Warm-up:** submit `arch-full` once so the first demo call is not slow.
6. Have fallbacks open: terminal with pytest output (324 passed), screenshots, `reports/c3_pp1_comprehensive_audit/12_rapid_revision_sheet.md`, dataset card.

## B. 4-minute demo (say limits first)
| Min | Do | Say | Expected (V) |
|---|---|---|---|
| 0:00 | Slide/architecture sentence | "React → Express → FastAPI pipeline; the lecturer decides." | — |
| 0:30 | Student page → preset `arch-full` → submit | "Concepts and the rubric levels decide the mark; no mark comes from a percentage formula." | **4/4**, level L4, evidence sentences, feedback, mind map |
| 1:30 | Preset `arch-partial` | "A half-correct answer earns a middle level." | **2/4** (L2), missing concepts listed |
| 2:00 | Preset `arch-zero` | "Nothing relevant → zero, with reasons." | **0/4** |
| 2:15 | Lecturer queue → open the submission → **Override** with a reason → **Finalize** | "Original AI mark is kept; override needs a reason; finalising sends an event to C1." | status pending_review → reviewed → finalized |
| 3:15 | State limits | "It matches words, not meaning: a paraphrase scores 0 and keyword stuffing can score full. That is why the next step is SBERT/RoBERTa/LLM comparison." | — |
| 3:45 | Close | "324 + 75 automated tests, dataset audit, protocol ready." | — |

Optional extra presets verified: `oop-higher` 3/3; `quality-multi` 2/4 (C1 = L2, C2 = L0).

## C. 10-minute extended path
1. Terminal: `.venv_c3\Scripts\python.exe -m pytest -q -p no:cacheprovider` → 324 passed, 13 xfailed (show one `AUDIT-` xfail to prove honesty).
2. Show `services/marking/criterion_evaluator.py:155-184` (level selection) and `services/semantic/analyzer.py` (token overlap) — 60 s each.
3. Show `reports/read_only_audit/03` headline: 576/355/71, ratio-concentration fail, baseline 1.939 vs E 3.544.
4. Batch marking MCQ with "Fill Sample Cohort" (deterministic, Node only) — open the table, **do not** open the per-student modal (mind-map crash risk).
5. Show the experiment protocol (08 §5) as "next phase".

## D. What not to show or claim
- MCQ student result screen with mind map; batch with real student data; `.env`; `seed_users.js`; mock-era result files (`exp1..5`, `master_research_summary.json`); the older evidence HTML pages (stale numbers).
- Never say: "validated dataset", "semantic understanding", "LLM results", "RAG improves", "model comparison done", "approved by the panel/supervisor" (no signed record), "100 % complete".

## E. If something fails
| Failure | Quick response |
|---|---|
| Python not started / 502 | "That is the designed failure mapping (502/504)." Start uvicorn, retry; else show test output + screenshots |
| 504 on first call | Warm-up skipped; retry once |
| Mongo down | Server will not start — use screenshots and terminal tests |
| Login blocked | Show tests (`npm test`: 75 pass) and recorded screenshots |
| Wrong mark | Explain the lexical limit; show xfail bug list; do not improvise a fix |

## F. PP1 evidence pack (lecture slide 19) — your checklist
- [ ] Working demo (above) · [ ] two key functions (answer processing + semantic analysis; rubric-aware marking + evidence) · [ ] architecture diagram (Day 24) · [ ] user/supervisor feedback — **only real, signed or dated items** · [ ] GitHub history (branch `feature/c3-pp1-experiments-20261020`) · [ ] MS Planner · [ ] RP diary/logbook · [ ] **AI-use record incl. code-level assistance** · [ ] test evidence (pytest/npm outputs) · [ ] risk register (RSK-01..07 + research risks from 08 §7).

## G. Five questions every student must answer (slide 21)
1. Which component? *C3, Automated Marking and Answer Analysis.* 2. Which two functions? *As above.* 3. Input/output? *Answer + rubric + expected concepts → mark, level evidence, concept status, feedback, map.* 4. Evidence of my own work? *Commits, tests, dataset repair, audits, ability to explain files.* 5. AI assistance and verification? *See 10 Q55.*
