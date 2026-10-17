// Run from the backend folder:   node scripts/checkPilotCsv.js
// Checks the Google Form file reader on a small made-up file with the awkward cases (commas inside options,
// select-all answers, quotes, blank cells).
import assert from 'node:assert/strict';
import { parseCsv, pickedOptions, eventsFromResponses } from '../src/modules/c1/services/pilotCsv.js';

const opts = ['Local is for calls in the same JVM (by reference), and remote is for calls across JVMs', 'Plain', 'Has a "quote" inside', 'Plain, with comma'];
assert.deepEqual(pickedOptions(`${opts[0]}, ${opts[3]}`, opts), [0, 3], 'options containing commas are found');
assert.deepEqual(pickedOptions(opts[1], opts), [1], 'short option is not confused with a longer one');
assert.deepEqual(pickedOptions('', opts), []);

const f = (v) => `"${String(v).replace(/"/g, '""')}"`; // CSV quoting: a quote is doubled
const csv = 'Timestamp,"Q01. First?","Q02. Pick all (select ALL that apply)"\n' +
  `2026/10/17,${f(opts[1])},${f(`${opts[0]}, ${opts[3]}`)}\n` +
  `2026/10/17,${f(opts[2])},${f(opts[0])}\n` +
  `2026/10/17,,${f(opts[0])}\n`;
const key = [
  { n: 1, question_id: 'A', options: opts, correct: [1], multi: false },
  { n: 2, question_id: 'B', options: opts, correct: [0, 3], multi: true },
];
const { events, respondents } = eventsFromResponses(parseCsv(csv), key);
assert.equal(respondents, 3);
const get = (s, q) => events.find((e) => e.student_id === s && e.question_id === q);
assert.equal(get('R1', 'A').correct, true);
assert.equal(get('R1', 'B').correct, true, 'both correct options picked');
assert.equal(get('R2', 'A').correct, false);
assert.equal(get('R2', 'B').correct, false, 'only one of two correct options is not enough');
assert.equal(get('R3', 'A'), undefined, 'blank answer is skipped');
console.log('Pilot file reader checks passed.');
