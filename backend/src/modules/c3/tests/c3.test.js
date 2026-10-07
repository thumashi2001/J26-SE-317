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

  await t.test('all four C3 endpoints are registered', async () => {
    aiRequests = [];
    nextAiResponse = { success: true };
    await fetchApi('/analysis', studentToken, {});
    await fetchApi('/marking', studentToken, {});
    await fetchApi('/feedback', studentToken, {});
    await fetchApi('/mindmap', studentToken, {});
    
    const paths = aiRequests.map(r => r.path);
    assert.deepStrictEqual(paths, [
      '/analysis/answer',
      '/marking/evaluate',
      '/feedback/generate',
      '/mindmap/generate'
    ]);
  });

  // Cleanup
  server.close();
  aiServer.close();
});
