import test from 'node:test';
import assert from 'node:assert/strict';
import { createMemoryDb, seedTwin } from './memoryDb.js';
import * as feedback from '../services/feedbackService.js';
import { syncPathPracticeEvidence } from '../services/practiceSync.js';
import * as pathService from '../services/pathService.js';

const STUDENT = 'IT20261234';
const AI = 'http://127.0.0.1:9';

const mastery = {
  ux_testing_heuristics: {
    score: 25,
    answered: 2,
    correct: 1,
    last_practiced: new Date(),
    practice_sessions: 1,
  },
  file_organization_indexing: {
    score: 55,
    answered: 2,
    correct: 1,
    last_practiced: new Date(),
    practice_sessions: 1,
  },
  object_relational_db: {
    score: 40,
    answered: 2,
    correct: 1,
    last_practiced: new Date(),
    practice_sessions: 1,
  },
};

async function primed() {
  const db = createMemoryDb();
  await db.collection('students').insertOne({
    student_id: STUDENT,
    semester: 'Y3S2',
    name: 'Test Student',
  });
  await seedTwin(db, STUDENT, mastery);
  return db;
}

test('feedback validates and stores for owner only', async () => {
  const db = createMemoryDb();
  await assert.rejects(
    () => feedback.submitFeedback(db, STUDENT, {}),
    (e) => e.status === 400
  );
  const saved = await feedback.submitFeedback(db, STUDENT, {
    target: 'study_plan',
    usefulness: 5,
    suggestion: 'More daily cards',
  });
  assert.ok(saved.feedbackId);
  const list = await feedback.listFeedback(db, STUDENT);
  assert.equal(list.items.length, 1);
});

test('single quiz_answer is practice_observed not practice_verified', async () => {
  const db = await primed();
  const created = await pathService.createPath(db, STUDENT, { planDayCount: 7 }, AI);
  const doc = await db.collection('c4_learning_paths').findOne({ path_id: created.pathId });
  const pending = doc.activities.find((a) => a.status === 'pending');
  assert.ok(pending);

  await db.collection('learning_events').insertOne({
    student_id: STUDENT,
    topic: pending.topic,
    type: 'quiz_answer',
    correct: true,
    timestamp: new Date(),
  });

  const sync = await syncPathPracticeEvidence(db, doc);
  assert.equal(sync.changed, true);
  const updated = sync.activities.find((a) => a.activity_id === pending.activity_id);
  assert.equal(updated.status, 'practice_observed');
  assert.equal(updated.completion_kind, 'practice_observed');
  assert.equal(updated.completed_at, null);
});

test('finished C1 session verifies; abandoned or partial does not', async () => {
  const db = await primed();
  const created = await pathService.createPath(db, STUDENT, { planDayCount: 7 }, AI);
  const doc = await db.collection('c4_learning_paths').findOne({ path_id: created.pathId });
  const pending = doc.activities.find((a) => a.status === 'pending');

  await db.collection('practice_sessions').insertOne({
    session_id: 'sess-partial',
    student_id: STUDENT,
    topic: pending.topic,
    started_at: new Date(),
    completed: false,
    items: [{ question_id: 'q1', answered: true }, { question_id: 'q2', answered: false }],
  });
  let sync = await syncPathPracticeEvidence(db, doc);
  let act = sync.activities.find((a) => a.activity_id === pending.activity_id);
  assert.equal(act.completion_kind, 'practice_observed');

  await db.collection('practice_sessions').insertOne({
    session_id: 'sess-abandoned',
    student_id: STUDENT,
    topic: pending.topic,
    started_at: new Date(),
    completed: true,
    abandoned: true,
    completed_at: new Date(),
    items: [{ question_id: 'q1', answered: true }],
  });
  sync = await syncPathPracticeEvidence(db, {
    ...doc,
    activities: sync.activities,
  });
  act = sync.activities.find((a) => a.activity_id === pending.activity_id);
  assert.notEqual(act.completion_kind, 'practice_verified');

  await db.collection('practice_sessions').insertOne({
    session_id: 'sess-done',
    student_id: STUDENT,
    topic: pending.topic,
    started_at: new Date(),
    completed: true,
    abandoned: false,
    completed_at: new Date(),
    items: [
      { question_id: 'q1', answered: true },
      { question_id: 'q2', answered: true },
    ],
  });
  sync = await syncPathPracticeEvidence(db, { ...doc, activities: sync.activities });
  act = sync.activities.find((a) => a.activity_id === pending.activity_id);
  assert.equal(act.completion_kind, 'practice_verified');
  assert.equal(act.practice_evidence.sessionId, 'sess-done');
});

test('old finished session before eligible_since cannot complete new activity', async () => {
  const db = await primed();
  const created = await pathService.createPath(db, STUDENT, { planDayCount: 7 }, AI);
  let doc = await db.collection('c4_learning_paths').findOne({ path_id: created.pathId });
  const pending = doc.activities.find((a) => a.status === 'pending');

  const old = new Date(Date.now() - 7 * 24 * 3600 * 1000);
  await db.collection('practice_sessions').insertOne({
    session_id: 'sess-old',
    student_id: STUDENT,
    topic: pending.topic,
    started_at: old,
    completed: true,
    completed_at: old,
    items: [{ question_id: 'q1', answered: true }],
  });

  // Force eligible_since to now so old session is out of window
  doc = {
    ...doc,
    activities: doc.activities.map((a) =>
      a.activity_id === pending.activity_id
        ? { ...a, eligible_since: new Date().toISOString() }
        : a
    ),
  };
  const sync = await syncPathPracticeEvidence(db, doc);
  const act = sync.activities.find((a) => a.activity_id === pending.activity_id);
  assert.notEqual(act.completion_kind, 'practice_verified');
});

test('one finished session cannot verify two activities; refresh is duplicate-safe', async () => {
  const db = await primed();
  const created = await pathService.createPath(db, STUDENT, { planDayCount: 7 }, AI);
  const doc = await db.collection('c4_learning_paths').findOne({ path_id: created.pathId });
  const pending = doc.activities.filter((a) => a.status === 'pending').slice(0, 1);
  assert.ok(pending[0]);

  // Fabricate a second pending activity for same topic (repeated practice)
  const twin = {
    ...pending[0],
    activity_id: `${pending[0].activity_id}:repeat`,
    eligible_since: new Date().toISOString(),
  };
  const activities = [...doc.activities, twin];

  await db.collection('practice_sessions').insertOne({
    session_id: 'sess-once',
    student_id: STUDENT,
    topic: pending[0].topic,
    started_at: new Date(),
    completed: true,
    completed_at: new Date(),
    items: [{ question_id: 'q1', answered: true }],
  });

  const sync1 = await syncPathPracticeEvidence(db, { ...doc, activities });
  const verified = sync1.activities.filter((a) => a.completion_kind === 'practice_verified');
  assert.equal(verified.length, 1);
  assert.equal(verified[0].practice_evidence.sessionId, 'sess-once');

  const sync2 = await syncPathPracticeEvidence(db, { ...doc, activities: sync1.activities });
  assert.equal(sync2.changed, false);
  assert.equal(
    sync2.activities.filter((a) => a.completion_kind === 'practice_verified').length,
    1
  );
});

test('refresh rejects stale expectedRevision', async () => {
  const db = await primed();
  const created = await pathService.createPath(db, STUDENT, { planDayCount: 7 }, AI);
  await assert.rejects(
    () =>
      pathService.refreshPath(db, STUDENT, created.pathId, AI, {
        expectedRevision: created.revision + 99,
      }),
    (e) => e.status === 409 && e.code === 'concurrent_modification'
  );
});
