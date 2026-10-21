/**
 * C4 simulation demo proxy tests — run with: node --test src/modules/c4/tests/simProxy.test.js
 * Does not require Atlas or a live Python service (fetch is stubbed).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { signToken, requireAuth } from '../../../middleware/auth.js';
import {
  buildExamScenario,
  buildPathScenario,
  buildResponseScenario,
  listSyntheticScenarios,
} from '../services/simScenarioBuilder.js';
import {
  SIM_CATALOGUE_HASH,
  SIM_EXAM_FEATURE_NAMES,
  SIM_N_TOPICS,
  SIM_OBS_DIM,
  SIM_ORDERED_TOPICS,
  SIM_RESPONSE_FEATURE_NAMES,
  SIM_TOPIC_SEMESTER,
} from '../data/simCatalogue.generated.js';
import { callC4Ai, c4AiBaseUrl, httpError } from '../services/c4AiClient.js';
import * as sim from '../controllers/simDemoController.js';

const originalFetch = globalThis.fetch;

function restoreFetch() {
  globalThis.fetch = originalFetch;
}

function stubFetch(handler) {
  // Only intercept C4 AI upstream calls; keep real fetch for local Express smoke.
  globalThis.fetch = async (url, opts) => {
    const u = String(url);
    if (u.includes('127.0.0.1:8004') || u.includes('localhost:8004') || /\/v1\/se-(path|supervised)/.test(u)) {
      return handler(u, opts || {});
    }
    return originalFetch(url, opts);
  };
}

test('c4AiBaseUrl defaults to local 8004 and ignores browser-supplied hosts', () => {
  const prev = process.env.C4_AI_URL;
  delete process.env.C4_AI_URL;
  assert.equal(c4AiBaseUrl(), 'http://127.0.0.1:8004');
  process.env.C4_AI_URL = 'http://127.0.0.1:8004/';
  assert.equal(c4AiBaseUrl(), 'http://127.0.0.1:8004');
  if (prev === undefined) delete process.env.C4_AI_URL;
  else process.env.C4_AI_URL = prev;
});

test('callC4Ai maps unreachable upstream to 502', async () => {
  stubFetch(async () => {
    throw new Error('ECONNREFUSED');
  });
  try {
    await assert.rejects(
      () => callC4Ai('GET', '/v1/se-path-simulation-v1/ready'),
      (e) => e.status === 502 && e.code === 'c4_ai_unreachable'
    );
  } finally {
    restoreFetch();
  }
});

test('callC4Ai maps abort/timeout to 502 c4_ai_timeout', async () => {
  stubFetch(async (_url, opts) => {
    const err = new Error('aborted');
    err.name = 'AbortError';
    // Honour abort if signal already aborted; otherwise throw AbortError-like
    if (opts.signal?.aborted) throw err;
    throw err;
  });
  try {
    await assert.rejects(
      () => callC4Ai('GET', '/v1/se-path-simulation-v1/ready', { timeoutMs: 5 }),
      (e) => e.status === 502 && e.code === 'c4_ai_timeout'
    );
  } finally {
    restoreFetch();
  }
});

test('callC4Ai forwards JSON and maps 400/503', async () => {
  stubFetch(async (url, opts) => {
    assert.match(url, /\/v1\/se-path-simulation-v1\/predict$/);
    assert.equal(opts.method, 'POST');
    const body = JSON.parse(opts.body);
    assert.equal(body.semester, 'Y3S1');
    return {
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ detail: 'action_mask invalid for semester' }),
    };
  });
  try {
    await assert.rejects(
      () => callC4Ai('POST', '/v1/se-path-simulation-v1/predict', { body: { semester: 'Y3S1' } }),
      (e) => e.status === 400 && /semester/i.test(e.message)
    );
  } finally {
    restoreFetch();
  }

  stubFetch(async () => ({
    ok: false,
    status: 503,
    text: async () => JSON.stringify({ detail: 'model not loaded' }),
  }));
  try {
    await assert.rejects(
      () => callC4Ai('GET', '/v1/se-path-simulation-v1/ready'),
      (e) => e.status === 503 && e.code === 'c4_ai_not_ready'
    );
  } finally {
    restoreFetch();
  }
});

test('buildPathScenario yields schema-valid observation and semester mask', () => {
  const sc = buildPathScenario({ semester: 'Y3S1', masteryLevel: 0.35, priorStrength: 0.4 });
  assert.equal(sc.request.observation.length, SIM_OBS_DIM);
  assert.equal(sc.request.action_mask.length, SIM_N_TOPICS);
  assert.ok(sc.request.action_mask.some(Boolean));
  assert.equal(sc.request.catalogue_hash, SIM_CATALOGUE_HASH);
  // Masked-on actions must be available in-semester (no off-semester recommendations)
  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    if (!sc.request.action_mask[i]) continue;
    assert.ok(sc.request.observation[SIM_N_TOPICS + i] > 0.5, `masked-on ${i} must be available`);
  }
});

test('Y3S2 path scenario never enables Y3S1-only topics', () => {
  const sc = buildPathScenario({ semester: 'Y3S2', masteryLevel: 0.35 });
  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    if (!sc.request.action_mask[i]) continue;
    assert.equal(SIM_TOPIC_SEMESTER[SIM_ORDERED_TOPICS[i]], 'Y3S2');
  }
});

test('buildResponseScenario fills all 54 features coherently', () => {
  const sc = buildResponseScenario({ scenarioId: 'mid_progress', semester: 'Y3S1' });
  const keys = Object.keys(sc.request.features);
  assert.equal(keys.length, SIM_RESPONSE_FEATURE_NAMES.length);
  for (const n of SIM_RESPONSE_FEATURE_NAMES) {
    assert.ok(n in sc.request.features, `missing ${n}`);
    assert.ok(Number.isFinite(sc.request.features[n]));
  }
  assert.ok(sc.request.features.topic_prior_correct <= sc.request.features.topic_prior_attempts);
  const ohSum = SIM_RESPONSE_FEATURE_NAMES.filter((n) => n.startsWith('topic_oh_')).reduce(
    (s, n) => s + sc.request.features[n],
    0
  );
  assert.equal(ohSum, 1);
});

test('buildExamScenario fills all 98 features; pass threshold documented', () => {
  const sc = buildExamScenario({ scenarioId: 'balanced_practice', semester: 'Y3S1' });
  assert.equal(Object.keys(sc.request.features).length, SIM_EXAM_FEATURE_NAMES.length);
  assert.equal(sc.pass_threshold, 0.55);
  assert.ok(sc.request.features.global_attempts > 0);
  assert.ok(sc.request.features.n_topics_practiced >= 1);
});

test('listSyntheticScenarios marks synthetic and includes request payloads', () => {
  const list = listSyntheticScenarios();
  assert.equal(list.synthetic, true);
  assert.ok(list.path.length >= 2);
  assert.ok(list.response.length >= 2);
  assert.ok(list.exam.length >= 2);
  assert.ok(list.path[0].request.observation);
  assert.ok(list.response[0].request.features);
});

test('pathPredict validates body and forwards to Python (stub)', async () => {
  const sc = buildPathScenario({ semester: 'Y3S1', masteryLevel: 0.35 });
  let seen = null;
  stubFetch(async (url, opts) => {
    seen = { url, body: JSON.parse(opts.body) };
    return {
      ok: true,
      status: 200,
      text: async () =>
        JSON.stringify({
          topic_id: 'interaction_functional_design',
          action_index: 0,
          protocol: 'se-path-sim-v1',
          simulation_only: true,
          seed: 2,
        }),
    };
  });
  try {
    const req = { body: sc.request };
    const out = await new Promise((resolve, reject) => {
      const res = {
        statusCode: 200,
        status(c) {
          this.statusCode = c;
          return this;
        },
        json(payload) {
          if (this.statusCode >= 400) reject(Object.assign(new Error(payload.error), payload));
          else resolve(payload);
        },
      };
      sim.pathPredict(req, res);
    });
    assert.equal(out.demo_not_persisted, true);
    assert.equal(out.proxy, 'c4-node');
    assert.equal(out.topic_id, 'interaction_functional_design');
    assert.match(seen.url, /se-path-simulation-v1\/predict/);
    assert.equal(seen.body.semester, 'Y3S1');
  } finally {
    restoreFetch();
  }
});

test('pathPredict rejects bad observation length with 400 (no upstream call)', async () => {
  let called = false;
  stubFetch(async () => {
    called = true;
    return { ok: true, status: 200, text: async () => '{}' };
  });
  try {
    const req = {
      body: {
        observation: [0, 1, 2],
        action_mask: Array(SIM_N_TOPICS).fill(true),
        semester: 'Y3S1',
      },
    };
    await assert.rejects(
      () =>
        new Promise((resolve, reject) => {
          const res = {
            statusCode: 200,
            status(c) {
              this.statusCode = c;
              return this;
            },
            json(payload) {
              const e = Object.assign(new Error(payload.error), {
                status: this.statusCode,
                code: payload.code,
              });
              if (this.statusCode >= 400) reject(e);
              else resolve(payload);
            },
          };
          sim.pathPredict(req, res);
        }),
      (e) => e.status === 400 && /observation/i.test(e.message)
    );
    assert.equal(called, false);
  } finally {
    restoreFetch();
  }
});

test('simulation routes reject unauthenticated requests (401)', async () => {
  const app = express();
  app.use(express.json());
  const r = express.Router();
  r.use(requireAuth);
  r.get('/simulation/v1/ready', sim.demoReady);
  r.post('/simulation/v1/path/predict', sim.pathPredict);
  app.use('/api/v1/c4', r);

  const res = await new Promise((resolve) => {
    const server = app.listen(0, async () => {
      const { port } = server.address();
      const r1 = await fetch(`http://127.0.0.1:${port}/api/v1/c4/simulation/v1/ready`);
      const r2 = await fetch(`http://127.0.0.1:${port}/api/v1/c4/simulation/v1/path/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      server.close();
      resolve({ r1, r2 });
    });
  });
  assert.equal(res.r1.status, 401);
  assert.equal(res.r2.status, 401);
});

test('authenticated scenarios endpoint does not touch a database', async () => {
  // listSyntheticScenarios is pure; demoReady only calls AI. Assert no db import side effects.
  const src = await import('node:fs').then((fs) =>
    fs.promises.readFile(new URL('../controllers/simDemoController.js', import.meta.url), 'utf8')
  );
  assert.equal(/getDb|mongodb|mastery_state|learning_events|practice_sessions/.test(src), false);
  const list = listSyntheticScenarios();
  assert.equal(list.simulation_only, true);
});

test('httpError preserves status/code without stacking traces for clients', () => {
  const e = httpError(502, 'C4 AI service unreachable', 'c4_ai_unreachable');
  assert.equal(e.status, 502);
  assert.equal(e.code, 'c4_ai_unreachable');
  assert.equal(e.message.includes('Error:'), false);
});

test('auth token allows ready handler to return stubbed upstream', async () => {
  stubFetch(async (url) => {
    if (url.includes('se-path-simulation-v1/ready')) {
      return {
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({ ready: true, protocol: 'se-path-sim-v1', simulation_only: true }),
      };
    }
    if (url.includes('se-supervised-simulation-v1/ready')) {
      return {
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({ ready: true, protocol: 'se-supervised-sim-v1', simulation_only: true }),
      };
    }
    return { ok: false, status: 404, text: async () => '{}' };
  });
  try {
    const token = signToken({ sub: 'IT20261234', role: 'student' });
    const app = express();
    app.use(express.json());
    const r = express.Router();
    r.use(requireAuth);
    r.get('/simulation/v1/ready', sim.demoReady);
    app.use('/api/v1/c4', r);
    const body = await new Promise((resolve, reject) => {
      const server = app.listen(0, async () => {
        try {
          const { port } = server.address();
          const resp = await fetch(`http://127.0.0.1:${port}/api/v1/c4/simulation/v1/ready`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          const text = await resp.text();
          const json = text ? JSON.parse(text) : {};
          server.close();
          resolve({ status: resp.status, json });
        } catch (e) {
          server.close();
          reject(e);
        }
      });
    });
    assert.equal(body.status, 200);
    assert.equal(body.json.ready, true);
    assert.equal(body.json.synthetic, true);
    assert.equal(body.json.proxy, 'c4-node');
  } finally {
    restoreFetch();
  }
});
