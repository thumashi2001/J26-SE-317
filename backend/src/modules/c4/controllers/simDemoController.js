/**
 * Authenticated proxy + synthetic scenario helpers for C4 simulation demo.
 * Does not read/write student mastery, progress, or exam scores.
 */
import { callC4Ai, httpError } from '../services/c4AiClient.js';
import {
  buildExamScenario,
  buildPathScenario,
  buildResponseScenario,
  listSyntheticScenarios,
} from '../services/simScenarioBuilder.js';
import {
  SIM_CATALOGUE_HASH,
  SIM_N_TOPICS,
  SIM_OBS_DIM,
  SIM_ORDERED_TOPICS,
} from '../data/simCatalogue.generated.js';

function handle(fn) {
  return async (req, res) => {
    try {
      const data = await fn(req);
      res.json(data);
    } catch (err) {
      const body = { error: err.message };
      if (err.code) body.code = err.code;
      res.status(err.status || 500).json(body);
    }
  };
}

function requireObject(body, label = 'body') {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    throw httpError(400, `${label} must be a JSON object`);
  }
  return body;
}

function assertFiniteArray(arr, len, name) {
  if (!Array.isArray(arr) || arr.length !== len) {
    throw httpError(400, `${name} must be an array of length ${len}`);
  }
  for (let i = 0; i < arr.length; i += 1) {
    const v = Number(arr[i]);
    if (!Number.isFinite(v)) {
      throw httpError(400, `${name}[${i}] must be a finite number`);
    }
  }
}

/** GET /simulation/v1/path/ready */
export const pathReady = handle(async () => {
  const upstream = await callC4Ai('GET', '/v1/se-path-simulation-v1/ready');
  return {
    ...upstream,
    proxy: 'c4-node',
    note: 'Synthetic simulation readiness only. Not student path readiness.',
  };
});

/** GET /simulation/v1/path/catalogue */
export const pathCatalogue = handle(async () => {
  const upstream = await callC4Ai('GET', '/v1/se-path-simulation-v1/catalogue');
  return {
    ...upstream,
    proxy: 'c4-node',
    local_catalogue_hash: SIM_CATALOGUE_HASH,
  };
});

/** POST /simulation/v1/path/predict */
export const pathPredict = handle(async (req) => {
  const body = requireObject(req.body);
  // Optional convenience: build from scenario knobs without raw 96-dim vector.
  if (body.use_synthetic_scenario === true) {
    const built = buildPathScenario({
      semester: body.semester,
      masteryLevel: body.masteryLevel,
      priorStrength: body.priorStrength,
      unavailableWithinSemester: body.unavailableWithinSemester,
    });
    const upstream = await callC4Ai('POST', '/v1/se-path-simulation-v1/predict', {
      body: built.request,
    });
    return {
      ...upstream,
      proxy: 'c4-node',
      synthetic_scenario: {
        id: built.id,
        label: built.label,
        semester: built.semester,
      },
      demo_not_persisted: true,
    };
  }

  assertFiniteArray(body.observation, SIM_OBS_DIM, 'observation');
  if (!Array.isArray(body.action_mask) || body.action_mask.length !== SIM_N_TOPICS) {
    throw httpError(400, `action_mask must be length ${SIM_N_TOPICS}`);
  }
  if (body.semester !== 'Y3S1' && body.semester !== 'Y3S2') {
    throw httpError(400, 'semester must be Y3S1 or Y3S2');
  }
  const payload = {
    observation: body.observation.map(Number),
    action_mask: body.action_mask.map(Boolean),
    semester: body.semester,
    protocol: body.protocol || 'se-path-sim-v1',
    catalogue_hash: body.catalogue_hash || SIM_CATALOGUE_HASH,
    deterministic: body.deterministic !== false,
  };
  const upstream = await callC4Ai('POST', '/v1/se-path-simulation-v1/predict', {
    body: payload,
  });
  return { ...upstream, proxy: 'c4-node', demo_not_persisted: true };
});

/** GET /simulation/v1/supervised/ready */
export const supervisedReady = handle(async () => {
  const upstream = await callC4Ai('GET', '/v1/se-supervised-simulation-v1/ready');
  return {
    ...upstream,
    proxy: 'c4-node',
    note: 'Synthetic supervised models only. real_exam_validation=false.',
  };
});

async function supervisedPredict(kind, req) {
  const body = requireObject(req.body);
  let features;
  let scenarioMeta = null;
  if (body.use_synthetic_scenario === true) {
    if (kind === 'response') {
      const built = buildResponseScenario({
        scenarioId: body.scenarioId || 'mid_progress',
        topic: body.topic,
        semester: body.semester || 'Y3S1',
      });
      features = built.request.features;
      scenarioMeta = { id: built.id, label: built.label, topic: built.topic };
    } else {
      const built = buildExamScenario({
        scenarioId: body.scenarioId || 'balanced_practice',
        semester: body.semester || 'Y3S1',
      });
      features = built.request.features;
      scenarioMeta = { id: built.id, label: built.label, semester: built.semester };
    }
  } else {
    if (!body.features || typeof body.features !== 'object' || Array.isArray(body.features)) {
      throw httpError(400, 'features must be an object keyed by saved schema names');
    }
    features = body.features;
  }

  const path =
    kind === 'response'
      ? '/v1/se-supervised-simulation-v1/response'
      : kind === 'exam-score'
        ? '/v1/se-supervised-simulation-v1/exam-score'
        : '/v1/se-supervised-simulation-v1/pass';

  const upstream = await callC4Ai('POST', path, {
    body: {
      features,
      protocol: body.protocol || 'se-supervised-sim-v1',
    },
  });
  return {
    ...upstream,
    proxy: 'c4-node',
    synthetic_scenario: scenarioMeta,
    demo_not_persisted: true,
  };
}

export const supervisedResponse = handle((req) => supervisedPredict('response', req));
export const supervisedExamScore = handle((req) => supervisedPredict('exam-score', req));
export const supervisedPass = handle((req) => supervisedPredict('pass', req));

/** GET /simulation/v1/scenarios — labelled synthetic inputs (no DB). */
export const scenarios = handle(async () => listSyntheticScenarios());

/** Combined readiness for the demo UI. */
export const demoReady = handle(async () => {
  let path = null;
  let supervised = null;
  let pathError = null;
  let supervisedError = null;
  try {
    path = await callC4Ai('GET', '/v1/se-path-simulation-v1/ready');
  } catch (e) {
    pathError = { status: e.status, message: e.message, code: e.code };
  }
  try {
    supervised = await callC4Ai('GET', '/v1/se-supervised-simulation-v1/ready');
  } catch (e) {
    supervisedError = { status: e.status, message: e.message, code: e.code };
  }
  return {
    proxy: 'c4-node',
    synthetic: true,
    simulation_only: true,
    catalogue_hash: SIM_CATALOGUE_HASH,
    n_topics: SIM_N_TOPICS,
    topic_ids: SIM_ORDERED_TOPICS,
    obs_dim: SIM_OBS_DIM,
    path,
    path_error: pathError,
    supervised,
    supervised_error: supervisedError,
    ready: Boolean(path?.ready && supervised?.ready),
    note:
      'Synthetic simulation demo readiness. Operational student path remains the Node heuristic.',
  };
});
