// Checks how logged answers are turned into model input, and how the model reply is shown. Run: node scripts/checkPrediction.js
import assert from 'node:assert';
import { toModelEvents, getPredictions } from '../src/modules/c1/services/predictionService.js';

const T0 = new Date('2026-10-01T10:00:00Z').getTime();
const at = (days) => new Date(T0 + days * 86400000);
const logged = [
  { topic: 'code_quality_solid', timestamp: at(0), correct: true, time_sec: 30, hint_used: false, session_id: 'a' },
  { topic: 'code_quality_solid', timestamp: at(0.001), correct: false, time_sec: 12, hint_used: true, session_id: 'a' },
  { topic: 'code_quality_solid', timestamp: at(3), correct: true, time_sec: 40, session_id: 'b' },
];
const { events } = toModelEvents([logged[2], logged[0], logged[1]]); // out of order on purpose
assert.deepStrictEqual(events.map((e) => e.q_in_session), [0, 1, 0]);
assert.strictEqual(events[0].day, 0);
assert.ok(Math.abs(events[2].day - 3) < 1e-9);
assert.strictEqual(events[1].hint_used, 1);
assert.strictEqual(events[0].module, 'SE3070');
assert.strictEqual(events[0].source, 'quiz');

const db = {
  collection: (name) => ({
    findOne: async () => ({ diagnostic_completed: true }),
    find: () => ({ toArray: async () => (name === 'learning_events' ? logged : []) }),
  }),
};
const calls = [];
globalThis.__fakeAi = async (url, path, body) => { calls.push([path, body]); return { topics: { code_quality_solid: { p: 0.684, answers: 3 } } }; };
const out = await getPredictions(db, 'S1', 'http://x', at(5), globalThis.__fakeAi);
assert.strictEqual(calls[0][0], '/twin/predict-correct');
assert.ok(Math.abs(calls[0][1].as_of_day - 5) < 1e-9);
assert.deepStrictEqual(out.topics.code_quality_solid, { chance: 68, band: 'unsure', answers: 3 });

const empty = { collection: () => ({ findOne: async () => ({ diagnostic_completed: true }), find: () => ({ toArray: async () => [] }) }) };
assert.deepStrictEqual((await getPredictions(empty, 'S1', 'http://x', at(5), globalThis.__fakeAi)).topics, {});
console.log('Prediction checks passed.');
