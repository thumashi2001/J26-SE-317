import test from 'node:test';
import assert from 'node:assert/strict';

import {
  prepareAttemptPayload,
  executeAttemptSubmission,
} from '../../../../../frontend/src/services/attemptSubmissionHelper.js';
import {
  submitMockAttempt,
  getMockAttempt,
  MockAttemptError,
} from '../services/mockAttemptService.js';
import { resetMemoryStoreForTesting } from '../services/mockAttemptRepository.js';

test('attemptSubmissionWiring: setup and teardown', () => {
  resetMemoryStoreForTesting();
});

test('prepareAttemptPayload: prepares 20-question Distributed Systems synthetic practice exam', () => {
  const syntheticQuestions = Array.from({ length: 20 }, (_, i) => ({
    question_id: `M16-DS-SYNTH-${String(i + 1).padStart(3, '0')}`,
    question_text: `Explain distributed consensus in system architecture component #${i + 1}.`,
    marks: null,
    marks_status: 'unassessed',
    difficulty: 'unassessed',
    source_type: 'synthetic',
    verification_status: 'unverified',
  }));

  const answers = {};
  syntheticQuestions.forEach((q, i) => {
    answers[q.question_id] = `Student response for distributed systems question ${i + 1}: Raft leader election details.`;
  });

  const paper = {
    paper_id: 'MOCK-SYNTH-DISTRIBUTED-001',
    module_key: 'distributed_systems',
    practice_mode: 'synthetic_experimental',
    source_type: 'synthetic',
    total_marks: null,
    questions: syntheticQuestions,
  };

  const payload = prepareAttemptPayload({
    paper,
    moduleKey: 'distributed_systems',
    questions: syntheticQuestions,
    answers,
    secondsElapsed: 345,
  });

  assert.equal(payload.mockId, 'MOCK-SYNTH-DISTRIBUTED-001');
  assert.equal(payload.moduleKey, 'distributed_systems');
  assert.equal(payload.sourceType, 'synthetic');
  assert.equal(payload.timeSpentSeconds, 345);
  assert.equal(payload.questions.length, 20);

  // Verify each question preserved unassessed null marks and synthetic source
  payload.questions.forEach((q, i) => {
    assert.equal(q.question_id, `M16-DS-SYNTH-${String(i + 1).padStart(3, '0')}`);
    assert.equal(q.marks, null, 'Synthetic question marks must remain null (unassessed)');
    assert.equal(q.source_type, 'synthetic');
    assert.equal(payload.answers[q.question_id].length > 0, true);
  });
  assert.equal(Object.keys(payload.answers).length, 20);
});

test('prepareAttemptPayload: prepares authentic past-paper practice exam with numeric marks', () => {
  const authenticQuestions = [
    {
      question_id: 'IT3020-2023-Q1a',
      question_text: 'Discuss ACID transaction isolation levels.',
      marks: 10,
      topic_id: 'transactions',
      difficulty: 'medium',
      source_type: 'authentic',
    },
    {
      question_id: 'IT3020-2023-Q1b',
      question_text: 'Explain write-ahead logging (WAL) recovery mechanisms.',
      marks: 15,
      topic_id: 'recovery',
      difficulty: 'hard',
      source_type: 'authentic',
    },
  ];

  const answers = {
    'IT3020-2023-Q1a': 'Serializable is the highest isolation level.',
  };

  const paper = {
    paper_id: 'MOCK-AUTH-DB-001',
    module_key: 'database_systems',
    practice_mode: 'standard',
    source_type: 'authentic',
    total_marks: 25,
    questions: authenticQuestions,
  };

  const payload = prepareAttemptPayload({
    paper,
    moduleKey: 'database_systems',
    questions: authenticQuestions,
    answers,
    secondsElapsed: 120,
  });

  assert.equal(payload.mockId, 'MOCK-AUTH-DB-001');
  assert.equal(payload.moduleKey, 'database_systems');
  assert.equal(payload.sourceType, 'authentic');
  assert.equal(payload.timeSpentSeconds, 120);
  assert.equal(payload.questions.length, 2);
  assert.equal(payload.questions[0].marks, 10);
  assert.equal(payload.questions[1].marks, 15);
});

test('executeAttemptSubmission: invokes provided onSubmitAttempt callback', async () => {
  let callbackInvoked = false;
  let receivedPayload = null;
  let successInvoked = false;

  const mockSubmitCallback = async (payload) => {
    callbackInvoked = true;
    receivedPayload = payload;
    return { attemptId: 'ATT-SUCCESS-001', status: 'pending_marking' };
  };

  const mockSuccessCallback = (res) => {
    successInvoked = true;
    assert.equal(res.attemptId, 'ATT-SUCCESS-001');
  };

  const testPayload = {
    mockId: 'MOCK-001',
    moduleKey: 'distributed_systems',
    questions: [],
    answers: {},
  };

  const res = await executeAttemptSubmission({
    onSubmitAttempt: mockSubmitCallback,
    onSubmitSuccess: mockSuccessCallback,
    payload: testPayload,
  });

  assert.equal(callbackInvoked, true);
  assert.equal(successInvoked, true);
  assert.equal(receivedPayload.mockId, 'MOCK-001');
  assert.equal(res.attemptId, 'ATT-SUCCESS-001');
});

test('executeAttemptSubmission: uses fallbackSubmitFn when onSubmitAttempt is omitted', async () => {
  let fallbackInvoked = false;
  const mockFallback = async (payload) => {
    fallbackInvoked = true;
    return { attemptId: 'ATT-FALLBACK-002', status: 'pending_marking' };
  };

  const res = await executeAttemptSubmission({
    onSubmitAttempt: null, // missing callback
    fallbackSubmitFn: mockFallback,
    payload: { mockId: 'MOCK-FALLBACK' },
  });

  assert.equal(fallbackInvoked, true);
  assert.equal(res.attemptId, 'ATT-FALLBACK-002');
});

test('executeAttemptSubmission: throws clear error instead of TypeError when no handler configured', async () => {
  await assert.rejects(
    async () => {
      await executeAttemptSubmission({
        onSubmitAttempt: null,
        fallbackSubmitFn: null,
        payload: {},
      });
    },
    (err) => {
      assert(err instanceof Error);
      assert.equal(err.message, 'Attempt submission handler is not configured.');
      return true;
    }
  );
});

test('End-to-End: Submitting 20/20 Distributed Systems synthetic practice attempt to backend service', async () => {
  const syntheticQuestions = Array.from({ length: 20 }, (_, i) => ({
    question_id: `M16-DS-SYNTH-${String(i + 1).padStart(3, '0')}`,
    question_text: `Distributed Systems Concept #${i + 1}: CAP theorem trade-offs.`,
    marks: null,
    source_type: 'synthetic',
    difficulty: 'unassessed',
  }));

  const answers = {};
  syntheticQuestions.forEach((q, i) => {
    answers[q.question_id] = `Student comprehensive response for question ${i + 1}`;
  });

  const payload = prepareAttemptPayload({
    paper: {
      paper_id: 'MOCK-DS-20-SYNTH',
      module_key: 'distributed_systems',
      source_type: 'synthetic',
    },
    moduleKey: 'distributed_systems',
    questions: syntheticQuestions,
    answers,
    secondsElapsed: 600,
  });

  // Call backend submitMockAttempt
  const attempt = await submitMockAttempt({
    studentId: 'student_distributed_001',
    mockId: payload.mockId,
    moduleKey: payload.moduleKey,
    questions: payload.questions,
    answers: payload.answers,
    timeSpentSeconds: payload.timeSpentSeconds,
    sourceType: payload.sourceType,
  });

  assert.ok(attempt.attemptId);
  assert.equal(attempt.studentId, 'student_distributed_001');
  assert.equal(attempt.moduleKey, 'distributed_systems');
  assert.equal(attempt.sourceType, 'synthetic');
  assert.equal(attempt.status, 'pending_marking');
  assert.equal(attempt.c3MarkingStatus, 'pending_marking');
  assert.equal(attempt.totalMarks, null, 'Synthetic totalMarks must remain null');
  assert.equal(attempt.hasUnassessedMarks, true);
  assert.equal(attempt.marksAwarded, null, 'marksAwarded must remain null to prevent fabricated grades');
  assert.equal(attempt.questionCount, 20);
  assert.equal(attempt.answeredCount, 20);
  assert.equal(attempt.timeSpentSeconds, 600);

  // Retrieve attempt and check persistence
  const retrieved = await getMockAttempt(attempt.attemptId, 'student_distributed_001');
  assert.equal(retrieved.attemptId, attempt.attemptId);
  assert.equal(retrieved.questions.length, 20);
  assert.equal(retrieved.questions[0].studentAnswer, 'Student comprehensive response for question 1');
  assert.equal(retrieved.questions[0].marks, null);
  assert.equal(retrieved.questions[0].sourceType, 'synthetic');
});
