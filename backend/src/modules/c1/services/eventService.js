import { callAi, httpError } from './aiClient.js';
import { recordSnapshot } from './historyService.js';
import { baselineFrom, classify, gainWeight } from './behaviourService.js';

const DAY_MS = 24 * 60 * 60 * 1000;
const WEAK_BELOW = 30;
const DROP_POINTS = 15; // a fall of this many points from a recent high is a sudden drop
const ALERT_GAP_DAYS = 3; // the same kind of alert is not raised again within this time
const GUESS_WINDOW = 7;
const GUESS_LIMIT = 4;

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

  // The student's own normal answer time, from earlier quiz answers. Used to judge this answer.
  const prior = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  const baseline = baselineFrom(prior);
  const isQuizAnswer = !!input.questionId;
  const weight = isQuizAnswer ? gainWeight({ correct, timeSec, tabLeaves: input.tabLeaves }, baseline) : 1;

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
  // A correct answer that looks risky (tab left, answered very fast) raises the score by only part of the normal gain.
  entry.score = weight < 1 ? Math.round((ai.after_forgetting + weight * (ai.score_after - ai.after_forgetting)) * 100) / 100 : ai.score_after;
  entry.answered += 1;
  if (correct) entry.correct += 1;
  entry.last_practiced = when;
  // A quiz of several answers counts as one practice session (the quiz sets newSession false after its first answer).
  if (input.newSession !== false) entry.practice_sessions = (entry.practice_sessions || 0) + 1;

  // 2. log the event
  await db.collection('learning_events').insertOne({
    student_id: studentId,
    timestamp: when,
    type: 'quiz_answer',
    topic,
    correct,
    hint_used: hintUsed,
    time_sec: timeSec,
    ...(isQuizAnswer ? { weight } : {}),
    ...(input.questionId ? { question_id: input.questionId, session_id: input.sessionId } : {}),
    ...(input.tabLeaves !== undefined ? { tab_leaves: input.tabLeaves, away_sec: input.awaySec || 0 } : {}),
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
  // sudden drop: the score is far below its recent high (checked before this answer is saved to the history)
  const recentHigh = await recentHighScore(db, studentId, topic, when);
  if (recentHigh !== null && recentHigh - entry.score >= DROP_POINTS && !(await recentAlert(db, studentId, 'sudden_drop', topic, when))) {
    alerts.push({
      type: 'sudden_drop',
      severity: 'Medium',
      topic,
      message: `${topic} fell from ${Math.round(recentHigh)}% to ${Math.round(entry.score)}% in your recent answers. Look at the explanations and try the topic again.`,
    });
  }
  // guessing: several of the latest quiz answers were very fast and wrong
  if (isQuizAnswer) {
    const latest = [...prior, { type: 'quiz_answer', question_id: input.questionId, time_sec: timeSec, correct, timestamp: when }]
      .filter((e) => e.type === 'quiz_answer' && e.question_id && e.time_sec != null)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
      .slice(-GUESS_WINDOW);
    const guesses = latest.filter((e) => classify(e, baseline) === 'guess').length;
    if (guesses >= GUESS_LIMIT && !(await recentAlert(db, studentId, 'guessing', null, when))) {
      alerts.push({
        type: 'guessing',
        severity: 'Medium',
        message: 'Several of your latest answers were very quick and wrong, which looks like guessing. Slow down and read each option.',
      });
    }
  }
  for (const a of alerts) {
    await db.collection('alerts').insertOne({ student_id: studentId, created_at: when, ...a });
  }

  // 5. save the twin
  state.risk_level = risk.risk_level;
  state.risk_probability = risk.risk_probability;
  state.updated_at = when;
  await db.collection('mastery_state').replaceOne({ student_id: studentId }, state, { upsert: true });
  await recordSnapshot(db, {
    studentId,
    topic,
    score: entry.score,
    scoreBefore: before,
    afterForgetting: ai.after_forgetting,
    source: 'quiz_answer',
    when,
  });

  return {
    studentId,
    topic,
    scoreBefore: before,
    afterForgetting: ai.after_forgetting,
    scoreAfter: entry.score,
    riskLevel: risk.risk_level,
    riskProbability: risk.risk_probability,
    alertsCreated: alerts.length,
    gainWeight: weight,
  };
}

async function recentHighScore(db, studentId, topic, when) {
  const rows = await db.collection('mastery_history').find({ student_id: studentId, topic }).toArray();
  const from = when.getTime() - 14 * DAY_MS;
  const last = rows
    .filter((r) => new Date(r.timestamp).getTime() >= from)
    .sort((a, b) => a.version - b.version)
    .slice(-3);
  return last.length ? Math.max(...last.map((r) => r.score)) : null;
}

async function recentAlert(db, studentId, type, topic, when) {
  const rows = await db.collection('alerts').find({ student_id: studentId, type }).toArray();
  const from = when.getTime() - ALERT_GAP_DAYS * DAY_MS;
  return rows.some((a) => (topic === null || a.topic === topic) && new Date(a.created_at).getTime() >= from);
}

export async function getAlerts(db, studentId) {
  const student = await db.collection('students').findOne({ student_id: studentId });
  if (!student) throw httpError(404, `Student ${studentId} not found`);
  const rows = await db.collection('alerts').find({ student_id: studentId }).toArray();
  rows.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return { studentId, alerts: rows.map(({ _id, ...rest }) => rest) };
}
