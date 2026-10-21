import { httpError } from './aiClient.js';

// Every time a topic score changes, one snapshot is saved. Together they form the
// student's versioned learning history (version 1 is the diagnostic, then 2, 3, ...).
export async function recordSnapshot(db, snap) {
  const { studentId, topic, score, scoreBefore = null, afterForgetting = null, source, when } = snap;
  const col = db.collection('mastery_history');
  const earlier = await col.find({ student_id: studentId, topic }).toArray();
  await col.insertOne({
    student_id: studentId,
    topic,
    version: earlier.length + 1,
    timestamp: when,
    score,
    score_before: scoreBefore,
    after_forgetting: afterForgetting,
    source, // 'diagnostic' or 'quiz_answer'
  });
}

export async function getHistory(db, studentId, topic) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');
  const entry = state.mastery[topic];
  if (!entry) throw httpError(404, `Unknown topic: ${topic}`);

  const rows = await db.collection('mastery_history').find({ student_id: studentId, topic }).toArray();
  rows.sort((a, b) => a.version - b.version);

  let points = rows.map((r) => ({
    version: r.version,
    timestamp: r.timestamp,
    score: r.score,
    scoreBefore: r.score_before,
    afterForgetting: r.after_forgetting,
    source: r.source,
  }));

  // Accounts created before history existed get one point built from the current score.
  if (points.length === 0) {
    points = [{
      version: 1,
      timestamp: entry.last_practiced,
      score: entry.score,
      scoreBefore: null,
      afterForgetting: null,
      source: 'current',
    }];
  }

  return {
    studentId,
    topic,
    current: {
      score: entry.score,
      answered: entry.answered,
      correct: entry.correct,
      practiceSessions: entry.practice_sessions || 0,
      lastPracticed: entry.last_practiced,
    },
    points,
  };
}
