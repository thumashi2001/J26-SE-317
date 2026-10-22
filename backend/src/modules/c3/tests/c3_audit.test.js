import test, { before, after, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert';
import http from 'node:http';

// Audit regression suite for the C3 backend.
// Tests named AUDIT-* assert the correct behaviour of defects found in the PP1 audit. They are now fixed (no `todo` flags left);
// AUDIT-B9 (404/error middleware) is outside the C3 security scope and remains a known todo where marked.

process.env.AUTH_SECRET = 'test-secret-change-me';

import app from '../../../app.js';
import { signToken } from '../../../middleware/auth.js';
import { resetRateLimits } from '../middleware/rateLimit.js';
import { setDb } from '../../../config/db.js';
import { syncC3AssessmentToC1 } from '../../../integration/c3-c1/index.js';

// ---------------------------------------------------------------------------
// Fake in-memory Mongo (supports equality, $or, $in, $ne, $eq, $set, $setOnInsert, upsert).
// Every operation yields to the event loop so concurrent requests interleave like real I/O.
// ---------------------------------------------------------------------------
const tick = () => new Promise((resolve) => setImmediate(resolve));
const isOperatorObject = (c) => c && typeof c === 'object' && !(c instanceof Date) && Object.keys(c).some((k) => k.startsWith('$'));

function matchValue(docVal, cond) {
  if (isOperatorObject(cond)) {
    return Object.entries(cond).every(([op, arg]) => {
      if (op === '$ne') return !matchValue(docVal, arg);
      if (op === '$eq') return matchValue(docVal, arg);
      if (op === '$in') return arg.some((a) => matchValue(docVal, a));
      throw new Error(`fake db: unsupported operator ${op}`);
    });
  }
  if (cond === null || cond === undefined) return docVal === null || docVal === undefined;
  if (docVal === null || docVal === undefined) return false;
  return String(docVal) === String(cond);
}

function matchDoc(doc, q = {}) {
  return Object.entries(q).every(([k, cond]) => {
    if (k === '$or') return cond.some((sub) => matchDoc(doc, sub));
    return matchValue(doc[k], cond);
  });
}

const store = {};
const failures = { insertSubmissions: false };
let idCounter = 0;

function col(name) {
  store[name] ||= [];
  const rows = store[name];
  return {
    async insertOne(doc) {
      await tick();
      if (name === 'c3_submissions' && failures.insertSubmissions) throw new Error('simulated mongo insert failure');
      const saved = { ...doc, _id: doc._id || `${name}-${++idCounter}` };
      rows.push(saved);
      return { insertedId: saved._id };
    },
    async findOne(q) {
      await tick();
      return rows.find((r) => matchDoc(r, q)) || null;
    },
    find(q = {}) {
      const run = async () => { await tick(); return rows.filter((r) => matchDoc(r, q)); };
      return { sort() { return this; }, limit() { return this; }, toArray: run };
    },
    async updateOne(q, u) {
      await tick();
      const item = rows.find((r) => matchDoc(r, q));
      if (item && u.$set) Object.assign(item, u.$set);
      if (item && u.$push) for (const [k, v] of Object.entries(u.$push)) (item[k] ||= []).push(v);
      return { matchedCount: item ? 1 : 0 };
    },
    async findOneAndUpdate(q, u, opts = {}) {
      await tick();
      let item = rows.find((r) => matchDoc(r, q));
      if (!item && opts.upsert) {
        item = { _id: `${name}-${++idCounter}`, ...(u.$setOnInsert || {}), ...(u.$set || {}) };
        rows.push(item);
        return { value: item };
      }
      if (item && u.$set) Object.assign(item, u.$set);
      return { value: item };
    },
  };
}

const fakeDb = { collection: col };
const rowsOf = (name) => (store[name] ||= []);
function resetDb() {
  for (const k of Object.keys(store)) store[k].length = 0;
  failures.insertSubmissions = false;
}

// ---------------------------------------------------------------------------
// Servers + helpers
// ---------------------------------------------------------------------------
let aiServer;
let server;
let baseUrl;
let aiRequests = [];

const student = signToken({ sub: 'student123', role: 'student' });
const lecturer1 = signToken({ sub: 'lecturer1', role: 'lecturer' });
const lecturer2 = signToken({ sub: 'lecturer2', role: 'lecturer' });

before(async () => {
  aiServer = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => { body += c; });
    req.on('end', () => {
      aiRequests.push({ path: req.url, body: JSON.parse(body || '{}') });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'mock_success' }));
    });
  });
  await new Promise((r) => aiServer.listen(0, r));
  process.env.C3_AI_URL = `http://127.0.0.1:${aiServer.address().port}`;
  server = http.createServer(app);
  await new Promise((r) => server.listen(0, r));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
  setDb(fakeDb);
});

beforeEach(() => { resetDb(); aiRequests = []; });

// Let fire-and-forget C1 syncs settle so they cannot leak into the next test.
afterEach(async () => { for (let i = 0; i < 20; i++) await tick(); });

after(async () => {
  await new Promise((r) => server.close(r));
  await new Promise((r) => aiServer.close(r));
});

async function api(method, path, token, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${baseUrl}/api/v1/c3${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  return { status: res.status, data };
}

const mcqPayload = (extra = {}) => ({
  question_id: 'AUDIT-MCQ-01',
  question_text: 'Which style structures an app as independently deployable services?',
  answer_type: 'mcq',
  max_marks: 2,
  correct_answer: 'B',
  options: [
    { option_id: 'A', label: 'A', text: 'Monolith' },
    { option_id: 'B', label: 'B', text: 'Microservices' },
    { option_id: 'C', label: 'C', text: 'MVC' },
  ],
  selected_option_id: 'B',
  ...extra,
});

let seedCounter = 0;
function seedSubmission({ status = 'pending_review', studentId = 'student123', mark = 3, total = 4, finalMark = null, decision = null } = {}) {
  const id = `seed-sub-${++seedCounter}`;
  rowsOf('c3_submissions').push({
    _id: id, student_id: studentId, question_id: 'AUDIT-Q', question_text: 'q', student_answer: 'a',
    status, submitted_at: new Date(), updated_at: new Date(),
  });
  rowsOf('c3_results').push({
    _id: `seed-res-${seedCounter}`, submission_id: id, student_id: studentId, question_id: 'AUDIT-Q',
    automated_mark: mark, total_possible_marks: total, percentage: (mark / total) * 100,
    ai_evaluation: { total_awarded_marks: mark, total_possible_marks: total },
    lecturer_decision: decision, final_mark: finalMark, override_reason: null, status,
  });
  return id;
}
const resultOf = (subId) => rowsOf('c3_results').find((r) => r.submission_id === subId);

async function createMcqSetup(token = lecturer1) {
  const res = await api('POST', '/batch/setup', token, {
    title: 'Audit MCQ batch',
    question_id: 'AUDIT-BATCH-MCQ',
    question_text: 'Which style uses independently deployable services?',
    answer_type: 'mcq',
    max_marks: 2,
    correct_answer: 'B',
    options: [{ option_id: 'A', label: 'A', text: 'Monolith' }, { option_id: 'B', label: 'B', text: 'Microservices' }],
  });
  assert.strictEqual(res.status, 200, JSON.stringify(res.data));
  return res.data;
}

// ---------------------------------------------------------------------------
// Passing tests: correct behaviour that must keep holding
// ---------------------------------------------------------------------------
test('override persists: automated_mark preserved, final_mark/override_reason/reviewed_by recorded', async () => {
  const id = seedSubmission({ mark: 3, total: 4 });
  const res = await api('POST', `/submissions/${id}/review`, lecturer1, {
    decision: 'overridden', new_mark: 4, override_reason: '  Clear explanation  ',
  });
  assert.strictEqual(res.status, 200);
  assert.strictEqual(res.data.result.automated_mark, 3);
  assert.strictEqual(res.data.result.final_mark, 4);
  assert.strictEqual(res.data.result.override_reason, 'Clear explanation');
  assert.strictEqual(res.data.result.reviewed_by, 'lecturer1');
  const stored = resultOf(id);
  assert.strictEqual(stored.automated_mark, 3, 'automated mark must not be overwritten');
  assert.strictEqual(stored.final_mark, 4);
  assert.strictEqual(stored.lecturer_decision, 'overridden');
  assert.strictEqual(stored.reviewed_by, 'lecturer1');
  assert.strictEqual(stored.status, 'reviewed');
});

test('accepting keeps final_mark equal to the automated mark with no override reason', async () => {
  const id = seedSubmission({ mark: 3, total: 4 });
  const res = await api('POST', `/submissions/${id}/review`, lecturer1, { decision: 'accepted' });
  assert.strictEqual(res.status, 200);
  assert.strictEqual(res.data.result.final_mark, 3);
  assert.strictEqual(res.data.result.override_reason, null);
});

test('review with invalid decision or negative mark -> 400', async () => {
  const id = seedSubmission();
  assert.strictEqual((await api('POST', `/submissions/${id}/review`, lecturer1, { decision: 'maybe' })).status, 400);
  const neg = await api('POST', `/submissions/${id}/review`, lecturer1, { decision: 'overridden', new_mark: -1, override_reason: 'x' });
  assert.strictEqual(neg.status, 400);
});

test('review of a finalized result -> 409 and result is untouched', async () => {
  const id = seedSubmission({ status: 'finalized', finalMark: 3, decision: 'accepted' });
  const res = await api('POST', `/submissions/${id}/review`, lecturer1, {
    decision: 'overridden', new_mark: 1, override_reason: 'late change',
  });
  assert.strictEqual(res.status, 409);
  assert.strictEqual(resultOf(id).final_mark, 3);
  assert.strictEqual(resultOf(id).status, 'finalized');
});

test('finalize before review -> 400 and result stays pending_review', async () => {
  const id = seedSubmission();
  const res = await api('POST', `/submissions/${id}/finalize`, lecturer1, {});
  assert.strictEqual(res.status, 400);
  assert.strictEqual(resultOf(id).status, 'pending_review');
});

test('finalize twice sequentially -> second call 409', async () => {
  const id = seedSubmission();
  await api('POST', `/submissions/${id}/review`, lecturer1, { decision: 'accepted' });
  assert.strictEqual((await api('POST', `/submissions/${id}/finalize`, lecturer1, {})).status, 200);
  assert.strictEqual((await api('POST', `/submissions/${id}/finalize`, lecturer1, {})).status, 409);
});

test('review/finalize of unknown submission -> 404', async () => {
  assert.strictEqual((await api('POST', '/submissions/nope/review', lecturer1, { decision: 'accepted' })).status, 404);
  assert.strictEqual((await api('POST', '/submissions/nope/finalize', lecturer1, {})).status, 404);
});

test('batch setup list is scoped to the creating lecturer', async () => {
  await createMcqSetup(lecturer1);
  const mine = await api('GET', '/batch/setup', lecturer1);
  const theirs = await api('GET', '/batch/setup', lecturer2);
  assert.strictEqual(mine.data.setups.length, 1);
  assert.strictEqual(theirs.data.setups.length, 0);
});

test('C1 sync: second provisional sync of same submission_id updates in place (no duplicate)', async () => {
  const base = { studentId: 's1', submissionId: 'sub-c1-a', questionId: 'QX', totalPossible: 4, percentage: 50, finalized: false };
  await syncC3AssessmentToC1({ ...base, score: 2 });
  await syncC3AssessmentToC1({ ...base, score: 3, percentage: 75 });
  const events = rowsOf('learning_events');
  assert.strictEqual(events.length, 1);
  assert.strictEqual(events[0].provisional_score, 3);
  assert.strictEqual(events[0].lifecycle_stage, 'provisional');
});

test('C1 sync: a late provisional sync does not overwrite a finalized event', async () => {
  const base = { studentId: 's1', submissionId: 'sub-c1-b', questionId: 'QX', totalPossible: 4 };
  await syncC3AssessmentToC1({ ...base, score: 2, percentage: 50, finalized: false });
  await syncC3AssessmentToC1({
    ...base, score: 4, percentage: 100, finalized: true, lecturerDecision: 'overridden', overrideReason: 'ok', reviewedBy: 'lecturer1',
  });
  const late = await syncC3AssessmentToC1({ ...base, score: 1, percentage: 25, finalized: false });
  assert.strictEqual(late.synced, true);
  assert.strictEqual(late.lifecycle_stage, 'finalized');
  const events = rowsOf('learning_events');
  assert.strictEqual(events.length, 1);
  assert.strictEqual(events[0].lifecycle_stage, 'finalized');
  assert.strictEqual(events[0].final_score, 4);
  assert.strictEqual(events[0].score, 4);
  assert.strictEqual(events[0].lecturer_decision, 'overridden');
  assert.strictEqual(events[0].reviewed_by, 'lecturer1');
});

test('C1 sync: missing submissionId is refused without writing', async () => {
  const r = await syncC3AssessmentToC1({ studentId: 's1', submissionId: '', questionId: 'Q', score: 1, totalPossible: 2 });
  assert.strictEqual(r.synced, false);
  assert.strictEqual(rowsOf('learning_events').length, 0);
});

// ---------------------------------------------------------------------------
// AUDIT known bugs: tests assert the CORRECT behaviour
// ---------------------------------------------------------------------------
test(
  'AUDIT-B2: re-posting /assess for a finalized demo submission must not reopen it',
  async () => {
    const first = (await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'B' })).data;
    assert.ok(first.submission_id, 'student demo submission must be saved');
    await api('POST', `/submissions/${first.submission_id}/review`, lecturer1, { decision: 'accepted' });
    assert.strictEqual((await api('POST', `/submissions/${first.submission_id}/finalize`, lecturer1, {})).status, 200);
    assert.strictEqual(resultOf(first.submission_id).status, 'finalized');

    const again = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'A' });

    const stored = resultOf(first.submission_id);
    assert.ok(again.status === 409 || stored.status === 'finalized',
      `finalized result was reopened: http=${again.status} stored.status=${stored.status}`);
    assert.strictEqual(stored.status, 'finalized');
    assert.strictEqual(stored.final_mark, 2);
    assert.strictEqual(rowsOf('c3_submissions').find((s) => String(s._id) === first.submission_id).status, 'finalized');
  }
);

test(
  'AUDIT-B3: override with new_mark above total_possible_marks -> 400',
  async () => {
    const id = seedSubmission({ mark: 3, total: 4 });
    const res = await api('POST', `/submissions/${id}/review`, lecturer1, {
      decision: 'overridden', new_mark: 999, override_reason: 'typo',
    });
    assert.strictEqual(res.status, 400, `got ${res.status}, stored final_mark=${resultOf(id).final_mark}`);
  }
);

test(
  'AUDIT-X1: override with new_mark "Infinity" -> 400',
  async () => {
    const id = seedSubmission({ mark: 3, total: 4 });
    const res = await api('POST', `/submissions/${id}/review`, lecturer1, {
      decision: 'overridden', new_mark: 'Infinity', override_reason: 'typo',
    });
    assert.strictEqual(res.status, 400, `got ${res.status}, stored final_mark=${resultOf(id).final_mark}`);
  }
);

test(
  'AUDIT-B4a: another lecturer cannot read a batch setup they do not own',
  async () => {
    const setup = await createMcqSetup(lecturer1);
    const res = await api('GET', `/batch/setup/${setup.batch_id}`, lecturer2);
    assert.ok([403, 404].includes(res.status), `got ${res.status}`);
  }
);

test(
  'AUDIT-B4b: another lecturer cannot mark a batch they do not own',
  async () => {
    const setup = await createMcqSetup(lecturer1);
    const res = await api('POST', '/batch/mark', lecturer2, {
      setup_id: setup.batch_id, items: [{ student_id: 'IT1', selected_option_id: 'B' }],
    });
    assert.ok([403, 404].includes(res.status), `got ${res.status}`);
  }
);

test(
  'AUDIT-B4c: another lecturer cannot finalize a batch they do not own',
  async () => {
    const setup = await createMcqSetup(lecturer1);
    await api('POST', '/batch/mark', lecturer1, {
      setup_id: setup.batch_id, items: [{ student_id: 'IT1', selected_option_id: 'B' }],
    });
    const res = await api('POST', `/batch/${setup.batch_id}/finalize-all`, lecturer2, {});
    assert.ok([403, 404].includes(res.status), `got ${res.status}`);
    assert.ok(rowsOf('c3_results').every((r) => r.status !== 'finalized'), 'results were finalized by a non-owner');
  }
);

// --- finalize-all policy: only lecturer-reviewed results are finalized -----------------------------
async function markedBatch(items) {
  const setup = await createMcqSetup(lecturer1);
  await api('POST', '/batch/mark', lecturer1, { setup_id: setup.batch_id, items });
  const results = rowsOf('c3_results');
  return { setup, results };
}

test('finalize-all: nothing reviewed -> 409 and no result is finalized', async () => {
  const { setup } = await markedBatch([{ student_id: 'IT1', selected_option_id: 'B' }, { student_id: 'IT2', selected_option_id: 'A' }]);
  const res = await api('POST', `/batch/${setup.batch_id}/finalize-all`, lecturer1, {});
  assert.strictEqual(res.status, 409);
  assert.ok(rowsOf('c3_results').every((r) => r.status !== 'finalized'));
});

test('finalize-all: mixed batch finalizes only reviewed results and reports the rest', async () => {
  const { setup, results } = await markedBatch([{ student_id: 'IT1', selected_option_id: 'B' }, { student_id: 'IT2', selected_option_id: 'A' }]);
  const first = results[0];
  const rev = await api('POST', `/submissions/${first.submission_id}/review`, lecturer1, { decision: 'accepted' });
  assert.strictEqual(rev.status, 200);
  const res = await api('POST', `/batch/${setup.batch_id}/finalize-all`, lecturer1, {});
  assert.strictEqual(res.status, 200);
  assert.strictEqual(res.data.finalized_count, 1);
  assert.strictEqual(res.data.skipped_unreviewed_count, 1);
  assert.strictEqual(res.data.status, 'partially_finalized');
  const byId = Object.fromEntries(rowsOf('c3_results').map((r) => [String(r.submission_id), r]));
  assert.strictEqual(byId[String(first.submission_id)].status, 'finalized');
  assert.strictEqual(byId[String(first.submission_id)].finalized_by, 'lecturer1');
  const other = results.find((r) => r !== first);
  assert.notStrictEqual(byId[String(other.submission_id)].status, 'finalized');
});

test('finalize-all: repeated call is idempotent (no double finalize) and counts already finalized', async () => {
  const { setup, results } = await markedBatch([{ student_id: 'IT1', selected_option_id: 'B' }]);
  await api('POST', `/submissions/${results[0].submission_id}/review`, lecturer1, { decision: 'accepted' });
  const a = await api('POST', `/batch/${setup.batch_id}/finalize-all`, lecturer1, {});
  const b = await api('POST', `/batch/${setup.batch_id}/finalize-all`, lecturer1, {});
  assert.strictEqual(a.status, 200);
  assert.strictEqual(a.data.finalized_count, 1);
  assert.strictEqual(b.status, 200);
  assert.strictEqual(b.data.finalized_count, 0);
  assert.strictEqual(b.data.already_finalized_count, 1);
});

test('finalize-all: concurrent calls finalize each result exactly once', async () => {
  const { setup, results } = await markedBatch([{ student_id: 'IT1', selected_option_id: 'B' }, { student_id: 'IT2', selected_option_id: 'B' }]);
  for (const r of results) await api('POST', `/submissions/${r.submission_id}/review`, lecturer1, { decision: 'accepted' });
  const [a, b] = await Promise.all([
    api('POST', `/batch/${setup.batch_id}/finalize-all`, lecturer1, {}),
    api('POST', `/batch/${setup.batch_id}/finalize-all`, lecturer1, {}),
  ]);
  assert.strictEqual(a.data.finalized_count + b.data.finalized_count, 2, JSON.stringify([a.data, b.data]));
});

test('finalize-all: admin may finalize reviewed results, student is denied', async () => {
  const { setup, results } = await markedBatch([{ student_id: 'IT1', selected_option_id: 'B' }]);
  await api('POST', `/submissions/${results[0].submission_id}/review`, lecturer1, { decision: 'accepted' });
  const adminTok = signToken({ sub: 'admin1', role: 'admin' });
  assert.strictEqual((await api('POST', `/batch/${setup.batch_id}/finalize-all`, student, {})).status, 403);
  const res = await api('POST', `/batch/${setup.batch_id}/finalize-all`, adminTok, {});
  assert.strictEqual(res.status, 200);
  assert.strictEqual(res.data.finalized_count, 1);
});

test(
  'AUDIT-B5: two concurrent finalize calls -> exactly one 200 and one 409',
  async () => {
    // Faithful to the app code: the fake DB yields on every operation, so both requests read
    // status='reviewed' before either writes. Real Mongo has the same gap because updateOne
    // filters on _id only (no `status: { $ne: 'finalized' }` guard).
    const id = seedSubmission({ status: 'reviewed', finalMark: 3, decision: 'accepted' });
    const [a, b] = await Promise.all([
      api('POST', `/submissions/${id}/finalize`, lecturer1, {}),
      api('POST', `/submissions/${id}/finalize`, lecturer1, {}),
    ]);
    assert.deepStrictEqual([a.status, b.status].sort(), [200, 409]);
  }
);

test(
  'AUDIT-B6: when persistence fails, /assess must not report the result as saved',
  async () => {
    failures.insertSubmissions = true;
    const res = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'B' });
    assert.ok(res.status >= 500 || (res.data && res.data.persisted === false),
      `got http ${res.status} body ${JSON.stringify(res.data).slice(0, 120)}`);
    assert.strictEqual(rowsOf('c3_submissions').length, 0);
  }
);

test(
  'AUDIT-B7a: GET /submissions?status[$ne]=x (operator injection) -> 400',
  async () => {
    seedSubmission({ status: 'pending_review' });
    seedSubmission({ status: 'finalized' });
    const res = await api('GET', '/submissions?status[$ne]=x', lecturer1);
    assert.strictEqual(res.status, 400, `got ${res.status} with ${res.data?.submissions?.length} rows`);
  }
);

test(
  'AUDIT-B7b: POST /batch/mark with setup_id {"$ne":null} -> 400',
  async () => {
    const setup = await createMcqSetup(lecturer1);
    const res = await api('POST', '/batch/mark', lecturer2, {
      setup_id: { $ne: null }, items: [{ student_id: 'IT1', selected_option_id: 'B' }],
    });
    assert.strictEqual(res.status, 400, `got ${res.status}; batch ${setup.batch_id} marked=${res.data?.batch_id}`);
  }
);

test(
  'AUDIT-B7c: POST /batch/validate with setup_id {"$ne":null} -> 400',
  async () => {
    await createMcqSetup(lecturer1);
    const res = await api('POST', '/batch/validate', lecturer1, {
      setup_id: { $ne: null }, items: [{ student_id: 'IT1', selected_option_id: 'B' }],
    });
    assert.strictEqual(res.status, 400, `got ${res.status}`);
  }
);

test('AUDIT-B8: a student cannot self-grade an MCQ by supplying their own answer key', async () => {
  const res = await api('POST', '/assess', student, mcqPayload({ correct_answer: 'C', selected_option_id: 'C' }));
  assert.strictEqual(res.status, 400);
  assert.match(res.data.error, /cannot supply assessment configuration/);
  assert.strictEqual(rowsOf('c3_submissions').length, 0);
});

test('AUDIT-B8: a student cannot swap in their own rubric or max marks either', async () => {
  const res = await api('POST', '/assess', student, {
    demo_id: 'arch-full', student_answer: 'x', max_marks: 999, rubric: { criteria: [] },
  });
  assert.strictEqual(res.status, 400);
});

test('AUDIT-B8: a student must choose a server-held demo assessment (demo_id)', async () => {
  const res = await api('POST', '/assess', student, { student_answer: 'anything' });
  assert.strictEqual(res.status, 400);
  const unknown = await api('POST', '/assess', student, { demo_id: 'does-not-exist', student_answer: 'x' });
  assert.strictEqual(unknown.status, 404);
  const badType = await api('POST', '/assess', student, { batch_id: { $ne: null }, selected_option_id: 'B' });
  assert.strictEqual(badType.status, 400);
});

test('AUDIT-B8: student answers an MCQ against the server-held key (wrong and right option)', async () => {
  const wrong = await api('POST', '/assess', student, { demo_id: 'mcq-incorrect', selected_option_id: 'A' });
  assert.strictEqual(wrong.status, 200, JSON.stringify(wrong.data));
  assert.strictEqual(wrong.data.total_awarded_marks, 0);
  // A student cannot upgrade the answer by sending a different key: the key is not read from the request.
  const right = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'B' });
  assert.strictEqual(right.data.total_awarded_marks, 2);
  assert.strictEqual(right.data.persisted, true);
  assert.strictEqual(rowsOf('c3_submissions').length, 2);
});

test('GET /assessments exposes questions and options but never keys, rubrics or reference answers', async () => {
  await createMcqSetup(lecturer1);
  const res = await api('GET', '/assessments', student);
  assert.strictEqual(res.status, 200);
  const list = res.data.assessments;
  assert.ok(list.length > 0 && list.every((a) => a.kind === 'demo'), 'only demo assessments are listed');
  const text = JSON.stringify(list);
  assert.ok(!/correct_answer|reference_answer|expected_concepts|scoring_levels|required_concepts|"rubric"/.test(text), 'protected field leaked');
  const mcq = list.find((a) => a.id === 'mcq-correct');
  assert.deepStrictEqual(Object.keys(mcq.options[0]).sort(), ['label', 'option_id', 'text']);
});

test('a student reading their own submission never receives reference answer, rubric, expected concepts or answer key', async () => {
  const sub = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'B' });
  assert.strictEqual(sub.status, 200);
  const staff = await api('GET', `/submissions/${sub.data.submission_id}`, lecturer1);
  assert.ok(staff.data.submission.correct_options, 'staff must still see the key');
  const own = await api('GET', `/submissions/${sub.data.submission_id}`, student);
  assert.strictEqual(own.status, 200);
  for (const k of ['reference_answer', 'expected_concepts', 'correct_options', 'rubric']) assert.ok(!(k in own.data.submission), `${k} must be absent for students`);
});

const KEY_LEAK = /correct_option_ids|correct_labels|authoritative|answer key|Correct: Option|Key: |requires_key/i;

test('MCQ answer key is not disclosed to the student in the live response or in submission history', async () => {
  for (const option of ['A', 'B']) {
    const live = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: option });
    assert.strictEqual(live.status, 200, JSON.stringify(live.data));
    assert.ok(!KEY_LEAK.test(JSON.stringify(live.data)), `key leaked in live response (option ${option}): ${JSON.stringify(live.data).match(KEY_LEAK)?.[0]}`);
    assert.strictEqual(live.data.analysis, null);
    assert.strictEqual(live.data.mindmap, null);
    assert.strictEqual(typeof live.data.is_correct, 'boolean');
    const own = await api('GET', `/submissions/${live.data.submission_id}`, student);
    assert.ok(!KEY_LEAK.test(JSON.stringify(own.data)), `key leaked in student history detail: ${JSON.stringify(own.data).match(KEY_LEAK)?.[0]}`);
    assert.strictEqual(own.data.result.ai_evaluation.redacted, true);
    assert.ok(!('correct_options' in own.data.submission));
    // The stored evaluation is complete: staff still see the key and the full analysis.
    const staff = await api('GET', `/submissions/${live.data.submission_id}`, lecturer1);
    assert.ok(staff.data.result.ai_evaluation.correct_labels.length > 0, 'lecturer lost the answer key');
    assert.ok(/Key|Correct/.test(JSON.stringify(staff.data.result.ai_evaluation)));
    assert.ok(staff.data.result.ai_evaluation.mindmap?.nodes?.length > 0, 'lecturer lost the stored map');
  }
});

test('Subjective results are returned to students unchanged (no key exists to redact)', async () => {
  const { redactEvaluationForStudent } = await import('../services/redaction.js');
  const subjective = { answer_type: 'short', marking: { marking_version: 'f2-rubric-v1' }, analysis: { concept_matches: [{ concept: 'x', status: 'demonstrated' }] }, mindmap: { nodes: [{ node_id: 'a' }] } };
  assert.strictEqual(redactEvaluationForStudent(subjective), subjective);
  assert.strictEqual(redactEvaluationForStudent(null), null);
});

test('GET /examples (answer keys and rubrics) is staff-only', async () => {
  assert.strictEqual((await api('GET', '/examples', student)).status, 403);
  assert.strictEqual((await api('GET', '/examples', null)).status, 401);
  const res = await api('GET', '/examples', lecturer1);
  assert.strictEqual(res.status, 200);
  assert.ok(res.data.examples.some((e) => e.id === 'mcq-correct' && e.config.correct_answer));
});

test('GET /assessments requires login', async () => {
  const res = await api('GET', '/assessments', null);
  assert.strictEqual(res.status, 401);
});

test('student workflow is demo-only: a lecturer batch_id cannot be used to submit, and nothing is stored or marked', async () => {
  const setup = await createMcqSetup(lecturer1);
  const before = rowsOf('c3_submissions').length;
  for (const body of [
    { batch_id: setup.batch_id, selected_option_id: 'B' },
    { batch_id: 'BATCH-NOPE', selected_option_id: 'B' },
    { batch_id: setup.batch_id, demo_id: 'mcq-correct', selected_option_id: 'B' }, // cannot smuggle a batch next to a valid demo id
  ]) {
    const res = await api('POST', '/assess', student, body);
    assert.strictEqual(res.status, 400, JSON.stringify(body) + ' -> ' + res.status);
    assert.deepStrictEqual(Object.keys(res.data), ['error']);
  }
  assert.strictEqual(rowsOf('c3_submissions').length, before, 'nothing may be stored');
  assert.ok(rowsOf('c3_batch_setups').some((r) => r.batch_id === setup.batch_id), 'the lecturer batch itself is untouched');
  // lecturers keep their own batch workflow
  const marked = await api('POST', '/batch/mark', lecturer1, { setup_id: setup.batch_id, items: [{ student_id: 'IT1', selected_option_id: 'B' }] });
  assert.strictEqual(marked.status, 200);
});

test(
  'AUDIT-B9a: unknown route returns JSON {error} with 404',
  { todo: 'AUDIT-B9 app.js has no 404 handler; Express default replies with HTML (shared app, outside C3 security scope)' },
  async () => {
    const res = await fetch(`${baseUrl}/api/v1/does-not-exist`);
    assert.strictEqual(res.status, 404);
    assert.match(res.headers.get('content-type') || '', /application\/json/);
    const body = await res.json();
    assert.ok(body.error);
  }
);

test(
  'AUDIT-B9b: malformed JSON body returns JSON {error} with 400',
  { todo: 'AUDIT-B9 app.js has no error middleware; express.json() parse errors return an HTML stack page (shared app, outside C3 security scope)' },
  async () => {
    const res = await fetch(`${baseUrl}/api/v1/c3/assess`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${student}` },
      body: '{"question_id": ',
    });
    assert.strictEqual(res.status, 400);
    assert.match(res.headers.get('content-type') || '', /application\/json/);
    const body = await res.json();
    assert.ok(body.error);
  }
);

test('malformed JSON is at least rejected with a 400 status', async () => {
  const res = await fetch(`${baseUrl}/api/v1/c3/assess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${student}` },
    body: '{"question_id": ',
  });
  assert.strictEqual(res.status, 400);
});

// ---------------------------------------------------------------------------
// Student response contracts (exact field sets), cross-student access, limits, rate limiting
// ---------------------------------------------------------------------------
const sorted = (o) => Object.keys(o).sort();

test('contract: student MCQ live response, history list and detail expose exactly the allowed fields', async () => {
  const live = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'A' });
  assert.strictEqual(live.status, 200, JSON.stringify(live.data));
  assert.deepStrictEqual(sorted(live.data), [
    'analysis', 'answer_type', 'feedback', 'is_correct', 'is_unanswered', 'marking', 'mindmap', 'options', 'percentage',
    'persisted', 'question_id', 'redacted', 'result_id', 'selected_labels', 'selected_option_ids', 'status', 'submission_id',
    'total_awarded_marks', 'total_possible_marks',
  ]);
  assert.deepStrictEqual(sorted(live.data.options[0]), ['label', 'option_id', 'text']);
  assert.deepStrictEqual(sorted(live.data.marking.criteria_results[0]), [
    'awarded_mark', 'criterion_description', 'criterion_id', 'evidence_sentence_ids', 'explanation', 'max_marks',
    'rubric_descriptor', 'selected_level_id', 'selected_level_label', 'supporting_concepts', 'warnings',
  ]);
  const list = await api('GET', '/submissions', student);
  assert.deepStrictEqual(sorted(list.data.submissions[0]), [
    '_id', 'automated_mark', 'final_mark', 'finalized_at', 'is_demo', 'lecturer_decision', 'override_reason', 'percentage',
    'provenance', 'question_id', 'question_text', 'reviewed_at', 'reviewed_by', 'status', 'student_id', 'submitted_at',
    'total_possible_marks',
  ]);
  const detail = await api('GET', `/submissions/${live.data.submission_id}`, student);
  assert.deepStrictEqual(sorted(detail.data.submission), [
    '_id', 'answer_type', 'is_demo', 'options', 'provenance', 'question_id', 'question_text', 'selected_options',
    'status', 'student_answer', 'student_id', 'submitted_at', 'updated_at',
  ]);
  for (const o of detail.data.submission.options) assert.deepStrictEqual(sorted(o).filter((k) => !['label', 'option_id', 'text'].includes(k)), []);
});

test('contract: error responses carry only an error message, never a key, stack or internal address', async () => {
  const responses = [
    await api('POST', '/assess', student, { demo_id: 'nope', selected_option_id: 'A' }),
    await api('POST', '/assess', student, { demo_id: 'mcq-correct', correct_answer: 'A', selected_option_id: 'A' }),
    await api('GET', '/submissions/not-an-id', student),
  ];
  for (const r of responses) {
    assert.ok(r.status >= 400 && r.status < 500, `status ${r.status}`);
    assert.deepStrictEqual(sorted(r.data), ['error']);
    assert.ok(!/at .*\.js|127\.0\.0\.1|localhost|stack/i.test(r.data.error), r.data.error);
  }
});

test('cross-student: another student cannot read a submission; staff can; foreign and malformed ids are 4xx never 500', async () => {
  const mine = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'B' });
  const other = signToken({ sub: 'student999', role: 'student' });
  const denied = await api('GET', `/submissions/${mine.data.submission_id}`, other);
  assert.ok([403, 404].includes(denied.status), `got ${denied.status}`);
  assert.ok(!JSON.stringify(denied.data).includes('student123'));
  assert.strictEqual((await api('GET', `/submissions/${mine.data.submission_id}`, lecturer1)).status, 200);
  const otherList = await api('GET', '/submissions', other);
  assert.strictEqual(otherList.data.submissions.length, 0, 'another student must not see my history');
  for (const id of ['xyz', '000000000000000000000000', '..%2F..%2Fetc%2Fpasswd', '%7B%22%24ne%22%3Anull%7D']) {
    const r = await api('GET', `/submissions/${id}`, student);
    assert.ok(r.status === 404 || r.status === 400, `${id} -> ${r.status}`);
  }
});

test('limits: oversize answer, batch list and setup are refused with 413', async () => {
  const long = 'x'.repeat(20001);
  const a = await api('POST', '/assess', student, { demo_id: 'arch-full', student_answer: long });
  assert.strictEqual(a.status, 413);
  assert.strictEqual(rowsOf('c3_submissions').length, 0, 'nothing may be stored for a refused answer');
  const setup = await createMcqSetup(lecturer1);
  const many = Array.from({ length: 501 }, (_, i) => ({ student_id: `S${i}`, selected_option_id: 'A' }));
  assert.strictEqual((await api('POST', '/batch/validate', lecturer1, { setup_id: setup.batch_id, items: many })).status, 413);
  const big = await api('POST', '/batch/setup', lecturer1, {
    title: 'Too many options', question_id: 'Q', question_text: 'Which one?', answer_type: 'mcq', max_marks: 1, correct_answer: 'A',
    options: Array.from({ length: 21 }, (_, i) => ({ option_id: `O${i}`, label: `O${i}`, text: 't' })),
  });
  assert.strictEqual(big.status, 413);
});

test('rate limit: per-user budget returns 429 with Retry-After; other users and the disabled setting are unaffected', async () => {
  const saved = process.env.C3_RATE_LIMIT_PER_MIN;
  try {
    process.env.C3_RATE_LIMIT_PER_MIN = '3';
    resetRateLimits();
    const statuses = [];
    for (let i = 0; i < 5; i++) statuses.push((await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'A' })).status);
    assert.deepStrictEqual(statuses, [200, 200, 200, 429, 429]);
    const res = await fetch(`${baseUrl}/api/v1/c3/assess`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${student}` },
      body: JSON.stringify({ demo_id: 'mcq-correct', selected_option_id: 'A' }),
    });
    assert.strictEqual(res.status, 429);
    assert.ok(Number(res.headers.get('retry-after')) >= 1);
    const other = signToken({ sub: 'student777', role: 'student' });
    assert.strictEqual((await api('POST', '/assess', other, { demo_id: 'mcq-correct', selected_option_id: 'A' })).status, 200);
    process.env.C3_RATE_LIMIT_PER_MIN = '0';
    assert.strictEqual((await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'A' })).status, 200);
  } finally {
    if (saved === undefined) delete process.env.C3_RATE_LIMIT_PER_MIN; else process.env.C3_RATE_LIMIT_PER_MIN = saved;
    resetRateLimits();
  }
});

test('review history: every review and finalize action is appended, earlier decisions remain visible to staff only', async () => {
  const id = seedSubmission({ mark: 2, total: 4 });
  await api('POST', `/submissions/${id}/review`, lecturer1, { decision: 'accepted' });
  await api('POST', `/submissions/${id}/review`, lecturer1, { decision: 'overridden', new_mark: 3, override_reason: 'Rechecked against the rubric' });
  await api('POST', `/submissions/${id}/finalize`, lecturer1, {});
  const staff = await api('GET', `/submissions/${id}`, lecturer1);
  const h = staff.data.result.review_history;
  assert.deepStrictEqual(h.map((e) => e.action + ':' + (e.decision || '')), ['reviewed:accepted', 'reviewed:overridden', 'finalized:overridden']);
  assert.strictEqual(h[1].override_reason, 'Rechecked against the rubric');
  assert.strictEqual(h[1].automated_mark, 2);
  assert.strictEqual(h[1].by, 'lecturer1');
  const own = await api('GET', `/submissions/${id}`, student);
  assert.ok(!('review_history' in own.data.result), 'students must not receive the reviewer audit trail');
});

test('processing time is recorded with each evaluated response (NFR-C3-08)', async () => {
  const r = await api('POST', '/assess', lecturer1, { student_id: 'student123', question_id: 'T1', question_text: 'q?', answer_type: 'short', student_answer: 'a' });
  assert.strictEqual(r.status, 200);
  assert.strictEqual(typeof r.data.processing_time_ms, 'number');
  const stored = rowsOf('c3_results')[0];
  assert.strictEqual(typeof stored.ai_evaluation.processing_time_ms, 'number');
});

// --- Assessment list: source labelling and honest C2 status ---------------------------------------------------------
test('GET /assessments lists only the built-in demo assessments and reports C2 as unavailable', async () => {
  const setup = await createMcqSetup(lecturer1); // an active lecturer batch exists in the database
  const res = await api('GET', '/assessments', student);
  assert.strictEqual(res.status, 200);
  assert.deepStrictEqual(res.data.integrations, { c2: { available: false, reason: 'No C2 assessment export is available yet' } });
  assert.strictEqual(res.data.assessments.length, 7, 'the built-in demo bank');
  assert.ok(res.data.assessments.every((a) => a.kind === 'demo'), 'every listed item is a demo assessment');
  assert.ok(!res.data.assessments.some((a) => a.id === setup.batch_id || a.kind === 'batch'), 'lecturer batches must not be offered to students');
  assert.ok(!res.data.assessments.some((a) => /c2/i.test(`${a.kind} ${a.source || ''}`)), 'nothing may be labelled as C2');
  for (const a of res.data.assessments) {
    for (const k of ['correct_answer', 'correct_options', 'rubric', 'reference_answer', 'expected_concepts']) assert.ok(!(k in a), `${k} leaked in the list`);
    for (const o of a.options || []) assert.deepStrictEqual(Object.keys(o).sort(), ['label', 'option_id', 'text']);
  }
  // the lecturer's batch data is untouched
  assert.ok(rowsOf('c3_batch_setups').some((r) => r.batch_id === setup.batch_id), 'the batch setup must remain stored');
});

// --- Demo-only student submission: every built-in demo id, malformed ids, association, no key exposure ----------------
const DEMO_IDS = ['arch-full', 'arch-partial', 'arch-zero', 'oop-higher', 'quality-multi', 'mcq-correct', 'mcq-incorrect'];

test('every built-in demo assessment id resolves, is listed, and submits to the right assessment', async () => {
  const listed = (await api('GET', '/assessments', student)).data.assessments.map((a) => a.id).sort();
  assert.deepStrictEqual(listed, [...DEMO_IDS].sort());
  const { DEMO_ASSESSMENTS } = await import('../data/demoAssessments.js');
  for (const id of DEMO_IDS) {
    const cfg = DEMO_ASSESSMENTS[id].config;
    const isMcq = cfg.answer_type === 'mcq';
    const body = isMcq
      ? { demo_id: id, selected_option_id: cfg.options[0].option_id }
      : { demo_id: id, student_answer: 'Software architecture is the high-level structure of a system with components and relationships.' };
    const res = await api('POST', '/assess', student, body);
    assert.strictEqual(res.status, 200, `${id}: ${JSON.stringify(res.data).slice(0, 150)}`);
    assert.ok(res.data.submission_id && res.data.persisted === true, `${id}: not saved`);
    assert.strictEqual(res.data.status, 'pending_review');
    const stored = rowsOf('c3_submissions').find((r) => String(r._id) === res.data.submission_id);
    assert.strictEqual(stored.question_id, cfg.question_id, `${id}: wrong question stored`);
    assert.strictEqual(stored.student_id, 'student123');
    assert.strictEqual(stored.is_demo, true);
    assert.strictEqual(stored.answer_type === 'mcq', isMcq);
    const text = JSON.stringify(res.data);
    assert.ok(!/correct_option_ids|correct_labels|reference_answer|expected_concepts|"rubric"|scoring_levels/.test(text), `${id}: protected data in the response`);
  }
});

test('written-answer and MCQ demo submissions return valid, correctly typed results', async () => {
  const written = await api('POST', '/assess', student, { demo_id: 'arch-full', student_answer: 'Architecture has components.' });
  assert.strictEqual(written.status, 200);
  assert.ok(written.data && typeof written.data === 'object' && written.data.submission_id);
  const mcq = await api('POST', '/assess', student, { demo_id: 'mcq-correct', selected_option_id: 'B' });
  assert.strictEqual(mcq.status, 200);
  assert.strictEqual(mcq.data.is_correct, true);
  assert.strictEqual(mcq.data.total_awarded_marks, 2);
  assert.strictEqual(mcq.data.total_possible_marks, 2);
});

test('unknown or malformed demo ids are rejected with a client error and nothing is stored', async () => {
  const before = rowsOf('c3_submissions').length;
  const cases = [
    ['', 400], [null, 400], [undefined, 400], ['nope', 404], ['ARCH-FULL', 404], [' arch-full', 404], ['arch-full ', 404],
    ['constructor', 404], ['__proto__', 404], ['toString', 404], ['hasOwnProperty', 404],
    [['arch-full'], 400], [{ $ne: null }, 400], [123, 400], [true, 400],
  ];
  for (const [id, expected] of cases) {
    const body = { student_answer: 'x' };
    if (id !== undefined) body.demo_id = id;
    const res = await api('POST', '/assess', student, body);
    assert.strictEqual(res.status, expected, `demo_id=${JSON.stringify(id)} -> ${res.status} ${JSON.stringify(res.data)}`);
    assert.deepStrictEqual(Object.keys(res.data), ['error']);
  }
  assert.strictEqual(rowsOf('c3_submissions').length, before, 'nothing may be stored for a rejected id');
});
