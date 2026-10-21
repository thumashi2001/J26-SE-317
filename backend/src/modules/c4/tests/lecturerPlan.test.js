import test from 'node:test';
import assert from 'node:assert/strict';
import { createMemoryDb, seedTwin } from './memoryDb.js';
import * as paths from '../services/pathService.js';
import {
  LIVE_LECTURER_SCOPE,
  assertAssigned,
  assertLecturerReader,
} from '../services/lecturerScope.js';
import { listLecturerStudents, readLecturerStudentPlan } from '../services/lecturerPlan.js';
import * as lecturer from '../controllers/lecturerController.js';

const LECTURER = 'SLIITLEC001';
const STUDENT = 'IT20261234';
const OTHER = 'IT20269999';
const AI = 'http://127.0.0.1:9';

const FIXTURE = Object.freeze({
  mode: 'test_fixture',
  assignments: Object.freeze([{ lecturerId: LECTURER, studentId: STUDENT }]),
});

function invoke(handler, req) {
  return new Promise((resolve, reject) => {
    const res = {
      statusCode: 200,
      status(code) {
        this.statusCode = code;
        return this;
      },
      json(body) {
        resolve({ status: this.statusCode, body });
      },
    };
    Promise.resolve(handler(req, res)).catch(reject);
  });
}

async function dbWithPlan() {
  const db = createMemoryDb();
  await db.collection('students').insertOne({ student_id: STUDENT, semester: 'Y3S1', name: 'Test' });
  await seedTwin(db, STUDENT, {
    ux_testing_heuristics: {
      score: 25,
      answered: 2,
      correct: 1,
      last_practiced: new Date(),
      practice_sessions: 1,
    },
  });
  await paths.createPath(db, STUDENT, {}, AI);
  return db;
}

test('lecturer reader rejects missing, student, and admin tokens', () => {
  assert.throws(() => assertLecturerReader({}), (err) => err.status === 401);
  assert.throws(
    () => assertLecturerReader({ user: { sub: STUDENT, role: 'student' } }),
    (err) => err.status === 403 && err.code === 'role_not_lecturer'
  );
  assert.throws(
    () => assertLecturerReader({ user: { sub: 'ADMIN1', role: 'admin' } }),
    (err) => err.status === 403 && err.code === 'role_not_lecturer'
  );
  assert.equal(assertLecturerReader({ user: { sub: LECTURER, role: 'lecturer' } }), LECTURER);
});

test('live lecturer scope fails closed before any database read', async () => {
  const db = {
    collection() {
      throw new Error('live scope must not read student records');
    },
  };
  assert.throws(
    () => listLecturerStudents(LECTURER, LIVE_LECTURER_SCOPE),
    (err) => err.status === 403 && err.code === 'lecturer_scope_unavailable'
  );
  await assert.rejects(
    () => readLecturerStudentPlan(db, LECTURER, STUDENT, LIVE_LECTURER_SCOPE),
    (err) => err.status === 403 && err.code === 'lecturer_scope_unavailable'
  );
  assert.throws(
    () => assertAssigned(LECTURER, STUDENT, { mode: 'unavailable', studentId: STUDENT }),
    (err) => err.code === 'lecturer_scope_unavailable'
  );
});

test('empty fixture assignment rejects a direct student id before any database read', async () => {
  const db = {
    collection() {
      throw new Error('revoked fixture must not read student records');
    },
  };
  const revoked = { mode: 'test_fixture', assignments: [] };
  await assert.rejects(
    () => readLecturerStudentPlan(db, LECTURER, STUDENT, revoked),
    (err) => err.status === 403 && err.code === 'lecturer_student_forbidden'
  );
});

test('lecturer HTTP scope is unauthenticated without a token', async () => {
  const res = await invoke(lecturer.scope, {});
  assert.equal(res.status, 401);
  assert.equal(res.body.code, 'unauthenticated');
});

test('HTTP lecturer routes stay fail-closed even if a studentId is supplied', async () => {
  const req = { user: { sub: LECTURER, role: 'lecturer' }, params: { studentId: STUDENT } };
  const listed = await invoke(lecturer.students, req);
  assert.equal(listed.body.code, 'lecturer_scope_unavailable', JSON.stringify(listed.body));
  assert.equal(listed.status, 403);
  const detail = await invoke(lecturer.plan, req);
  assert.equal(detail.status, 403);
  assert.equal(detail.body.code, 'lecturer_scope_unavailable');
});

test('test fixture allows one assigned plan and rejects other students and lecturers', async () => {
  const db = await dbWithPlan();
  const allowed = await readLecturerStudentPlan(db, LECTURER, STUDENT, FIXTURE);
  assert.equal(allowed.plan.studentId, STUDENT);
  assert.equal(allowed.plan.quizAnswerKeys, 'not included');
  assert.ok(allowed.plan.activities.length >= 1);
  assert.equal(allowed.operational, false);
  await assert.rejects(
    () => readLecturerStudentPlan(db, LECTURER, OTHER, FIXTURE),
    (err) => err.status === 403 && err.code === 'lecturer_student_forbidden'
  );
  await assert.rejects(
    () => readLecturerStudentPlan(db, 'SLIITLEC002', STUDENT, FIXTURE),
    (err) => err.status === 403 && err.code === 'lecturer_student_forbidden'
  );
});
