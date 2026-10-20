/**
 * Call C4 Python for live (non-demo) predictions. Failures return structured fallback.
 */

import { callC4Ai } from './c4AiClient.js';
import {
  SIM_N_TOPICS,
  SIM_ORDERED_TOPICS,
  SIM_PASS_THRESHOLD,
  SIM_CLASSIFICATION_PROB_THRESHOLD,
} from '../data/simCatalogue.generated.js';
import { PRACTICE_LAUNCH_PATH } from '../data/supportedTopics.js';
import { assessPathModelInputs, assessSupervisedModelInputs } from './liveModelAdapter.js';
import { deriveAvailability, normalizeMasteryEntry } from './liveFeatureBuilders.js';
import {
  MULTI_PROTOCOL,
  MULTI_PROTOCOL_V2,
  buildMultiMask,
  buildMultiObservation,
  maskCompletedActivities,
  resolveMultiAction,
} from './multiActionContract.js';
function failResult(code, reason, extra = {}) {
  return {
    ok: false,
    usable: false,
    code,
    reason,
    experimental: true,
    ...extra,
  };
}

/**
 * Run path policy on live twin; return recommended topic or fallback signal.
 */
export async function predictLivePathRecommendation({
  semester,
  twinMastery,
  elapsedEnvSteps,
  priorStrength,
  priorStrengthProvenance,
}) {
  const assessment = assessPathModelInputs({
    semester,
    twinMastery,
    elapsedEnvSteps,
    priorStrength,
    priorStrengthProvenance,
  });
  if (!assessment.usable) {
    return failResult(assessment.code, assessment.reason, { assessment });
  }

  let upstream;
  try {
    upstream = await callC4Ai('POST', '/v1/se-path-simulation-v1/predict', {
      body: {
        observation: assessment.observation,
        action_mask: assessment.action_mask,
        semester,
        protocol: 'se-path-sim-v1',
        catalogue_hash: assessment.catalogue_hash,
        deterministic: true,
      },
      timeoutMs: 20_000,
    });
  } catch (err) {
    return failResult(err.code || 'c4_ai_error', err.message, {
      assessment,
      fallback: 'weakest_stored_mastery_v1',
    });
  }

  const idx =
    typeof upstream.action_index === 'number'
      ? upstream.action_index
      : typeof upstream.action === 'number'
        ? upstream.action
        : -1;
  const topicFromUpstream =
    upstream.topic_id ||
    (idx >= 0 && idx < SIM_ORDERED_TOPICS.length ? SIM_ORDERED_TOPICS[idx] : null);
  const topicIdx = topicFromUpstream ? SIM_ORDERED_TOPICS.indexOf(topicFromUpstream) : -1;

  if (!topicFromUpstream || topicIdx < 0 || !assessment.action_mask[topicIdx]) {
    return failResult('invalid_policy_action', 'Policy returned a masked/unknown topic', {
      assessment,
      upstream_summary: {
        action_index: upstream.action_index,
        topic_id: upstream.topic_id,
      },
      fallback: 'weakest_stored_mastery_v1',
    });
  }

  return {
    ok: true,
    usable: true,
    experimental: true,
    simulation_trained: true,
    real_student_validation: false,
    protocol: assessment.protocol,
    model_protocol: assessment.model_protocol,
    catalogue_hash: assessment.catalogue_hash,
    input_timestamp: assessment.input_timestamp,
    recommended_topic: topicFromUpstream,
    launch_path: PRACTICE_LAUNCH_PATH(topicFromUpstream),
    action_index: topicIdx,
    provenance: assessment.provenance,
    upstream: {
      protocol: upstream.protocol,
      model_hash: upstream.model_hash,
      catalogue_hash: upstream.catalogue_hash,
      algorithm: upstream.algorithm,
      simulation_only: upstream.simulation_only,
    },
    note:
      'Experimental next-practice recommendation from simulation-trained se-path-sim-v1. ' +
      'When usable, this topic is pinned as the next actionable practice on the student plan; ' +
      'calendar date/time-budget packing remains weakest_stored_mastery_v1. ' +
      'step_frac uses deduplicated quiz_answer attempts since episode start ÷ 40 (Mark done never counted) — ' +
      'a serving approximation of training attempt steps, not a claim that training/serving mismatch is gone. ' +
      'prior_strength = 0.45 assumed protocol constant (not measured). It is not an input to se-path-multi-v2.',
  };
}

function recentAccuracyFromTwin(twinMastery, available) {
  let answered = 0;
  let correct = 0;
  for (let i = 0; i < SIM_N_TOPICS; i += 1) {
    if (!(available[i] > 0.5)) continue;
    const entry = twinMastery[SIM_ORDERED_TOPICS[i]];
    const n = Number(entry?.answered);
    if (!Number.isFinite(n) || n <= 0) continue;
    answered += n;
    const ok = Number(entry?.correct);
    if (Number.isFinite(ok) && ok >= 0) correct += ok;
  }
  if (answered <= 0) return null;
  return Math.min(1, Math.max(0, correct / answered));
}

function examUrgencyFromDays(examDaysUntil) {
  if (examDaysUntil == null || !Number.isFinite(Number(examDaysUntil))) return null;
  const days = Number(examDaysUntil);
  if (days < 0) return null;
  if (days >= 14) return 0;
  return (14 - days) / 14;
}

/**
 * Observation fields for se-path-multi-v2 (same 101-value layout as v1):
 * mastery and availability come from the C1 twin; unavailable topics are 0.
 * mean_mastery and frac_mastered are computed from those arrays.
 * elapsed_env_step_frac is deduplicated practice attempt steps since the
 * episode started, divided by 40. Mark done is not an attempt.
 * recent_accuracy is the twin's correct/answered ratio on available topics,
 * or unobserved when no attempts exist.
 * engagement_completion_rate is the current plan's completion rate when the
 * caller has a plan; it is unobserved on a brand-new plan. It is not a reward.
 * exam_urgency is derived from the saved exam date, or unobserved when no date
 * is set. prior_strength is not an input.
 */
function multiFeatureBundle({
  semester,
  twinMastery,
  elapsedEnvSteps = 0,
  engagementCompletionRate = null,
  examDaysUntil = null,
}) {
  const avail = deriveAvailability({ semester, twinMastery });
  if (!avail.ok) return { ok: false, reason: avail.reason };
  const mastery = SIM_ORDERED_TOPICS.map((topic, i) => {
    if (avail.available[i] < 0.5) return 0;
    return normalizeMasteryEntry(twinMastery[topic]).value ?? 0;
  });
  const observation = buildMultiObservation({
    mastery,
    available: avail.available,
    elapsedEnvSteps,
    recentAccuracy: recentAccuracyFromTwin(twinMastery, avail.available),
    engagementCompletionRate,
    examUrgency: examUrgencyFromDays(examDaysUntil),
  });
  const mask = buildMultiMask({ semester, available: avail.available, mastery });
  if (!observation.usable || !mask.usable || !mask.mask.some(Boolean)) {
    return { ok: false, reason: 'No eligible practice, revision, or quiz action for this student.' };
  }
  return { ok: true, mastery, available: avail.available, observation, mask };
}

/**
 * Ask se-path-multi-v2 for one eligible practice, revision, or quiz.
 * Failure leaves activated false. The caller must keep the heuristic fallback
 * and must not describe that fallback as this policy.
 */
export async function predictLiveMultiActionV2({
  semester,
  twinMastery,
  elapsedEnvSteps = 0,
  engagementCompletionRate = null,
  examDaysUntil = null,
  completedActivityIds = [],
}) {
  const inactive = (reason) => ({
    ok: false,
    usable: false,
    protocol: MULTI_PROTOCOL_V2,
    multi_action: {
      protocol: MULTI_PROTOCOL_V2,
      activated: false,
      algorithm: null,
      reason,
    },
  });
  const features = multiFeatureBundle({
    semester,
    twinMastery,
    elapsedEnvSteps,
    engagementCompletionRate,
    examDaysUntil,
  });
  if (!features.ok) return inactive(features.reason);
  const openMask = maskCompletedActivities(features.mask.mask, completedActivityIds);
  if (!openMask.some(Boolean)) {
    return inactive('No eligible practice, revision, or quiz remains after completed activities.');
  }
  let upstream;
  try {
    upstream = await callC4Ai('POST', '/v1/se-path-multi-v2/predict', {
      body: {
        observation: features.observation.observation,
        action_mask: openMask,
        protocol: MULTI_PROTOCOL_V2,
        catalogue_hash: features.observation.catalogue_hash,
      },
      timeoutMs: 8_000,
    });
  } catch (err) {
    return inactive(err.message || 'se-path-multi-v2 is not active');
  }
  if (upstream?.algorithm !== 'maskable_ppo' || upstream?.protocol !== MULTI_PROTOCOL_V2) {
    return inactive('Upstream response is not a se-path-multi-v2 MaskablePPO action.');
  }
  const resolved = resolveMultiAction({
    actionType: upstream.action_type,
    topicId: upstream.topic_id,
    semester,
    available: features.available,
    mastery: features.mastery,
    protocol: MULTI_PROTOCOL_V2,
  });
  if (!resolved.usable || !openMask[resolved.actionIndex]) {
    return inactive(resolved.reason || 'Policy action is not an eligible activity.');
  }
  return {
    ok: true,
    usable: true,
    protocol: MULTI_PROTOCOL_V2,
    experimental: true,
    simulation_trained: true,
    synthetic_validation: true,
    activity: {
      ...resolved,
      reason: `Next ${resolved.actionType} selected by se-path-multi-v2 (synthetic validation). Calendar packing stays heuristic.`,
    },
    multi_action: {
      protocol: MULTI_PROTOCOL_V2,
      activated: true,
      algorithm: 'maskable_ppo',
      training_revision: upstream.training_revision || null,
      selected_seed: upstream.selected_seed ?? null,
      checkpoint_sha256: upstream.checkpoint_sha256 || null,
      catalogue_hash: upstream.catalogue_hash || features.observation.catalogue_hash,
      action_type: resolved.actionType,
      topic: resolved.topic,
      launch_path: resolved.launchPath,
      weights_updated: false,
      serves_students: false,
      artifact_serves_students: false,
      student_plan_requested: true,
      reason: 'Native MaskablePPO checkpoint passed the synthetic validation floor.',
    },
  };
}

/**
 * Ask the historical multi-action endpoint for one eligible practice, revision, or quiz.
 * A 503 or any other failure leaves the heuristic / v1 pin in place.
 * There is no Node flag that can mark this policy active.
 */
export async function predictLiveMultiAction({
  semester,
  twinMastery,
  elapsedEnvSteps = 0,
  engagementCompletionRate = null,
  examDaysUntil = null,
}) {
  const inactive = (reason) => ({
    ok: false,
    usable: false,
    protocol: MULTI_PROTOCOL,
    multi_action: {
      protocol: MULTI_PROTOCOL,
      activated: false,
      algorithm: null,
      reason,
    },
  });
  const avail = deriveAvailability({ semester, twinMastery });
  if (!avail.ok) return inactive(avail.reason);
  const mastery = SIM_ORDERED_TOPICS.map((topic, i) => {
    if (avail.available[i] < 0.5) return 0;
    return normalizeMasteryEntry(twinMastery[topic]).value ?? 0;
  });
  const observation = buildMultiObservation({
    mastery,
    available: avail.available,
    elapsedEnvSteps,
    recentAccuracy: recentAccuracyFromTwin(twinMastery, avail.available),
    engagementCompletionRate,
    examUrgency: examUrgencyFromDays(examDaysUntil),
  });
  const mask = buildMultiMask({ semester, available: avail.available, mastery });
  if (!observation.usable || !mask.usable || !mask.mask.some(Boolean)) {
    return inactive('No eligible practice, revision, or quiz action for this student.');
  }
  let upstream;
  try {
    upstream = await callC4Ai('POST', '/v1/se-path-multi-v1/predict', {
      body: {
        observation: observation.observation,
        action_mask: mask.mask,
        protocol: MULTI_PROTOCOL,
        catalogue_hash: observation.catalogue_hash,
      },
      timeoutMs: 8_000,
    });
  } catch (err) {
    return inactive(err.message || 'se-path-multi-v1 is not active');
  }
  if (upstream?.algorithm !== 'maskable_ppo') {
    return inactive('Upstream response is not a MaskablePPO action.');
  }
  const resolved = resolveMultiAction({
    actionType: upstream.action_type,
    topicId: upstream.topic_id,
    semester,
    available: avail.available,
    mastery,
  });
  if (!resolved.usable || !mask.mask[resolved.actionIndex]) {
    return inactive(resolved.reason || 'Policy action is not an eligible activity.');
  }
  return {
    ok: true,
    usable: true,
    protocol: MULTI_PROTOCOL,
    experimental: true,
    simulation_trained: true,
    activity: {
      ...resolved,
      reason: `Next ${resolved.actionType} selected by experimental se-path-multi-v1.`,
    },
    multi_action: {
      protocol: MULTI_PROTOCOL,
      activated: true,
      algorithm: 'maskable_ppo',
      action_type: resolved.actionType,
      topic: resolved.topic,
      launch_path: resolved.launchPath,
      uncalibrated_action_probability: upstream.uncalibrated_action_probability ?? null,
      weights_updated: false,
      reason: 'Native MaskablePPO checkpoint passed artifact checks.',
    },
  };
}

/**
 * Freeze exam-score + pass predictions at mock-attempt creation.
 */
export async function predictLiveExamEstimates({
  studentId,
  events,
  practiceSessions,
  cutoffIso,
}) {
  const assessment = assessSupervisedModelInputs({
    mode: 'exam',
    events,
    practiceSessions,
    cutoffIso,
    studentId,
  });
  if (!assessment.usable) {
    return failResult(assessment.code, assessment.reason, { assessment });
  }

  let scoreOut = null;
  let passOut = null;
  try {
    scoreOut = await callC4Ai('POST', '/v1/se-supervised-simulation-v1/exam-score', {
      body: { features: assessment.features, protocol: 'se-supervised-sim-v1' },
      timeoutMs: 20_000,
    });
    passOut = await callC4Ai('POST', '/v1/se-supervised-simulation-v1/pass', {
      body: { features: assessment.features, protocol: 'se-supervised-sim-v1' },
      timeoutMs: 20_000,
    });
  } catch (err) {
    return failResult(err.code || 'c4_ai_error', err.message, {
      assessment,
      partial: { scoreOut, passOut },
    });
  }

  const predictedScore =
    scoreOut?.exam_score_clipped_display ??
    scoreOut?.exam_score_raw ??
    scoreOut?.predicted_score ??
    null;
  const passProb = passOut?.p_pass ?? passOut?.pass_probability ?? null;
  const predictedPass =
    passProb != null ? passProb >= SIM_CLASSIFICATION_PROB_THRESHOLD : null;

  return {
    ok: true,
    usable: true,
    experimental: true,
    simulation_trained: true,
    real_student_validation: false,
    real_exam_validation: false,
    protocol: assessment.protocol,
    model_protocol: assessment.model_protocol,
    catalogue_hash: assessment.catalogue_hash,
    prediction_cutoff_utc: assessment.prediction_cutoff_utc,
    cold_start: assessment.cold_start,
    provenance: assessment.provenance,
    exam_score: {
      predicted_score: predictedScore,
      model_hash: scoreOut?.model_hash,
    },
    pass: {
      pass_probability: passProb,
      predicted_pass: predictedPass,
      pass_label_threshold: SIM_PASS_THRESHOLD,
      classification_prob_threshold: SIM_CLASSIFICATION_PROB_THRESHOLD,
      model_hash: passOut?.model_hash,
    },
    note:
      'Frozen experimental practice-readiness estimate (simulation-trained fraction-correct scale). ' +
      'Not a prediction of this C4 practice-bank quiz score (different topic coverage / length). ' +
      'Score cutoff 0.55 is synthetic training only. Prob 0.5 is the classifier threshold — not accuracy. ' +
      'Never recomputed from exam answers.',
  };
}
