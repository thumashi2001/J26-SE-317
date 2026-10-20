/**
 * Synthetic scenario builders for C4 simulation demo (C4-owned only).
 * Features follow training_se_supervised_v1 / training_se_v1 semantics.
 * Never writes to student records or Atlas.
 */

import {
  SIM_CATALOGUE_HASH,
  SIM_CLASSIFICATION_PROB_THRESHOLD,
  SIM_EXAM_FEATURE_NAMES,
  SIM_MASTERY_THRESHOLD,
  SIM_N_TOPICS,
  SIM_OBS_DIM,
  SIM_ORDERED_TOPICS,
  SIM_PASS_THRESHOLD,
  SIM_RESPONSE_FEATURE_NAMES,
  SIM_TOPIC_LABEL,
  SIM_Y3S1_TOPICS,
  SIM_Y3S2_TOPICS,
  simSemesterEligibilityMask,
  simTopicIndex,
} from '../data/simCatalogue.generated.js';

function err(status, message, code) {
  const e = new Error(message);
  e.status = status;
  if (code) e.code = code;
  return e;
}

function clamp01(x) {
  return Math.min(1, Math.max(0, x));
}

/** Build se-path-sim-v1 observation + mask (training reopen rule). */
export function buildPathScenario({
  semester = 'Y3S1',
  masteryLevel = 0.35,
  priorStrength = 0.4,
  elapsedEnvSteps = 2,
  maxEpisodeSteps = 40,
  unavailableWithinSemester = [],
} = {}) {
  if (semester !== 'Y3S1' && semester !== 'Y3S2') {
    throw err(400, 'semester must be Y3S1 or Y3S2');
  }
  const mLevel = clamp01(Number(masteryLevel));
  const prior = clamp01(Number(priorStrength));
  if (!Number.isFinite(mLevel) || !Number.isFinite(prior)) {
    throw err(400, 'masteryLevel and priorStrength must be finite numbers in [0,1]');
  }

  const semesterOk = simSemesterEligibilityMask(semester);
  const unavailable = new Set(unavailableWithinSemester);
  const mastery = new Array(SIM_N_TOPICS).fill(0);
  const available = new Array(SIM_N_TOPICS).fill(0);

  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    if (!semesterOk[i]) {
      available[i] = 0;
      mastery[i] = 0;
      continue;
    }
    const topic = SIM_ORDERED_TOPICS[i];
    if (unavailable.has(topic)) {
      available[i] = 0;
      mastery[i] = 0;
    } else {
      available[i] = 1;
      mastery[i] = mLevel;
    }
  }

  const availIdx = [];
  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    if (available[i] > 0.5) availIdx.push(i);
  }
  let meanMastery = 0;
  let fracMastered = 0;
  if (availIdx.length) {
    meanMastery = availIdx.reduce((s, i) => s + mastery[i], 0) / availIdx.length;
    fracMastered =
      availIdx.filter((i) => mastery[i] >= SIM_MASTERY_THRESHOLD).length / availIdx.length;
  }
  const stepFrac = Math.min(1, Number(elapsedEnvSteps) / Math.max(1, Number(maxEpisodeSteps)));
  const observation = [
    ...mastery,
    ...available,
    meanMastery,
    fracMastered,
    stepFrac,
    prior,
  ];
  if (observation.length !== SIM_OBS_DIM) {
    throw err(500, `Internal obs dim ${observation.length} != ${SIM_OBS_DIM}`);
  }

  let actionMask = observation.slice(0, SIM_N_TOPICS).map((_, i) => {
    if (available[i] < 0.5) return false;
    if (!semesterOk[i]) return false;
    return mastery[i] < SIM_MASTERY_THRESHOLD;
  });
  if (!actionMask.some(Boolean) && availIdx.length) {
    actionMask = available.map((a, i) => a > 0.5 && semesterOk[i]);
  }
  if (!actionMask.some(Boolean)) {
    throw err(400, 'No eligible actions for this synthetic path scenario', 'no_eligible_actions');
  }

  return {
    id: `path_${semester.toLowerCase()}_mastery_${mLevel}`,
    label: `Path · ${semester} · mastery ${mLevel.toFixed(2)}`,
    description:
      'Synthetic learner state: semester-eligible topics available at uniform mastery; ' +
      'mask = semester ∩ available ∩ below-threshold (with reopen rule).',
    synthetic: true,
    simulation_only: true,
    protocol: 'se-path-sim-v1',
    catalogue_hash: SIM_CATALOGUE_HASH,
    semester,
    request: {
      observation,
      action_mask: actionMask,
      semester,
      protocol: 'se-path-sim-v1',
      catalogue_hash: SIM_CATALOGUE_HASH,
      deterministic: true,
    },
  };
}

/**
 * Coherent next-attempt features matching training_se_supervised_v1 builders:
 * priors are history BEFORE the predicted attempt; one topic one-hot = 1.
 */
export function buildResponseScenario({
  scenarioId = 'mid_progress',
  topic,
  semester = 'Y3S1',
} = {}) {
  const pool = semester === 'Y3S2' ? SIM_Y3S2_TOPICS : SIM_Y3S1_TOPICS;
  const chosen = topic && pool.includes(topic) ? topic : pool[0];
  const tIdx = simTopicIndex(chosen);

  // Declared item difficulty (training used N(mean, sd); demo uses a fixed declared param).
  const presets = {
    cold_start: {
      label: 'Response · cold start on first semester topic',
      difficulty: 0.0,
      topic_prior_attempts: 0,
      topic_prior_correct: 0,
      topic_prior_streak: 0,
      global_prior_attempts: 0,
      global_prior_correct: 0,
      learner_step: 0,
    },
    mid_progress: {
      label: 'Response · mid-progress topic with mixed history',
      difficulty: 0.15,
      topic_prior_attempts: 4,
      topic_prior_correct: 2,
      topic_prior_streak: 1,
      global_prior_attempts: 12,
      global_prior_correct: 7,
      learner_step: 12,
    },
    strong_topic: {
      label: 'Response · strong recent streak on practised topic',
      difficulty: -0.25,
      topic_prior_attempts: 8,
      topic_prior_correct: 7,
      topic_prior_streak: 4,
      global_prior_attempts: 24,
      global_prior_correct: 18,
      learner_step: 24,
    },
  };
  const p = presets[scenarioId] || presets.mid_progress;
  const ta = p.topic_prior_attempts;
  const tc = p.topic_prior_correct;
  if (tc > ta) throw err(500, 'Internal incoherent topic priors');
  const ga = p.global_prior_attempts;
  const gc = p.global_prior_correct;
  if (gc > ga) throw err(500, 'Internal incoherent global priors');

  const features = Object.fromEntries(SIM_RESPONSE_FEATURE_NAMES.map((n) => [n, 0]));
  features.difficulty = p.difficulty;
  features.topic_prior_attempts = ta;
  features.topic_prior_correct = tc;
  features.topic_prior_accuracy = ta > 0 ? tc / ta : 0.5;
  features.topic_prior_streak = p.topic_prior_streak;
  features.global_prior_attempts = ga;
  features.global_prior_accuracy = ga > 0 ? gc / ga : 0.5;
  features.learner_step = p.learner_step;
  for (const name of SIM_RESPONSE_FEATURE_NAMES) {
    if (name.startsWith('topic_oh_')) features[name] = 0;
  }
  features[`topic_oh_${chosen}`] = 1;

  return {
    id: `response_${scenarioId}_${chosen}`,
    label: `${p.label} (${SIM_TOPIC_LABEL[chosen] || chosen})`,
    description:
      'Synthetic practice history before the predicted attempt (training feature semantics). ' +
      'Not a real student record.',
    synthetic: true,
    simulation_only: true,
    protocol: 'se-supervised-sim-v1',
    catalogue_hash: SIM_CATALOGUE_HASH,
    topic: chosen,
    topic_index: tIdx,
    semester,
    request: {
      features,
      protocol: 'se-supervised-sim-v1',
    },
  };
}

/** Exam features from practice aggregates before exam cutoff (training semantics). */
export function buildExamScenario({
  scenarioId = 'balanced_practice',
  semester = 'Y3S1',
} = {}) {
  const pool = semester === 'Y3S2' ? [...SIM_Y3S2_TOPICS] : [...SIM_Y3S1_TOPICS];
  const presets = {
    sparse_practice: {
      label: 'Exam · sparse practice (few topics)',
      topicCount: 3,
      attemptsEach: 2,
      accuracy: 0.5,
      spanHours: 12,
    },
    balanced_practice: {
      label: 'Exam · balanced multi-topic practice',
      topicCount: 6,
      attemptsEach: 5,
      accuracy: 0.6,
      spanHours: 48,
    },
    heavy_practice: {
      label: 'Exam · heavy practice, higher accuracy',
      topicCount: 10,
      attemptsEach: 8,
      accuracy: 0.75,
      spanHours: 120,
    },
  };
  const p = presets[scenarioId] || presets.balanced_practice;
  const topics = pool.slice(0, Math.min(p.topicCount, pool.length));
  const features = Object.fromEntries(SIM_EXAM_FEATURE_NAMES.map((n) => [n, 0]));

  let globalAttempts = 0;
  let globalCorrect = 0;
  const practicedAcc = [];
  for (const topic of topics) {
    const attempts = p.attemptsEach;
    const correct = Math.round(attempts * p.accuracy);
    features[`topic_attempts_${topic}`] = attempts;
    features[`topic_accuracy_${topic}`] = attempts > 0 ? correct / attempts : 0.5;
    globalAttempts += attempts;
    globalCorrect += correct;
    practicedAcc.push(features[`topic_accuracy_${topic}`]);
  }
  // Unpractised topics: training uses 0.5 accuracy placeholder when attempts==0
  for (const topic of SIM_ORDERED_TOPICS) {
    if (!topics.includes(topic)) {
      features[`topic_attempts_${topic}`] = 0;
      features[`topic_accuracy_${topic}`] = 0.5;
    }
  }

  features.global_attempts = globalAttempts;
  features.global_accuracy = globalAttempts > 0 ? globalCorrect / globalAttempts : 0.5;
  features.mean_topic_accuracy =
    practicedAcc.length > 0
      ? practicedAcc.reduce((a, b) => a + b, 0) / practicedAcc.length
      : 0.5;
  features.n_topics_practiced = topics.length;
  features.practice_span_hours = p.spanHours;
  features.last_topic_index = simTopicIndex(topics[topics.length - 1]);

  return {
    id: `exam_${scenarioId}_${semester.toLowerCase()}`,
    label: `${p.label} (${semester})`,
    description:
      'Synthetic pre-exam practice aggregates (attempts/accuracy per topic) matching ' +
      'training exam feature construction. Not real exam evidence.',
    synthetic: true,
    simulation_only: true,
    protocol: 'se-supervised-sim-v1',
    catalogue_hash: SIM_CATALOGUE_HASH,
    semester,
    pass_threshold: SIM_PASS_THRESHOLD,
    classification_prob_threshold: SIM_CLASSIFICATION_PROB_THRESHOLD,
    request: {
      features,
      protocol: 'se-supervised-sim-v1',
    },
  };
}

export function listSyntheticScenarios() {
  return {
    synthetic: true,
    simulation_only: true,
    note:
      'All scenarios are synthetic simulation inputs for demo inference only. ' +
      'They are not student records and are not written to C1/Atlas.',
    path: [
      buildPathScenario({ semester: 'Y3S1', masteryLevel: 0.35 }),
      buildPathScenario({ semester: 'Y3S2', masteryLevel: 0.35 }),
      buildPathScenario({ semester: 'Y3S1', masteryLevel: 0.55 }),
    ].map(({ request, ...meta }) => ({ ...meta, has_request: true, request })),
    response: [
      buildResponseScenario({ scenarioId: 'cold_start', semester: 'Y3S1' }),
      buildResponseScenario({ scenarioId: 'mid_progress', semester: 'Y3S1' }),
      buildResponseScenario({ scenarioId: 'strong_topic', semester: 'Y3S2' }),
    ].map(({ request, ...meta }) => ({ ...meta, has_request: true, request })),
    exam: [
      buildExamScenario({ scenarioId: 'sparse_practice', semester: 'Y3S1' }),
      buildExamScenario({ scenarioId: 'balanced_practice', semester: 'Y3S1' }),
      buildExamScenario({ scenarioId: 'heavy_practice', semester: 'Y3S2' }),
    ].map(({ request, ...meta }) => ({
      ...meta,
      has_request: true,
      request,
      also_for: ['exam-score', 'pass'],
    })),
  };
}
