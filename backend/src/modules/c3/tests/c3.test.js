import test from 'node:test';
import assert from 'node:assert';
import http from 'node:http';

process.env.AUTH_SECRET = 'test-secret-change-me';

import app from '../../../app.js';
import { signToken } from '../../../middleware/auth.js';

test('C3 Module Backend Integration', async (t) => {
  // 1. Setup Mock AI Server
  let aiRequests = [];
  let nextAiStatus = 200;
  let nextAiResponse = { status: 'mock_success' };
  
  const aiServer = http.createServer((req, res) => {
    let body = '';
    req.on('data', chunk => body += chunk.toString());
    req.on('end', () => {
      aiRequests.push({ path: req.url, body: JSON.parse(body || '{}') });
      res.writeHead(nextAiStatus, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(nextAiResponse));
    });
  });
  await new Promise(resolve => aiServer.listen(0, resolve));
  process.env.C3_AI_URL = `http://127.0.0.1:${aiServer.address().port}`;

  // 2. Setup Node App Server
  const server = http.createServer(app);
  await new Promise(resolve => server.listen(0, resolve));
  const port = server.address().port;
  const baseUrl = `http://127.0.0.1:${port}/api/v1/c3`;

  // Tokens
  const studentToken = signToken({ sub: 'student123', role: 'student' });
  const otherStudentToken = signToken({ sub: 'student456', role: 'student' });
  const lecturerToken = signToken({ sub: 'lecturer1', role: 'lecturer' });

  const fetchApi = async (path, token, body = {}) => {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body)
    });
    const data = await res.json().catch(() => null);
    return { status: res.status, data };
  };

  await t.test('unauthenticated request rejected', async () => {
    const res = await fetchApi('/analysis', null, { question_id: 'Q1' });
    assert.strictEqual(res.status, 401);
  });

  await t.test('authenticated request works and routes correctly', async () => {
    aiRequests = [];
    const res = await fetchApi('/analysis', studentToken, { question_id: 'Q1' });
    assert.strictEqual(res.status, 200);
    assert.deepStrictEqual(res.data, { status: 'mock_success' });
    assert.strictEqual(aiRequests.length, 1);
    assert.strictEqual(aiRequests[0].path, '/analysis/answer');
  });

  await t.test('student identity comes from req.user.sub', async () => {
    aiRequests = [];
    await fetchApi('/analysis', studentToken, { question_id: 'Q2' });
    assert.strictEqual(aiRequests[0].body.student_id, undefined);
  });

  await t.test('student cannot impersonate another student', async () => {
    const res = await fetchApi('/analysis', studentToken, { student_id: 'student456' });
    assert.strictEqual(res.status, 403);
    assert.strictEqual(res.data.error, 'You can only see your own data');
  });

  await t.test('lecturer authorization where applicable (can supply studentId)', async () => {
    aiRequests = [];
    const res = await fetchApi('/analysis', lecturerToken, { student_id: 'student456' });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(aiRequests[0].body.student_id, undefined);
  });
  
  await t.test('invalid request is rejected (lecturer missing student_id)', async () => {
    const res = await fetchApi('/analysis', lecturerToken, {});
    assert.strictEqual(res.status, 400);
    assert.strictEqual(res.data.error, 'studentId is required');
  });

  await t.test('Python service failure is handled (500)', async () => {
    nextAiStatus = 500;
    nextAiResponse = { detail: 'Internal Server Error' };
    const res = await fetchApi('/marking', studentToken, {});
    assert.strictEqual(res.status, 502);
    assert.ok(res.data.error.includes('C3 AI service returned 500'));
    nextAiStatus = 200; // reset
  });
  
  await t.test('Python service timeout/unreachable is handled', async () => {
    // temporarily change URL to an unreachable port
    const oldUrl = process.env.C3_AI_URL;
    process.env.C3_AI_URL = 'http://127.0.0.1:12345';
    const res = await fetchApi('/feedback', studentToken, {});
    assert.strictEqual(res.status, 502);
    assert.ok(res.data.error.includes('unreachable'));
    process.env.C3_AI_URL = oldUrl;
  });

  await t.test('all C3 endpoints including /assess are registered', async () => {
    aiRequests = [];
    nextAiResponse = { success: true };
    await fetchApi('/analysis', studentToken, {});
    await fetchApi('/marking', studentToken, {});
    await fetchApi('/feedback', studentToken, {});
    await fetchApi('/mindmap', studentToken, {});
    await fetchApi('/assess', studentToken, {});
    
    const paths = aiRequests.map(r => r.path);
    assert.deepStrictEqual(paths, [
      '/analysis/answer',
      '/marking/evaluate',
      '/feedback/generate',
      '/mindmap/generate',
      '/c3/assess'
    ]);
  });

  // Lecturer & Human-In-The-Loop Workflow Tests
  const { setDb } = await import('../../../config/db.js');
  const mockSubmissions = [];
  const mockResults = [];
  const mockLearningEvents = [];
  const testSubId = 'sub-test-1234567890123456';

  const mockDb = {
    collection(name) {
      if (name === 'c3_submissions') {
        return {
          async insertOne(doc) {
            const _id = doc._id || testSubId;
            const saved = { ...doc, _id };
            mockSubmissions.push(saved);
            return { insertedId: _id };
          },
          async findOne(q) {
            return mockSubmissions.find(s => {
              if (q._id && String(s._id) !== String(q._id) && !q.$or) return false;
              if (q.$or) {
                return q.$or.some(cond => cond._id && String(s._id) === String(cond._id));
              }
              return true;
            }) || null;
          },
          find(q = {}) {
            let res = mockSubmissions.filter(s => {
              if (q.student_id && s.student_id !== q.student_id) return false;
              if (q.status && s.status !== q.status) return false;
              return true;
            });
            return {
              sort() { return this; },
              limit() { return this; },
              async toArray() { return res; }
            };
          },
          async updateOne(q, u) {
            const item = mockSubmissions.find(s => {
              if (q._id && String(s._id) === String(q._id)) return true;
              return false;
            });
            if (item && u.$set) Object.assign(item, u.$set);
            return { matchedCount: item ? 1 : 0 };
          }
        };
      }
      if (name === 'c3_results') {
        return {
          async insertOne(doc) {
            const _id = doc._id || 'res-test-1234567890123456';
            const saved = { ...doc, _id };
            mockResults.push(saved);
            return { insertedId: _id };
          },
          async findOne(q) {
            return mockResults.find(r => {
              if (q._id && String(r._id) === String(q._id)) return true;
              if (q.submission_id && String(r.submission_id) === String(q.submission_id)) return true;
              if (q.$or) {
                return q.$or.some(cond => cond.submission_id && String(r.submission_id) === String(cond.submission_id));
              }
              return false;
            }) || null;
          },
          find(q = {}) {
            let res = mockResults;
            if (q.submission_id && q.submission_id.$in) {
              res = res.filter(r => q.submission_id.$in.includes(String(r.submission_id)));
            }
            return {
              async toArray() { return res; }
            };
          },
          async updateOne(q, u) {
            const item = mockResults.find(r => {
              if (q._id && String(r._id) === String(q._id)) return true;
              if (q.submission_id && String(r.submission_id) === String(q.submission_id)) return true;
              return false;
            });
            if (item && u.$set) Object.assign(item, u.$set);
            return { matchedCount: item ? 1 : 0 };
          }
        };
      }
      if (name === 'learning_events') {
        return {
          async insertOne(doc) {
            mockLearningEvents.push(doc);
            return { insertedId: 'event-c1-sync-123' };
          }
        };
      }
      return null;
    }
  };
  setDb(mockDb);

  // Seed one submission and result in mock DB
  mockSubmissions.push({
    _id: testSubId,
    student_id: 'student123',
    question_id: 'SE-ARCH-001',
    question_text: 'Explain Microservices',
    student_answer: 'Microservices architecture separates concerns.',
    status: 'pending_review',
    submitted_at: new Date(),
    updated_at: new Date()
  });
  mockResults.push({
    _id: 'res-test-1234567890123456',
    submission_id: testSubId,
    student_id: 'student123',
    question_id: 'SE-ARCH-001',
    automated_mark: 3,
    total_possible_marks: 4,
    percentage: 75.0,
    ai_evaluation: {
      question_id: 'SE-ARCH-001',
      total_awarded_marks: 3,
      total_possible_marks: 4,
      percentage: 75.0,
      marking: { total_awarded_marks: 3, total_possible_marks: 4 }
    },
    lecturer_decision: null,
    final_mark: null,
    override_reason: null,
    status: 'pending_review'
  });

  await t.test('student forbidden from lecturer review endpoints (403)', async () => {
    const res = await fetchApi(`/submissions/${testSubId}/review`, studentToken, { decision: 'accepted' });
    assert.strictEqual(res.status, 403);
    assert.strictEqual(res.data.error, 'You do not have access to this page');
  });

  await t.test('student forbidden from lecturer finalize endpoint (403)', async () => {
    const res = await fetchApi(`/submissions/${testSubId}/finalize`, studentToken, {});
    assert.strictEqual(res.status, 403);
    assert.strictEqual(res.data.error, 'You do not have access to this page');
  });

  await t.test('lecturer can list all submissions', async () => {
    const res = await fetch(`http://127.0.0.1:${port}/api/v1/c3/submissions`, {
      headers: { Authorization: `Bearer ${lecturerToken}` }
    });
    const body = await res.json();
    assert.strictEqual(res.status, 200);
    assert.ok(Array.isArray(body.submissions));
    assert.strictEqual(body.submissions.length, 1);
    assert.strictEqual(body.submissions[0].status, 'pending_review');
  });

  await t.test('lecturer override without reason is rejected (400)', async () => {
    const res = await fetchApi(`/submissions/${testSubId}/review`, lecturerToken, {
      decision: 'overridden',
      new_mark: 4,
      override_reason: ''
    });
    assert.strictEqual(res.status, 400);
    assert.ok(res.data.error.includes('override reason is required'));
  });

  await t.test('lecturer override with reason preserves original AI mark', async () => {
    const res = await fetchApi(`/submissions/${testSubId}/review`, lecturerToken, {
      decision: 'overridden',
      new_mark: 4,
      override_reason: 'Excellent understanding demonstrated in sentence 1'
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.data.result.decision, 'overridden');
    assert.strictEqual(res.data.result.automated_mark, 3); // Original AI mark preserved!
    assert.strictEqual(res.data.result.final_mark, 4);     // New Lecturer mark!
    assert.strictEqual(res.data.result.override_reason, 'Excellent understanding demonstrated in sentence 1');
    assert.strictEqual(res.data.result.status, 'reviewed');
  });

  await t.test('lecturer finalize transitions assessment to finalized', async () => {
    const res = await fetchApi(`/submissions/${testSubId}/finalize`, lecturerToken, {});
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.data.result.status, 'finalized');
    assert.strictEqual(res.data.result.automated_mark, 3);
    assert.strictEqual(res.data.result.final_mark, 4);
    assert.ok(res.data.result.finalized_at);
  });

  await t.test('scanned image / OCR upload endpoint explicitly rejects with 400', async () => {
    const res = await fetchApi('/upload-scanned', studentToken, { file: 'answer.png' });
    assert.strictEqual(res.status, 400);
    assert.ok(res.data.error.includes('OCR processing is currently unsupported'));
  });

  await t.test('assessAnswer with image/scanned document payload explicitly rejects with 400', async () => {
    const res = await fetchApi('/assess', studentToken, {
      question_id: 'Q1',
      question_text: 'Explain Normalization',
      image: 'data:image/png;base64,...',
      student_answer: ''
    });
    assert.strictEqual(res.status, 400);
    assert.ok(res.data.error.includes('OCR processing is currently unsupported'));
  });

  await t.test('C3 to C1 live integration bridge syncs learning event', async () => {
    mockLearningEvents.length = 0;
    const { syncC3AssessmentToC1 } = await import('../../../integration/c3-c1/index.js');
    const syncRes = await syncC3AssessmentToC1({
      studentId: 'student123',
      submissionId: testSubId,
      questionId: 'SE-ARCH-001',
      questionText: 'Explain Microservices',
      score: 4,
      totalPossible: 4,
      percentage: 100,
      conceptMatches: [{ concept: 'microservices', status: 'demonstrated' }],
      finalized: true
    });
    assert.strictEqual(syncRes.synced, true);
    assert.strictEqual(syncRes.topic, 'ds_cloud_microservices');
    assert.strictEqual(mockLearningEvents.length, 1);
    assert.strictEqual(mockLearningEvents[0].student_id, 'student123');
    assert.strictEqual(mockLearningEvents[0].type, 'c3_finalized_assessment');
    assert.strictEqual(mockLearningEvents[0].score, 4);
  });

  // Cleanup
  server.close();
  aiServer.close();
});
