import test from 'node:test';
import assert from 'node:assert/strict';
import {
  submitMockAttempt,
  listMockAttempts,
  getMockAttempt,
  MockAttemptError,
} from '../services/mockAttemptService.js';
import { resetMemoryStoreForTesting } from '../services/mockAttemptRepository.js';

const SAMPLE_QUESTIONS = [
  {
    question_id: 'DS-2023-Q1a',
    question_text: 'Explain B-tree clustered index scans.',
    marks: 10,
    topic_id: 'database_indexing',
    difficulty: 'medium',
    source_type: 'authentic',
  },
  {
    question_id: 'DS-2023-Q1b',
    question_text: 'Differentiate between optimistic and pessimistic locking.',
    marks: 15,
    topic_id: 'transactions',
    difficulty: 'hard',
    source_type: 'authentic',
  },
];

test('beforeEach cleanup', () => {
  resetMemoryStoreForTesting();
});

test('submitMockAttempt rejects missing studentId', async () => {
  await assert.rejects(
    async () => {
      await submitMockAttempt({
        studentId: '',
        mockId: 'MOCK-123',
        moduleKey: 'database_systems',
        questions: SAMPLE_QUESTIONS,
      });
    },
    (err) => {
      assert(err instanceof MockAttemptError);
      assert.equal(err.status, 401);
      return true;
    }
  );
});

test('submitMockAttempt rejects invalid moduleKey', async () => {
  await assert.rejects(
    async () => {
      await submitMockAttempt({
        studentId: 'student_123',
        mockId: 'MOCK-123',
        moduleKey: 'invalid_module_xyz',
        questions: SAMPLE_QUESTIONS,
      });
    },
    (err) => {
      assert(err instanceof MockAttemptError);
      assert.equal(err.status, 400);
      assert(err.message.includes('Invalid module key'));
      return true;
    }
  );
});

test('submitMockAttempt rejects missing mockId', async () => {
  await assert.rejects(
    async () => {
      await submitMockAttempt({
        studentId: 'student_123',
        mockId: '   ',
        moduleKey: 'database_systems',
        questions: SAMPLE_QUESTIONS,
      });
    },
    (err) => {
      assert(err instanceof MockAttemptError);
      assert.equal(err.status, 400);
      return true;
    }
  );
});

test('submitMockAttempt rejects empty questions array', async () => {
  await assert.rejects(
    async () => {
      await submitMockAttempt({
        studentId: 'student_123',
        mockId: 'MOCK-123',
        moduleKey: 'database_systems',
        questions: [],
      });
    },
    (err) => {
      assert(err instanceof MockAttemptError);
      assert.equal(err.status, 400);
      return true;
    }
  );
});

test('submitMockAttempt rejects non-object answers parameter', async () => {
  await assert.rejects(
    async () => {
      await submitMockAttempt({
        studentId: 'student_123',
        mockId: 'MOCK-123',
        moduleKey: 'database_systems',
        questions: SAMPLE_QUESTIONS,
        answers: 'invalid_answers_string',
      });
    },
    (err) => {
      assert(err instanceof MockAttemptError);
      assert.equal(err.status, 400);
      return true;
    }
  );
});

test('submitMockAttempt creates attempt with pending_marking status and null marks', async () => {
  const result = await submitMockAttempt({
    studentId: 'student_123',
    mockId: 'MOCK-12345',
    moduleKey: 'database_systems',
    questions: SAMPLE_QUESTIONS,
    answers: {
      'DS-2023-Q1a': 'Clustered indexing arranges table rows physically in index order.',
    },
    timeSpentSeconds: 120,
  });

  assert(result.attemptId.startsWith('ATT-'));
  assert.equal(result.studentId, 'student_123');
  assert.equal(result.mockId, 'MOCK-12345');
  assert.equal(result.moduleKey, 'database_systems');
  assert.equal(result.totalMarks, 25);
  // Academic integrity: never fabricate marks
  assert.equal(result.marksAwarded, null);
  assert.equal(result.status, 'pending_marking');
  assert.equal(result.c3MarkingStatus, 'pending_marking');
  assert.equal(result.questionCount, 2);
  assert.equal(result.answeredCount, 1);
  assert.equal(result.timeSpentSeconds, 120);

  // Check question items
  assert.equal(result.questions.length, 2);
  const q1 = result.questions[0];
  assert.equal(q1.questionId, 'DS-2023-Q1a');
  assert.equal(q1.isAnswered, true);
  assert.equal(q1.studentAnswer, 'Clustered indexing arranges table rows physically in index order.');
  assert.equal(q1.marksAwarded, null);
  assert.equal(q1.markingStatus, 'pending_marking');

  const q2 = result.questions[1];
  assert.equal(q2.questionId, 'DS-2023-Q1b');
  assert.equal(q2.isAnswered, false);
  assert.equal(q2.studentAnswer, '');
  assert.equal(q2.marksAwarded, null);
  assert.equal(q2.markingStatus, 'pending_marking');
});

test('listMockAttempts returns attempts for student and filters by module', async () => {
  resetMemoryStoreForTesting();

  await submitMockAttempt({
    studentId: 'student_A',
    mockId: 'MOCK-1',
    moduleKey: 'database_systems',
    questions: SAMPLE_QUESTIONS,
  });

  await submitMockAttempt({
    studentId: 'student_A',
    mockId: 'MOCK-2',
    moduleKey: 'software_architecture',
    questions: SAMPLE_QUESTIONS,
  });

  await submitMockAttempt({
    studentId: 'student_B',
    mockId: 'MOCK-3',
    moduleKey: 'database_systems',
    questions: SAMPLE_QUESTIONS,
  });

  // Student A all modules
  const studentAAll = await listMockAttempts('student_A');
  assert.equal(studentAAll.length, 2);

  // Student A filtered by module
  const studentADb = await listMockAttempts('student_A', 'database_systems');
  assert.equal(studentADb.length, 1);
  assert.equal(studentADb[0].mockId, 'MOCK-1');

  // Student B isolated
  const studentBAll = await listMockAttempts('student_B');
  assert.equal(studentBAll.length, 1);
  assert.equal(studentBAll[0].mockId, 'MOCK-3');
});

test('getMockAttempt retrieves attempt and enforces student isolation', async () => {
  resetMemoryStoreForTesting();

  const saved = await submitMockAttempt({
    studentId: 'student_A',
    mockId: 'MOCK-1',
    moduleKey: 'database_systems',
    questions: SAMPLE_QUESTIONS,
  });

  // Allowed for student_A
  const fetched = await getMockAttempt(saved.attemptId, 'student_A');
  assert.equal(fetched.attemptId, saved.attemptId);

  // Denied / 404 for student_B trying to access student_A's attempt
  await assert.rejects(
    async () => {
      await getMockAttempt(saved.attemptId, 'student_B');
    },
    (err) => {
      assert(err instanceof MockAttemptError);
      assert.equal(err.status, 404);
      return true;
    }
  );
});

test('submitMockAttempt persists with MongoDB collection when dbOverride is provided', async () => {
  const store = new Map();
  const mockCollection = {
    replaceOne: async (filter, doc) => {
      store.set(filter.attemptId, doc);
      return { acknowledged: true };
    },
    findOne: async (query) => {
      const doc = store.get(query.attemptId);
      if (!doc) return null;
      if (query.studentId && doc.studentId !== query.studentId) return null;
      return doc;
    },
    find: (query) => {
      return {
        sort: () => ({
          toArray: async () => {
            const list = Array.from(store.values()).filter((d) => d.studentId === query.studentId);
            return list;
          },
        }),
      };
    },
  };

  const mockDb = {
    collection: (name) => {
      assert.equal(name, 'c2_mock_attempts');
      return mockCollection;
    },
  };

  const attempt = await submitMockAttempt({
    studentId: 'student_mongo',
    mockId: 'MOCK-MONGO',
    moduleKey: 'software_architecture',
    questions: SAMPLE_QUESTIONS,
    dbOverride: mockDb,
  });

  assert(store.has(attempt.attemptId));
  const retrieved = await getMockAttempt(attempt.attemptId, 'student_mongo', mockDb);
  assert.equal(retrieved.attemptId, attempt.attemptId);
});

test('submitMockAttempt supports synthetic questions with unassessed marks across all 8 modules', async () => {
  const ALL_EIGHT_MODULES = [
    'application_frameworks',
    'case_studies_software_engineering',
    'database_systems',
    'distributed_systems',
    'software_architecture',
    'software_engineering_process_quality_management',
    'software_project_management',
    'user_experience_engineering',
  ];

  for (const moduleKey of ALL_EIGHT_MODULES) {
    const syntheticQuestions = [
      {
        question_id: `SYN-${moduleKey.toUpperCase()}-001`,
        question_text: `Sample synthetic scenario question for ${moduleKey}.`,
        marks: null, // Strictly null: unassessed!
        source_type: 'synthetic',
        difficulty: 'unassessed',
        topic_id: `provisional_${moduleKey}_topic`,
      },
      {
        question_id: `SYN-${moduleKey.toUpperCase()}-002`,
        question_text: `Second synthetic question for ${moduleKey}.`,
        marks: null,
        source_type: 'synthetic',
        difficulty: 'unassessed',
        topic_id: `provisional_${moduleKey}_topic_2`,
      },
    ];

    const result = await submitMockAttempt({
      studentId: `student_${moduleKey}`,
      mockId: `SYN-PRACTICE-${moduleKey.toUpperCase()}`,
      moduleKey,
      questions: syntheticQuestions,
      answers: {
        [`SYN-${moduleKey.toUpperCase()}-001`]: 'Student response for question 1.',
      },
      timeSpentSeconds: 65,
    });

    assert(result.attemptId.startsWith('ATT-'));
    assert.equal(result.moduleKey, moduleKey);
    // Unassessed marks must not be fabricated!
    assert.equal(result.totalMarks, null);
    assert.equal(result.hasUnassessedMarks, true);
    assert.equal(result.marksAwarded, null);
    assert.equal(result.status, 'pending_marking');
    assert.equal(result.questionCount, 2);
    assert.equal(result.answeredCount, 1);

    const q1 = result.questions[0];
    assert.equal(q1.marks, null);
    assert.equal(q1.sourceType, 'synthetic');
    assert.equal(q1.difficulty, 'unassessed');
    assert.equal(q1.studentAnswer, 'Student response for question 1.');
    assert.equal(q1.isAnswered, true);

    const q2 = result.questions[1];
    assert.equal(q2.marks, null);
    assert.equal(q2.sourceType, 'synthetic');
    assert.equal(q2.difficulty, 'unassessed');
    assert.equal(q2.studentAnswer, '');
    assert.equal(q2.isAnswered, false);
  }
});

