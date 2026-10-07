import { callAi, httpError } from './aiClient.js';

const DAY_MS = 24 * 60 * 60 * 1000;

// What-if forecast for one topic: "do nothing" against "practise N times a week",
// from today until the exam. The maths lives in the Python AI service.
export async function getForecast(db, studentId, topic, options, aiUrl) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');
  const entry = state.mastery[topic];
  if (!entry) throw httpError(404, `Unknown topic: ${topic}`);

  const daysSince = Math.max(0, (Date.now() - new Date(entry.last_practiced).getTime()) / DAY_MS);
  const ai = await callAi(aiUrl, '/twin/forecast', {
    current_score: entry.score,
    days_since_practice: daysSince,
    practice_sessions: entry.practice_sessions || 0,
    correct: entry.correct || 0,
    answered: entry.answered || 0,
    days_ahead: options.days,
    sessions_per_week: options.perWeek,
  });

  const start = Date.now();
  const dateOf = (d) => new Date(start + d * DAY_MS).toISOString().slice(0, 10);
  return {
    studentId,
    topic,
    startDate: dateOf(0),
    examDate: dateOf(ai.days_ahead),
    daysAhead: ai.days_ahead,
    sessionsPerWeek: ai.sessions_per_week,
    assumedAccuracy: ai.assumed_accuracy,
    todayScore: ai.today,
    practiceDays: ai.practice_days,
    nothing: {
      series: ai.nothing.series,
      examDayScore: ai.nothing.exam_day,
      firstWeakDay: ai.nothing.first_weak_day,
    },
    plan: {
      series: ai.plan.series,
      examDayScore: ai.plan.exam_day,
      firstWeakDay: ai.plan.first_weak_day,
    },
    gain: ai.gain,
  };
}
