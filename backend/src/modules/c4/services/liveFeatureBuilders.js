/**
 * C4-owned live feature builders for se-*-sim-v1 serving.
 *
 * Training semantics (verified from training_se_v1 / training_se_supervised_v1):
 * - prior_strength: fixed episode latent used only to initialise synthetic mastery;
 *   also appears as a constant observation slot. No C1 field exists.
 * - elapsed_env_step_frac: RL env step / max_episode_steps (default max 40).
 * - Exam features: aggregates of practice events with timestamp <= prediction_cutoff.
 * - Response features: pre-attempt priors + item difficulty (synthetic in training).
 *
 * Live serving protocol (documented, experimental):
 * - Path: mastery/available from C1; elapsed from C4 path episode counter;
 *   prior_strength uses protocol constant LIVE_PRIOR_STRENGTH_CONSTANT (val-split mid)
 *   OR a frozen path-episode proxy if already stored — never confidence/days invent.
 * - Exam/pass: cutoff = C4 mock-attempt created_at; features from learning_events.
 * - Response: remains unusable — item difficulty has no C1 source on that scale.
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
  simSemesterEligibilityMask,
} from '../data/simCatalogue.generated.js';
import { isSupportedPracticeTopic } from '../data/supportedTopics.js';

/** Normalize C1 0–100 mastery to [0,1]. Missing twin entry ≠ observed zero. */
export function normalizeMasteryEntry(entry) {
  if (!entry || typeof entry.score !== 'number' || !Number.isFinite(entry.score)) {
    return { value: null, available: 0, source: 'missing' };
  }
  const v = Math.min(1, Math.max(0, entry.score / 100));
  return { value: v, available: 1, source: 'twin.score/100' };
}

/** Availability: semester ∩ practice bank ∩ twin presence. */
export function deriveAvailability({ semester, twinMastery }) {
  if (semester !== 'Y3S1' && semester !== 'Y3S2') {
    return {
      ok: false,
      reason: 'Student semester must be Y3S1 or Y3S2 for catalogue eligibility.',
      available: null,
    };
  }
  const semesterOk = simSemesterEligibilityMask(semester);
  const twinKeys = new Set(Object.keys(twinMastery || {}));
  const available = SIM_ORDERED_TOPICS.map((topic, i) => {
    if (!semesterOk[i]) return 0;
    if (!isSupportedPracticeTopic(topic)) return 0;
    if (!twinKeys.has(topic)) return 0;
    return 1;
  });
  return { ok: true, available, semester, catalogue_hash: SIM_CATALOGUE_HASH };
}

/** Matches training_se_v1 protocol y3s*_sim_val prior_strength mid-band. */
export const LIVE_PRIOR_STRENGTH_CONSTANT = 0.45;
export const LIVE_MAX_EPISODE_STEPS = 40;
export const LIVE_PATH_PROTOCOL = 'se-path-sim-v1/live-serving-v1';
export const LIVE_EXAM_PROTOCOL = 'se-supervised-sim-v1/live-exam-serving-v1';

export function buildPathObservationPayload({
  semester,
  twinMastery,
  elapsedEnvSteps = 0,
  maxEpisodeSteps = LIVE_MAX_EPISODE_STEPS,
  priorStrength = LIVE_PRIOR_STRENGTH_CONSTANT,
  priorStrengthProvenance = 'protocol_constant_val_split_prior_0.45',
}) {
  const avail = deriveAvailability({ semester, twinMastery });
  if (!avail.ok) {
    return {
      usable: false,
      code: 'semester_unavailable',
      reason: avail.reason,
    };
  }

  const mastery = [];
  const fieldSources = [];
  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    if (avail.available[i] < 0.5) {
      mastery.push(0);
      fieldSources.push({
        topic: SIM_ORDERED_TOPICS[i],
        mastery: 'missing_or_ineligible',
        available: 0,
      });
    } else {
      const n = normalizeMasteryEntry(twinMastery[SIM_ORDERED_TOPICS[i]]);
      mastery.push(n.value ?? 0);
      fieldSources.push({
        topic: SIM_ORDERED_TOPICS[i],
        mastery: n.source,
        available: 1,
      });
    }
  }

  const availIdx = [];
  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    if (avail.available[i] > 0.5) availIdx.push(i);
  }
  let meanMastery = 0;
  let fracMastered = 0;
  if (availIdx.length) {
    meanMastery = availIdx.reduce((s, i) => s + mastery[i], 0) / availIdx.length;
    fracMastered =
      availIdx.filter((i) => mastery[i] >= SIM_MASTERY_THRESHOLD).length / availIdx.length;
  }

  const steps = Math.max(0, Number(elapsedEnvSteps) || 0);
  const maxSteps = Math.max(1, Number(maxEpisodeSteps) || LIVE_MAX_EPISODE_STEPS);
  const stepFrac = Math.min(1, steps / maxSteps);
  const prior = Math.min(1, Math.max(0, Number(priorStrength)));

  const observation = [
    ...mastery,
    ...avail.available,
    meanMastery,
    fracMastered,
    stepFrac,
    prior,
  ];
  if (observation.length !== SIM_OBS_DIM) {
    return {
      usable: false,
      code: 'obs_dim_mismatch',
      reason: `Built obs length ${observation.length} != ${SIM_OBS_DIM}`,
    };
  }

  const semesterOk = simSemesterEligibilityMask(semester);
  let actionMask = SIM_ORDERED_TOPICS.map((_, i) => {
    if (avail.available[i] < 0.5) return false;
    if (!semesterOk[i]) return false;
    return mastery[i] < SIM_MASTERY_THRESHOLD;
  });
  // Training reopen rule: if none below threshold, reopen all available semester topics.
  if (!actionMask.some(Boolean) && availIdx.length) {
    actionMask = avail.available.map((a, i) => a > 0.5 && semesterOk[i]);
  }
  if (!actionMask.some(Boolean)) {
    return {
      usable: false,
      code: 'no_eligible_actions',
      reason: 'No semester-eligible available topics for the path policy mask.',
      experimental: true,
    };
  }

  return {
    usable: true,
    code: 'ok',
    experimental: true,
    simulation_trained: true,
    real_student_validation: false,
    protocol: LIVE_PATH_PROTOCOL,
    model_protocol: 'se-path-sim-v1',
    catalogue_hash: SIM_CATALOGUE_HASH,
    semester,
    observation,
    action_mask: actionMask,
    input_timestamp: new Date().toISOString(),
    provenance: {
      mastery: 'twin.score/100 clipped [0,1]; missing twin → available=0 mastery=0',
      available: 'semester ∩ C1 practice bank ∩ twin key presence',
      mean_mastery: 'mean over available=1',
      frac_mastered: `share of available with mastery >= ${SIM_MASTERY_THRESHOLD} (sim threshold)`,
      elapsed_env_step_frac: {
        rule: 'deduplicated_quiz_answer_attempts / max_episode_steps',
        steps,
        max_episode_steps: maxSteps,
        value: stepFrac,
        cold_start: steps === 0,
        note:
          'Serving rule: unique session+question quiz_answer rows since path episode start; ' +
          'abandoned sessions excluded; Mark done never counted. Intended to approximate ' +
          'training’s one-attempt-per-step units, but episode boundaries and attempt definitions ' +
          'are still a live-serving approximation — training/serving mismatch is not eliminated.',
      },
      prior_strength: {
        value: prior,
        provenance: priorStrengthProvenance,
        note:
          'Assumed serving constant (0.45) — not measured student data. Training uses a simulator ' +
          'latent. This remaining training/serving mismatch is intentional for frozen v1 weights. ' +
          'Prepared se-path-sim-v2 files are paused and not activated.',
      },
      field_sources: fieldSources,
    },
  };
}

/**
 * Legacy helper: verified session completions on this path.
 * Prefer countPracticeAttemptSteps for live-serving (matches training env steps).
 */
export function countPathEpisodeSteps(activities = []) {
  return (activities || []).filter(
    (a) =>
      a.completion_kind === 'practice_verified' ||
      a.status === 'practice_verified'
  ).length;
}

/**
 * Count single practice attempts for path episode step_frac.
 *
 * Training (se-path-sim-v1): each env step = one practice action/attempt.
 * Live contract: one attempt = one deduplicated quiz_answer
 * (session_id+question_id) with answered=true, excluding abandoned sessions
 * and excluding self-reported Mark done (never a measured attempt).
 *
 * Optional sinceIso bounds the episode (path live_model_episode.created_at).
 */
export function countPracticeAttemptSteps({
  events = [],
  practiceSessions = [],
  sinceIso = null,
} = {}) {
  const since = sinceIso ? new Date(sinceIso) : null;
  const sinceOk = since && !Number.isNaN(since.getTime());

  const abandoned = new Set();
  for (const s of practiceSessions || []) {
    if (s && s.abandoned === true && s.session_id) abandoned.add(String(s.session_id));
  }

  const seen = new Set();
  let count = 0;
  for (const e of events || []) {
    if (!e || e.type !== 'quiz_answer' || e.answered === false) continue;
    if (e.session_id && abandoned.has(String(e.session_id))) continue;
    const t = new Date(e.timestamp || e.created_at || e.ts);
    if (Number.isNaN(t.getTime())) continue;
    if (sinceOk && t < since) continue;
    const key =
      e.session_id && e.question_id
        ? `s:${e.session_id}:q:${e.question_id}`
        : e._id
          ? `id:${e._id}`
          : null;
    if (!key) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    count += 1;
  }
  return count;
}

/**
 * Freeze episode prior at path create: protocol constant (not mean-mastery invent).
 * Also records episode_init_mean_mastery for future se-path-sim-v2 (not loaded into v1 weights).
 */
export function initialPathEpisodeState(twinMastery = null, semester = null) {
  let episodeInitMean = null;
  if (twinMastery && semester) {
    const avail = deriveAvailability({ semester, twinMastery });
    if (avail.ok) {
      const vals = [];
      for (let i = 0; i < SIM_N_TOPICS; i += 1) {
        if (avail.available[i] < 0.5) continue;
        const n = normalizeMasteryEntry(twinMastery[SIM_ORDERED_TOPICS[i]]);
        if (n.value != null) vals.push(n.value);
      }
      if (vals.length) episodeInitMean = vals.reduce((s, v) => s + v, 0) / vals.length;
    }
  }
  return {
    protocol: LIVE_PATH_PROTOCOL,
    prior_strength: LIVE_PRIOR_STRENGTH_CONSTANT,
    prior_strength_provenance: 'protocol_constant_val_split_prior_0.45',
    episode_init_mean_mastery: episodeInitMean,
    episode_init_mean_mastery_note:
      'Observable freeze for se-path-sim-v2 training/serving. Not injected into se-path-sim-v1 observation (would change schema under old weights).',
    step_counting: 'deduplicated_quiz_answer_attempts',
    max_episode_steps: LIVE_MAX_EPISODE_STEPS,
    created_at: new Date().toISOString(),
  };
}

/** Product practice-quiz pass target (not institutional). */
export const PRACTICE_QUIZ_SCORE_TARGET = 0.6;
export const LIVE_PRACTICE_QUIZ_PROTOCOL = 'c4-practice-quiz-estimate-v1';

/**
 * Heuristic (not trained) estimate for THIS C4 practice-bank mock quiz.
 *
 * Calculation:
 *   for each snapshotted question q: p_q = topic prior accuracy from quiz_answer
 *     events with timestamp <= cutoff (deduped; abandoned sessions excluded);
 *     if that topic has 0 prior attempts → p_q = 0.5 (explicit default, not observed);
 *   predicted_score = mean(p_q);
 *   predicted_pass = predicted_score >= PRACTICE_QUIZ_SCORE_TARGET (product rule 0.6).
 *
 * Not an ML model: no weights, no fitting, no simulation training.
 */
export function estimatePracticeQuizFromBlueprint({
  events = [],
  practiceSessions = [],
  cutoffIso,
  questionSnapshot = [],
  scoreTarget = PRACTICE_QUIZ_SCORE_TARGET,
} = {}) {
  const cutoff = new Date(cutoffIso);
  if (Number.isNaN(cutoff.getTime())) {
    return {
      usable: false,
      code: 'invalid_cutoff',
      reason: 'prediction_cutoff must be a valid timestamp.',
    };
  }
  const questions = questionSnapshot || [];
  if (questions.length < 1) {
    return {
      usable: false,
      code: 'empty_blueprint',
      reason: 'No snapshotted questions to estimate against.',
    };
  }

  const built = buildExamFeaturesFromEvents(events, {
    cutoffIso,
    practiceSessions,
  });
  if (!built.usable) {
    return {
      usable: false,
      code: built.code,
      reason: built.reason,
    };
  }

  const perQuestion = [];
  let questionsUsingDefaultPrior = 0;
  for (const q of questions) {
    const topic = q.topic;
    const idx = SIM_ORDERED_TOPICS.indexOf(topic);
    let p = 0.5;
    let attempts = 0;
    let usedDefaultPrior = true;
    if (idx >= 0) {
      attempts = Number(built.features[`topic_attempts_${topic}`]) || 0;
      if (attempts > 0) {
        p = Number(built.features[`topic_accuracy_${topic}`]);
        if (!Number.isFinite(p)) p = 0.5;
        else usedDefaultPrior = false;
      }
    }
    if (usedDefaultPrior) questionsUsingDefaultPrior += 1;
    perQuestion.push({
      topic,
      prior_accuracy: p,
      prior_attempts: attempts,
      used_default_prior: usedDefaultPrior,
    });
  }

  const predicted =
    perQuestion.reduce((s, row) => s + row.prior_accuracy, 0) / perQuestion.length;
  const target = Math.min(1, Math.max(0, Number(scoreTarget) || PRACTICE_QUIZ_SCORE_TARGET));
  const predictedPass = predicted >= target;
  const topicCounts = {};
  for (const row of perQuestion) {
    topicCounts[row.topic] = (topicCounts[row.topic] || 0) + 1;
  }
  const coldStart = built.cold_start === true;
  const partialDefaults = !coldStart && questionsUsingDefaultPrior > 0;

  return {
    usable: true,
    code: coldStart ? 'ok_cold_start' : partialDefaults ? 'ok_partial_defaults' : 'ok',
    method: 'heuristic_mean_topic_prior_accuracy',
    trained_model: false,
    experimental: false,
    simulation_trained: false,
    real_student_validation: false,
    protocol: LIVE_PRACTICE_QUIZ_PROTOCOL,
    prediction_cutoff_utc: cutoff.toISOString(),
    question_count: questions.length,
    blueprint_topic_counts: topicCounts,
    predicted_score: predicted,
    predicted_pass: predictedPass,
    practice_quiz_score_target: target,
    practice_quiz_score_target_note:
      'C4 product practice-quiz target (fraction correct). Not an institutional module pass rule. ' +
      'Distinct from any ML classifier probability threshold.',
    cold_start: coldStart,
    questions_using_default_prior: questionsUsingDefaultPrior,
    default_prior_accuracy: 0.5,
    per_question: perQuestion,
    provenance: {
      kind: 'statistical_heuristic_formula_not_a_trained_model',
      formula:
        'mean_q( topic_accuracy[topic(q)] ) where topic_accuracy = correct/attempts from ' +
        'quiz_answer events <= cutoff; if attempts=0 then topic_accuracy := 0.5 (default)',
      unpractised_topic_accuracy: '0.5 default (not observed performance)',
      excludes: 'current-attempt answers, answer keys, future events, Mark done',
      event_counts: {
        event_count: built.provenance?.event_count ?? null,
        skipped_abandoned_events: built.provenance?.skipped_abandoned_events ?? null,
        skipped_duplicate_events: built.provenance?.skipped_duplicate_events ?? null,
      },
      not_the_simulation_model:
        'This formula is c4-practice-quiz-estimate-v1. It is not se-supervised-sim-v1 and does not use the 0.55 synthetic-exam cutoff.',
    },
    note:
      'Heuristic this-quiz estimate only — not a trained model and not se-supervised-sim-v1. ' +
      (coldStart
        ? 'Cold start: no prior quiz_answer events before cutoff; every question uses the 0.5 default.'
        : partialDefaults
          ? `${questionsUsingDefaultPrior}/${questions.length} questions use the 0.5 default (no prior attempts on that topic).`
          : 'All blueprint topics have at least one prior practice attempt before cutoff.'),
  };
}

/**
 * Build exam-score / pass features from chronological quiz_answer events.
 * Cutoff must be at or before exam start (C4 attempt created_at).
 *
 * @param {object[]} events learning_events rows
 * @param {object} opts
 * @param {string} opts.cutoffIso
 * @param {string} [opts.studentId]
 * @param {object[]} [opts.practiceSessions] optional C1 practice_sessions for abandon filter
 * @param {Set<string>|string[]} [opts.excludeAttemptIds] unused; exam answers live in C4, not events
 */
export function buildExamFeaturesFromEvents(events, { cutoffIso, studentId, practiceSessions } = {}) {
  const cutoff = new Date(cutoffIso);
  if (Number.isNaN(cutoff.getTime())) {
    return {
      usable: false,
      code: 'invalid_cutoff',
      reason: 'prediction_cutoff must be a valid timestamp (C4 attempt created_at).',
    };
  }

  const abandonedSessions = new Set();
  for (const s of practiceSessions || []) {
    if (s && s.abandoned === true && s.session_id) abandonedSessions.add(String(s.session_id));
  }

  const seenKeys = new Set();
  const prior = [];
  const sorted = (events || [])
    .filter((e) => e && e.type === 'quiz_answer' && e.answered !== false)
    .filter((e) => {
      const t = new Date(e.timestamp || e.created_at || e.ts);
      return !Number.isNaN(t.getTime()) && t <= cutoff;
    })
    .sort((a, b) => {
      const ta = new Date(a.timestamp || a.created_at || 0).getTime();
      const tb = new Date(b.timestamp || b.created_at || 0).getTime();
      return ta - tb;
    });

  let skippedAbandoned = 0;
  let skippedDuplicate = 0;
  for (const e of sorted) {
    if (e.session_id && abandonedSessions.has(String(e.session_id))) {
      skippedAbandoned += 1;
      continue;
    }
    // Dedupe identical answer records (same session + question) so retries do not inflate counts.
    const dedupeKey =
      e.session_id && e.question_id
        ? `s:${e.session_id}:q:${e.question_id}`
        : e._id
          ? `id:${e._id}`
          : null;
    if (dedupeKey) {
      if (seenKeys.has(dedupeKey)) {
        skippedDuplicate += 1;
        continue;
      }
      seenKeys.add(dedupeKey);
    }
    prior.push(e);
  }

  const topicAttempts = new Array(SIM_N_TOPICS).fill(0);
  const topicCorrect = new Array(SIM_N_TOPICS).fill(0);
  for (const ev of prior) {
    const topic = ev.topic;
    const idx = SIM_ORDERED_TOPICS.indexOf(topic);
    if (idx < 0) continue;
    if (!isSupportedPracticeTopic(topic)) continue;
    topicAttempts[idx] += 1;
    if (ev.correct === true) topicCorrect[idx] += 1;
  }

  const topicAcc = topicAttempts.map((att, i) =>
    att > 0 ? topicCorrect[i] / att : 0.5
  );
  const practicedIdx = topicAttempts.map((a, i) => (a > 0 ? i : -1)).filter((i) => i >= 0);
  const meanTopicAcc = practicedIdx.length
    ? practicedIdx.reduce((s, i) => s + topicAcc[i], 0) / practicedIdx.length
    : 0.5;
  const globalAttempts = topicAttempts.reduce((s, n) => s + n, 0);
  const globalCorrect = topicCorrect.reduce((s, n) => s + n, 0);
  const globalAccuracy = globalAttempts > 0 ? globalCorrect / globalAttempts : 0.5;

  let practiceSpanHours = 0;
  if (prior.length > 1) {
    const t0 = new Date(prior[0].timestamp || prior[0].created_at).getTime();
    const t1 = new Date(prior[prior.length - 1].timestamp || prior[prior.length - 1].created_at).getTime();
    practiceSpanHours = Math.max(0, (t1 - t0) / 3600000);
  }

  let lastTopicIndex = 0;
  if (prior.length) {
    const lastTopic = prior[prior.length - 1].topic;
    const li = SIM_ORDERED_TOPICS.indexOf(lastTopic);
    lastTopicIndex = li >= 0 ? li : 0;
  }

  const features = {};
  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    const t = SIM_ORDERED_TOPICS[i];
    features[`topic_attempts_${t}`] = topicAttempts[i];
    features[`topic_accuracy_${t}`] = topicAcc[i];
  }
  features.global_attempts = globalAttempts;
  features.global_accuracy = globalAccuracy;
  features.mean_topic_accuracy = meanTopicAcc;
  features.n_topics_practiced = practicedIdx.length;
  features.practice_span_hours = practiceSpanHours;
  features.last_topic_index = lastTopicIndex;

  for (const name of SIM_EXAM_FEATURE_NAMES) {
    if (features[name] == null || !Number.isFinite(Number(features[name]))) {
      return {
        usable: false,
        code: 'feature_incomplete',
        reason: `Missing or non-finite exam feature: ${name}`,
      };
    }
  }

  const coldStart = globalAttempts === 0;

  return {
    usable: true,
    code: coldStart ? 'ok_cold_start' : 'ok',
    experimental: true,
    simulation_trained: true,
    real_student_validation: false,
    real_exam_validation: false,
    protocol: LIVE_EXAM_PROTOCOL,
    model_protocol: 'se-supervised-sim-v1',
    catalogue_hash: SIM_CATALOGUE_HASH,
    student_id: studentId,
    prediction_cutoff_utc: cutoff.toISOString(),
    features,
    feature_names: [...SIM_EXAM_FEATURE_NAMES],
    pass_label_threshold: SIM_PASS_THRESHOLD,
    classification_prob_threshold: SIM_CLASSIFICATION_PROB_THRESHOLD,
    cold_start: coldStart,
    provenance: {
      events:
        'learning_events type=quiz_answer with timestamp <= cutoff; ' +
        'abandoned practice_sessions excluded; session+question duplicates dropped',
      unpractised_topic_accuracy:
        '0.5 placeholder matching training when attempts=0 (not observed zero mastery)',
      cutoff: 'C4 mock-attempt created_at (frozen before any exam answers)',
      excludes: 'C4 mock-exam answers/results (stored only on c4_exam_attempts, never in this window)',
      skipped_abandoned_events: skippedAbandoned,
      skipped_duplicate_events: skippedDuplicate,
      note:
        'Pass label threshold 0.55 is synthetic training only — not an institutional rule. ' +
        'Classification probability threshold 0.5 is separate. ' +
        'Simulation-trained model; inputs are real practice history when present.',
      event_count: prior.length,
    },
  };
}

/**
 * Response (next-answer) features — fail closed: item difficulty unavailable on C1.
 */
export function assessLiveResponseFeatures() {
  return {
    usable: false,
    code: 'response_difficulty_unavailable',
    reason:
      'Next-answer response model requires item difficulty on the synthetic training scale. ' +
      'C1 practice items and learning_events do not expose a comparable numeric difficulty. ' +
      'Streak/learner_step could be derived from events, but difficulty cannot without invention ' +
      'or a new versioned response contract. Use the synthetic simulation demo for this target.',
    experimental: true,
    simulation_trained: true,
    real_student_validation: false,
    field_status: {
      difficulty: 'unavailable',
      topic_prior_attempts: 'derivable_from_events',
      topic_prior_correct: 'derivable_from_events',
      topic_prior_accuracy: 'derivable_from_events',
      topic_prior_streak: 'derivable_from_events_same_algorithm_as_training',
      global_prior_attempts: 'derivable_from_events',
      global_prior_accuracy: 'derivable_from_events',
      learner_step: 'derivable_as_prior_event_count',
      topic_oh: 'available_from_topic_id',
    },
  };
}
