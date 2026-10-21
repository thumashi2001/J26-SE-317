/**
 * C4-owned decision log. Recording an outcome is not a policy weight update.
 * Frozen se-path-sim-v1 inference stays inference. Self-report is never a measured reward.
 */

import { randomUUID } from 'crypto';

export const DECISIONS_COLLECTION = 'c4_policy_decisions';

export const REWARD_DEFINITION_VERSION = 'se-path-multi-v1-reward-1';

export async function recordPolicyDecision(db, { studentId, pathId, path }) {
  const activities = path?.activities || [];
  const eligible = activities.filter((a) => a.status === 'pending');
  const next =
    activities.find((a) => a.next_activity && a.status === 'pending') ||
    activities.find((a) => a.kind === 'c1_practice' && a.status === 'pending') ||
    null;
  const multi = path?.multi_action_policy || path?.modelRecommendation?.multi_action || {};
  const multiProtocol = multi.protocol || null;
  const multiActive = multi.activated === true && multiProtocol === 'se-path-multi-v2';
  const doc = {
    decision_id: randomUUID(),
    student_id: studentId,
    path_id: pathId,
    recorded_at: new Date().toISOString(),
    policy_id: multiActive
      ? 'se-path-multi-v2'
      : path?.modelRecommendation?.ok
        ? path.modelRecommendation.protocol || 'se-path-sim-v1'
        : 'weakest_stored_mastery_v1',
    policy_version: multiActive
      ? multi.training_revision || 'se-path-multi-v2'
      : path?.modelRecommendation?.ok
        ? path.modelRecommendation.protocol || 'se-path-sim-v1'
        : 'heuristic-activity-mix-v1',
    multi_action_policy: multiProtocol,
    multi_action_activated: multiActive,
    catalogue_hash: multi.catalogue_hash || path?.modelRecommendation?.catalogue_hash || null,
    checkpoint_sha256: multi.checkpoint_sha256 || null,
    selected_seed: multi.selected_seed ?? null,
    inference_only: true,
    weights_updated: false,
    feature_cutoff: new Date().toISOString(),
    prior_strength_assumed: path?.liveModelEpisode?.prior_strength ?? 0.45,
    prior_strength_note:
      'Assumed constant for the experimental se-path-sim-v1 practice pin only. Not an input to se-path-multi-v2.',
    eligible_actions: eligible.slice(0, 12).map((a) => ({
      activity_id: a.activity_id,
      kind: a.kind,
      topic: a.topic,
    })),
    action: next
      ? {
          activity_id: next.activity_id,
          kind: next.kind,
          topic: next.topic,
          launch_path: next.launch_path,
        }
      : null,
    outcome: null,
    reward: null,
    reward_definition_version: REWARD_DEFINITION_VERSION,
    reward_definition:
      'Measured reward only. practice_verified with correct/total → correct/total. ' +
      'Submitted quiz with a score → observed fraction. ' +
      'Revision self-report stores evidence_level=self_reported and reward=null. ' +
      'Coding stays unavailable. The same evidence_key is not rewarded twice. ' +
      'This log does not update weights. MaskablePPO is on-policy: do not replay this log into PPO and call it retraining. ' +
      'Offline improvement is a new Colab run or a separately specified off-policy method.',
  };
  await db.collection(DECISIONS_COLLECTION).insertOne(doc);
  return doc;
}

async function writeOutcomeOnce(db, latest, outcome, reward, rewardReason) {
  if (latest.outcome?.evidence_key && latest.outcome.evidence_key === outcome.evidence_key) {
    return latest;
  }
  if (latest.outcome) return latest;
  latest.outcome = { ...outcome, attached_at: new Date().toISOString() };
  latest.reward = reward;
  latest.reward_reason = rewardReason;
  latest.reward_definition_version = REWARD_DEFINITION_VERSION;
  latest.weights_updated = false;
  await db.collection(DECISIONS_COLLECTION).replaceOne({ decision_id: latest.decision_id }, latest);
  return latest;
}

export async function attachVerifiedOutcome(db, { studentId, pathId, activity }) {
  if (!activity || activity.completion_kind !== 'practice_verified') return null;
  const evidenceKey = `practice:${activity.practice_evidence?.sessionId || activity.activity_id}:${activity.completed_at || ''}`;
  const open = await db
    .collection(DECISIONS_COLLECTION)
    .find({ student_id: studentId, path_id: pathId, 'action.activity_id': activity.activity_id })
    .toArray();
  const pending = open.filter((d) => !d.outcome || d.outcome.evidence_key === evidenceKey);
  if (!pending.length) return null;
  const latest = pending.sort((a, b) => String(b.recorded_at).localeCompare(String(a.recorded_at)))[0];
  const ev = activity.practice_evidence || {};
  const total = Number(ev.total);
  const correct = Number(ev.correct);
  const reward =
    Number.isFinite(total) && total > 0 && Number.isFinite(correct)
      ? Math.min(1, Math.max(0, correct / total))
      : null;
  return writeOutcomeOnce(
    db,
    latest,
    {
      evidence_key: evidenceKey,
      completion_kind: 'practice_verified',
      evidence_level: 'c1_session_completed',
      completed_at: activity.completed_at || null,
    },
    reward,
    reward == null ? 'verified_without_score' : 'session_accuracy'
  );
}

export async function attachSelfReport(db, { studentId, pathId, activity }) {
  if (!activity || activity.completion_kind !== 'self_reported') return null;
  const evidenceKey = `self:${activity.activity_id}:${activity.completed_at || ''}`;
  const open = await db
    .collection(DECISIONS_COLLECTION)
    .find({ student_id: studentId, path_id: pathId, 'action.activity_id': activity.activity_id })
    .toArray();
  const pending = open.filter((d) => !d.outcome);
  if (!pending.length) return null;
  const latest = pending.sort((a, b) => String(b.recorded_at).localeCompare(String(a.recorded_at)))[0];
  return writeOutcomeOnce(
    db,
    latest,
    {
      evidence_key: evidenceKey,
      completion_kind: 'self_reported',
      evidence_level: 'self_reported',
      completed_at: activity.completed_at || null,
    },
    null,
    'self_report_is_not_measured_gain'
  );
}

export async function attachQuizOutcome(db, { studentId, topic, attemptId, scoreFraction }) {
  const evidenceKey = `quiz:${attemptId}`;
  const open = await db.collection(DECISIONS_COLLECTION).find({ student_id: studentId }).toArray();
  const pending = open.filter(
    (d) => !d.outcome && d.action?.kind === 'c4_quiz' && d.action?.topic === topic
  );
  if (!pending.length) return null;
  const latest = pending.sort((a, b) => String(b.recorded_at).localeCompare(String(a.recorded_at)))[0];
  const reward = Number.isFinite(scoreFraction) ? Math.min(1, Math.max(0, scoreFraction)) : null;
  return writeOutcomeOnce(
    db,
    latest,
    {
      evidence_key: evidenceKey,
      completion_kind: 'quiz_graded',
      evidence_level: 'c4_server_grade',
      attempt_id: attemptId,
    },
    reward,
    reward == null ? 'quiz_without_score' : 'observed_score_fraction'
  );
}
