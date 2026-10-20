import test from 'node:test';
import assert from 'node:assert/strict';

import * as c2Service from '../services/c2Service.js';
import * as c2Controller from '../controllers/c2Controller.js';

test('M21 Bloom Question Generation Service Function Exports', () => {
  assert.equal(typeof c2Service.getGenerationTopics, 'function');
  assert.equal(typeof c2Service.generateBloomQuestion, 'function');
  assert.equal(typeof c2Service.submitBloomQuestionDecision, 'function');
  assert.equal(typeof c2Service.listApprovedGeneratedQuestions, 'function');
  assert.equal(typeof c2Service.getBloomClassifierEvaluation, 'function');
});

test('M21 Controller: getGenerationTopics validates moduleKey parameter', async () => {
  const req = { query: {} };
  let status = null;
  let json = null;
  const res = {
    status(code) {
      status = code;
      return this;
    },
    json(payload) {
      json = payload;
      return this;
    },
  };

  await c2Controller.getGenerationTopics(req, res);
  assert.equal(status, 400);
  assert.match(json.error, /moduleKey/i);
});

test('M21 Controller: generateBloomQuestion validates required parameters', async () => {
  const testCases = [
    { body: {}, expected: /moduleKey/i },
    { body: { moduleKey: 'database_systems' }, expected: /topicId/i },
    { body: { moduleKey: 'database_systems', topicId: 'normalization', marks: -5 }, expected: /marks/i },
    { body: { moduleKey: 'database_systems', topicId: 'normalization', marks: 'invalid' }, expected: /marks/i },
  ];

  for (const tc of testCases) {
    let status = null;
    let json = null;
    const res = {
      status(code) {
        status = code;
        return this;
      },
      json(payload) {
        json = payload;
        return this;
      },
    };

    await c2Controller.generateBloomQuestion({ body: tc.body }, res);
    assert.equal(status, 400);
    assert.match(json.error, tc.expected);
  }
});

test('M21 Controller: submitBloomQuestionDecision validates decision and rejection notes', async () => {
  let status = null;
  let json = null;
  const res = {
    status(code) {
      status = code;
      return this;
    },
    json(payload) {
      json = payload;
      return this;
    },
  };

  // Invalid decision
  await c2Controller.submitBloomQuestionDecision(
    { body: { decision: 'unknown_action' }, user: { sub: 'lecturer_1' } },
    res
  );
  assert.equal(status, 400);
  assert.match(json.error, /decision/i);

  // Missing question object
  await c2Controller.submitBloomQuestionDecision(
    { body: { decision: 'approved', question: null }, user: { sub: 'lecturer_1' } },
    res
  );
  assert.equal(status, 400);
  assert.match(json.error, /question/i);

  // Rejection requires notes
  await c2Controller.submitBloomQuestionDecision(
    {
      body: {
        decision: 'rejected',
        question: { question_id: 'GEN-SE3060-1234' },
        reviewNotes: '   ',
      },
      user: { sub: 'lecturer_1' },
    },
    res
  );
  assert.equal(status, 400);
  assert.match(json.error, /rejection requires review notes/i);
});
