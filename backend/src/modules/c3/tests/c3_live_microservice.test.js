import test from 'node:test';
import assert from 'node:assert';
import http from 'node:http';

process.env.AUTH_SECRET = 'test-secret-change-me';

import app from '../../../app.js';
import { signToken } from '../../../middleware/auth.js';

test('C3 Live Microservice Boundary Integration (Express <-> FastAPI)', async (t) => {
  const restoreEnv = (key, original) => {
    if (original === undefined) delete process.env[key];
    else process.env[key] = original;
  };
  const fastapiUrl = process.env.C3_AI_URL || 'http://127.0.0.1:8003';

  // 1. Check if the live Python FastAPI service is active
  let isFastApiLive = false;
  try {
    const healthRes = await fetch(`${fastapiUrl}/health`, { signal: AbortSignal.timeout(2000) });
    if (healthRes.ok) {
      const data = await healthRes.json();
      if (data.service === 'component-3-ai-service') {
        isFastApiLive = true;
      }
    }
  } catch {
    isFastApiLive = false;
  }

  // 2. Setup Node Express App Server
  const server = http.createServer(app);
  await new Promise((resolve) => server.listen(0, resolve));
  t.after(() => server.close());
  const port = server.address().port;
  const baseUrl = `http://127.0.0.1:${port}/api/v1/c3`;

  // Auth tokens
  const studentToken = signToken({ sub: 'IT21001001', role: 'student' });

  const fetchApi = async (path, token, body = {}) => {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => null);
    return { status: res.status, data };
  };

  await t.test('1. Python FastAPI service health check is reachable', { skip: !isFastApiLive && 'FastAPI service is not running on port 8003' }, async () => {
    const res = await fetch(`${fastapiUrl}/health`);
    assert.strictEqual(res.status, 200);
    const data = await res.json();
    assert.strictEqual(data.service, 'component-3-ai-service');
    assert.strictEqual(data.status, 'running');
  });

  await t.test('2. Express successfully invokes live FastAPI for full subjective assessment', { skip: !isFastApiLive && 'FastAPI service is not running on port 8003' }, async () => {
    const payload = {
      question_id: 'SE3010-ARCH-01',
      question_text: 'Explain high cohesion and loose coupling in modular software architectures.',
      reference_answer: 'High cohesion ensures single responsibility. Loose coupling minimizes inter-service dependencies.',
      student_answer: 'High cohesion means each component has a single focused responsibility. Loose coupling ensures microservices communicate through well-defined APIs without depending on internal class implementations.',
      rubric: {
        rubric_id: 'RUBRIC-ARCH-01',
        title: 'Modular Architecture Rubric',
        criteria: [
          {
            criterion_id: 'C1',
            description: 'Understanding of High Cohesion',
            max_marks: 5,
            scoring_levels: [
              { level_id: 'L0', label: 'None', mark: 0, descriptor: 'No cohesion mentioned.' },
              { level_id: 'L1', label: 'Basic', mark: 2.5, descriptor: 'Mentions module cohesion.', required_concepts: ['cohesion'] },
              { level_id: 'L2', label: 'Proficient', mark: 5, descriptor: 'Explains single responsibility and high cohesion.', required_concepts: ['high cohesion'] },
            ],
          },
          {
            criterion_id: 'C2',
            description: 'Understanding of Loose Coupling',
            max_marks: 5,
            scoring_levels: [
              { level_id: 'L0', label: 'None', mark: 0, descriptor: 'No coupling mentioned.' },
              { level_id: 'L1', label: 'Basic', mark: 2.5, descriptor: 'Mentions loose coupling.', required_concepts: ['coupling'] },
              { level_id: 'L2', label: 'Proficient', mark: 5, descriptor: 'Explains loose coupling and API boundaries.', required_concepts: ['loose coupling'] },
            ],
          },
        ],
      },
    };

    const res = await fetchApi('/assess', studentToken, payload);
    assert.strictEqual(res.status, 200);
    assert.ok(res.data, 'Response must contain data');
    assert.strictEqual(res.data.question_id, 'SE3010-ARCH-01');

    // Verify Function 1 (Analysis)
    assert.ok(res.data.analysis, 'Must contain analysis block');
    assert.ok(res.data.analysis.token_count > 5, 'Tokens must be extracted by Python');
    assert.ok(res.data.analysis.sentences.length >= 1, 'Sentences must be extracted');

    // Verify Function 2 (Marking Engine)
    assert.ok(res.data.marking, 'Must contain marking block');
    assert.strictEqual(res.data.marking.total_possible_marks, 10);
    assert.ok(res.data.marking.total_awarded_marks >= 5, 'Should award marks for demonstrated concepts');
    assert.strictEqual(res.data.marking.criteria_results.length, 2);

    // Verify Function 3 (Feedback)
    assert.ok(res.data.feedback, 'Must contain feedback block');
    assert.ok(res.data.feedback.overall_feedback?.overall_summary?.length > 5, 'Must have explainable feedback summary');
    assert.ok(res.data.feedback.criteria_feedback?.length >= 1, 'Must have criteria feedback');

    // Verify Function 4 (Mind Map)
    assert.ok(res.data.mindmap, 'Must contain mindmap block');
    assert.ok(res.data.mindmap.nodes.length >= 1, 'Must contain mind map nodes');

    // Verify Express persistence wrapper fields
    assert.strictEqual(res.data.status, 'pending_review');
  });

  await t.test('3. FastAPI schema validation failure is translated to 400 by Express with details', { skip: !isFastApiLive && 'FastAPI service is not running on port 8003' }, async () => {
    // Invalid payload: rubric criteria array is empty (violates rubric validation)
    const invalidPayload = {
      question_id: 'SE3010-INVALID',
      question_text: 'Invalid rubric test',
      student_answer: 'Some answer',
      rubric: {
        rubric_id: 'RUBRIC-EMPTY',
        title: 'Empty Rubric',
        criteria: [], // Invalid: Criteria cannot be empty
      },
    };

    const res = await fetchApi('/assess', studentToken, invalidPayload);
    assert.strictEqual(res.status, 400, 'Express must map FastAPI 422 to 400 Bad Request');
    assert.ok(res.data.error.includes('Validation error') || res.data.error.includes('criteria'), 'Error must describe validation problem');
  });

  await t.test('4. Express returns 502 Bad Gateway when FastAPI is down (no fake success)', async (st) => {
    const originalUrl = process.env.C3_AI_URL;
    st.after(() => restoreEnv('C3_AI_URL', originalUrl));
    // Point to non-existent port
    process.env.C3_AI_URL = 'http://127.0.0.1:54321';

    const res = await fetchApi('/assess', studentToken, {
      question_id: 'Q-TEST',
      question_text: 'Valid question',
      student_answer: 'Valid answer',
      rubric: {
        rubric_id: 'R1',
        title: 'R1',
        criteria: [{ criterion_id: 'C1', description: 'C1', max_marks: 2, scoring_levels: [{ level_id: 'L0', label: 'None', mark: 0, descriptor: 'None' }] }],
      },
    });

    assert.strictEqual(res.status, 502, 'Must return 502 when service is down');
    assert.ok(res.data.error.includes('unreachable'), 'Must clearly report service unreachable');
    assert.strictEqual(res.data.status, undefined, 'Must NEVER return a fake success or pending_review result');

  });

  await t.test('5. Express handles request timeout cleanly and returns 504 Gateway Timeout', async (st) => {
    const originalUrl = process.env.C3_AI_URL;
    const originalTimeout = process.env.C3_AI_TIMEOUT_MS;
    st.after(() => {
      restoreEnv('C3_AI_URL', originalUrl);
      restoreEnv('C3_AI_TIMEOUT_MS', originalTimeout);
    });

    // Create a slow server that hangs for 500ms
    const slowServer = http.createServer((req, res) => {
      setTimeout(() => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'too_slow' }));
      }, 500);
    });
    await new Promise((resolve) => slowServer.listen(0, resolve));
    st.after(() => slowServer.close());
    const slowPort = slowServer.address().port;

    process.env.C3_AI_URL = `http://127.0.0.1:${slowPort}`;
    process.env.C3_AI_TIMEOUT_MS = '50'; // 50ms timeout

    const res = await fetchApi('/assess', studentToken, {
      question_id: 'Q-TIMEOUT',
      question_text: 'Timeout test',
      student_answer: 'Answer text',
      rubric: {
        rubric_id: 'R1',
        title: 'R1',
        criteria: [{ criterion_id: 'C1', description: 'C1', max_marks: 2, scoring_levels: [{ level_id: 'L0', label: 'None', mark: 0, descriptor: 'None' }] }],
      },
    });

    assert.strictEqual(res.status, 504, 'Must return 504 Gateway Timeout');
    assert.ok(res.data.error.includes('timed out'), 'Must report request timed out');

  });

});
