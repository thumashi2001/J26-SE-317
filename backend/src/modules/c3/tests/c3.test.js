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
    assert.strictEqual(aiRequests[0].body.question_id, 'Q2', 'other fields must be forwarded unchanged');
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

  await t.test('Python 5xx is surfaced to the client as 502 Bad Gateway', async () => {
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
    await fetchApi('/assess', lecturerToken, { student_id: 'student123' });
    
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
  const mockBatchSetups = [];
  const testSubId = 'sub-test-1234567890123456';

  const mockDb = {
    collection(name) {
      if (name === 'c3_batch_setups') {
        return {
          async insertOne(doc) {
            const _id = doc._id || ('batch-test-' + Date.now() + '-' + Math.random().toString(36).slice(2));
            const saved = { ...doc, _id };
            mockBatchSetups.push(saved);
            return { insertedId: _id };
          },
          async findOne(q) {
            return mockBatchSetups.find(b => {
              if (q._id && String(b._id) === String(q._id)) return true;
              if (q.batch_id && String(b.batch_id) === String(q.batch_id)) return true;
              if (q.$or) {
                return q.$or.some(c => (c._id && String(b._id) === String(c._id)) || (c.batch_id && String(b.batch_id) === String(c.batch_id)));
              }
              return false;
            }) || null;
          },
          find(q = {}) {
            let res = mockBatchSetups.filter(b => {
              if (q.created_by && b.created_by !== q.created_by) return false;
              return true;
            });
            return {
              sort() { return this; },
              limit() { return this; },
              async toArray() { return res; }
            };
          }
        };
      }
      if (name === 'c3_submissions') {
        return {
          async insertOne(doc) {
            const _id = doc._id || ('sub-test-' + Date.now() + '-' + Math.random().toString(36).slice(2));
            const saved = { ...doc, _id };
            mockSubmissions.push(saved);
            return { insertedId: _id };
          },
          async findOne(q) {
            return mockSubmissions.find(s => {
              if (q.student_id && s.student_id !== q.student_id) return false;
              if (q.batch_id && s.batch_id !== q.batch_id) return false;
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
              if (q.batch_id) {
                if (q.batch_id.$in) {
                  if (!q.batch_id.$in.includes(s.batch_id)) return false;
                } else if (s.batch_id !== q.batch_id) {
                  return false;
                }
              }
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
            const _id = doc._id || ('res-test-' + Date.now() + '-' + Math.random().toString(36).slice(2));
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
            if (q.batch_id) {
              res = res.filter(r => r.batch_id === q.batch_id);
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
          },
          async findOne(q) {
            return mockLearningEvents.find(e => {
              if (q.submission_id && String(e.submission_id) !== String(q.submission_id)) return false;
              if (q.student_id && e.student_id !== q.student_id) return false;
              return true;
            }) || null;
          },
          async findOneAndUpdate(q, u, opts) {
            let item = mockLearningEvents.find(e => {
              if (q.submission_id && String(e.submission_id) === String(q.submission_id)) return true;
              return false;
            });
            if (!item && opts && opts.upsert) {
              item = {
                _id: 'event-c1-sync-' + (mockLearningEvents.length + 1),
                ...(u.$setOnInsert || {}),
                ...(u.$set || {}),
              };
              mockLearningEvents.push(item);
              return { value: item };
            }
            if (item && u.$set) {
              Object.assign(item, u.$set);
            }
            return { value: item };
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
    const seeded = body.submissions.find((sub) => String(sub._id) === String(testSubId));
    assert.ok(seeded, 'seeded submission must be listed');
    assert.strictEqual(seeded.status, 'pending_review');
  });

  await t.test('another student cannot read a submission they do not own', async () => {
    const res = await fetch(`http://127.0.0.1:${port}/api/v1/c3/submissions/${testSubId}`, {
      headers: { Authorization: `Bearer ${otherStudentToken}` }
    });
    assert.ok([403, 404].includes(res.status), `expected 403/404, got ${res.status}`);
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

  await t.test('C3 to C1 live integration bridge syncs provisional learning event', async () => {
    mockLearningEvents.length = 0;
    const { syncC3AssessmentToC1 } = await import('../../../integration/c3-c1/index.js');
    const syncRes = await syncC3AssessmentToC1({
      studentId: 'student123',
      submissionId: testSubId,
      questionId: 'SE-ARCH-001',
      questionText: 'Explain Microservices',
      score: 3,
      totalPossible: 4,
      percentage: 75,
      conceptMatches: [{ concept: 'microservices', status: 'demonstrated' }],
      finalized: false
    });
    assert.strictEqual(syncRes.synced, true);
    assert.strictEqual(syncRes.topic, 'ds_cloud_microservices');
    assert.strictEqual(syncRes.lifecycle_stage, 'provisional');
    assert.strictEqual(mockLearningEvents.length, 1);
    assert.strictEqual(mockLearningEvents[0].student_id, 'student123');
    assert.strictEqual(mockLearningEvents[0].type, 'c3_automated_assessment');
    assert.strictEqual(mockLearningEvents[0].lifecycle_stage, 'provisional');
    assert.strictEqual(mockLearningEvents[0].provisional_score, 3);
    assert.strictEqual(mockLearningEvents[0].final_score, null);
  });

  await t.test('repeated provisional sync calls update in-place without duplicate events (idempotency)', async () => {
    const { syncC3AssessmentToC1 } = await import('../../../integration/c3-c1/index.js');
    const syncRes2 = await syncC3AssessmentToC1({
      studentId: 'student123',
      submissionId: testSubId,
      questionId: 'SE-ARCH-001',
      questionText: 'Explain Microservices',
      score: 3,
      totalPossible: 4,
      percentage: 75,
      conceptMatches: [{ concept: 'microservices', status: 'demonstrated' }],
      finalized: false
    });
    assert.strictEqual(syncRes2.synced, true);
    // Crucial check: still exactly 1 event!
    assert.strictEqual(mockLearningEvents.length, 1);
  });

  await t.test('finalization transitions event to finalized preserving provisional_score and authoritative final_score', async () => {
    const { syncC3AssessmentToC1 } = await import('../../../integration/c3-c1/index.js');
    const finalizeRes = await syncC3AssessmentToC1({
      studentId: 'student123',
      submissionId: testSubId,
      questionId: 'SE-ARCH-001',
      questionText: 'Explain Microservices',
      score: 4,
      totalPossible: 4,
      percentage: 100,
      conceptMatches: [{ concept: 'microservices', status: 'demonstrated' }],
      finalized: true,
      lecturerDecision: 'overridden',
      overrideReason: 'Full credit for clear architectural explanation',
      reviewedBy: 'lecturer1'
    });
    assert.strictEqual(finalizeRes.synced, true);
    assert.strictEqual(finalizeRes.lifecycle_stage, 'finalized');
    // Exactly 1 event, not 2!
    assert.strictEqual(mockLearningEvents.length, 1);
    const ev = mockLearningEvents[0];
    assert.strictEqual(ev.type, 'c3_finalized_assessment');
    assert.strictEqual(ev.lifecycle_stage, 'finalized');
    assert.strictEqual(ev.provisional_score, 3); // Original AI proposed mark preserved!
    assert.strictEqual(ev.final_score, 4);       // Authoritative lecturer mark stored!
    assert.strictEqual(ev.score, 4);             // Consumer score updated!
    assert.strictEqual(ev.lecturer_decision, 'overridden');
    assert.strictEqual(ev.override_reason, 'Full credit for clear architectural explanation');
    assert.strictEqual(ev.reviewed_by, 'lecturer1');
    assert.ok(ev.finalized_at);
  });

  await t.test('repeated finalization calls do not duplicate learning events', async () => {
    const { syncC3AssessmentToC1 } = await import('../../../integration/c3-c1/index.js');
    const resync = await syncC3AssessmentToC1({
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
    assert.strictEqual(resync.synced, true);
    assert.strictEqual(mockLearningEvents.length, 1);
  });

  // =========================================================================
  // Phase 2: MCQ Marking Engine Test Suite
  // =========================================================================

  const standardMcqPayload = {
    question_id: 'MCQ-TEST-01',
    question_text: 'Which architectural style emphasizes loose coupling across independent services?',
    answer_type: 'mcq',
    max_marks: 2,
    correct_answer: 'B',
    options: [
      { option_id: 'A', label: 'A', text: 'Monolith' },
      { option_id: 'B', label: 'B', text: 'Microservices' },
      { option_id: 'C', label: 'C', text: 'Pipe & Filter' },
      { option_id: 'D', label: 'D', text: 'MVC' }
    ]
  };

  await t.test('MCQ: correct answer awards full marks (2/2, 100%)', async () => {
    const res = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      selected_option_id: 'B'
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.data.is_correct, true);
    assert.strictEqual(res.data.total_awarded_marks, 2);
    assert.strictEqual(res.data.total_possible_marks, 2);
    assert.strictEqual(res.data.percentage, 100);
    assert.strictEqual(res.data.marking.marking_version, 'mcq-deterministic-v1');
    assert.strictEqual(res.data.marking.criteria_results[0].selected_level_id, 'MCQ-CORRECT');
  });

  await t.test('MCQ: incorrect answer awards zero marks (0/2, 0%)', async () => {
    const res = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      selected_option_id: 'A'
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.data.is_correct, false);
    assert.strictEqual(res.data.total_awarded_marks, 0);
    assert.strictEqual(res.data.percentage, 0);
    assert.strictEqual(res.data.marking.criteria_results[0].selected_level_id, 'MCQ-INCORRECT');
  });

  await t.test('MCQ: unanswered question awards zero marks safely without crashing', async () => {
    const res = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      selected_option_id: null
    });
    assert.strictEqual(res.status, 200);
    assert.strictEqual(res.data.is_correct, false);
    assert.strictEqual(res.data.is_unanswered, true);
    assert.strictEqual(res.data.total_awarded_marks, 0);
    assert.strictEqual(res.data.marking.criteria_results[0].selected_level_id, 'MCQ-UNANSWERED');
  });

  await t.test('MCQ: invalid option ID is rejected with 400', async () => {
    const res = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      selected_option_id: 'Z'
    });
    assert.strictEqual(res.status, 400);
    assert.ok(res.data.error.includes("not a valid option"));
  });

  await t.test('MCQ: missing question_id or text is rejected with 400', async () => {
    const res1 = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      question_id: ''
    });
    assert.strictEqual(res1.status, 400);
    assert.ok(res1.data.error.includes('question_id is required'));

    const res2 = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      question_text: ''
    });
    assert.strictEqual(res2.status, 400);
    assert.ok(res2.data.error.includes('question_text is required'));
  });

  await t.test('MCQ: missing answer key is rejected with 400', async () => {
    const res = await fetchApi('/marking', studentToken, {
      question_id: 'MCQ-NO-KEY',
      question_text: 'Which is valid?',
      answer_type: 'mcq',
      options: ['Option 1', 'Option 2']
    });
    assert.strictEqual(res.status, 400);
    assert.ok(res.data.error.includes('Authoritative answer key is missing'));
  });

  await t.test('MCQ: duplicate option IDs are rejected with 400', async () => {
    const res = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      options: [
        { option_id: 'A', text: 'Option A1' },
        { option_id: 'A', text: 'Option A2' }
      ]
    });
    assert.strictEqual(res.status, 400);
    assert.ok(res.data.error.includes('Duplicate option ID'));
  });

  await t.test('MCQ: option ID versus displayed-label mapping resolves correctly', async () => {
    const customOptionsPayload = {
      question_id: 'MCQ-LABELS-01',
      question_text: 'Identify the pattern',
      answer_type: 'mcq',
      max_marks: 3,
      correct_answer: 'opt_micro',
      options: [
        { option_id: 'opt_mono', label: '1', text: 'Monolith' },
        { option_id: 'opt_micro', label: '2', text: 'Microservices' },
        { option_id: 'opt_event', label: '3', text: 'Event-driven' }
      ]
    };

    // Submitting by label "2" should resolve to opt_micro and award full marks
    const resByLabel = await fetchApi('/marking', studentToken, {
      ...customOptionsPayload,
      selected_option_id: '2'
    });
    assert.strictEqual(resByLabel.status, 200);
    assert.strictEqual(resByLabel.data.is_correct, true);
    assert.strictEqual(resByLabel.data.total_awarded_marks, 3);

    // Submitting by text "Microservices" should also resolve correctly
    const resByText = await fetchApi('/marking', studentToken, {
      ...customOptionsPayload,
      selected_option_id: 'Microservices'
    });
    assert.strictEqual(resByText.status, 200);
    assert.strictEqual(resByText.data.is_correct, true);
    assert.strictEqual(resByText.data.total_awarded_marks, 3);
  });

  await t.test('MCQ: valid and invalid mark ranges are validated strictly', async () => {
    const resInvalid = await fetchApi('/marking', studentToken, {
      ...standardMcqPayload,
      max_marks: -5,
      selected_option_id: 'B'
    });
    assert.strictEqual(resInvalid.status, 400);
    assert.ok(resInvalid.data.error.includes('max_marks must be a positive number'));
  });

  await t.test('MCQ: multi-select behaviour awards full marks only when all correct options are selected', async () => {
    const multiPayload = {
      question_id: 'MCQ-MULTI-01',
      question_text: 'Select all microservice benefits (Select all that apply)',
      answer_type: 'mcq',
      max_marks: 4,
      correct_options: ['B', 'C'],
      options: [
        { option_id: 'A', text: 'Shared database required' },
        { option_id: 'B', text: 'Independent scalability' },
        { option_id: 'C', text: 'Decoupled deployments' },
        { option_id: 'D', text: 'Single point of failure' }
      ]
    };

    // 1. Fully correct
    const resFull = await fetchApi('/marking', studentToken, {
      ...multiPayload,
      selected_options: ['B', 'C']
    });
    assert.strictEqual(resFull.status, 200);
    assert.strictEqual(resFull.data.is_correct, true);
    assert.strictEqual(resFull.data.total_awarded_marks, 4);

    // 2. Partial / incomplete -> 0 marks
    const resPartial = await fetchApi('/marking', studentToken, {
      ...multiPayload,
      selected_options: ['B']
    });
    assert.strictEqual(resPartial.status, 200);
    assert.strictEqual(resPartial.data.is_correct, false);
    assert.strictEqual(resPartial.data.total_awarded_marks, 0);

    // 3. Extra wrong option -> 0 marks
    const resWrong = await fetchApi('/marking', studentToken, {
      ...multiPayload,
      selected_options: ['B', 'C', 'A']
    });
    assert.strictEqual(resWrong.status, 200);
    assert.strictEqual(resWrong.data.is_correct, false);
    assert.strictEqual(resWrong.data.total_awarded_marks, 0);
  });

  await t.test('MCQ: assessAnswer persists into c3_submissions & allows lecturer review & override', async () => {
    // Lecturer-supplied configuration for a named student (students cannot supply an answer key).
    const resAssess = await fetchApi('/assess', lecturerToken, {
      ...standardMcqPayload,
      student_id: 'student123',
      selected_option_id: 'B'
    });
    assert.strictEqual(resAssess.status, 200);
    assert.strictEqual(resAssess.data.is_correct, true);
    assert.strictEqual(resAssess.data.total_awarded_marks, 2);
    assert.strictEqual(resAssess.data.status, 'pending_review');
    const subId = resAssess.data.submission_id;
    assert.ok(subId);

    // Verify submission is in mock submissions
    const savedSub = mockSubmissions.find((s) => String(s._id) === String(subId));
    assert.ok(savedSub);
    assert.strictEqual(savedSub.answer_type, 'mcq');
    assert.strictEqual(savedSub.status, 'pending_review');

    // Lecturer overrides mark from 2 to 1.5 with mandatory reason
    const resOverride = await fetchApi(`/submissions/${subId}/review`, lecturerToken, {
      decision: 'overridden',
      new_mark: 1.5,
      override_reason: 'Partial credit for late submission adjustment'
    });
    assert.strictEqual(resOverride.status, 200);
    assert.strictEqual(resOverride.data.result.automated_mark, 2);
    assert.strictEqual(resOverride.data.result.final_mark, 1.5);
    assert.strictEqual(resOverride.data.result.decision, 'overridden');

    // Lecturer finalizes the result
    const resFinalize = await fetchApi(`/submissions/${subId}/finalize`, lecturerToken, {});
    assert.strictEqual(resFinalize.status, 200);
    assert.strictEqual(resFinalize.data.result.status, 'finalized');
    assert.strictEqual(resFinalize.data.result.final_mark, 1.5);
  });

  // =========================================================================
  // Batch Marking Workflow Tests (Lecturer configure once, cohort mark)
  // =========================================================================

  await t.test('Batch Marking: unauthorized student rejected from batch endpoints', async () => {
    const resSetup = await fetchApi('/batch/setup', studentToken, { title: 'Test' });
    assert.strictEqual(resSetup.status, 403);

    const resMark = await fetchApi('/batch/mark', studentToken, { setup_id: 'b1', items: [] });
    assert.strictEqual(resMark.status, 403);

    const resFinalize = await fetchApi('/batch/b1/finalize-all', studentToken, {});
    assert.strictEqual(resFinalize.status, 403);
  });

  await t.test('Batch Marking: validate setup data rejects invalid max marks or criteria sum mismatch', async () => {
    // Mismatched criteria sum (sum is 2, but max_marks is 4)
    const resMismatch = await fetchApi('/batch/setup', lecturerToken, {
      title: 'Architecture Assessment',
      question_id: 'SE-BATCH-ERR-01',
      question_text: 'Explain microservices architecture.',
      answer_type: 'short',
      max_marks: 4,
      rubric: {
        criteria: [
          { criterion_id: 'C1', description: 'Cohesion', max_marks: 2, scoring_levels: [{ mark: 0 }, { mark: 2 }] }
        ]
      }
    });
    assert.strictEqual(resMismatch.status, 400);
    assert.ok(resMismatch.data.error.includes('must equal the assessment max marks'));

    // Missing criteria
    const resMissingCriteria = await fetchApi('/batch/setup', lecturerToken, {
      title: 'Architecture Assessment',
      question_id: 'SE-BATCH-ERR-02',
      question_text: 'Explain microservices architecture.',
      answer_type: 'short',
      max_marks: 4,
      rubric: { criteria: [] }
    });
    assert.strictEqual(resMissingCriteria.status, 400);
    assert.ok(resMissingCriteria.data.error.includes('at least one evaluation criterion'));
  });

  let savedBatchId = null;

  await t.test('Batch Marking: lecturer creates subjective question & rubric setup once', async () => {
    const resSetup = await fetchApi('/batch/setup', lecturerToken, {
      title: 'Modular Architecture Assessment',
      module_id: 'SE3010',
      question_id: 'SE3010-BATCH-01',
      question_text: 'Explain high cohesion and loose coupling with architectural patterns.',
      answer_type: 'short',
      max_marks: 4,
      reference_answer: 'High cohesion ensures single responsibility; loose coupling minimizes dependencies.',
      expected_concepts: ['high cohesion', 'loose coupling', 'microservices'],
      rubric: {
        title: 'Modularity Rubric',
        criteria: [
          { criterion_id: 'C1', description: 'Cohesion', max_marks: 2, scoring_levels: [{ mark: 0 }, { mark: 2 }] },
          { criterion_id: 'C2', description: 'Coupling', max_marks: 2, scoring_levels: [{ mark: 0 }, { mark: 2 }] }
        ]
      }
    });
    assert.strictEqual(resSetup.status, 200);
    assert.ok(resSetup.data.batch_id);
    assert.strictEqual(resSetup.data.max_marks, 4);
    assert.strictEqual(resSetup.data.rubric.criteria.length, 2);

    savedBatchId = resSetup.data.batch_id;

    // Verify it is listed in listBatchSetups
    const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${lecturerToken}` };
    const resList = await fetch(`${baseUrl}/batch/setup`, { headers });
    const listData = await resList.json();
    assert.strictEqual(resList.status, 200);
    const found = listData.setups.find((s) => s.batch_id === savedBatchId);
    assert.ok(found);
  });

  await t.test('Batch Marking: validate batch answers identifies valid, invalid, duplicate, and empty rows', async () => {
    const resValidate = await fetchApi('/batch/validate', lecturerToken, {
      setup_id: savedBatchId,
      items: [
        { student_id: 'IT21001001', student_answer: 'High cohesion and loose coupling are key.' },
        { student_id: 'IT21001001', student_answer: 'Duplicate submission attempt.' }, // duplicate
        { student_id: 'IT21001002', student_answer: '' }, // empty answer
        { student_id: 'IT21001003', student_answer: 'Loose coupling is achieved using microservices.' } // valid
      ]
    });
    assert.strictEqual(resValidate.status, 200);
    assert.strictEqual(resValidate.data.total_rows, 4);
    assert.strictEqual(resValidate.data.valid_count, 2);
    assert.strictEqual(resValidate.data.invalid_count, 2);
    assert.strictEqual(resValidate.data.valid_items.length, 2);
    assert.strictEqual(resValidate.data.valid_items[0].student_id, 'IT21001001');
    assert.strictEqual(resValidate.data.valid_items[1].student_id, 'IT21001003');
  });

  await t.test('Batch Marking: automated batch marking marks all valid students against shared setup', async () => {
    nextAiStatus = 200;
    nextAiResponse = {
      total_awarded_marks: 4,
      total_possible_marks: 4,
      percentage: 100,
      marking: {
        total_awarded_marks: 4,
        total_possible_marks: 4,
        criteria_results: [
          { criterion_id: 'C1', awarded_mark: 2, max_marks: 2, explanation: 'Cohesion demonstrated' },
          { criterion_id: 'C2', awarded_mark: 2, max_marks: 2, explanation: 'Coupling demonstrated' }
        ]
      },
      feedback: { summary: 'Strong modular architecture answer.' },
      analysis: { concept_matches: [{ concept: 'high cohesion', status: 'demonstrated' }] }
    };

    const resMark = await fetchApi('/batch/mark', lecturerToken, {
      setup_id: savedBatchId,
      items: [
        { student_id: 'IT21001001', student_answer: 'High cohesion and loose coupling are key.' },
        { student_id: 'IT21001003', student_answer: 'Loose coupling is achieved using microservices.' }
      ]
    });

    assert.strictEqual(resMark.status, 200);
    assert.strictEqual(resMark.data.total_processed, 2);
    assert.strictEqual(resMark.data.successful_count, 2);
    assert.strictEqual(resMark.data.failed_count, 0);
    assert.strictEqual(resMark.data.results.length, 2);

    // Verify both submissions were stored with batch_id
    const subsInBatch = mockSubmissions.filter((s) => s.batch_id === savedBatchId);
    assert.strictEqual(subsInBatch.length, 2);
    assert.strictEqual(subsInBatch[0].question_id, 'SE3010-BATCH-01');
    assert.strictEqual(subsInBatch[1].question_id, 'SE3010-BATCH-01');
  });

  await t.test('Batch Marking: retrying batch does not create duplicate submissions (idempotency)', async () => {
    const resRetry = await fetchApi('/batch/mark', lecturerToken, {
      setup_id: savedBatchId,
      items: [
        { student_id: 'IT21001001', student_answer: 'Updated answer for student 1.' },
        { student_id: 'IT21001003', student_answer: 'Updated answer for student 3.' }
      ]
    });

    assert.strictEqual(resRetry.status, 200);
    assert.strictEqual(resRetry.data.successful_count, 2);

    // Verify submission count remains 2 (not 4)
    const subsInBatch = mockSubmissions.filter((s) => s.batch_id === savedBatchId);
    assert.strictEqual(subsInBatch.length, 2);
    assert.strictEqual(subsInBatch[0].student_answer, 'Updated answer for student 1.');
  });

  await t.test('Batch Marking: MCQ batch marking evaluates students deterministically using answer key', async () => {
    // Create MCQ batch setup (Authoritative key: B)
    const resMcqSetup = await fetchApi('/batch/setup', lecturerToken, {
      title: 'Architecture Pattern MCQ Batch',
      module_id: 'SE3010',
      question_id: 'SE3010-MCQ-BATCH-01',
      question_text: 'Which architectural style structures an application as independently deployable services?',
      answer_type: 'mcq',
      max_marks: 2,
      correct_answer: 'B',
      options: [
        { option_id: 'A', label: 'A', text: 'Monolith' },
        { option_id: 'B', label: 'B', text: 'Microservices' },
        { option_id: 'C', label: 'C', text: 'Pipe and Filter' }
      ]
    });
    assert.strictEqual(resMcqSetup.status, 200);
    const mcqBatchId = resMcqSetup.data.batch_id;

    // Grade batch of 3 students:
    // Student 1: 'B' (correct -> 2/2)
    // Student 2: 'A' (incorrect -> 0/2)
    // Student 3: '' (unanswered -> 0/2)
    const resMcqMark = await fetchApi('/batch/mark', lecturerToken, {
      setup_id: mcqBatchId,
      items: [
        { student_id: 'IT3001', selected_option_id: 'B' },
        { student_id: 'IT3002', selected_option_id: 'A' },
        { student_id: 'IT3003', selected_option_id: '' }
      ]
    });

    assert.strictEqual(resMcqMark.status, 200);
    assert.strictEqual(resMcqMark.data.successful_count, 3);
    const results = resMcqMark.data.results;
    assert.strictEqual(results[0].student_id, 'IT3001');
    assert.strictEqual(results[0].awarded_mark, 2);
    assert.strictEqual(results[0].percentage, 100);

    assert.strictEqual(results[1].student_id, 'IT3002');
    assert.strictEqual(results[1].awarded_mark, 0);
    assert.strictEqual(results[1].percentage, 0);

    assert.strictEqual(results[2].student_id, 'IT3003');
    assert.strictEqual(results[2].awarded_mark, 0);
    assert.strictEqual(results[2].percentage, 0);
  });

  await t.test('Batch Marking: lecturer can finalize entire batch in one confirmed operation & syncs to C1', async () => {
    const resFinalizeAll = await fetchApi(`/batch/${savedBatchId}/finalize-all`, lecturerToken, {});
    assert.strictEqual(resFinalizeAll.status, 200);
    assert.strictEqual(resFinalizeAll.data.finalized_count, 2);

    // Verify submissions in mockSubmissions are finalized
    const subsInBatch = mockSubmissions.filter((s) => s.batch_id === savedBatchId);
    assert.strictEqual(subsInBatch[0].status, 'finalized');
    assert.strictEqual(subsInBatch[1].status, 'finalized');

    // Verify results in mockResults are finalized
    const subIds = subsInBatch.map((s) => String(s._id));
    const resultsInBatch = mockResults.filter((r) => subIds.includes(String(r.submission_id)));
    assert.strictEqual(resultsInBatch[0].status, 'finalized');
    assert.strictEqual(resultsInBatch[1].status, 'finalized');

    // Verify learning events in mockLearningEvents were updated
    const events = mockLearningEvents.filter((e) => subIds.includes(String(e.submission_id)));
    assert.ok(events.length >= 2);
    assert.strictEqual(events[0].lifecycle_stage, 'finalized');
  });

  // Cleanup
  server.close();
  aiServer.close();
});
