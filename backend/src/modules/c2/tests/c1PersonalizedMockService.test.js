import test from 'node:test';
import assert from 'node:assert/strict';

import {
  selectWeakTopics,
  evaluatePersonalization,
  generateC1PersonalizedMock,
} from '../services/c1PersonalizedMockService.js';

const mapping = {
  modules: {
    database_systems: {
      SQL: 'sql_queries',
      Normalization: 'normalization',
      Transactions: 'transactions',
    },
  },
};

test('maps only weak C1 topics', () => {
  const result = selectWeakTopics(
    {
      topics: [
        { topic: 'SQL', masteryScore: 35 },
        { topic: 'Transactions', masteryScore: 55 },
        { topic: 'Normalization', masteryScore: 85 },
      ],
    },
    'database_systems',
    mapping
  );

  assert.deepEqual(
    result.map((item) => item.c2TopicId),
    ['sql_queries', 'transactions']
  );
});

test('ignores topics without explicit mappings', () => {
  const result = selectWeakTopics(
    {
      topics: [
        { topic: 'Unknown Topic', masteryScore: 10 },
      ],
    },
    'database_systems',
    mapping
  );

  assert.deepEqual(result, []);
});

test('detects applied personalization', () => {
  const result = evaluatePersonalization(
    {
      questions: [
        { topic_id: 'sql_queries' },
        { topic_id: null },
      ],
    },
    ['sql_queries']
  );

  assert.equal(result.status, 'applied');
  assert.equal(result.matchedQuestionCount, 1);
});

test('detects unavailable verified questions', () => {
  const result = evaluatePersonalization(
    {
      questions: [
        { topic_id: null },
      ],
    },
    ['sql_queries']
  );

  assert.equal(result.status, 'no_verified_questions');
});

test('reports missing topic mapping', () => {
  const result = evaluatePersonalization(
    { questions: [] },
    []
  );

  assert.equal(result.status, 'no_topic_mapping');
});

test('integrates C1 mastery with C2 generation', async () => {
  let capturedPayload = null;

  const result = await generateC1PersonalizedMock({
    db: {},
    studentId: 'student_001',
    moduleKey: 'database_systems',
    mapping,
    getMastery: async () => ({
      available: true,
      topics: [
        { topic: 'SQL', masteryScore: 35 },
        { topic: 'Normalization', masteryScore: 85 },
      ],
    }),
    generate: async (payload) => {
      capturedPayload = payload;

      return {
        status: 'partial',
        practice_only: true,
        questions: [
          { question_id: 'Q1', topic_id: 'sql_queries' },
        ],
        personalization: {},
      };
    },
  });

  assert.deepEqual(
    capturedPayload.preferred_topics,
    ['sql_queries']
  );

  assert.equal(result.personalization.applied, true);
  assert.equal(result.personalization.status, 'applied');
  assert.equal(result.practice_only, true);
});

test('falls back when diagnostic is unavailable', async () => {
  let capturedPayload = null;

  const result = await generateC1PersonalizedMock({
    db: {},
    studentId: 'student_001',
    moduleKey: 'database_systems',
    mapping,
    getMastery: async () => ({
      available: false,
      reason: 'diagnostic_not_completed',
      topics: [],
    }),
    generate: async (payload) => {
      capturedPayload = payload;

      return {
        status: 'partial',
        practice_only: true,
        questions: [],
        personalization: {},
      };
    },
  });

  assert.deepEqual(
    capturedPayload.preferred_topics,
    []
  );

  assert.equal(result.personalization.applied, false);
  assert.equal(result.personalization.status, 'unavailable');
});