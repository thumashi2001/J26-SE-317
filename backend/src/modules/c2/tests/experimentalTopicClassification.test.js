import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyTopicExperimental } from '../controllers/c2Controller.js';
import * as c2Service from '../services/c2Service.js';

function mockRes() {
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
  return res;
}

test('classifyTopicExperimental rejects missing moduleKey', async () => {
  const req = {
    body: { questionText: 'Explain database indexing.' },
    user: { sub: 'lecturer_123', role: 'lecturer' },
  };
  const res = mockRes();

  await classifyTopicExperimental(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'A valid moduleKey is required');
});

test('classifyTopicExperimental rejects blank moduleKey', async () => {
  const req = {
    body: { moduleKey: '   ', questionText: 'Explain database indexing.' },
    user: { sub: 'lecturer_123', role: 'lecturer' },
  };
  const res = mockRes();

  await classifyTopicExperimental(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'A valid moduleKey is required');
});

test('classifyTopicExperimental rejects missing questionText', async () => {
  const req = {
    body: { moduleKey: 'database_systems' },
    user: { sub: 'lecturer_123', role: 'lecturer' },
  };
  const res = mockRes();

  await classifyTopicExperimental(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'questionText must be a non-empty string');
});

test('classifyTopicExperimental rejects blank questionText', async () => {
  const req = {
    body: { moduleKey: 'database_systems', questionText: '  \n  ' },
    user: { sub: 'lecturer_123', role: 'lecturer' },
  };
  const res = mockRes();

  await classifyTopicExperimental(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'questionText must be a non-empty string');
});

test('classifyTopicExperimental rejects overlong questionText', async () => {
  const req = {
    body: {
      moduleKey: 'database_systems',
      questionText: 'A'.repeat(10001),
    },
    user: { sub: 'lecturer_123', role: 'lecturer' },
  };
  const res = mockRes();

  await classifyTopicExperimental(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'questionText must be 10000 characters or fewer');
});

test('classifyTopicExperimental rejects invalid abstentionThreshold', async () => {
  const req = {
    body: {
      moduleKey: 'database_systems',
      questionText: 'Explain database indexing.',
      abstentionThreshold: 'invalid_number',
    },
    user: { sub: 'lecturer_123', role: 'lecturer' },
  };
  const res = mockRes();

  await classifyTopicExperimental(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'abstentionThreshold must be a number between 0 and 10');
});

test('classifyTopicExperimental forwards valid request and returns result', async () => {
  const originalFetch = globalThis.fetch;

  const mockPrediction = {
    module_key: 'database_systems',
    question_text: 'Explain B-tree clustered index scans.',
    predicted_topic: 'Database Indexing',
    provisional_topic_id: 'provisional_database_indexing',
    confidence_score: 0.42,
    score_type: 'calibrated_probability',
    decision: 'classified',
    abstention_threshold: 0.38,
    abstained: false,
    model_type: 'logistic_regression',
    verification_status: 'unverified',
    academic_verification: 'pending_lecturer_review',
    source_type: 'synthetic_model_inference',
  };

  process.env.C2_INTERNAL_TOKEN = 'test-token';

  globalThis.fetch = async (url, options) => {
    assert(url.includes('/api/v1/experimental/classify-topic'));
    assert.equal(options.method, 'POST');
    assert.equal(options.headers['X-C2-Internal-Token'], 'test-token');
    const body = JSON.parse(options.body);
    assert.equal(body.module_key, 'database_systems');
    assert.equal(body.question_text, 'Explain B-tree clustered index scans.');
    assert.equal(body.abstention_threshold, 0.38);

    return {
      ok: true,
      status: 200,
      json: async () => mockPrediction,
    };
  };

  try {
    const req = {
      body: {
        moduleKey: 'database_systems',
        questionText: 'Explain B-tree clustered index scans.',
        abstentionThreshold: 0.38,
      },
      user: { sub: 'lecturer_123', role: 'lecturer' },
    };
    const res = mockRes();

    await classifyTopicExperimental(req, res);
    assert.equal(res.statusCode, 200);
    assert.deepEqual(res.body, mockPrediction);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('classifyTopicExperimental handles upstream 503 model unavailable', async () => {
  const originalFetch = globalThis.fetch;
  process.env.C2_INTERNAL_TOKEN = 'test-token';

  globalThis.fetch = async () => {
    return {
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Topic classification model not available' }),
    };
  };

  try {
    const req = {
      body: {
        moduleKey: 'database_systems',
        questionText: 'Explain B-tree clustered index scans.',
      },
      user: { sub: 'lecturer_123', role: 'lecturer' },
    };
    const res = mockRes();

    await classifyTopicExperimental(req, res);
    assert.equal(res.statusCode, 503);
    assert.equal(res.body.error, 'Topic classification model not available');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('classifyTopicExperimental handles upstream network/timeout failure gracefully', async () => {
  const originalFetch = globalThis.fetch;
  process.env.C2_INTERNAL_TOKEN = 'test-token';

  globalThis.fetch = async () => {
    throw new Error('connect ECONNREFUSED 127.0.0.1:8002');
  };

  try {
    const req = {
      body: {
        moduleKey: 'database_systems',
        questionText: 'Explain B-tree clustered index scans.',
      },
      user: { sub: 'lecturer_123', role: 'lecturer' },
    };
    const res = mockRes();

    await classifyTopicExperimental(req, res);
    assert.equal(res.statusCode, 503);
    assert.equal(res.body.error, 'C2 Python service is unavailable');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

