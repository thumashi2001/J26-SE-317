import test from 'node:test';
import assert from 'node:assert/strict';
import { createMemoryDb, seedTwin } from './memoryDb.js';
import * as service from '../services/pathService.js';

const STUDENT = 'IT20261234';
const OTHER = 'IT20269999';
const AI = 'http://127.0.0.1:9'; // unreachable on purpose; insights degrade

async function primedDb(mastery) {
  const db = createMemoryDb();
  await db.collection('students').insertOne({
    student_id: STUDENT,
    semester: 'Y3S2',
    name: 'Test Student',
  });
  await db.collection('students').insertOne({
    student_id: OTHER,
    semester: 'Y3S2',
    name: 'Other',
  });
  await seedTwin(db, STUDENT, mastery);
  await seedTwin(db, OTHER, {
    file_organization_indexing: {
      score: 15,
      answered: 2,
      correct: 1,
      last_practiced: new Date(),
      practice_sessions: 1,
    },
  });
  return db;
}

/** Mastery keys must be current C1 PRACTICE_QUESTIONS ids (post Development content). */
const sampleMastery = {
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

test('createPath builds deterministic weakest-first order', async () => {
  const db = await primedDb(sampleMastery);
  const path = await service.createPath(db, STUDENT, { horizon: 10 }, AI);
  assert.equal(path.reused, false);
  assert.equal(path.strategy, 'weakest_stored_mastery_v1');
  assert.equal(path.multiActionPolicy.activated, false);
  assert.equal(path.multiActionPolicy.protocol, 'se-path-multi-v2');
  assert.notEqual(path.nextActivitySource, 'se-path-multi-v2');
  assert.equal(path.activities[0].topic, 'ux_testing_heuristics');
  assert.ok(path.activities.length >= 3);
  assert.ok(path.sourceSnapshotAt);
  assert.equal(path.sourceSnapshot.mastery_scale, '0-100');
});

test('createPath is idempotent for active path and clientRequestId', async () => {
  const db = await primedDb(sampleMastery);
  const a = await service.createPath(db, STUDENT, { clientRequestId: 'req-1' }, AI);
  const b = await service.createPath(db, STUDENT, { clientRequestId: 'req-1' }, AI);
  assert.equal(b.reused, true);
  assert.equal(b.pathId, a.pathId);
  const c = await service.createPath(db, STUDENT, {}, AI);
  assert.equal(c.reused, true);
  assert.equal(c.reuseReason, 'active_path_exists');
  assert.equal(c.pathId, a.pathId);
});

test('progress is self-reported, idempotent, and does not write C1 mastery', async () => {
  const db = await primedDb(sampleMastery);
  const before = await db.collection('mastery_state').findOne({ student_id: STUDENT });
  const path = await service.createPath(db, STUDENT, {}, AI);
  const activityId = path.activities[0].activityId;
  const first = await service.recordProgress(db, STUDENT, path.pathId, { activityId });
  assert.equal(first.progress.completionKind, 'self_reported');
  assert.equal(first.progress.duplicate, false);
  const second = await service.recordProgress(db, STUDENT, path.pathId, { activityId });
  assert.equal(second.progress.duplicate, true);

  const after = await db.collection('mastery_state').findOne({ student_id: STUDENT });
  assert.deepEqual(after.mastery, before.mastery);
  const events = await db.collection('learning_events').find({}).toArray();
  assert.equal(events.length, 0);
});

test('rejects access to another student path', async () => {
  const db = await primedDb(sampleMastery);
  const path = await service.createPath(db, STUDENT, {}, AI);
  await assert.rejects(
    () => service.getPath(db, OTHER, path.pathId),
    (err) => err.status === 403
  );
  await assert.rejects(
    () =>
      service.recordProgress(db, OTHER, path.pathId, {
        activityId: path.activities[0].activityId,
      }),
    (err) => err.status === 403
  );
});

test('replan rejects a stale expected revision before writing', async () => {
  const db = await primedDb(sampleMastery);
  const path = await service.createPath(db, STUDENT, {}, AI);
  await assert.rejects(
    () =>
      service.replanPath(
        db,
        STUDENT,
        path.pathId,
        { expectedRevision: path.revision - 1 },
        AI
      ),
    (err) => err.status === 409 && err.code === 'concurrent_modification'
  );
  const current = await service.getPath(db, STUDENT, path.pathId);
  assert.equal(current.revision, path.revision);
});

test('replan preserves completed activities and bumps revision', async () => {
  const db = await primedDb(sampleMastery);
  const path = await service.createPath(db, STUDENT, {}, AI);
  const activityId = path.activities[0].activityId;
  await service.recordProgress(db, STUDENT, path.pathId, { activityId });
  const replanned = await service.replanPath(db, STUDENT, path.pathId, {}, AI);
  assert.equal(replanned.revision, 2);
  const kept = replanned.activities.find((a) => a.activityId === activityId);
  assert.ok(kept);
  assert.equal(kept.status, 'self_reported_complete');
  const revisions = await db.collection('c4_learning_path_revisions').find({}).toArray();
  assert.ok(revisions.length >= 1);
});

test('diagnostic required before create', async () => {
  const db = createMemoryDb();
  await db.collection('students').insertOne({ student_id: STUDENT, semester: 'Y3S2' });
  await db.collection('mastery_state').insertOne({
    student_id: STUDENT,
    diagnostic_completed: false,
    mastery: {},
  });
  await assert.rejects(
    () => service.createPath(db, STUDENT, {}, AI),
    (err) => err.status === 409
  );
});
