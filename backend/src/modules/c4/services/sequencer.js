/**
 * Deterministic SE sequencing — NOT the ASSISTments MaskablePPO policy.
 *
 * Strategy: weakest_stored_mastery_v1
 * -----------------------------------
 * Eligible topics = intersection of:
 *   - C1 PRACTICE_QUESTIONS keys (real practice pages exist)
 *   - keys present on the student's C1 twin mastery map (practice start requires this)
 *
 * Ranking score (0–100, lower = higher priority):
 *   1. insights.topics[t].estimatedNow when it is a finite number
 *   2. else insights.topics[t].storedScore when finite
 *   3. else twin.mastery[t].score when finite
 *   4. else treat as missing → topic is listed under unavailable, not sequenced
 *
 * Tie-break: ascending topic ID (lexicographic).
 *
 * Missing / stale data:
 *   - Diagnostic incomplete → caller rejects (409) before sequencing.
 *   - Insights unavailable → use twin scores only; snapshot.insightsAvailable = false.
 *   - Topic on twin but not in practice catalogue → unavailable (no invented URL).
 *   - Topic in catalogue but not on twin → unavailable (C1 cannot start practice).
 *
 * Does not invent readiness %, confidence, or learning gains for display.
 */

import {
  PRACTICE_LAUNCH_PATH,
  SUPPORTED_PRACTICE_TOPICS,
  isSupportedPracticeTopic,
} from '../data/supportedTopics.js';

export const STRATEGY_ID = 'weakest_stored_mastery_v1';
export const STRATEGY_VERSION = '1.0.0';

function finiteNumber(v) {
  return typeof v === 'number' && Number.isFinite(v);
}

function rankingScore(topic, twinMastery, insightsTopics) {
  const insight = insightsTopics && insightsTopics[topic];
  if (insight) {
    if (finiteNumber(insight.estimatedNow)) return { score: insight.estimatedNow, scoreSource: 'estimatedNow' };
    if (finiteNumber(insight.storedScore)) return { score: insight.storedScore, scoreSource: 'storedScore' };
  }
  const entry = twinMastery[topic];
  if (entry && finiteNumber(entry.score)) return { score: entry.score, scoreSource: 'twin.score' };
  return null;
}

function reasonFor(topic, score, scoreSource) {
  const label =
    scoreSource === 'estimatedNow'
      ? 'estimated mastery now'
      : scoreSource === 'storedScore'
        ? 'stored mastery'
        : 'twin mastery score';
  return (
    `Prioritised because this topic has one of the lowest ${label} values ` +
    `among topics you can practise in C1 (${score} on the 0–100 scale).`
  );
}

/**
 * @param {object} input
 * @param {object} input.twinMastery - mastery map from C1 twin
 * @param {object|null} input.insightsTopics - insights.topics or null
 * @param {number|null} [input.horizon] - max pending activities to include (completed preserved separately)
 * @param {Array<{topic:string}>} [input.preserveCompleted] - completed activities to keep
 * @param {string[]} [input.boostTopics] - mock-quiz weak topics get a small ranking boost
 * @param {string|null} [input.pinFirstTopic] - eligible topic forced to front (model next activity)
 * @param {string|null} [input.pinReason] - reason text when pin is applied
 * @param {number|null} [input.examDaysUntil] - days until student exam date (urgency); null if unset
 * @param {{topic:string, kind:'practice'|'revision'|'quiz'}|null} [input.pinNextActivity]
 */
export function buildActivitySequence({
  twinMastery = {},
  insightsTopics = null,
  horizon = null,
  preserveCompleted = [],
  boostTopics = [],
  pinFirstTopic = null,
  pinReason = null,
  examDaysUntil = null,
  pinNextActivity = null,
}) {
  const boost = new Set(boostTopics || []);
  const twinKeys = new Set(Object.keys(twinMastery || {}));
  const unavailable = [];

  for (const topic of SUPPORTED_PRACTICE_TOPICS) {
    if (!twinKeys.has(topic)) {
      unavailable.push({
        topic,
        reason: 'Topic has C1 practice content but is not on this student twin yet (diagnostic coverage).',
      });
    }
  }
  for (const topic of twinKeys) {
    if (!isSupportedPracticeTopic(topic)) {
      unavailable.push({
        topic,
        reason: 'Topic is on the twin but has no C1 practice page/questions in the current catalogue.',
      });
    }
  }

  const completedIds = new Set(
    (preserveCompleted || []).map((a) => a.activity_id || `c1_practice:${a.topic}`)
  );
  const scored = [];
  for (const topic of SUPPORTED_PRACTICE_TOPICS) {
    if (!twinKeys.has(topic)) continue;
    const ranked = rankingScore(topic, twinMastery, insightsTopics);
    if (!ranked) {
      unavailable.push({ topic, reason: 'Mastery score missing or non-finite; cannot rank.' });
      continue;
    }
    scored.push({ topic, ...ranked });
  }

  // Weak mock-quiz topics get a small ranking boost (lower score = higher priority).
  // Exam urgency (deterministic): if the student supplied an exam date within 14 days,
  // subtract up to 10 points so weaker topics surface sooner. Missing exam date = no boost.
  const days =
    examDaysUntil != null && Number.isFinite(Number(examDaysUntil))
      ? Number(examDaysUntil)
      : null;
  const urgency =
    days != null && days >= 0 && days <= 14 ? Math.round((10 * (14 - days)) / 14) : 0;

  for (const row of scored) {
    if (boost.has(row.topic)) {
      row.score = Math.max(0, row.score - 8);
      row.scoreSource = `${row.scoreSource}+mock_weakness_boost`;
    }
    if (urgency > 0) {
      row.score = Math.max(0, row.score - urgency);
      row.scoreSource = `${row.scoreSource}+exam_urgency_${urgency}`;
      row.urgency = urgency;
    }
  }

  scored.sort((a, b) => {
    if (a.score !== b.score) return a.score - b.score;
    return a.topic < b.topic ? -1 : a.topic > b.topic ? 1 : 0;
  });

  let pending = scored;
  let pinned = false;
  const pin = typeof pinFirstTopic === 'string' ? pinFirstTopic.trim() : '';
  if (pin) {
    const idx = pending.findIndex((row) => row.topic === pin);
    if (idx > 0) {
      const [row] = pending.splice(idx, 1);
      row.scoreSource = `${row.scoreSource}+model_pin`;
      pending.unshift(row);
      pinned = true;
    } else if (idx === 0) {
      pending[0].scoreSource = `${pending[0].scoreSource}+model_pin`;
      pinned = true;
    }
  }
  if (horizon != null && Number.isFinite(horizon) && horizon >= 0) {
    pending = pending.slice(0, Math.floor(horizon));
  }

  const eligibleSince = new Date().toISOString();

  const completedActivities = (preserveCompleted || []).map((prev, i) => ({
    activity_id: prev.activity_id || `c1_practice:${prev.topic}`,
    topic: prev.topic,
    kind: prev.kind || 'c1_practice',
    launch_path: prev.launch_path || PRACTICE_LAUNCH_PATH(prev.topic),
    status:
      prev.status === 'practice_verified' || prev.completion_kind === 'practice_verified'
        ? 'practice_verified'
        : 'self_reported_complete',
    completion_kind: prev.completion_kind || 'self_reported',
    completed_at: prev.completed_at || null,
    practice_evidence: prev.practice_evidence || null,
    eligible_since: prev.eligible_since || null,
    recommendation_reason:
      prev.recommendation_reason || 'Kept from earlier path revision (completed).',
    rank_score: prev.rank_score ?? null,
    score_source: prev.score_source || null,
    order: i,
  }));

  let pendingActivities = [];
  pending.forEach((row, i) => {
    const isPinnedNext = pinned && i === 0 && row.topic === pin;
    const urgencyNote =
      row.urgency > 0
        ? ` Exam date is within 14 days (urgency −${row.urgency} on the 0–100 rank).`
        : '';
    const baseReason = isPinnedNext
      ? pinReason ||
        `Next practice chosen by experimental se-path-sim-v1 among eligible topics; calendar packing remains heuristic (${STRATEGY_ID}).`
      : reasonFor(row.topic, row.score, row.scoreSource);
    const practice = {
      activity_id: `c1_practice:${row.topic}`,
      topic: row.topic,
      kind: 'c1_practice',
      launch_path: PRACTICE_LAUNCH_PATH(row.topic),
      status: 'pending',
      completion_kind: null,
      completed_at: null,
      eligible_since: eligibleSince,
      recommendation_reason: `${baseReason}${urgencyNote}`,
      rank_score: row.score,
      score_source: row.scoreSource,
      next_activity: isPinnedNext,
      next_activity_source: isPinnedNext ? 'se-path-sim-v1' : null,
      recommendation_source: isPinnedNext ? 'se-path-sim-v1' : STRATEGY_ID,
    };
    const practiceId = `c1_practice:${row.topic}`;
    if (!completedIds.has(practiceId)) {
      pendingActivities.push(practice);
    }
    // Companion revision + quiz for the three highest-priority topics only.
    // Revision uses the existing C1 topic page. Quiz opens the C4 practice-bank mock.
    // Coding exercises are not emitted: no authorized coding launch exists.
    if (i < 3) {
      const revisionId = `c1_revision:${row.topic}`;
      if (!completedIds.has(revisionId)) {
        pendingActivities.push({
          activity_id: revisionId,
        topic: row.topic,
        kind: 'c1_revision',
        launch_path: `/c1/topic/${encodeURIComponent(row.topic)}`,
        status: 'pending',
        completion_kind: null,
        completed_at: null,
        eligible_since: eligibleSince,
        recommendation_reason:
          `Revision for a high-priority weak topic using the existing C1 topic page (not a new content engine).${urgencyNote}`,
        rank_score: row.score,
        score_source: row.scoreSource,
        next_activity: false,
        next_activity_source: null,
        recommendation_source: STRATEGY_ID,
      });
      }
      const quizId = `c4_quiz:${row.topic}`;
      if (!completedIds.has(quizId)) {
      pendingActivities.push({
        activity_id: quizId,
        topic: row.topic,
        kind: 'c4_quiz',
        launch_path: `/c4?tab=exams&focusTopic=${encodeURIComponent(row.topic)}`,
        status: 'pending',
        completion_kind: null,
        completed_at: null,
        eligible_since: eligibleSince,
        recommendation_reason:
          `Practice-bank mock quiz focused on this weak topic. Item difficulty adaptation is unavailable (no difficulty metadata).${urgencyNote}`,
        rank_score: row.score,
        score_source: row.scoreSource,
        next_activity: false,
        next_activity_source: null,
        recommendation_source: STRATEGY_ID,
      });
      }
    }
  });
  const multiSource =
    pinNextActivity?.source === 'se-path-multi-v2' ? 'se-path-multi-v2' : 'se-path-multi-v1';
  const multiKind = { practice: 'c1_practice', revision: 'c1_revision', quiz: 'c4_quiz' }[
    pinNextActivity?.kind
  ];
  const multiRow = multiKind ? scored.find((row) => row.topic === pinNextActivity.topic) : null;
  let multiPinned = false;
  if (multiRow && multiKind) {
    const activityId = `${multiKind}:${multiRow.topic}`;
    if (!completedIds.has(activityId)) {
      let activity = pendingActivities.find((row) => row.activity_id === activityId);
      if (!activity) {
        const launch =
          multiKind === 'c1_practice'
            ? PRACTICE_LAUNCH_PATH(multiRow.topic)
            : multiKind === 'c1_revision'
              ? `/c1/topic/${encodeURIComponent(multiRow.topic)}`
              : `/c4?tab=exams&focusTopic=${encodeURIComponent(multiRow.topic)}`;
        activity = {
          activity_id: activityId,
          topic: multiRow.topic,
          kind: multiKind,
          launch_path: launch,
          status: 'pending',
          completion_kind: null,
          completed_at: null,
          eligible_since: eligibleSince,
          recommendation_reason: pinNextActivity.reason || `Selected by ${multiSource}.`,
          rank_score: multiRow.score,
          score_source: multiRow.scoreSource,
          next_activity: false,
          next_activity_source: null,
          recommendation_source: multiSource,
        };
        pendingActivities.push(activity);
      }
      pendingActivities.forEach((row) => {
        row.next_activity = false;
        if (row.next_activity_source === 'se-path-multi-v1' || row.next_activity_source === 'se-path-multi-v2') {
          row.next_activity_source = null;
        }
      });
      const rest = pendingActivities.filter((row) => row.activity_id !== activityId);
      activity.next_activity = true;
      activity.next_activity_source = multiSource;
      activity.recommendation_source = multiSource;
      activity.recommendation_reason =
        pinNextActivity.reason ||
        `Next ${pinNextActivity.kind} selected by ${multiSource} among eligible activities.`;
      pendingActivities = [activity, ...rest];
      multiPinned = true;
    }
  }
  pendingActivities.forEach((a, i) => {
    a.order = completedActivities.length + i;
  });

  return {
    strategy: multiPinned
      ? `${STRATEGY_ID}+${multiSource}_next`
      : pinned
        ? `${STRATEGY_ID}+se-path-sim-v1_next`
        : STRATEGY_ID,
    strategy_version: STRATEGY_VERSION,
    next_activity_topic: multiPinned ? multiRow.topic : pinned ? pin : null,
    next_activity_source: multiPinned ? multiSource : pinned ? 'se-path-sim-v1' : null,
    exam_urgency_points: urgency,
    activity_type_limits: {
      coding_exercise: {
        scheduled: false,
        reason:
          'No authorized coding-exercise interface is available (C3 student routes are not implemented). ' +
          'C4 does not invent coding tasks or rename MCQs as coding.',
      },
    },
    activities: [...completedActivities, ...pendingActivities],
    unavailable,
  };
}
