import test from 'node:test';
import assert from 'node:assert/strict';

import {
  normalizeMastery,
} from '../services/c1MasteryAdapter.js';

test('sorts valid mastery scores from weakest to strongest', () => {
  const result = normalizeMastery({
    diagnosticCompleted: true,
    mastery: {
      Normalization: { score: 85 },
      SQL: { score: 35 },
      Transactions: { score: 60 },
    },
  });

  assert.equal(result.available, true);
  assert.deepEqual(
    result.topics.map((item) => item.topic),
    ['SQL', 'Transactions', 'Normalization']
  );
});

test('returns unavailable when diagnostic is incomplete', () => {
  const result = normalizeMastery({
    diagnosticCompleted: false,
    mastery: {},
  });

  assert.equal(result.available, false);
  assert.equal(result.reason, 'diagnostic_not_completed');
});

test('excludes invalid mastery scores', () => {
  const result = normalizeMastery({
    diagnosticCompleted: true,
    mastery: {
      Valid: { score: 40 },
      Negative: { score: -5 },
      TooHigh: { score: 110 },
      Text: { score: '30' },
      Missing: {},
    },
  });

  assert.deepEqual(result.topics, [
    { topic: 'Valid', masteryScore: 40 },
  ]);
});

test('rejects malformed mastery structure', () => {
  assert.throws(
    () => normalizeMastery({
      diagnosticCompleted: true,
      mastery: [],
    }),
    /Invalid C1 mastery structure/
  );
});

test('reports no valid mastery scores', () => {
  const result = normalizeMastery({
    diagnosticCompleted: true,
    mastery: {
      Invalid: { score: null },
    },
  });

  assert.equal(result.available, false);
  assert.equal(result.reason, 'no_valid_mastery_scores');
});