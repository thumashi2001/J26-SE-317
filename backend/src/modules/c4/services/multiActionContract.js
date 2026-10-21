/**
 * Node twin of training_se_v2/multi_action/contract.py.
 * Shared observation layout for se-path-multi-v1 and se-path-multi-v2.
 * No prior_strength slot. Coding masked until content ids exist.
 */

import {
  SIM_CATALOGUE_HASH,
  SIM_MASTERY_THRESHOLD,
  SIM_N_TOPICS,
  SIM_ORDERED_TOPICS,
  simSemesterEligibilityMask,
} from '../data/simCatalogue.generated.js';

export const MULTI_PROTOCOL = 'se-path-multi-v1';
/** Same feature layout as v1. The v2 reward is clipped mastery change, not this vector. */
export const MULTI_PROTOCOL_V2 = 'se-path-multi-v2';
export const MULTI_ACTION_TYPES = Object.freeze(['practice', 'revision', 'quiz', 'coding']);
export const MULTI_N_ACTIONS = MULTI_ACTION_TYPES.length * SIM_N_TOPICS;
export const MULTI_EXTRA_NAMES = Object.freeze([
  'mean_mastery',
  'frac_mastered',
  'elapsed_env_step_frac',
  'recent_accuracy',
  'recent_accuracy_observed',
  'engagement_completion_rate',
  'engagement_observed',
  'exam_urgency',
  'exam_date_known',
]);
export const MULTI_OBS_DIM = 2 * SIM_N_TOPICS + MULTI_EXTRA_NAMES.length;
export const CODING_CONTENT_IDS = Object.freeze([]);

export function buildMultiObservation({
  mastery,
  available,
  elapsedEnvSteps = 0,
  maxEpisodeSteps = 40,
  recentAccuracy = null,
  engagementCompletionRate = null,
  examUrgency = null,
}) {
  if (!Array.isArray(mastery) || mastery.length !== SIM_N_TOPICS) {
    return { usable: false, code: 'bad_mastery' };
  }
  if (!Array.isArray(available) || available.length !== SIM_N_TOPICS) {
    return { usable: false, code: 'bad_available' };
  }
  const m = mastery.map((v, i) => (available[i] > 0.5 ? Math.min(1, Math.max(0, Number(v))) : 0));
  const a = available.map((v) => Math.min(1, Math.max(0, Number(v))));
  if (m.some((v) => !Number.isFinite(v)) || a.some((v) => !Number.isFinite(v))) {
    return { usable: false, code: 'non_finite' };
  }
  const idx = a.map((v, i) => (v > 0.5 ? i : -1)).filter((i) => i >= 0);
  const mean = idx.length ? idx.reduce((s, i) => s + m[i], 0) / idx.length : 0;
  const frac = idx.length
    ? idx.filter((i) => m[i] >= SIM_MASTERY_THRESHOLD).length / idx.length
    : 0;
  const step = Math.min(1, Math.max(0, Number(elapsedEnvSteps) || 0) / Math.max(1, maxEpisodeSteps));
  const recentObserved = recentAccuracy == null ? 0 : 1;
  const recentValue = recentAccuracy == null ? 0.5 : Math.min(1, Math.max(0, Number(recentAccuracy)));
  const engagementObserved = engagementCompletionRate == null ? 0 : 1;
  const engagementValue =
    engagementCompletionRate == null ? 0 : Math.min(1, Math.max(0, Number(engagementCompletionRate)));
  const urgencyKnown = examUrgency == null ? 0 : 1;
  const urgencyValue = examUrgency == null ? 0 : Math.min(1, Math.max(0, Number(examUrgency)));
  const observation = [
    ...m,
    ...a,
    mean,
    frac,
    step,
    recentValue,
    recentObserved,
    engagementValue,
    engagementObserved,
    urgencyValue,
    urgencyKnown,
  ];
  if (observation.length !== MULTI_OBS_DIM) return { usable: false, code: 'obs_dim' };
  return {
    usable: true,
    protocol: MULTI_PROTOCOL,
    catalogue_hash: SIM_CATALOGUE_HASH,
    observation,
    obs_dim: MULTI_OBS_DIM,
  };
}

export function buildMultiMask({ semester, available, mastery }) {
  if (semester !== 'Y3S1' && semester !== 'Y3S2') {
    return { usable: true, mask: Array(MULTI_N_ACTIONS).fill(false), code: 'semester_unavailable' };
  }
  let semesterOk;
  try {
    semesterOk = simSemesterEligibilityMask(semester);
  } catch {
    return { usable: false, code: 'bad_semester' };
  }
  const base = SIM_ORDERED_TOPICS.map(
    (_, i) => available[i] > 0.5 && semesterOk[i]
  );
  let practice = base.map((ok, i) => ok && mastery[i] < SIM_MASTERY_THRESHOLD);
  if (!practice.some(Boolean) && base.some(Boolean)) practice = [...base];
  const revision = [...base];
  const quiz = [...base];
  const coding = SIM_ORDERED_TOPICS.map((topic, i) => CODING_CONTENT_IDS.includes(topic) && base[i]);
  return {
    usable: true,
    mask: [...practice, ...revision, ...quiz, ...coding],
    coding_scheduled: coding.some(Boolean),
    n_actions: MULTI_N_ACTIONS,
  };
}

const ACTIVITY_KIND = Object.freeze({
  practice: 'c1_practice',
  revision: 'c1_revision',
  quiz: 'c4_quiz',
});

const KIND_TO_ACTION = Object.freeze({
  c1_practice: 'practice',
  c1_revision: 'revision',
  c4_quiz: 'quiz',
});

/** Drop plan activities that are already complete. Does not change mastery or availability. */
export function maskCompletedActivities(mask, completedActivityIds) {
  const next = Array.isArray(mask) ? mask.slice() : [];
  for (const id of completedActivityIds || []) {
    const text = String(id);
    const splitAt = text.indexOf(':');
    if (splitAt < 0) continue;
    const actionType = KIND_TO_ACTION[text.slice(0, splitAt)];
    const topicId = text.slice(splitAt + 1);
    const topicIndex = SIM_ORDERED_TOPICS.indexOf(topicId);
    if (!actionType || topicIndex < 0) continue;
    const actionIndex = MULTI_ACTION_TYPES.indexOf(actionType) * SIM_N_TOPICS + topicIndex;
    if (actionIndex >= 0 && actionIndex < next.length) next[actionIndex] = false;
  }
  return next;
}

function launchPathFor(actionType, topicId) {
  const topic = encodeURIComponent(topicId);
  if (actionType === 'practice') return `/c1/practice/${topic}`;
  if (actionType === 'revision') return `/c1/topic/${topic}`;
  if (actionType === 'quiz') return `/c4?tab=exams&focusTopic=${topic}`;
  return null;
}

/**
 * Map a policy action onto a real C4/C1 activity. Coding stays unavailable.
 * The topic must already be inside the semester/availability mask.
 */
export function resolveMultiAction({
  actionType,
  topicId,
  semester,
  available,
  mastery,
  protocol = MULTI_PROTOCOL,
}) {
  if (actionType === 'coding') {
    return {
      usable: false,
      code: 'coding_unavailable',
      reason: 'No coding exercise is registered, so a coding action cannot be launched.',
    };
  }
  const kind = ACTIVITY_KIND[actionType];
  const topicIndex = SIM_ORDERED_TOPICS.indexOf(topicId);
  if (!kind || topicIndex < 0) {
    return { usable: false, code: 'unknown_action', reason: 'Action type or topic is outside the catalogue.' };
  }
  const built = buildMultiMask({ semester, available, mastery });
  if (!built.usable) return { usable: false, code: built.code || 'bad_mask' };
  const actionIndex = MULTI_ACTION_TYPES.indexOf(actionType) * SIM_N_TOPICS + topicIndex;
  if (!built.mask[actionIndex]) {
    return {
      usable: false,
      code: 'ineligible',
      reason: 'That activity is outside the semester, availability, or mastery mask.',
    };
  }
  return {
    usable: true,
    protocol,
    actionType,
    actionIndex,
    topic: topicId,
    kind,
    activityId: `${kind}:${topicId}`,
    launchPath: launchPathFor(actionType, topicId),
  };
}
