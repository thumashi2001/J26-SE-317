// Run: node scripts/checkAdminSummary.js
import assert from 'node:assert';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { summarise, modelInfo, aiStatus } from '../src/modules/c1/services/adminSummaryService.js';

const now = new Date('2026-10-13T10:00:00Z');
const ago = (d) => new Date(now.getTime() - d * 86400000);
const m = (score, sessions = 1, days = 0) => ({ score, practice_sessions: sessions, last_practiced: ago(days) });
const states = [
  { student_id: 'A', diagnostic_completed: true, risk_level: 'High', mastery: { t1: m(10), t2: m(30) } },
  { student_id: 'B', diagnostic_completed: true, risk_level: 'Low', mastery: { t1: m(90, 3), t2: m(70, 3) } },
  { student_id: 'C', diagnostic_completed: false, risk_level: 'Low', mastery: {} },
];
const events = [
  { student_id: 'A', timestamp: ago(1) }, { student_id: 'A', timestamp: ago(2) },
  { student_id: 'B', timestamp: ago(20) },
];
const s = summarise({ studentCount: 3, states, events, sessionCount: 4, now });
assert.strictEqual(s.students, 3);
assert.strictEqual(s.diagnosticDone, 2);
assert.strictEqual(s.activeThisWeek, 1);
assert.deepStrictEqual(s.answers, { total: 3, thisWeek: 2 });
assert.strictEqual(s.practiceSessions, 4);
assert.deepStrictEqual(s.risk, { Low: 1, Medium: 0, High: 1 });
assert.strictEqual(s.weakestTopics[0].topic, 't1'); // t1 averages 50, t2 averages 50: tie keeps t1 first
assert.ok(s.averageLevel.score > 0);
assert.ok(!JSON.stringify(s).includes('"A"') && !JSON.stringify(s).includes('student_id'), 'no student identifiers in the summary');

const empty = summarise({ studentCount: 0, states: [], events: [], sessionCount: 0, now });
assert.strictEqual(empty.averageLevel, null);
assert.deepStrictEqual(empty.weakestTopics, []);

assert.strictEqual(modelInfo('/no/such/file.json'), null);
const f = path.join(os.tmpdir(), 'res.json');
fs.writeFileSync(f, JSON.stringify({ next_answer: { gbm: { auc: 0.65662 }, rule_twin: { auc: 0.59997 } } }));
assert.deepStrictEqual(modelInfo(f), { name: 'Gradient boosting', measure: 'AUC on students it had not seen', score: 0.657, ruleBasedScore: 0.6, trainedOn: 'synthetic students' });

assert.strictEqual(await aiStatus('http://x', async () => ({ ok: true })), 'online');
assert.strictEqual(await aiStatus('http://x', async () => { throw new Error('down'); }), 'offline');
console.log('Admin summary checks passed.');
