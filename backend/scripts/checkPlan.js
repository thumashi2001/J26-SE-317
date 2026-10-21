// Quick check of the study plan rules, no database needed.
// Run from the backend folder:  node scripts/checkPlan.js
import assert from 'node:assert/strict';
import { buildPlan, decay, reviewAfterDays, tasksPerDay } from '../src/modules/c1/services/planService.js';

const now = new Date('2026-10-12T12:00:00');
const ago = (n) => new Date(now.getTime() - n * 86400000).toISOString();
const mastery = {
  a_weak: { score: 20, last_practiced: ago(12), practice_sessions: 1, correct: 2, answered: 8 },
  a_strong: { score: 85, last_practiced: ago(1), practice_sessions: 4, correct: 18, answered: 20 },
  b_never: { score: 30, last_practiced: ago(15), practice_sessions: 0, correct: 0, answered: 0 },
  c_open: { score: 40, last_practiced: ago(5), practice_sessions: 2, correct: 5, answered: 10 },
};
const moduleOf = (t) => ({ a: 'SE3020', b: 'SE3030', c: 'SE3040' }[t[0]]);
const moduleName = (c) => c;
// SE3020 exam in 14 days, SE3030 exam in 4 days, SE3040 has no date, one module's exam already passed
const examDates = { SE3020: '2026-10-26', SE3030: '2026-10-16' };
const plan = buildPlan({ mastery, events: [], examDates, now, moduleOf, moduleName });

assert.equal(plan.nextExam.module, 'SE3030', 'the nearest exam leads');
assert.equal(plan.daysLeft, 4);
const byCode = Object.fromEntries(plan.modules.map((m) => [m.code, m]));
assert.equal(byCode.SE3020.daysLeft, 14);
assert.equal(byCode.SE3040.daysLeft, null, 'a module without a date has no countdown');
assert.equal(plan.today.tasks[0].topic, 'b_never', 'the topic with the nearest exam and no practice comes first');
assert.ok(decay(100, 14, 0) < 100 && decay(100, 14, 4) > decay(100, 14, 0), 'more sessions means slower forgetting');
assert.ok(reviewAfterDays(3) > reviewAfterDays(0), 'review gaps grow with practice');
assert.equal(tasksPerDay(2), 5);
assert.ok(plan.predicted.withPlan > plan.predicted.ifYouStop, 'following the plan must beat doing nothing');

const day4 = plan.days.find((d) => d.offset === 4);
assert.deepEqual(day4.exams.map((e) => e.module), ['SE3030'], 'the calendar marks that module on its own date');
assert.ok(day4.items.every((i) => i.module !== 'SE3030'), 'no quiz for a module on its exam day');
assert.ok(plan.days.filter((d) => d.offset > 4).every((d) => d.items.every((i) => i.module !== 'SE3030')), 'topics leave the plan after their exam');
assert.equal(plan.days.find((d) => d.offset === 14).exams[0].module, 'SE3020');

// a module whose exam has passed disappears from the plan
const passed = buildPlan({ mastery, events: [], examDates: { SE3020: '2026-10-01', SE3030: '2026-10-16' }, now, moduleOf, moduleName });
assert.ok(passed.today.tasks.every((t) => t.module !== 'SE3020'));
assert.equal(passed.modules.find((m) => m.code === 'SE3020').passed, true);
console.log('Plan checks passed. Today:', plan.today.tasks.map((t) => `${t.topic} (${t.kind})`).join(', '));
