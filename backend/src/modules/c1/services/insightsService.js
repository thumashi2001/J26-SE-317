import { callAi, httpError } from './aiClient.js';
import { FAST_SEC } from './behaviourService.js';

// Engagement, confidence and "estimated score now" for one student.
//
// ENGAGEMENT INDEX (0 to 100) looks at the last 14 days of practice quizzes:
//   regularity  35%   days with at least one quiz answer, 5 or more days = full marks
//   recency     30%   full marks if the last answer was 0 to 2 days ago, fading to 0 at 14 days
//   volume      20%   answers given, 30 or more = full marks
//   finishing   15%   quizzes finished out of quizzes started
//   labels: below 30 Low, 30 to 64 Steady, 65 and above High, "Not started" if no quiz answer exists
//
// CONFIDENCE (0 to 100) says how far a topic score can be trusted:
//   evidence = sum of answer reliability on that topic (diagnostic and quiz answers)
//   an answer counts 1.0, half if the student left the tab during it, x0.6 if answered in under 8 seconds
//   confidence = (1 - e^(-evidence / 8)) x recency, where recency fades slowly with days since practice
//   labels: below 40 Low, 40 to 69 Medium, 70 and above High
//
// ESTIMATED SCORE NOW is the stored score with forgetting applied up to this moment. The number comes
// from the Python AI service, so it is the same forgetting rule the forecast and the twin use.

const DAY_MS = 24 * 60 * 60 * 1000;
export const WINDOW_DAYS = 14;

const clamp01 = (x) => Math.max(0, Math.min(1, x));
const round = (x) => Math.round(x);
const when = (t) => new Date(t).getTime();
const shortDate = (t) => new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const dayKey = (t) => new Date(t).toISOString().slice(0, 10);

// How far one answer can be trusted, from 0 to 1.
export function answerReliability(ev) {
  let r = 1;
  if ((ev.tab_leaves || 0) > 0) r *= 0.5;
  if (ev.type === 'quiz_answer' && ev.time_sec != null && ev.time_sec < FAST_SEC) r *= 0.6;
  return r;
}

export const isFlagged = (ev) => answerReliability(ev) < 1;

export function engagementFrom(events, sessions, now = new Date()) {
  const quiz = events.filter((e) => e.type === 'quiz_answer');
  if (quiz.length === 0) {
    return {
      index: 0,
      label: 'Not started',
      why: 'You have not practised yet. Start with your weakest topic.',
      activeDays: 0,
      windowDays: WINDOW_DAYS,
      answers: 0,
      lastPracticed: null,
      sessionsStarted: 0,
      sessionsFinished: 0,
    };
  }

  const from = now.getTime() - WINDOW_DAYS * DAY_MS;
  const recent = quiz.filter((e) => when(e.timestamp) >= from && when(e.timestamp) <= now.getTime() + DAY_MS);
  const last = quiz.reduce((m, e) => Math.max(m, when(e.timestamp)), 0);
  const daysSinceLast = Math.max(0, (now.getTime() - last) / DAY_MS);

  const activeDays = new Set(recent.map((e) => dayKey(e.timestamp))).size;
  const regularity = clamp01(activeDays / 5);
  const recency = clamp01(1 - Math.max(0, daysSinceLast - 2) / (WINDOW_DAYS - 2));
  const volume = clamp01(recent.length / 30);

  const recentSessions = sessions.filter((s) => when(s.started_at) >= from);
  const finished = recentSessions.filter((s) => s.completed && !s.abandoned).length;
  const started = recentSessions.filter((s) => !s.abandoned).length;
  const finishing = started ? finished / started : 0;

  const index = round(100 * (0.35 * regularity + 0.3 * recency + 0.2 * volume + 0.15 * finishing));
  const label = index >= 65 ? 'High' : index >= 30 ? 'Steady' : 'Low';

  const lastText = daysSinceLast < 1 ? 'today' : `on ${shortDate(last)}`;
  const parts = [
    `You practised on ${activeDays} of the last ${WINDOW_DAYS} days, last ${lastText}`,
    started ? `${finished} of ${plural(started, 'quiz', 'quizzes')} finished` : null,
  ].filter(Boolean);
  const advice =
    label === 'High' ? 'Keep this rhythm.' : label === 'Steady' ? 'A short quiz every other day would lift this.' : 'Short, regular quizzes work better than one long session.';

  return {
    index,
    label,
    why: `${parts.join('. ')}. ${advice}`,
    activeDays,
    windowDays: WINDOW_DAYS,
    answers: recent.length,
    lastPracticed: new Date(last).toISOString(),
    sessionsStarted: started,
    sessionsFinished: finished,
  };
}

export function confidenceFrom(topicEvents, daysSincePractice) {
  const evidence = topicEvents.reduce((sum, e) => sum + answerReliability(e), 0);
  const flagged = topicEvents.filter(isFlagged).length;
  const base = 1 - Math.exp(-evidence / 8);
  const recency = 0.6 + 0.4 * Math.exp(-Math.max(0, daysSincePractice) / 30);
  const value = round(100 * base * recency);
  const label = value >= 70 ? 'High' : value >= 40 ? 'Medium' : 'Low';

  const n = topicEvents.length;
  let why = `Based on ${plural(n, 'answer', 'answers')}`;
  if (flagged > 0) why += `, ${flagged} of them counted less (left the tab or answered very fast)`;
  why += '.';
  if (label === 'Low') why += ' More practice answers will make this score more reliable.';
  else if (daysSincePractice > 14) why += ' It is a while since you practised this topic.';
  return { value, label, why, answers: n, flagged };
}

function scoreWhy(stored, estimated, daysSince, lastPracticed) {
  if (estimated === null) return null;
  if (daysSince < 1) return 'You practised this topic today, so the score is up to date.';
  const days = Math.floor(daysSince);
  if (stored - estimated < 0.5) return `Your score is ${Math.round(estimated)}% and has barely faded since ${shortDate(lastPracticed)}.`;
  return `Your score was ${Math.round(stored)}% when you last practised on ${shortDate(lastPracticed)}. ${plural(days, 'day', 'days')} without practice lowered it to about ${Math.round(estimated)}%. One quiz brings it back up.`;
}

export async function getInsights(db, studentId, aiUrl, now = new Date()) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');

  const events = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  const sessions = await db.collection('practice_sessions').find({ student_id: studentId }).toArray();

  const topics = Object.entries(state.mastery);
  const estimates = await Promise.allSettled(
    topics.map(([, m]) => {
      const days = Math.max(0, (now.getTime() - when(m.last_practiced)) / DAY_MS);
      return callAi(aiUrl, '/twin/forecast', {
        current_score: m.score,
        days_since_practice: days,
        practice_sessions: m.practice_sessions || 0,
        correct: m.correct || 0,
        answered: m.answered || 0,
        days_ahead: 1,
        sessions_per_week: 0,
      }).then((r) => r.today);
    })
  );

  const out = {};
  topics.forEach(([topic, m], i) => {
    const daysSince = Math.max(0, (now.getTime() - when(m.last_practiced)) / DAY_MS);
    const estimated = estimates[i].status === 'fulfilled' ? estimates[i].value : null; // null if the AI service is down
    const conf = confidenceFrom(
      events.filter((e) => e.topic === topic),
      daysSince
    );
    out[topic] = {
      storedScore: m.score,
      estimatedNow: estimated,
      daysSincePractice: Math.round(daysSince * 10) / 10,
      lastPracticed: new Date(m.last_practiced).toISOString(),
      scoreWhy: scoreWhy(m.score, estimated, daysSince, m.last_practiced),
      confidence: conf.value,
      confidenceLabel: conf.label,
      confidenceWhy: conf.why,
      answers: conf.answers,
      flaggedAnswers: conf.flagged,
    };
  });

  return {
    studentId,
    generatedAt: now.toISOString(),
    engagement: engagementFrom(events, sessions, now),
    topics: out,
  };
}
