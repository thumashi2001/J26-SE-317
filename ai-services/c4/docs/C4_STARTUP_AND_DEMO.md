# C4 startup and two-minute demo

## Startup (reuse if already healthy)

```powershell
# C4 Python (8004)
cd J26-SE-317\ai-services\c4
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 127.0.0.1 --port 8004

# C1 Python (8001) — needed for twin insights / practice scoring
cd ..\c1
# clear PYTHONPATH so C4 app is not imported by mistake
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
uvicorn app.main:app --host 127.0.0.1 --port 8001

# Node + frontend
cd ..\..\backend
npm run dev
cd ..\frontend
npm run dev
```

Expect: Mongo connected on Node; `http://localhost:5173/`; C1/C4 `/health` ok.

## Action only the operator can do

**Log in in the Cursor IDE browser panel** at http://localhost:5173/login  
(That panel does not share Chrome/Edge cookies.)

## Two-minute demo — two core workflows + C1

### Workflow A — Plan & progress (~60s)
1. Sidebar **Adaptive path** → `/c4` → Study plan.
2. Set start/exam dates, daily minutes, study days → Create (or show existing).
3. Show Today cards. Practice opens `/c1/practice/:topic`, revision opens `/c1/topic/:topic`, and quiz opens `/c4?tab=exams&focusTopic=`. The quiz settings name that topic. Coding is explicitly not scheduled (C3 has no launch API).
4. Note engagement (completion, streak, Colombo days) and exam-urgency text when an exam date is within 14 days.
4. **Next activity** card: se-path-multi-v2 practice, revision, or quiz when the checkpoint is active. The chip names that protocol. If it is unavailable, the page says the heuristic is not an RL action. Calendar dates stay heuristic.
5. Expand provenance: experimental; assumed `prior_strength=0.45`; step_frac is a serving approximation (mismatch not eliminated).
6. **Start next practice** → C1 practice → Refresh / Replan → completed kept.

### Workflow B — Mock assessment (~60s)
1. Mock quizzes → Start practice-bank quiz (not C2).
2. Expand **Pre-exam estimate (heuristic)**: not a trained model; cold-start/partial **50% defaults** labelled; product target 60%.
3. Optional expand: experimental simulation-trained readiness (different target).
4. Answer / Save → reload → resume → Submit → observed % vs frozen heuristic.
5. Feedback tab → reload list.
6. Optional: Simulation demo — synthetic only.

### Say out loud
- Calendar packing = heuristic. Next activity = se-path-multi-v2 when the card says so.
- This-quiz estimate = heuristic formula, not ML. Pass probability = insufficient evidence. Sim readiness is a different target.
- C2 / live response / lecturer roster unmet externally.

## Backup recording checklist

- [ ] Login (no credentials on screen)
- [ ] Plan + next practice pin
- [ ] C1 practice deep-link
- [ ] Refresh observed vs verified
- [ ] Mock quiz this-quiz estimate + observed score
- [ ] Feedback entry
- [ ] Simulation disclaimer  
Video: **pending** until operator records.

## Genuine feedback

Students use **Feedback** tab. Stored in C4 `c4_feedback` only — no invented testimonials.

## Missing or invalid input

- No diagnostic: path create returns `diagnostic_required` and the page links to `/c1/diagnostic`, with Retry.
- Stale replan: send `expectedRevision`. A mismatch returns 409 `concurrent_modification` and does not bump the revision.
- Ineligible `focusTopic`: exam create returns 400 `topics_not_eligible`.
- C2 source or C3 coding: unavailable responses, not a successful substitute.
- AI down: the plan stays on the heuristic and is not labelled `se-path-multi-v2`.

## Isolated regression

```powershell
cd backend
node --test src/modules/c4/tests/examService.test.js src/modules/c4/tests/pathService.test.js
cd ..\ai-services\c4
python -m pytest tests/test_practice_quiz_pass_v1.py -q
```
