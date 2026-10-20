/**
 * Read-only access to C1 learner state for sequencing.
 * Never writes mastery_state, mastery_history, learning_events, or practice_sessions.
 */

import { getTwin } from '../../c1/services/diagnosticService.js';
import { getInsights } from '../../c1/services/insightsService.js';

function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code;
  return err;
}

/**
 * @param {import('mongodb').Db} db
 * @param {string} studentId
 * @param {string} aiUrl - C1 AI URL for insights (optional forecast); failures degrade gracefully
 */
export async function readLearnerSnapshot(db, studentId, aiUrl) {
  const twin = await getTwin(db, studentId);
  if (!twin.diagnosticCompleted) {
    throw httpError(
      409,
      'Complete the C1 diagnostic test before creating a learning path',
      'diagnostic_required'
    );
  }

  let insights = null;
  let insightsError = null;
  try {
    insights = await getInsights(db, studentId, aiUrl);
  } catch (err) {
    // Insights may fail if C1 AI is down; twin scores remain usable.
    insightsError = err.message || 'insights_unavailable';
    insights = null;
  }

  return {
    studentId,
    twin,
    insights,
    insightsAvailable: !!insights,
    insightsError,
    snapshotAt: new Date().toISOString(),
  };
}

/** Public view of snapshot metadata stored on a path (no raw dump of unrelated fields). */
export function snapshotMeta(snapshot) {
  const mastery = snapshot.twin.mastery || {};
  const topics = {};
  for (const [topic, m] of Object.entries(mastery)) {
    topics[topic] = {
      score: m.score,
      answered: m.answered,
      correct: m.correct,
      practice_sessions: m.practice_sessions || 0,
      last_practiced: m.last_practiced,
    };
  }
  return {
    captured_at: snapshot.snapshotAt,
    twin_updated_at: snapshot.twin.updatedAt || null,
    insights_available: snapshot.insightsAvailable,
    insights_generated_at: snapshot.insights?.generatedAt || null,
    insights_error: snapshot.insightsError,
    mastery_scale: '0-100',
    topics,
  };
}
