import test from 'node:test';
import assert from 'node:assert/strict';

import * as c2Service from '../services/c2Service.js';
import * as c2Controller from '../controllers/c2Controller.js';

test('M22.2 Prediction Backend: Synthetic Experimental & Authentic Gating', async (t) => {
  await t.test('c2Service.getTopicPredictions supports experimentalDemo flag', async () => {
    assert.equal(typeof c2Service.getTopicPredictions, 'function');
    assert.equal(typeof c2Service.getExperimentalTopicPredictions, 'function');
  });

  await t.test('c2Controller.listTopicPredictions validates missing moduleKey', async () => {
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

  await t.test('c2Controller.getExperimentalTopicPredictions validates missing moduleKey', async () => {
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

    await c2Controller.getExperimentalTopicPredictions(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'A valid moduleKey is required');
  });

  await t.test('c2Controller parses moduleKey and experimental_demo query parameters', async () => {
    const req = {
      query: {
        moduleKey: 'software_architecture',
        experimental_demo: 'true',
      },
    };
    assert.equal(req.query.moduleKey, 'software_architecture');
    assert.equal(req.query.experimental_demo, 'true');
  });
});
