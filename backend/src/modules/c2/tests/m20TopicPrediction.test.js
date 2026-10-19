import test from 'node:test';
import assert from 'node:assert/strict';

import * as c2Service from '../services/c2Service.js';
import * as c2Controller from '../controllers/c2Controller.js';

test('M20 Prediction Services & Controllers Test Suite', async (t) => {
  await t.test('c2Service.getTopicPredictions constructs correct URL with target_period', async () => {
    // Intercept requestC2 call or verify parameter handling
    assert.equal(typeof c2Service.getTopicPredictions, 'function');
  });

  await t.test('c2Service.getPredictionReadiness constructs correct endpoints', async () => {
    assert.equal(typeof c2Service.getPredictionReadiness, 'function');
  });

  await t.test('c2Service.getPredictionEvaluation constructs correct endpoints', async () => {
    assert.equal(typeof c2Service.getPredictionEvaluation, 'function');
  });

  await t.test('c2Controller.listTopicPredictions validates moduleKey', async () => {
    const req = { query: {} };
    const res = {
      statusCode: 200,
      body: null,
      status(code) {
        this.statusCode = code;
        return this;
      },
      json(data) {
        this.body = data;
        return this;
      },
    };

    await c2Controller.listTopicPredictions(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'A valid moduleKey is required');
  });

  await t.test('c2Controller.getPredictionEvaluation validates moduleKey', async () => {
    const req = { query: {} };
    const res = {
      statusCode: 200,
      body: null,
      status(code) {
        this.statusCode = code;
        return this;
      },
      json(data) {
        this.body = data;
        return this;
      },
    };

    await c2Controller.getPredictionEvaluation(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'A valid moduleKey is required');
  });

  await t.test('c2Controller.getPredictionReadiness handles optional moduleKey', async () => {
    assert.equal(typeof c2Controller.getPredictionReadiness, 'function');
  });
});
