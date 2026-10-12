# Component 1: study plan, exam date and calendar

New endpoints (student token required):
- `GET /api/v1/c1/plan/:studentId` returns today's tasks, the day by day calendar, the next review dates and the predicted exam level.
- `PUT /api/v1/c1/exam-date` with `{ "studentId": "...", "examDate": "2026-11-20" }` saves the exam date. Send `null` to clear it.

New collection: `student_plans` (`student_id`, `exam_date`, `updated_at`). Created on first save.

## How the plan is built (`planService.js`)
1. **Forgetting curve.** score after d days = stored score x (0.35 + 0.65 x e^(-d / stability)), stability = 14 days x (1 + 0.6 x sessions).
2. **Review due date.** The day a topic has kept 80% of its last score (about 0.37 x stability after the last practice).
3. **Priority.** Gap to the 70% target on exam day, points lost to forgetting, overdue bonus, never-practised bonus, and a behaviour adjustment (guessing or needs-revision up, strong and quick down).
4. **Behaviour.** Per topic reads from `behaviourService` (guessing, needs revision, knows it but slow, strong). A student whose recent pattern is Rushing or Guessing is told to slow down on every task.
5. **Exam date.** Tasks per day grow as the exam gets closer (2, 3, 4, then 5 in the last 2 days). The last 2 days are final revision. Without an exam date the plan covers the next 14 days.
6. **Calendar simulation.** Each planned quiz is assumed to keep the topic's accuracy (at least 60%), moves the score by the same expected value rule as the forecast, and lengthens the next review gap.
7. **Predicted exam level.** Average topic score on exam day with the plan, and with no more practice.

Check the rules without a database: `node backend/scripts/checkPlan.js` (from the backend folder).

## Interface changes in this drop
- Light sidebar, 272px wide, student card under the logo with a larger gap.
- Full width content, shared light blue and ash palette (`index.css` tokens).
- Dashboard: KPI tiles, Today's plan, exam calendar with exam date field, simplified coloured topic cards.
- Topic page: hero with score ring, five fact tiles, score history and "What if I study?" side by side.
- Fixed: the amber, red, green and grey colour tokens in `index.css` referred to themselves in light mode and now have real values.
