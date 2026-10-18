import test from 'node:test';
import assert from 'node:assert/strict';
import {
  listQuestionClassificationReviews,
  reviewQuestionClassification,
} from '../controllers/c2Controller.js';

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

test('listQuestionClassificationReviews rejects invalid page numbers', async () => {
  const req = {
    query: { page: '0', pageSize: '10' },
  };
  const res = mockRes();

  await listQuestionClassificationReviews(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'Invalid pagination parameters');
});

test('listQuestionClassificationReviews rejects invalid page sizes', async () => {
  const req = {
    query: { page: '1', pageSize: '101' },
  };
  const res = mockRes();

  await listQuestionClassificationReviews(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'Invalid pagination parameters');
});

test('listQuestionClassificationReviews rejects blank module key', async () => {
  const req = {
    query: { page: '1', pageSize: '10', moduleKey: '   ' },
  };
  const res = mockRes();

  await listQuestionClassificationReviews(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'Invalid module key');
});

test('reviewQuestionClassification requires valid parameters', async () => {
  const req = {
    params: { questionId: ' ' },
    body: {
      moduleKey: 'database_systems',
      topicId: 'indexing',
      decision: 'approved',
    },
    user: { sub: 'lecturer_123' },
  };
  const res = mockRes();

  await reviewQuestionClassification(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'Valid questionId, moduleKey and topicId are required');
});

test('reviewQuestionClassification requires notes for rejection', async () => {
  const req = {
    params: { questionId: 'IT3020-Q1' },
    body: {
      moduleKey: 'database_systems',
      topicId: 'indexing',
      decision: 'rejected',
      reviewNotes: '   ',
    },
    user: { sub: 'lecturer_123' },
  };
  const res = mockRes();

  await reviewQuestionClassification(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'Rejection requires review notes');
});

test('reviewQuestionClassification rejects invalid decision', async () => {
  const req = {
    params: { questionId: 'IT3020-Q1' },
    body: {
      moduleKey: 'database_systems',
      topicId: 'indexing',
      decision: 'pending',
    },
    user: { sub: 'lecturer_123' },
  };
  const res = mockRes();

  await reviewQuestionClassification(req, res);
  assert.equal(res.statusCode, 400);
  assert.equal(res.body.error, 'Decision must be approved or rejected');
});
