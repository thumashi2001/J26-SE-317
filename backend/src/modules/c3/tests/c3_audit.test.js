import test, { before, after, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert';
import http from 'node:http';

// Audit regression suite for the C3 backend.
// Tests named AUDIT-* assert the correct behaviour of defects found in the PP1 audit. They are now fixed (no `todo` flags left);
// AUDIT-B9 (404/error middleware) is outside the C3 security scope and remains a known todo where marked.

process.env.AUTH_SECRET = 'test-secret-change-me';

import app from '../../../app.js';
import { signToken } from '../../../middleware/auth.js';
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
  'AUDIT-B2: re-posting /assess for a finalized batch submission must not reopen it',
  async () => {
    const setup = await createMcqSetup(lecturer1);
    const first = (await api('POST', '/assess', student, { batch_id: setup.batch_id, selected_option_id: 'B' })).data;
    assert.ok(first.submission_id, 'student submission against a lecturer batch must be saved');
    await api('POST', `/submissions/${first.submission_id}/review`, lecturer1, { decision: 'accepted' });
    assert.strictEqual((await api('POST', `/submissions/${first.submission_id}/finalize`, lecturer1, {})).status, 200);
    assert.strictEqual(resultOf(first.submission_id).status, 'finalized');

    const again = await api('POST', '/assess', student, { batch_id: setup.batch_id, selected_option_id: 'A' });

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

test('AUDIT-B8: a student must choose a server-held assessment (demo_id or batch_id)', async () => {
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

test('AUDIT-B8: lecturer batch setup drives a student submission (key hidden from the request)', async () => {
  const setup = await createMcqSetup(lecturer1);
  const res = await api('POST', '/assess', student, { batch_id: setup.batch_id, selected_option_id: 'B' });
  assert.strictEqual(res.status, 200, JSON.stringify(res.data));
  assert.strictEqual(res.data.is_correct, true);
  const ghost = await api('POST', '/assess', student, { batch_id: 'BATCH-NOPE', selected_option_id: 'B' });
  assert.strictEqual(ghost.status, 404);
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
