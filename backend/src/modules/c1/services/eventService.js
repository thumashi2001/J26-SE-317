import { callAi, httpError } from './aiClient.js';

const DAY_MS = 24 * 60 * 60 * 1000;
const WEAK_BELOW = 30;

// One learning event (a quiz answer): forgetting is applied, the topic score is updated,
// risk is recalculated from the whole history, and alerts are raised when needed.
export async function recordEvent(db, input, aiUrl) {
  const { studentId, topic } = input;
  const correct = !!input.correct;
  const hintUsed = !!input.hintUsed;
  const timeSec = Number(input.timeSec) || 30;
  const when = input.timestamp ? new Date(input.timestamp) : new Date();
  if (Number.isNaN(when.getTime())) throw httpError(400, 'timestamp is not a valid date');

  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');
  const entry = state.mastery[topic];
  if (!entry) throw httpError(400, `Unknown topic: ${topic}`);

  // 1. forgetting + update, using the Python service
  const daysSince = Math.max(0, (when - new Date(entry.last_practiced)) / DAY_MS);
  const ai = await callAi(aiUrl, '/twin/apply-event', {
    current_score: entry.score,
    correct,
    hint_used: hintUsed,
    days_since_practice: daysSince,
    practice_sessions: entry.practice_sessions || 0,
  });
  const before = entry.score;
  entry.score = ai.score_after;
  entry.answered += 1;
  if (correct) entry.correct += 1;
  entry.last_practiced = when;
  entry.practice_sessions = (entry.practice_sessions || 0) + 1;

  // 2. log the event
  await db.collection('learning_events').insertOne({
    student_id: studentId,
    timestamp: when,
    type: 'quiz_answer',
    topic,
    correct,
    hint_used: hintUsed,
    time_sec: timeSec,
  });

  // 3. risk from the whole history (day 1 = the student's first event)
  const all = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  all.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const start = new Date(all[0].timestamp);
  const toDay = (t) => Math.floor((new Date(t) - start) / DAY_MS) + 1;
  const events = all.map((e) => ({
    day: toDay(e.timestamp),
    topic: e.topic,
    correct: !!e.correct,
    hint_used: !!e.hint_used,
    time_sec: e.time_sec ?? 30,
  }));
  const risk = await callAi(aiUrl, '/risk/predict', {
    student_id: studentId,
    as_of_day: toDay(when),
    events,
  });

  // 4. alerts
  const alerts = [];
  if (risk.risk_level === 'High' && state.risk_level !== 'High') {
    alerts.push({
      type: 'risk_high',
      severity: 'High',
      message: `Risk level rose to High (probability ${risk.risk_probability}).`,
    });
  }
  if (entry.score < WEAK_BELOW && before >= WEAK_BELOW) {
    alerts.push({
      type: 'weak_topic',
      severity: 'Medium',
      topic,
      message: `${topic} dropped below ${WEAK_BELOW}% (now ${entry.score}%).`,
    });
  }
  for (const a of alerts) {
    await db.collection('alerts').insertOne({ student_id: studentId, created_at: when, ...a });
  }

  // 5. save the twin
  state.risk_level = risk.risk_level;
  state.risk_probability = risk.risk_probability;
  state.updated_at = when;
  await db.collection('mastery_state').replaceOne({ student_id: studentId }, state, { upsert: true });

  return {
    studentId,
    topic,
    scoreBefore: before,
    afterForgetting: ai.after_forgetting,
    scoreAfter: entry.score,
    riskLevel: risk.risk_level,
    riskProbability: risk.risk_probability,
    alertsCreated: alerts.length,
  };
}

export async function getAlerts(db, studentId) {
  const student = await db.collection('students').findOne({ student_id: studentId });
  if (!student) throw httpError(404, `Student ${studentId} not found`);
  const rows = await db.collection('alerts').find({ student_id: studentId }).toArray();
  rows.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return { studentId, alerts: rows.map(({ _id, ...rest }) => rest) };
}