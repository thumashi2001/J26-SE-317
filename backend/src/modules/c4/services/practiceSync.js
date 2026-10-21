/**
 * Read-only association of C1 practice evidence with C4 activities.
 * Never writes C1 collections.
 *
 * Completion criteria (matches C1 practiceService):
 * - practice_verified: a non-abandoned practice_sessions row with completed=true
 *   and completed_at >= activity.eligible_since, not already claimed by another activity.
 * - practice_observed: open session with ≥1 answered item, or quiz_answer events in window,
 *   without a finished session — participation only, not activity completion.
 *
 * A single quiz_answer is never enough for practice_verified.
 */

function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code;
  return err;
}

function toDate(v) {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Sessions already claimed by practice_verified activities on this path. */
function claimedSessionIds(activities) {
  const ids = new Set();
  for (const a of activities || []) {
    if (a.completion_kind === 'practice_verified' && a.practice_evidence?.sessionId) {
      ids.add(a.practice_evidence.sessionId);
    }
  }
  return ids;
}

/**
 * @param {object} opts
 * @param {string} opts.studentId
 * @param {string} opts.topic
 * @param {string|Date|null} opts.eligibleSince - activity-specific lower bound
 * @param {Set<string>} opts.claimedSessions - session ids already used on this path
 */
export async function findPracticeEvidence(db, { studentId, topic, eligibleSince, claimedSessions }) {
  if (!studentId || !topic) {
    return { level: 'none', evidence: null, note: 'Missing student or topic.' };
  }
  const since = toDate(eligibleSince);
  const claimed = claimedSessions || new Set();

  const sessions = await db
    .collection('practice_sessions')
    .find({ student_id: studentId, topic })
    .toArray();

  const inWindow = (d) => {
    if (!since) return true;
    const t = toDate(d);
    return t && t >= since;
  };

  // Full completion: C1 sets completed=true when every item is answered (not abandoned).
  const finished = sessions
    .filter((s) => s.completed === true && !s.abandoned)
    .filter((s) => inWindow(s.completed_at || s.updated_at || s.started_at))
    .filter((s) => !claimed.has(s.session_id))
    .sort(
      (a, b) =>
        new Date(b.completed_at || b.updated_at || 0) - new Date(a.completed_at || a.updated_at || 0)
    );

  if (finished.length) {
    const s = finished[0];
    const answered = (s.items || []).filter((i) => i.answered).length;
    const total = (s.items || []).length;
    return {
      level: 'verified',
      evidence: {
        source: 'practice_sessions',
        sessionId: s.session_id,
        finishedAt: s.completed_at || null,
        answered,
        total,
        topic,
      },
      note: 'Verified: finished C1 practice session (all items answered) after this activity became eligible.',
    };
  }

  // Participation only: open session with some answers, or quiz events without a finished session.
  const openPartial = sessions
    .filter((s) => !s.completed && !s.abandoned)
    .filter((s) => inWindow(s.started_at || s.updated_at))
    .filter((s) => (s.items || []).some((i) => i.answered))
    .sort((a, b) => new Date(b.started_at) - new Date(a.started_at));

  if (openPartial.length) {
    const s = openPartial[0];
    const answered = (s.items || []).filter((i) => i.answered).length;
    const total = (s.items || []).length || null;
    return {
      level: 'observed',
      evidence: {
        source: 'practice_sessions',
        sessionId: s.session_id,
        answered,
        total,
        topic,
        inProgress: true,
      },
      note: 'Practice observed (session in progress). Not marked complete — one or more answers alone do not finish the activity.',
    };
  }

  const events = await db
    .collection('learning_events')
    .find({ student_id: studentId, topic, type: 'quiz_answer' })
    .toArray();
  const recent = events
    .filter((e) => inWindow(e.timestamp))
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  if (recent.length >= 1) {
    return {
      level: 'observed',
      evidence: {
        source: 'learning_events',
        eventCount: recent.length,
        lastAt: recent[0].timestamp,
        topic,
        inProgress: true,
      },
      note: 'Practice observed from quiz_answer events. Not activity completion without a finished practice session.',
    };
  }

  return {
    level: 'none',
    evidence: null,
    note: 'No C1 practice evidence for this topic since the activity became eligible. Opening a link is not completion.',
  };
}

/**
 * Sync path activities from C1 evidence. Duplicate-safe: verified stays verified;
 * observed updates are idempotent; never reuses a claimed finished session for a new activity.
 */
export async function syncPathPracticeEvidence(db, doc) {
  if (!doc) throw httpError(404, 'Learning path not found');
  if (doc.student_id == null) throw httpError(400, 'Path missing student_id');

  let changed = false;
  const activities = [];
  // Build claimed set incrementally so two pending same-topic activities need two sessions.
  const claimed = claimedSessionIds(doc.activities);

  for (const a of doc.activities || []) {
    if (a.completion_kind === 'practice_verified') {
      activities.push(a);
      continue;
    }

    const eligibleSince =
      a.eligible_since || a.scheduled_date || doc.source_snapshot_at || doc.created_at;

    const hit = await findPracticeEvidence(db, {
      studentId: doc.student_id,
      topic: a.topic,
      eligibleSince,
      claimedSessions: claimed,
    });

    if (hit.level === 'verified' && (a.status === 'pending' || a.status === 'overdue' || a.status === 'self_reported_complete' || a.status === 'practice_observed')) {
      changed = true;
      if (hit.evidence?.sessionId) claimed.add(hit.evidence.sessionId);
      activities.push({
        ...a,
        status: 'practice_verified',
        completion_kind: 'practice_verified',
        completed_at: hit.evidence.finishedAt || new Date().toISOString(),
        practice_evidence: hit.evidence,
      });
      continue;
    }

    if (hit.level === 'observed' && (a.status === 'pending' || a.status === 'overdue')) {
      const same =
        a.completion_kind === 'practice_observed' &&
        a.practice_evidence?.sessionId === hit.evidence?.sessionId &&
        a.practice_evidence?.eventCount === hit.evidence?.eventCount;
      if (!same) {
        changed = true;
        activities.push({
          ...a,
          status: 'practice_observed',
          completion_kind: 'practice_observed',
          completed_at: null,
          practice_evidence: hit.evidence,
        });
        continue;
      }
    }

    activities.push(a);
  }

  return { activities, changed, syncedAt: new Date().toISOString() };
}
