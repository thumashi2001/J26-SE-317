// Quick check of the study plan rules, no database needed.
// Run from the backend folder:  node scripts/checkPlan.js
import assert from 'node:assert/strict';
import { buildPlan, decay, reviewAfterDays, tasksPerDay } from '../src/modules/c1/services/planService.js';

const now = new Date('2026-10-12T12:00:00');
const ago = (n) => new Date(now.getTime() - n * 86400000).toISOString();
const mastery = {
  weak_fading: { score: 20, last_practiced: ago(12), practice_sessions: 1, correct: 2, answered: 8 },
  strong_fresh: { score: 85, last_practiced: ago(1), practice_sessions: 4, correct: 18, answered: 20 },
  never: { score: 30, last_practiced: ago(15), practice_sessions: 0, correct: 0, answered: 0 },
};
const plan = buildPlan({ mastery, events: [], examDate: '2026-10-26', now });

assert.equal(plan.daysLeft, 14);
assert.equal(plan.today.tasks[0].topic !== 'strong_fresh', true, 'a fresh strong topic must not come first');
assert.ok(decay(100, 14, 0) < 100 && decay(100, 14, 4) > decay(100, 14, 0), 'more sessions means slower forgetting');
assert.ok(reviewAfterDays(3) > reviewAfterDays(0), 'review gaps grow with practice');
assert.equal(tasksPerDay(2), 5);
assert.ok(plan.predicted.withPlan > plan.predicted.ifYouStop, 'following the plan must beat doing nothing');
assert.equal(plan.days.at(-1).isExam, true);
assert.equal(plan.days.at(-1).items.length, 0, 'no quiz on exam day');
assert.equal(buildPlan({ mastery, events: [], examDate: null, now }).daysLeft, null);
console.log('Plan checks passed. Today:', plan.today.tasks.map((t) => `${t.topic} (${t.kind})`).join(', '));
