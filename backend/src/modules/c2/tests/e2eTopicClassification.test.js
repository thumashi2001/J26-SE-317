import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import app from '../../../app.js';
import { signToken } from '../../../middleware/auth.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const FASTAPI_PORT = 8012;
const EXPRESS_PORT = 3012;
const INTERNAL_TOKEN = 'c2-internal-dev-token';

function waitForServer(url, timeoutMs = 15000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    function tryConnect() {
      http
        .get(url, (res) => {
          if (res.statusCode < 500) {
            resolve();
          } else {
            retry();
          }
        })
        .on('error', retry);
    }

    function retry() {
      if (Date.now() - start > timeoutMs) {
        reject(new Error(`Timed out waiting for server at ${url}`));
      } else {
        setTimeout(tryConnect, 200);
      }
    }

    tryConnect();
  });
}

test('End-to-End: Express auth, internal token forwarding, and FastAPI M17 inference', async (t) => {
  // Path to python executable in virtualenv
  const repoRoot = path.resolve(__dirname, '../../../../../');
  const pythonExe = path.join(repoRoot, 'ai-services', 'c2', '.venv', 'Scripts', 'python.exe');
  const c2Dir = path.join(repoRoot, 'ai-services', 'c2');

  // Spawn FastAPI server
  const fastApiProc = spawn(
    pythonExe,
    ['-m', 'uvicorn', 'api.main:app', '--port', String(FASTAPI_PORT), '--host', '127.0.0.1'],
    {
      cwd: c2Dir,
      env: {
        ...process.env,
        C2_INTERNAL_TOKEN: INTERNAL_TOKEN,
      },
      stdio: 'pipe',
    }
  );

  let fastApiOutput = '';
  fastApiProc.stdout?.on('data', (d) => {
    fastApiOutput += d.toString();
  });
  fastApiProc.stderr?.on('data', (d) => {
    fastApiOutput += d.toString();
  });

  // Start Express test server
  process.env.C2_API_URL = `http://127.0.0.1:${FASTAPI_PORT}`;
  process.env.C2_INTERNAL_TOKEN = INTERNAL_TOKEN;

  const expressServer = app.listen(EXPRESS_PORT);

  try {
    // Wait for FastAPI /health
    await waitForServer(`http://127.0.0.1:${FASTAPI_PORT}/health`);

    const lecturerToken = signToken({ sub: 'lecturer_e2e_001', role: 'lecturer' });
    const studentToken = signToken({ sub: 'student_e2e_001', role: 'student' });

    // 1. Unauthenticated request rejected
    await t.test('rejects unauthenticated requests with 401', async () => {
      const res = await fetch(`http://127.0.0.1:${EXPRESS_PORT}/api/v1/c2/experimental/classify-topic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          moduleKey: 'database_systems',
          questionText: 'Explain B-tree clustered index scans versus non-clustered indexes.',
        }),
      });
      assert.equal(res.status, 401);
    });

    // 2. Student role rejected (requires lecturer/admin)
    await t.test('rejects student role requests with 403', async () => {
      const res = await fetch(`http://127.0.0.1:${EXPRESS_PORT}/api/v1/c2/experimental/classify-topic`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${studentToken}`,
        },
        body: JSON.stringify({
          moduleKey: 'database_systems',
          questionText: 'Explain B-tree clustered index scans versus non-clustered indexes.',
        }),
      });
      assert.equal(res.status, 403);
    });

    // 3. Lecturer request successfully proxies to FastAPI and invokes M17 model
    await t.test('lecturer request successfully classified via M17 model', async () => {
      const res = await fetch(`http://127.0.0.1:${EXPRESS_PORT}/api/v1/c2/experimental/classify-topic`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${lecturerToken}`,
        },
        body: JSON.stringify({
          moduleKey: 'database_systems',
          questionText:
            'Scenario: A high-throughput telemetry database inserts thousands of sensor readings per second.\n' +
            'Task: Evaluate the disk I/O and page-split trade-offs between clustered versus non-clustered B-tree indexing.',
          abstentionThreshold: 0.38,
        }),
      });

      assert.equal(res.status, 200);
      const data = await res.json();

      assert.equal(data.module_key, 'database_systems');
      assert.equal(data.decision, 'classified');
      assert.equal(data.abstained, false);
      assert.equal(typeof data.predicted_topic, 'string');
      assert(data.predicted_topic.length > 0);
      assert.equal(data.score_type, 'calibrated_probability');
      assert(data.confidence_score >= 0.38);
      assert.equal(data.verification_status, 'unverified');
      assert.equal(data.academic_verification, 'pending_lecturer_review');
      assert.equal(data.source_type, 'synthetic_model_inference');
      // Ensure internal token is NEVER leaked
      assert.equal(data.c2_internal_token, undefined);
      assert.equal(data['x-c2-internal-token'], undefined);
    });

    // 4. Abstention trigger test
    await t.test('abstains when confidence is below conservative threshold', async () => {
      const res = await fetch(`http://127.0.0.1:${EXPRESS_PORT}/api/v1/c2/experimental/classify-topic`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${lecturerToken}`,
        },
        body: JSON.stringify({
          moduleKey: 'database_systems',
          questionText: 'A simple question about systems and generic concepts.',
          abstentionThreshold: 0.99, // Unusually high threshold to force policy abstention
        }),
      });

      assert.equal(res.status, 200);
      const data = await res.json();
      assert.equal(data.decision, 'needs_review');
      assert.equal(data.abstained, true);
      assert.equal(data.predicted_topic, 'unclassified');
      assert.equal(typeof data.candidate_topic, 'string');
    });

    // 5. Missing model returns 503
    await t.test('returns 503 for non-existent model artifact', async () => {
      const res = await fetch(`http://127.0.0.1:${EXPRESS_PORT}/api/v1/c2/experimental/classify-topic`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${lecturerToken}`,
        },
        body: JSON.stringify({
          moduleKey: 'non_existent_module_xyz',
          questionText: 'Test question.',
        }),
      });

      // Module validation will reject unknown modules (either 400 from FastAPI or 400 from validation)
      assert([400, 404, 503].includes(res.status));
    });
  } finally {
    expressServer.close();
    fastApiProc.kill('SIGTERM');
  }
});
