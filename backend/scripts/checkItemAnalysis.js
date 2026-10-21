// Run from the backend folder:   node scripts/checkItemAnalysis.js
// Checks the item analysis maths on a tiny hand-made class where the right answers are known.
import assert from 'node:assert/strict';
import { analyse, MIN_ANSWERS } from '../src/modules/c1/services/itemAnalysis.js';

const ev = [];
// 40 students. Strong students (0..19) answer A, B, C1..C6 mostly right; weak students (20..39) mostly wrong.
for (let s = 0; s < 40; s++) {
  const strong = s < 20;
  const add = (q, c) => ev.push({ student_id: `S${s}`, question_id: q, correct: c, timestamp: new Date(1e12 + s) });
  add('GOOD', strong);                       // perfect discrimination: only strong students are right
  add('EASY', s !== 3);                      // almost everyone right
  add('KEYERR', !strong);                    // reversed: weak students right (a wrong answer key looks like this)
  for (let k = 0; k < 6; k++) add(`FILL${k}`, strong ? k !== 5 : k === 0);
}
ev.push({ student_id: 'S0', question_id: 'GOOD', correct: false, timestamp: new Date(2e12) }); // second attempt, must be ignored
ev.push({ student_id: 'S1', question_id: 'RARE', correct: true, timestamp: new Date(1e12), hint_used: true }); // hint, must be ignored
const rows = Object.fromEntries(analyse(ev, { GOOD: { difficulty: 'Medium' }, EASY: { difficulty: 'Hard' } }).map((r) => [r.question_id, r]));

assert.equal(rows.GOOD.n, 40, 'second attempt ignored');
assert.equal(rows.GOOD.p, 0.5);
assert.ok(rows.GOOD.discrimination > 0.6, 'GOOD separates strong from weak');
assert.ok(rows.KEYERR.discrimination < 0 && rows.KEYERR.flags.some((f) => f.includes('negative')), 'reversed item is flagged');
assert.equal(rows.EASY.p, 0.975);
assert.ok(rows.EASY.flags.includes('too easy') && rows.EASY.flags.some((f) => f.startsWith('expected Hard')), 'easy item flagged, prior mismatch noted');
assert.equal(rows.RARE, undefined, 'hint answers are left out');
assert.ok(40 >= MIN_ANSWERS);
console.log('Item analysis checks passed.');
