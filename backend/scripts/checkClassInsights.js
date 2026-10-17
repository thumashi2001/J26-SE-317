// Run: node scripts/checkClassInsights.js
import assert from 'node:assert';
import { buildClass } from '../src/modules/c1/services/classInsightsService.js';

const now = new Date('2026-10-13T10:00:00Z');
const ago = (d) => new Date(now.getTime() - d * 86400000);
const m = (score, sessions = 1, days = 0) => ({ score, practice_sessions: sessions, last_practiced: ago(days) });
const students = [
  { student_id: 'A', name: 'Ann', semester: 'Y3S1' },
  { student_id: 'B', name: 'Ben', semester: 'Y3S2' },
  { student_id: 'C', name: 'Cat', semester: 'Y3S1' },
  { student_id: 'D', name: 'Dan', semester: 'Y3S1' },
];
const states = [
  { student_id: 'A', diagnostic_completed: true, risk_level: 'Medium', mastery: { t1: m(45), t2: m(50) } },
  { student_id: 'B', diagnostic_completed: true, risk_level: 'High', mastery: { t1: m(20), t2: m(30) } },
  { student_id: 'C', diagnostic_completed: true, risk_level: 'Low', mastery: { t1: m(90, 3), t2: m(80, 3) } },
  { student_id: 'D', diagnostic_completed: false, risk_level: null, mastery: {} },
];
const events = [{ student_id: 'B', timestamp: ago(2) }, { student_id: 'B', timestamp: ago(5) }, { student_id: 'A', timestamp: ago(30) }];

const c = buildClass({ students, states, events, now });
assert.strictEqual(c.students, 4);
assert.strictEqual(c.diagnosticDone, 3);
assert.strictEqual(c.activeThisWeek, 1);
assert.deepStrictEqual(c.risk, { Low: 1, Medium: 1, High: 1 });
assert.strictEqual(c.notRated, 0);
assert.deepStrictEqual(c.needAttention.map((p) => p.name), ['Ben', 'Ann']); // High first, Low and not tested left out
assert.strictEqual(c.needAttention[0].lastActive, ago(2).toISOString()); // latest answer
assert.strictEqual(c.needAttention[0].weakest, 't1');
assert.strictEqual(c.needAttention[1].lastActive, ago(30).toISOString());
assert.ok(!JSON.stringify(c).includes('student_id') && !JSON.stringify(c).includes('"A"'), 'no student IDs in the class view');

const none = buildClass({ students: [], states: [], events: [], now });
assert.strictEqual(none.averageLevel, null);
assert.deepStrictEqual(none.needAttention, []);

// finished the diagnostic but no risk rating yet
const unrated = buildClass({ students, states: [...states, { student_id: 'D', diagnostic_completed: true, risk_level: null, mastery: { t1: m(50) } }].filter((x, i, a) => a.findIndex((y) => y.student_id === x.student_id) === i || x.diagnostic_completed), events, now });
assert.strictEqual(unrated.notRated, 1);

// a student with no practice shows no last-active date
const quiet = buildClass({ students, states, events: [], now });
assert.strictEqual(quiet.needAttention[0].lastActive, null);

// at most 8 students are listed
const many = Array.from({ length: 20 }, (_, i) => ({ student_id: `S${i}`, name: `N${i}`, semester: 'Y3S1' }));
const manyStates = many.map((s, i) => ({ student_id: s.student_id, diagnostic_completed: true, risk_level: 'High', mastery: { t1: m(i) } }));
assert.strictEqual(buildClass({ students: many, states: manyStates, events: [], now }).needAttention.length, 8);
console.log('Class insights checks passed.');
