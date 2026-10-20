import test from 'node:test';
import assert from 'node:assert/strict';
import * as controller from '../controllers/c2Controller.js';
import * as c2Service from '../services/c2Service.js';

function mockRes() {
  const res = {
    statusCode: 200,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      return this;
    },
  };
  return res;
}

test('M20.5 Service Function Exports Test Suite', async (t) => {
  await t.test('c2Service exports M20.5 review analytics function', () => {
    assert.equal(typeof c2Service.getQuestionClassificationReviewAnalytics, 'function');
  });

  await t.test('c2Service exports taxonomy review retrieval function', () => {
    assert.equal(typeof c2Service.getTaxonomyReview, 'function');
  });

  await t.test('c2Service exports taxonomy decision submission function', () => {
    assert.equal(typeof c2Service.submitTaxonomyDecision, 'function');
  });

  await t.test('c2Service exports authentic classification evaluation function', () => {
    assert.equal(typeof c2Service.getQuestionClassificationEvaluations, 'function');
  });
});

test('M20.5 Controller Validation Test Suite', async (t) => {
  await t.test('getTaxonomyReview validates moduleKey parameter', async () => {
    const req = { params: { moduleKey: '' } };
    const res = mockRes();
    await controller.getTaxonomyReview(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'Valid moduleKey is required');
  });

  await t.test('reviewTaxonomyDecision validates missing moduleKey', async () => {
    const req = {
      params: { moduleKey: '' },
      body: { decision: 'approved' },
      user: { sub: 'lecturer_123' },
    };
    const res = mockRes();
    await controller.reviewTaxonomyDecision(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'Valid moduleKey is required');
  });

  await t.test('reviewTaxonomyDecision validates invalid decision', async () => {
    const req = {
      params: { moduleKey: 'database_systems' },
      body: { decision: 'invalid_decision' },
      user: { sub: 'lecturer_123' },
    };
    const res = mockRes();
    await controller.reviewTaxonomyDecision(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'Decision must be approved or rejected');
  });

  await t.test('reviewQuestionClassification validates missing questionId', async () => {
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
    await controller.reviewQuestionClassification(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'Valid questionId, moduleKey and topicId are required');
  });

  await t.test('reviewQuestionClassification validates rejection requires notes', async () => {
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
    await controller.reviewQuestionClassification(req, res);
    assert.equal(res.statusCode, 400);
    assert.equal(res.body.error, 'Rejection requires review notes');
  });
});
