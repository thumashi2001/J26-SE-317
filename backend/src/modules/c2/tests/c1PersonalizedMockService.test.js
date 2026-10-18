
import test from 'node:test';
import assert from 'node:assert/strict';

import {
  selectWeakTopics,
  evaluatePersonalization,
  generateC1PersonalizedMock,
} from '../services/c1PersonalizedMockService.js';

// These are illustrative test fixtures, not approved
// production topic mappings.
const mapping = {
  modules: {
    database_systems: {
      SQL: 'sql_queries',
      Normalization: 'normalization',
      Transactions: 'transactions',
    },
  },
};

const approvedMappingResult = {
  valid: true,
  errors: [],
  mapping: mapping.modules.database_systems,
  mapped_count: 3,
  approved_topic_count: 3,
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

  assert.equal(
    result.status,
    'no_verified_questions'
  );
});

test('reports missing topic mapping', () => {
  const result = evaluatePersonalization(
    { questions: [] },
    []
  );

  assert.equal(
    result.status,
    'no_topic_mapping'
  );
});

test('integrates C1 mastery with C2 generation', async () => {
  let capturedPayload = null;

  const result = await generateC1PersonalizedMock({
    db: {},
    studentId: 'student_001',
    moduleKey: 'database_systems',
    mapping,

    // Simulates a successful validation result.
    // This does not approve the production taxonomy.
    getApprovedMapping: async () => approvedMappingResult,

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
          {
            question_id: 'Q1',
            topic_id: 'sql_queries',
          },
        ],
        personalization: {},
      };
    },
  });

  assert.deepEqual(
    capturedPayload.preferred_topics,
    ['sql_queries']
  );

  assert.equal(
    result.personalization.applied,
    true
  );

  assert.equal(
    result.personalization.status,
    'applied'
  );

  assert.equal(
    result.personalization.mapping_validation.valid,
    true
  );

  assert.equal(result.practice_only, true);
});

test('falls back when diagnostic is unavailable', async () => {
  let capturedPayload = null;

  const result = await generateC1PersonalizedMock({
    db: {},
    studentId: 'student_001',
    moduleKey: 'database_systems',
    mapping,

    getApprovedMapping: async () => approvedMappingResult,

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

  assert.equal(
    result.personalization.applied,
    false
  );

  assert.equal(
    result.personalization.status,
    'unavailable'
  );

  assert.equal(
    result.personalization.c1_diagnostic_integrated,
    false
  );
});

test('blocks personalization when mapping is unverified', async () => {
  let capturedPayload = null;

  const result = await generateC1PersonalizedMock({
    db: {},
    studentId: 'student_001',
    moduleKey: 'database_systems',
    mapping,

    getApprovedMapping: async () => ({
      valid: false,
      errors: [
        'C2 taxonomy is not verified: database_systems',
      ],
      mapping: {},
      mapped_count: 0,
      approved_topic_count: 0,
    }),

    getMastery: async () => ({
      available: true,
      topics: [
        { topic: 'SQL', masteryScore: 25 },
      ],
    }),

    generate: async (payload) => {
      capturedPayload = payload;

      return {
        status: 'partial',
        practice_only: true,
        questions: [
          {
            question_id: 'Q1',
            topic_id: null,
          },
        ],
        personalization: {},
      };
    },
  });

  assert.deepEqual(
    capturedPayload.preferred_topics,
    []
  );

  assert.equal(
    result.personalization.applied,
    false
  );

  assert.equal(
    result.personalization.status,
    'mapping_unverified'
  );

  assert.equal(
    result.personalization.mapping_validation.valid,
    false
  );

  assert.equal(
    result.personalization.matched_question_count,
    0
  );
});
