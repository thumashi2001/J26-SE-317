import test from 'node:test';
import assert from 'node:assert/strict';
import { createMemoryDb, seedTwin } from './memoryDb.js';
import * as exam from '../services/examService.js';
import { fetchC2ExamPaper } from '../services/c2ExamAdapter.js';

const STUDENT = 'IT20261234';
const AI = 'http://127.0.0.1:9';

async function dbWithTwin() {
  const db = createMemoryDb();
  await db.collection('students').insertOne({ student_id: STUDENT, semester: 'Y3S1' });
  await seedTwin(db, STUDENT, {
    interaction_functional_design: {
      score: 40,
      answered: 2,
      correct: 1,
      last_practiced: new Date(),
      practice_sessions: 1,
    },
    code_quality_solid: {
      score: 35,
      answered: 2,
      correct: 1,
      last_practiced: new Date(),
      practice_sessions: 1,
    },
    refactoring_best_practices: {
      score: 30,
      answered: 2,
      correct: 1,
      last_practiced: new Date(),
      practice_sessions: 1,
    },
  });
  // Align semester on twin for topic filtering
  const state = await db.collection('mastery_state').findOne({ student_id: STUDENT });
  state.semester = 'Y3S1';
  await db.collection('mastery_state').replaceOne({ student_id: STUDENT }, state);
  return db;
}

test('C2 adapter reports unavailable without disguising fixtures', async () => {
  const c2 = await fetchC2ExamPaper({});
  assert.equal(c2.available, false);
  assert.match(c2.reason, /without an authorized HTTP/i);
  assert.ok(c2.required_payload_sketch?.start);
});

test('create/save/submit grades server-side; keys not in public questions', async () => {
  const db = await dbWithTwin();
  const attempt = await exam.createExamAttempt(
    db,
    STUDENT,
    {
      source: 'c1_practice_bank',
      topics: ['interaction_functional_design', 'code_quality_solid', 'refactoring_best_practices'],
      questionCount: 5,
      timeLimitSec: 600,
      clientRequestId: 'exam-1',
    },
    AI
  );
  assert.equal(attempt.source, 'c1_practice_bank');
  assert.ok(attempt.questions.length >= 3);
  for (const q of attempt.questions) {
    assert.equal('correct' in q, false);
    assert.equal('correctIndexes' in q, false);
    assert.equal('why' in q, false);
  }
  assert.equal(attempt.preExamModel.features_from_exam_answers, false);
  assert.ok(attempt.preExamModel.assessment);
  // Primary this-quiz estimate (blueprint) must be present and distinct from sim readiness.
  assert.equal(attempt.preExamModel.assessment.practice_quiz?.usable, true);
  assert.equal(
    attempt.preExamModel.assessment.practice_quiz?.protocol,
    'c4-practice-quiz-estimate-v1'
  );
  assert.equal(attempt.preExamModel.assessment.practice_quiz?.simulation_trained, false);
  assert.ok(Number.isFinite(attempt.preExamModel.assessment.practice_quiz?.predicted_score));
  // Live exam estimate may be usable when C4 AI is up; response target stays blocked.
  assert.equal(attempt.preExamModel.assessment.response?.usable, false);

  const answers = {};
  for (const q of attempt.questions) {
    answers[q.questionId] = [0];
  }
  await exam.saveAnswers(db, STUDENT, attempt.attemptId, { answers });
  const submitted = await exam.submitAttempt(db, STUDENT, attempt.attemptId, {});
  assert.equal(submitted.status, 'submitted');
  assert.ok(submitted.result);
  assert.equal(submitted.result.grading, 'server_side_objective_mcq');
  assert.ok(Array.isArray(submitted.review));
  assert.ok(submitted.predictionOutcome);
  assert.equal(submitted.predictionOutcome.features_from_exam_answers, false);
  assert.ok(
    Number.isFinite(submitted.predictionOutcome.observed_score_fraction) ||
      submitted.predictionOutcome.observed_score_fraction === 0
  );
  assert.equal(
    submitted.predictionOutcome.practice_quiz_prediction?.protocol,
    'c4-practice-quiz-estimate-v1'
  );
  // Frozen pre-exam estimate must still match create-time prediction
  assert.equal(
    submitted.preExamModel.assessment.practice_quiz.predicted_score,
    attempt.preExamModel.assessment.practice_quiz.predicted_score
  );

  const again = await exam.submitAttempt(db, STUDENT, attempt.attemptId, {});
  assert.equal(again.duplicate, true);

  const listed = await exam.listAttempts(db, STUDENT);
  const listedRow = listed.attempts.find((row) => row.attemptId === attempt.attemptId);
  assert.equal(listedRow.result.review, undefined);
  assert.equal(JSON.stringify(listedRow).includes('correctIndexes'), false);
  const opened = await exam.getAttempt(db, STUDENT, attempt.attemptId);
  assert.ok(opened.review.some((row) => Array.isArray(row.correctIndexes)));

  // Ownership
  await assert.rejects(
    () => exam.getAttempt(db, 'IT20269999', attempt.attemptId),
    (e) => e.status === 403
  );
});

test('c2 source returns 503', async () => {
  const db = await dbWithTwin();
  await assert.rejects(
    () => exam.createExamAttempt(db, STUDENT, { source: 'c2_past_paper' }, AI),
    (e) => e.status === 503 && e.code === 'c2_exam_unavailable'
  );
});

test('idempotent create by clientRequestId', async () => {
  const db = await dbWithTwin();
  const a = await exam.createExamAttempt(
    db,
    STUDENT,
    {
      topics: ['interaction_functional_design', 'code_quality_solid', 'refactoring_best_practices'],
      questionCount: 4,
      clientRequestId: 'same',
    },
    AI
  );
  const b = await exam.createExamAttempt(
    db,
    STUDENT,
    {
      topics: ['interaction_functional_design', 'code_quality_solid', 'refactoring_best_practices'],
      questionCount: 4,
      clientRequestId: 'same',
    },
    AI
  );
  assert.equal(a.attemptId, b.attemptId);
});

test('timeout finalizes with grade on saved answers; review only after submit', async () => {
  const db = await dbWithTwin();
  const attempt = await exam.createExamAttempt(
    db,
    STUDENT,
    {
      topics: ['interaction_functional_design', 'code_quality_solid', 'refactoring_best_practices'],
      questionCount: 4,
      timeLimitSec: 60,
      clientRequestId: 'timeout-1',
    },
    AI
  );
  assert.equal(attempt.review, undefined);
  assert.equal(attempt.preExamModel.features_from_exam_answers, false);

  const answers = {};
  for (const q of attempt.questions) answers[q.questionId] = [0];
  await exam.saveAnswers(db, STUDENT, attempt.attemptId, { answers });

  // Force expiry
  const doc = await db.collection('c4_exam_attempts').findOne({ attempt_id: attempt.attemptId });
  doc.expires_at = new Date(Date.now() - 1000);
  await db.collection('c4_exam_attempts').replaceOne({ attempt_id: attempt.attemptId }, doc);

  const after = await exam.getAttempt(db, STUDENT, attempt.attemptId);
  assert.equal(after.status, 'submitted');
  assert.equal(after.result.finalizedReason, 'time_limit_exceeded');
  assert.ok(Array.isArray(after.review));
  assert.equal(after.preExamModel.features_from_exam_answers, false);

  const dup = await exam.submitAttempt(db, STUDENT, attempt.attemptId, {});
  assert.equal(dup.duplicate, true);
});

test('rejects off-semester topics even if requested', async () => {
  const db = await dbWithTwin();
  // Y3S2-only topic while twin semester is Y3S1
  await assert.rejects(
    () =>
      exam.createExamAttempt(
        db,
        STUDENT,
        {
          topics: ['ds_architectures_sockets'],
          questionCount: 3,
        },
        AI
      ),
    (e) => e.status === 400 && e.code === 'topics_not_eligible'
  );
});

test('save after submit is duplicate-safe and does not change answers', async () => {
  const db = await dbWithTwin();
  const attempt = await exam.createExamAttempt(
    db,
    STUDENT,
    {
      topics: ['interaction_functional_design', 'code_quality_solid', 'refactoring_best_practices'],
      questionCount: 4,
      clientRequestId: 'save-after',
    },
    AI
  );
  const answers = {};
  for (const q of attempt.questions) answers[q.questionId] = [0];
  await exam.submitAttempt(db, STUDENT, attempt.attemptId, { answers });
  const saved = await exam.saveAnswers(db, STUDENT, attempt.attemptId, {
    answers: Object.fromEntries(attempt.questions.map((q) => [q.questionId, [1]])),
  });
  assert.equal(saved.duplicate, true);
  assert.deepEqual(saved.answers[attempt.questions[0].questionId], [0]);
});
