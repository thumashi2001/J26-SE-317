// Checks how a quiz is built for a student's level, no database needed.
// Run from the backend folder:  node scripts/checkAdaptiveQuestions.js
import assert from 'node:assert/strict';
import { PRACTICE_QUESTIONS } from '../src/modules/c1/data/practiceQuestions.js';
import { difficultyOf } from '../src/modules/c1/data/questionMeta.js';
import { baseLevel, nextLevel, mixFor, pickQuestions } from '../src/modules/c1/services/questionBuilder.js';

assert.equal(baseLevel(20), 'Easy');
assert.equal(baseLevel(55), 'Medium');
assert.equal(baseLevel(80), 'Hard');
assert.equal(nextLevel(20, 0.9), 'Medium', '80% or more right on the last quiz moves up one step');
assert.equal(nextLevel(55, 0.3), 'Easy', '40% or less right moves down one step');
assert.equal(nextLevel(20, 0.1), 'Easy', 'cannot go below Easy');
assert.equal(nextLevel(90, 0.9), 'Hard', 'cannot go above Hard');
for (const l of ['Easy', 'Medium', 'Hard']) assert.equal(Object.values(mixFor(l)).reduce((a, b) => a + b, 0), 7);

let slots = 0;
const seen = { Easy: 0, Medium: 0, Hard: 0 };
for (const [topic, list] of Object.entries(PRACTICE_QUESTIONS)) {
  const items = list.map((q, i) => ({ id: `${topic}-${i}`, q, lastSeen: 0 }));
  for (const level of ['Easy', 'Medium', 'Hard']) {
    const picked = pickQuestions(items, mixFor(level, 7));
    assert.equal(picked.length, Math.min(7, list.length), `${topic} ${level}: 7 questions`);
    assert.equal(new Set(picked.map((p) => p.id)).size, picked.length, 'no repeats');
    const hardShare = picked.filter((p) => difficultyOf(p.q) === 'Hard').length / picked.length;
    seen[level] += hardShare;
    slots += 1;
  }
}
const per = (x) => (x / (slots / 3)).toFixed(2);
console.log(`average share of Hard questions in a quiz: Easy level ${per(seen.Easy)}, Medium level ${per(seen.Medium)}, Hard level ${per(seen.Hard)}`);
assert.ok(seen.Easy < seen.Medium && seen.Medium < seen.Hard, 'a higher level gets harder questions');
console.log('adaptive question checks passed');
