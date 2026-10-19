import test from 'node:test';
import assert from 'node:assert/strict';

import * as c2Service from '../services/c2Service.js';
import * as c2Controller from '../controllers/c2Controller.js';

test('generateSyntheticMockExam in c2Controller validates parameters', async () => {
  // Missing moduleKey
  const req1 = { body: {} };
  let status1 = null;
  let json1 = null;
  const res1 = {
    status: (code) => {
      status1 = code;
      return {
        json: (data) => {
          json1 = data;
        },
      };
    },
  };
  await c2Controller.generateSyntheticMockExam(req1, res1);
  assert.equal(status1, 400);
  assert(json1.error.includes('moduleKey'));

  // Invalid questionCount
  const req2 = { body: { moduleKey: 'software_architecture', questionCount: 0 } };
  let status2 = null;
  let json2 = null;
  const res2 = {
    status: (code) => {
      status2 = code;
      return {
        json: (data) => {
          json2 = data;
        },
      };
    },
  };
  await c2Controller.generateSyntheticMockExam(req2, res2);
  assert.equal(status2, 400);
  assert(json2.error.includes('questionCount'));
});

test('generateSyntheticMockExam forwards valid request to c2Service', async () => {
  const originalFetch = globalThis.fetch;
  process.env.C2_INTERNAL_TOKEN = 'test-token';

  try {
    globalThis.fetch = async (url, options) => {
      assert(url.endsWith('/mock-exams/synthetic'));
      assert.equal(options.method, 'POST');
      assert.equal(options.headers['X-C2-Internal-Token'], 'test-token');

      const body = JSON.parse(options.body);
      assert.equal(body.module_key, 'software_architecture');
      assert.equal(body.question_count, 5);
      assert.equal(body.seed, 42);

      return {
        ok: true,
        json: async () => ({
          paper_id: 'SYN-PRACTICE-SOFTWARE_ARCHITECTURE-1234',
          module_key: 'software_architecture',
          source_type: 'synthetic',
          verification_status: 'unverified',
          question_count: 5,
          total_marks: null,
          has_unassessed_marks: true,
          questions: [
            {
              question_id: 'SYN-M16-001',
              question_text: 'Synthetic question text',
              marks: null,
              source_type: 'synthetic',
            },
          ],
        }),
      };
    };

    const result = await c2Service.generateSyntheticMockExam({
      moduleKey: 'software_architecture',
      questionCount: 5,
      seed: 42,
    });

    assert.equal(result.module_key, 'software_architecture');
    assert.equal(result.source_type, 'synthetic');
    assert.equal(result.total_marks, null);
    assert.equal(result.has_unassessed_marks, true);
    assert.equal(result.questions.length, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
