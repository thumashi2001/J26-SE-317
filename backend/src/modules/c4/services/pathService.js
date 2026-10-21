/**
 * C4 learning-path persistence (C4-owned collections only).
 * Does not write to C1 mastery/history/events collections.
 */

import { randomUUID } from 'crypto';
import { readLearnerSnapshot, snapshotMeta } from './c1Reader.js';
import { STRATEGY_ID, STRATEGY_VERSION, buildActivitySequence } from './sequencer.js';
import { buildDailySchedule, parseSchedulePrefs, parseIsoDate } from './scheduleBuilder.js';
import { syncPathPracticeEvidence } from './practiceSync.js';
import { summarizeEngagement } from './engagementSummary.js';
import {
  assessPathModelInputs,
  assessSupervisedModelInputs,
  countPracticeAttemptSteps,
  initialPathEpisodeState,
} from './liveModelAdapter.js';
import {
  predictLiveMultiAction,
  predictLiveMultiActionV2,
  predictLivePathRecommendation,
} from './liveInference.js';
import { latestWeakTopics } from './examService.js';
import { attachVerifiedOutcome, attachSelfReport, recordPolicyDecision } from './policyDecisionLog.js';

export const PATHS_COLLECTION = 'c4_learning_paths';
export const REVISIONS_COLLECTION = 'c4_learning_path_revisions';

function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code;
  return err;
}

function publicActivity(a) {
  return {
    activityId: a.activity_id,
    topic: a.topic,
    kind: a.kind,
    launchPath: a.launch_path,
    status: a.status,
    completionKind: a.completion_kind,
    completedAt: a.completed_at,
    recommendationReason: a.recommendation_reason,
    recommendationSource: a.recommendation_source || null,
    rankScore: a.rank_score,
    scoreSource: a.score_source,
    order: a.order,
    scheduledDate: a.scheduled_date || null,
    estimatedMinutes: a.estimated_minutes ?? null,
    scheduleStatus: a.schedule_status || null,
    practiceEvidence: a.practice_evidence || null,
    eligibleSince: a.eligible_since || null,
    nextActivity: !!a.next_activity,
    nextActivitySource: a.next_activity_source || null,
  };
}

/** Load C1 practice events and count attempt steps for path observation. */
async function loadEpisodeAttemptSteps(db, studentId, episode) {
  const [events, practiceSessions] = await Promise.all([
    db.collection('learning_events').find({ student_id: studentId }).toArray(),
    db.collection('practice_sessions').find({ student_id: studentId }).toArray(),
  ]);
  const steps = countPracticeAttemptSteps({
    events,
    practiceSessions,
    sinceIso: episode?.created_at || null,
  });
  return { events, practiceSessions, steps };
}

function examDaysFromPrefs(schedulePrefs, now = new Date()) {
  const exam = schedulePrefs?.examDate ? parseIsoDate(schedulePrefs.examDate) : null;
  if (!exam) return null;
  const today = new Date(now);
  today.setHours(0, 0, 0, 0);
  return Math.round((exam.getTime() - today.getTime()) / 86400000);
}
function sourceAfterRecommendation(modelRecommendation, previous) {
  const protocol = modelRecommendation?.protocol;
  if (protocol === 'se-path-multi-v1' || protocol === 'se-path-multi-v2') return previous || null;
  if (modelRecommendation?.ok) return 'se-path-sim-v1';
  return previous || null;
}

function pinFromRecommendation(modelRecommendation) {
  if (
    (modelRecommendation?.protocol === 'se-path-multi-v2' ||
      modelRecommendation?.protocol === 'se-path-multi-v1') &&
    modelRecommendation.activity?.usable
  ) {
    return {
      pinFirstTopic: null,
      pinReason: null,
      pinNextActivity: {
        topic: modelRecommendation.activity.topic,
        kind: modelRecommendation.activity.actionType,
        reason: modelRecommendation.activity.reason,
        source: modelRecommendation.protocol,
      },
    };
  }
  if (modelRecommendation?.ok && modelRecommendation.recommended_topic) {
    return {
      pinFirstTopic: modelRecommendation.recommended_topic,
      pinReason:
        modelRecommendation.note ||
        'Next practice chosen by experimental se-path-sim-v1 among eligible topics.',
      pinNextActivity: null,
    };
  }
  return { pinFirstTopic: null, pinReason: null, pinNextActivity: null };
}

function publicSchedule(schedule) {
  if (!schedule) return null;
  return {
    prefs: schedule.prefs,
    days: schedule.days,
    unscheduled: schedule.unscheduled,
    summary: schedule.summary,
  };
}

function publicPath(doc) {
  if (!doc) return null;
  return {
    pathId: doc.path_id,
    studentId: doc.student_id,
    status: doc.status,
    revision: doc.revision,
    strategy: doc.strategy,
    strategyVersion: doc.strategy_version,
    createdAt: doc.created_at,
    updatedAt: doc.updated_at,
    sourceSnapshotAt: doc.source_snapshot_at,
    sourceSnapshot: doc.source_snapshot,
    goal: doc.goal || null,
    horizon: doc.horizon,
    schedule: publicSchedule(doc.schedule),
    activities: (doc.activities || []).map(publicActivity),
    unavailable: doc.unavailable || [],
    clientRequestId: doc.client_request_id || null,
    modelEstimates: doc.model_estimates || null,
    modelRecommendation: doc.model_recommendation || null,
    liveModelEpisode: doc.live_model_episode || null,
    nextActivityTopic: doc.next_activity_topic || null,
    nextActivitySource: doc.next_activity_source || null,
    planningHints: doc.planning_hints || null,
    multiActionPolicy: doc.multi_action_policy || {
      protocol: 'se-path-multi-v2',
      activated: false,
      reason:
        'se-path-multi-v2 was not used for this plan. Practice, revision and quiz order stays on the heuristic. Coding stays unavailable. An older experimental practice pin is not this policy.',
    },
    examUrgencyPoints: doc.exam_urgency_points || 0,
    engagement: summarizeEngagement(doc.activities || []),
    activityTypeLimits: doc.activity_type_limits || null,
    note:
      'Daily calendar packing: weakest_stored_mastery_v1 (heuristic). ' +
      'When se-path-multi-v2 is active it may pin the next eligible practice, revision, or quiz. ' +
      'Otherwise an experimental se-path-sim-v1 practice pin may apply. ' +
      'A heuristic or older-model activity is not labelled as se-path-multi-v2. ' +
      'Self-reported completion does not write C1 mastery. Practice-verified uses C1 records only.',
  };
}

async function findActive(db, studentId) {
  return db.collection(PATHS_COLLECTION).findOne({ student_id: studentId, status: 'active' });
}

async function findById(db, pathId) {
  return db.collection(PATHS_COLLECTION).findOne({ path_id: pathId });
}

function assertOwner(doc, studentId) {
  if (!doc) throw httpError(404, 'Learning path not found');
  if (doc.student_id !== studentId) {
    throw httpError(403, 'You do not have access to this learning path');
  }
}

function attachSchedule(activities, schedulePrefs, now) {
  const built = buildDailySchedule({ activities, prefs: schedulePrefs, now });
  return { activities: built.activities, schedule: built };
}

function modelEstimatesFor(snapshot, episode = null, elapsedEnvSteps = 0) {
  const semester = snapshot.twin?.semester || null;
  const path = assessPathModelInputs({
    semester,
    twinMastery: snapshot.twin?.mastery || {},
    elapsedEnvSteps,
    priorStrength: episode?.prior_strength,
    priorStrengthProvenance: episode?.prior_strength_provenance,
  });
  return {
    path,
    supervised: assessSupervisedModelInputs(),
    label:
      'Experimental estimates from simulation-trained models when live inputs allow. ' +
      'Calendar packing uses weakest_stored_mastery_v1; next activity may be model-pinned. ' +
      'Response model stays blocked (no item difficulty).',
  };
}

async function runPathRecommendation(snapshot, episode, elapsedEnvSteps = 0, extras = {}) {
  const semester = snapshot.twin?.semester || null;
  const twinMastery = snapshot.twin?.mastery || {};
  const callArgs = {
    semester,
    twinMastery,
    elapsedEnvSteps,
    engagementCompletionRate: extras.engagementCompletionRate ?? null,
    examDaysUntil: extras.examDaysUntil ?? null,
    completedActivityIds: extras.completedActivityIds || [],
  };
  let multiV2 = {
    ok: false,
    multi_action: {
      protocol: 'se-path-multi-v2',
      activated: false,
      reason: 'se-path-multi-v2 was not called.',
    },
  };
  try {
    multiV2 = await predictLiveMultiActionV2(callArgs);
  } catch (err) {
    multiV2 = {
      ok: false,
      multi_action: {
        protocol: 'se-path-multi-v2',
        activated: false,
        reason: err.message || 'se-path-multi-v2 call failed',
      },
    };
  }
  if (multiV2.ok) return multiV2;
  let multi = {
    ok: false,
    multi_action: multiV2.multi_action,
  };
  try {
    const historical = await predictLiveMultiAction(callArgs);
    if (historical.ok) return { ...historical, multi_action: multiV2.multi_action };
    multi = historical;
  } catch (err) {
    multi = {
      ok: false,
      multi_action: {
        ...multiV2.multi_action,
        historical_reason: err.message || 'se-path-multi-v1 call failed',
      },
    };
  }
  if (multi.ok) return multi;
  try {
    const v1 = await predictLivePathRecommendation({
      semester,
      twinMastery,
      elapsedEnvSteps,
      priorStrength: episode?.prior_strength,
      priorStrengthProvenance: episode?.prior_strength_provenance,
    });
    return { ...v1, multi_action: multiV2.multi_action };
  } catch (err) {
    return {
      ok: false,
      usable: false,
      code: err.code || 'path_inference_error',
      reason: err.message || 'Path inference failed',
      fallback: 'weakest_stored_mastery_v1',
      experimental: true,
      multi_action: multiV2.multi_action,
    };
  }
}

async function planningHintsFor(db, studentId) {
  const weak = await latestWeakTopics(db, studentId);
  return {
    mockExamWeakTopics: weak.topics,
    fromAttemptId: weak.attemptId,
    note: weak.topics.length
      ? 'Recent mock-quiz weak topics may be prioritised on the next replan ranking among eligible topics.'
      : 'No submitted C4 mock quiz yet.',
  };
}

function buildDoc({
  studentId,
  snapshot,
  horizon,
  goal,
  clientRequestId,
  preserveCompleted,
  revision,
  schedulePrefs,
  modelEstimates,
  modelRecommendation,
  liveModelEpisode,
  planningHints,
  pathId,
}) {
  const { pinFirstTopic, pinReason, pinNextActivity } = pinFromRecommendation(modelRecommendation);
  const seq = buildActivitySequence({
    twinMastery: snapshot.twin.mastery || {},
    insightsTopics: snapshot.insights?.topics || null,
    horizon: horizon == null ? null : Number(horizon),
    preserveCompleted,
    boostTopics: planningHints?.mockExamWeakTopics || [],
    pinFirstTopic,
    pinReason,
    pinNextActivity,
    examDaysUntil: examDaysFromPrefs(schedulePrefs),
  });
  const now = new Date();
  const { activities, schedule } = attachSchedule(seq.activities, schedulePrefs, now);
  return {
    path_id: pathId || randomUUID(),
    student_id: studentId,
    status: 'active',
    revision: revision || 1,
    strategy: seq.strategy || STRATEGY_ID,
    strategy_version: STRATEGY_VERSION,
    created_at: now,
    updated_at: now,
    source_snapshot_at: snapshot.snapshotAt,
    source_snapshot: snapshotMeta(snapshot),
    goal: goal || null,
    horizon: horizon == null ? null : Number(horizon),
    schedule_prefs: schedulePrefs,
    schedule,
    activities,
    unavailable: seq.unavailable,
    next_activity_topic: seq.next_activity_topic || null,
    next_activity_source: seq.next_activity_source || null,
    activity_type_limits: seq.activity_type_limits || null,
    exam_urgency_points: seq.exam_urgency_points || 0,
    client_request_id: clientRequestId || null,
    model_estimates: modelEstimates,
    model_recommendation: modelRecommendation || null,
    live_model_episode: liveModelEpisode || null,
    planning_hints: planningHints,
    multi_action_policy: modelRecommendation?.multi_action || {
      protocol: 'se-path-multi-v2',
      activated: false,
      reason:
        'se-path-multi-v2 was not used for this plan. Practice, revision and quiz order stays on the heuristic.',
    },
  };
}

export async function createPath(db, studentId, body, aiUrl) {
  const forceNew = !!body?.forceNew;
  const clientRequestId =
    typeof body?.clientRequestId === 'string' && body.clientRequestId.trim()
      ? body.clientRequestId.trim()
      : null;

  if (clientRequestId) {
    const byKey = await db.collection(PATHS_COLLECTION).findOne({
      student_id: studentId,
      client_request_id: clientRequestId,
    });
    if (byKey) return { ...publicPath(byKey), reused: true, reuseReason: 'client_request_id' };
  }

  const existing = await findActive(db, studentId);
  if (existing && !forceNew) {
    return { ...publicPath(existing), reused: true, reuseReason: 'active_path_exists' };
  }

  const snapshot = await readLearnerSnapshot(db, studentId, aiUrl);
  let horizon = body?.horizon;
  if (horizon != null) {
    horizon = Number(horizon);
    if (!Number.isFinite(horizon) || horizon < 0 || horizon > 50) {
      throw httpError(400, 'horizon must be a number between 0 and 50');
    }
  }
  const goal =
    body?.goal && typeof body.goal === 'object'
      ? { label: typeof body.goal.label === 'string' ? body.goal.label : null }
      : null;

  const schedulePrefs = parseSchedulePrefs(body || {}, new Date());
  const liveModelEpisode = initialPathEpisodeState(
    snapshot.twin?.mastery || {},
    snapshot.twin?.semester || null
  );
  const planningHints = await planningHintsFor(db, studentId);
  const { steps } = await loadEpisodeAttemptSteps(db, studentId, liveModelEpisode);
  const modelEstimates = modelEstimatesFor(snapshot, liveModelEpisode, steps);
  const modelRecommendation = await runPathRecommendation(snapshot, liveModelEpisode, steps, {
    examDaysUntil: examDaysFromPrefs(schedulePrefs),
    engagementCompletionRate: null,
  });

  if (existing && forceNew) {
    await archiveActive(db, existing, 'superseded_by_create');
  }

  const doc = buildDoc({
    studentId,
    snapshot,
    horizon: horizon ?? null,
    goal,
    clientRequestId,
    preserveCompleted: [],
    revision: 1,
    schedulePrefs,
    modelEstimates,
    modelRecommendation,
    liveModelEpisode,
    planningHints,
  });
  await db.collection(PATHS_COLLECTION).insertOne(doc);
  await recordPolicyDecision(db, {
    studentId,
    pathId: doc.path_id,
    path: {
      activities: doc.activities,
      modelRecommendation: doc.model_recommendation,
      liveModelEpisode: doc.live_model_episode,
    },
  });
  return { ...publicPath(doc), reused: false };
}

async function archiveActive(db, doc, reason) {
  const now = new Date();
  await db.collection(REVISIONS_COLLECTION).insertOne({
    revision_id: randomUUID(),
    path_id: doc.path_id,
    student_id: doc.student_id,
    revision: doc.revision,
    archived_at: now,
    reason,
    snapshot: {
      strategy: doc.strategy,
      strategy_version: doc.strategy_version,
      source_snapshot_at: doc.source_snapshot_at,
      source_snapshot: doc.source_snapshot,
      activities: doc.activities,
      unavailable: doc.unavailable,
      goal: doc.goal,
      horizon: doc.horizon,
      schedule_prefs: doc.schedule_prefs,
      schedule: doc.schedule,
    },
  });
  await db.collection(PATHS_COLLECTION).replaceOne(
    { path_id: doc.path_id },
    { ...doc, status: 'superseded', updated_at: now, superseded_reason: reason }
  );
}

export async function listPaths(db, studentId) {
  const rows = await db.collection(PATHS_COLLECTION).find({ student_id: studentId }).toArray();
  rows.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  return { studentId, paths: rows.map(publicPath) };
}

export async function getActivePath(db, studentId) {
  const doc = await findActive(db, studentId);
  if (!doc) throw httpError(404, 'No active learning path', 'no_active_path');
  return publicPath(doc);
}

export async function getPath(db, studentId, pathId) {
  const doc = await findById(db, pathId);
  assertOwner(doc, studentId);
  return publicPath(doc);
}

export async function listRevisions(db, studentId, pathId) {
  const doc = await findById(db, pathId);
  assertOwner(doc, studentId);
  const rows = await db.collection(REVISIONS_COLLECTION).find({ path_id: pathId }).toArray();
  rows.sort((a, b) => b.revision - a.revision);
  return {
    pathId,
    studentId,
    revisions: rows.map((r) => ({
      revisionId: r.revision_id,
      revision: r.revision,
      archivedAt: r.archived_at,
      reason: r.reason,
      activityCount: (r.snapshot?.activities || []).length,
      sourceSnapshotAt: r.snapshot?.source_snapshot_at || null,
    })),
  };
}

/**
 * Refresh C1 snapshot metadata on the path and sync practice evidence.
 * Optimistic concurrency: if expectedRevision / expectedUpdatedAt is supplied and
 * the path changed meanwhile, returns 409 instead of silently overwriting.
 */
export async function refreshPath(db, studentId, pathId, aiUrl, body = {}) {
  const doc = await findById(db, pathId);
  assertOwner(doc, studentId);
  if (doc.status !== 'active') throw httpError(409, 'Only the active path can be refreshed');

  if (body?.expectedRevision != null && Number(body.expectedRevision) !== doc.revision) {
    throw httpError(
      409,
      'Path revision changed since you loaded it. Reload and refresh again.',
      'concurrent_modification'
    );
  }
  if (body?.expectedUpdatedAt) {
    const expected = new Date(body.expectedUpdatedAt).getTime();
    const actual = new Date(doc.updated_at).getTime();
    if (Number.isFinite(expected) && expected !== actual) {
      throw httpError(
        409,
        'Path was updated since you loaded it. Reload and refresh again.',
        'concurrent_modification'
      );
    }
  }

  const snapshot = await readLearnerSnapshot(db, studentId, aiUrl);
  const sync = await syncPathPracticeEvidence(db, doc);

  // Re-read before write: merge only practice fields if user progressed concurrently.
  const latest = await findById(db, pathId);
  assertOwner(latest, studentId);
  if (latest.revision !== doc.revision || String(latest.updated_at) !== String(doc.updated_at)) {
    // Apply sync onto latest activities by activity_id instead of blind overwrite.
    const byId = new Map(sync.activities.map((a) => [a.activity_id, a]));
    const merged = (latest.activities || []).map((a) => {
      const s = byId.get(a.activity_id);
      if (!s) return a;
      if (a.completion_kind === 'practice_verified') return a;
      if (
        s.completion_kind === 'practice_verified' ||
        s.completion_kind === 'practice_observed'
      ) {
        return {
          ...a,
          status: s.status,
          completion_kind: s.completion_kind,
          completed_at: s.completed_at,
          practice_evidence: s.practice_evidence,
        };
      }
      return a;
    });
    const now = new Date();
    const schedulePrefs = latest.schedule_prefs || parseSchedulePrefs({}, now);
    const { activities, schedule } = attachSchedule(merged, schedulePrefs, now);
    const episode = latest.live_model_episode || initialPathEpisodeState();
    const { steps } = await loadEpisodeAttemptSteps(db, studentId, episode);
    const modelRecommendation = await runPathRecommendation(snapshot, episode, steps, {
      examDaysUntil: examDaysFromPrefs(schedulePrefs),
      engagementCompletionRate: summarizeEngagement(merged).completionRate,
    });
    const next = {
      ...latest,
      activities,
      schedule,
      updated_at: now,
      last_refreshed_at: now.toISOString(),
      source_snapshot_at: snapshot.snapshotAt,
      source_snapshot: snapshotMeta(snapshot),
      live_model_episode: episode,
      model_estimates: modelEstimatesFor(snapshot, episode, steps),
      model_recommendation: modelRecommendation,
      next_activity_topic: modelRecommendation?.recommended_topic || latest.next_activity_topic || null,
      next_activity_source: sourceAfterRecommendation(modelRecommendation, latest.next_activity_source),
      multi_action_policy: modelRecommendation?.multi_action || latest.multi_action_policy || null,
      planning_hints: await planningHintsFor(db, studentId),
      refresh_note:
        'Merged C1 practice evidence onto a concurrently updated path (revision preserved).',
    };
    await db.collection(PATHS_COLLECTION).replaceOne({ path_id: pathId }, next);
    return { ...publicPath(next), refreshNote: next.refresh_note, mergedConcurrent: true };
  }

  const now = new Date();
  const schedulePrefs = doc.schedule_prefs || parseSchedulePrefs({}, now);
  const { activities, schedule } = attachSchedule(sync.activities, schedulePrefs, now);
  const episode = doc.live_model_episode || initialPathEpisodeState();
  const { steps } = await loadEpisodeAttemptSteps(db, studentId, episode);
  const modelRecommendation = await runPathRecommendation(snapshot, episode, steps, {
    examDaysUntil: examDaysFromPrefs(schedulePrefs),
    engagementCompletionRate: summarizeEngagement(activities).completionRate,
  });

  const next = {
    ...doc,
    activities,
    schedule,
    updated_at: now,
    last_refreshed_at: now.toISOString(),
    source_snapshot_at: snapshot.snapshotAt,
    source_snapshot: snapshotMeta(snapshot),
    live_model_episode: episode,
    model_estimates: modelEstimatesFor(snapshot, episode, steps),
    model_recommendation: modelRecommendation,
    next_activity_topic: modelRecommendation?.recommended_topic || doc.next_activity_topic || null,
    next_activity_source: sourceAfterRecommendation(modelRecommendation, doc.next_activity_source),
    multi_action_policy: modelRecommendation?.multi_action || doc.multi_action_policy || null,
    planning_hints: await planningHintsFor(db, studentId),
    refresh_note: sync.changed
      ? 'Updated practice evidence from C1 records and refreshed twin snapshot. Experimental path policy recomputed.'
      : 'Twin snapshot refreshed. Experimental path policy recomputed. No new practice evidence found.',
  };
  await db.collection(PATHS_COLLECTION).replaceOne({ path_id: pathId }, next);
  return { ...publicPath(next), refreshNote: next.refresh_note };
}

export async function recordProgress(db, studentId, pathId, body) {
  const doc = await findById(db, pathId);
  assertOwner(doc, studentId);
  if (doc.status !== 'active') throw httpError(409, 'Only the active path accepts progress');

  const activityId = body?.activityId;
  if (!activityId || typeof activityId !== 'string') {
    throw httpError(400, 'activityId is required');
  }
  const status = body?.status || 'self_reported_complete';
  if (status !== 'self_reported_complete') {
    throw httpError(400, 'Only status self_reported_complete is supported for this endpoint');
  }

  const idx = doc.activities.findIndex((a) => a.activity_id === activityId);
  if (idx < 0) throw httpError(404, 'Activity not found on this path');

  const activity = doc.activities[idx];
  if (activity.status === 'self_reported_complete' || activity.status === 'practice_verified') {
    return {
      ...publicPath(doc),
      progress: {
        activityId,
        completionKind: activity.completion_kind,
        duplicate: true,
        note: 'Already marked complete; no C1 mastery write occurred.',
      },
    };
  }

  const now = new Date();
  doc.activities[idx] = {
    ...activity,
    status: 'self_reported_complete',
    completion_kind: 'self_reported',
    completed_at: now.toISOString(),
  };
  const schedulePrefs = doc.schedule_prefs || parseSchedulePrefs({}, now);
  const rebuilt = attachSchedule(doc.activities, schedulePrefs, now);
  doc.activities = rebuilt.activities;
  doc.schedule = rebuilt.schedule;
  doc.updated_at = now;
  await db.collection(PATHS_COLLECTION).replaceOne({ path_id: pathId }, doc);
  await attachSelfReport(db, { studentId, pathId, activity: doc.activities[idx] });

  return {
    ...publicPath(doc),
    progress: {
      activityId,
      completionKind: 'self_reported',
      duplicate: false,
      note:
        'Self-reported path progress only. Launch C1 practice to record assessed answers; ' +
        'use Refresh to mark practice-verified when C1 sessions/events exist.',
    },
  };
}

export async function replanPath(db, studentId, pathId, body, aiUrl) {
  const doc = await findById(db, pathId);
  assertOwner(doc, studentId);
  if (doc.status !== 'active') throw httpError(409, 'Only the active path can be replanned');
  if (body?.expectedRevision != null && Number(body.expectedRevision) !== doc.revision) {
    throw httpError(
      409,
      'Path revision changed since you loaded it. Reload and replan again.',
      'concurrent_modification'
    );
  }

  const snapshot = await readLearnerSnapshot(db, studentId, aiUrl);
  let horizon = body?.horizon != null ? Number(body.horizon) : doc.horizon;
  if (horizon != null && (!Number.isFinite(horizon) || horizon < 0 || horizon > 50)) {
    throw httpError(400, 'horizon must be a number between 0 and 50');
  }

  const schedulePrefs = parseSchedulePrefs(
    {
      ...(doc.schedule_prefs || {}),
      studyStartDate: body?.studyStartDate ?? doc.schedule_prefs?.studyStartDate,
      examDate: body?.examDate !== undefined ? body.examDate : doc.schedule_prefs?.examDate,
      dailyMinutesBudget: body?.dailyMinutesBudget ?? doc.schedule_prefs?.dailyMinutesBudget,
      studyDays: body?.studyDays ?? doc.schedule_prefs?.studyDays,
      planDayCount: body?.planDayCount ?? doc.schedule_prefs?.planDayCount,
      estimatedMinutesPerActivity:
        body?.estimatedMinutesPerActivity ?? doc.schedule_prefs?.estimatedMinutesPerActivity,
    },
    new Date()
  );

  const sync = await syncPathPracticeEvidence(db, doc);
  const preserveCompleted = sync.activities.filter(
    (a) => a.status === 'self_reported_complete' || a.status === 'practice_verified'
  );

  await db.collection(REVISIONS_COLLECTION).insertOne({
    revision_id: randomUUID(),
    path_id: doc.path_id,
    student_id: doc.student_id,
    revision: doc.revision,
    archived_at: new Date(),
    reason: 'replan',
    snapshot: {
      strategy: doc.strategy,
      strategy_version: doc.strategy_version,
      source_snapshot_at: doc.source_snapshot_at,
      source_snapshot: doc.source_snapshot,
      activities: doc.activities,
      unavailable: doc.unavailable,
      goal: doc.goal,
      horizon: doc.horizon,
      schedule_prefs: doc.schedule_prefs,
      schedule: doc.schedule,
    },
  });

  const planningHints = await planningHintsFor(db, studentId);
  const episode = doc.live_model_episode || initialPathEpisodeState();
  const { steps } = await loadEpisodeAttemptSteps(db, studentId, episode);
  const modelEstimates = modelEstimatesFor(snapshot, episode, steps);
  const modelRecommendation = await runPathRecommendation(snapshot, episode, steps, {
    examDaysUntil: examDaysFromPrefs(schedulePrefs),
    engagementCompletionRate: summarizeEngagement(sync.activities).completionRate,
    completedActivityIds: preserveCompleted.map((a) => a.activity_id),
  });
  const { pinFirstTopic, pinReason, pinNextActivity } = pinFromRecommendation(modelRecommendation);
  const seq = buildActivitySequence({
    twinMastery: snapshot.twin.mastery || {},
    insightsTopics: snapshot.insights?.topics || null,
    horizon,
    preserveCompleted,
    boostTopics: planningHints.mockExamWeakTopics || [],
    pinFirstTopic,
    pinReason,
    pinNextActivity,
    examDaysUntil: examDaysFromPrefs(schedulePrefs),
  });
  const now = new Date();
  const { activities, schedule } = attachSchedule(seq.activities, schedulePrefs, now);

  const next = {
    ...doc,
    revision: doc.revision + 1,
    updated_at: now,
    source_snapshot_at: snapshot.snapshotAt,
    source_snapshot: snapshotMeta(snapshot),
    horizon: horizon ?? null,
    schedule_prefs: schedulePrefs,
    schedule,
    activities,
    unavailable: seq.unavailable,
    strategy: seq.strategy || STRATEGY_ID,
    strategy_version: STRATEGY_VERSION,
    next_activity_topic: seq.next_activity_topic || null,
    next_activity_source: seq.next_activity_source || null,
    activity_type_limits: seq.activity_type_limits || null,
    exam_urgency_points: seq.exam_urgency_points || 0,
    live_model_episode: episode,
    model_estimates: modelEstimates,
    model_recommendation: modelRecommendation,
    multi_action_policy: modelRecommendation?.multi_action || {
      protocol: 'se-path-multi-v2',
      activated: false,
      reason:
        'se-path-multi-v2 was not used for this plan. Practice, revision and quiz order stays on the heuristic.',
    },
    planning_hints: planningHints,
    replan_note:
      'Pending activities re-ranked from refreshed C1 state; completed (self-reported or practice-verified) kept. ' +
      'se-path-multi-v2 may pin the next eligible practice, revision, or quiz. Calendar packing stays heuristic. ' +
      'A heuristic or older-model activity is not labelled as se-path-multi-v2.',
  };
  const latest = await findById(db, pathId);
  if (!latest || latest.revision !== doc.revision) {
    throw httpError(
      409,
      'Path revision changed while replanning. Reload and try again.',
      'concurrent_modification'
    );
  }
  await db.collection(PATHS_COLLECTION).replaceOne({ path_id: pathId }, next);
  await recordPolicyDecision(db, {
    studentId,
    pathId,
    path: {
      activities: next.activities,
      modelRecommendation: next.model_recommendation,
      liveModelEpisode: next.live_model_episode,
    },
  });
  for (const a of next.activities || []) {
    if (a.completion_kind === 'practice_verified') {
      await attachVerifiedOutcome(db, { studentId, pathId, activity: a });
    }
  }
  return publicPath(next);
}
