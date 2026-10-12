import { httpError } from './aiClient.js';
import { behaviourFrom, topicReads } from './behaviourService.js';
import { practiceTopics } from './practiceService.js';

// STUDY PLAN from the forgetting curve, the student's answer behaviour and the exam date.
//
// FORGETTING (same rule as the twin and the forecast)
//   score after d days = stored score x (0.35 + 0.65 x e^(-d / stability))
//   stability = 14 days x (1 + 0.6 x practice sessions), so every session makes the topic fade more slowly
//
// REVIEW DUE DATE   the day the score has kept only 80% of what it was at the last practice
//   days = stability x -ln((0.8 - 0.35) / 0.65)  (about 0.37 x stability)
//   a topic that is due or overdue goes into today's tasks
//
// PRIORITY of a topic (higher goes first)
//   gap to target     how far the estimated exam-day score (no more practice) is below the target of 70
//   fading            points lost between today and exam day if the student stops
//   overdue           a bonus when the review date has passed
//   behaviour         guessing or needs-revision topics get a bonus, strong and quick topics a discount
//
// TODAY'S TASKS   the number of topics scales with the days left (more as the exam gets closer)
//   a student who is rushing or guessing is told to slow down on every task
//
// CALENDAR   the plan is simulated day by day. Each practice is assumed to keep the topic's accuracy
//   (at least 60%), moves the score by the same expected-value rule as the forecast, and makes the
//   topic fade more slowly, so the review spacing grows. The last 2 days before the exam are final revision.
//
// Nothing here calls the AI service, so the plan works even when it is offline.

const DAY_MS = 24 * 60 * 60 * 1000;
export const FLOOR = 0.35;
export const BASE_STABILITY = 14;
export const SESSION_BOOST = 0.6;
export const LEARN_RATE = 0.25;
export const MIN_ACCURACY = 0.6;
export const TARGET = 70;
export const KEEP = 0.8;
export const MAX_HORIZON = 120;
export const SESSION_MINUTES = 5;

const REVIEW_FRACTION = -Math.log((KEEP - FLOOR) / (1 - FLOOR)); // about 0.368

export const stability = (sessions) => BASE_STABILITY * (1 + SESSION_BOOST * Math.max(0, sessions));
export const decay = (score, days, sessions) => score * (FLOOR + (1 - FLOOR) * Math.exp(-Math.max(0, days) / stability(sessions)));
export const reviewAfterDays = (sessions) => REVIEW_FRACTION * stability(sessions);

const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
const r1 = (x) => Math.round(x * 10) / 10;
const startOfDay = (d) => {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
};
export const isoDate = (d) => {
  const x = new Date(d);
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`;
};
const parseDate = (s) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || ''));
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(d.getTime()) || d.getMonth() !== Number(m[2]) - 1 ? null : d;
};
const daysBetween = (a, b) => Math.round((startOfDay(b) - startOfDay(a)) / DAY_MS);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

export function tasksPerDay(daysLeft) {
  if (daysLeft === null) return 3;
  if (daysLeft <= 2) return 5;
  if (daysLeft <= 7) return 4;
  if (daysLeft <= 30) return 3;
  return 2;
}

function accuracyOf(m) {
  return Math.max(MIN_ACCURACY, ((m.correct || 0) + 0.8) / ((m.answered || 0) + 2));
}

// What the behaviour read of a topic means for the plan.
const BEHAVIOUR = {
  guessing: { bonus: 14, kind: 'slow_down', label: 'Slow down', tip: 'Your answers here are quick and wrong. Read all four options and the explanation, aim for 15 seconds or more a question.' },
  revise: { bonus: 10, kind: 'read_first', label: 'Read, then practise', tip: 'Long and still wrong means the idea is not clear yet. Read the lecture notes for this topic first, then take the quiz.' },
  slow_right: { bonus: 2, kind: 'speed', label: 'Build speed', tip: 'You know this but answer slowly. A quick quiz under the timer will build speed.' },
  strong: { bonus: -8, kind: 'keep_sharp', label: 'Keep sharp', tip: 'You know this well. One short quiz keeps it from fading.' },
  building: { bonus: 3, kind: 'practise', label: 'Practise', tip: 'A mix of right and wrong. A full quiz and the explanations will firm it up.' },
};

function describeTask(t, daysLeft) {
  const parts = [];
  if (t.sessions === 0) parts.push('You have not practised this topic yet, so the score is only a starting guess');
  else if (t.overdueDays >= 1) parts.push(`Review was due ${plural(Math.round(t.overdueDays), 'day', 'days')} ago and the score has faded from ${Math.round(t.stored)}% to about ${Math.round(t.now)}%`);
  else if (t.dueInDays <= 0.5) parts.push(`Your review is due today. The score has faded from ${Math.round(t.stored)}% to about ${Math.round(t.now)}%`);
  else parts.push(`Estimated ${Math.round(t.now)}% now`);
  if (daysLeft !== null && t.examIfStop < TARGET) parts.push(`without practice it would be about ${Math.round(t.examIfStop)}% on exam day`);
  return `${parts.join(', ')}.`;
}

// Build the plan from plain data so it can be tested without a database.
export function buildPlan({ mastery, events, examDate, now = new Date(), practicable = null, engagement = null }) {
  const today = startOfDay(now);
  const exam = examDate ? parseDate(examDate) : null;
  let daysLeft = exam ? daysBetween(today, exam) : null;
  if (daysLeft !== null && daysLeft < 0) daysLeft = null; // the exam date has passed: plan as if none is set
  const examActive = daysLeft !== null;
  const horizon = examActive ? Math.min(daysLeft, MAX_HORIZON) : 14;

  const reads = topicReads(events || []);
  const overall = behaviourFrom(events || [], now);
  const slowDown = overall.pattern === 'Rushing' || overall.pattern === 'Guessing';

  const topics = Object.entries(mastery || {})
    .filter(([t]) => !practicable || practicable.includes(t))
    .map(([topic, m]) => {
      const last = m.last_practiced ? new Date(m.last_practiced) : today;
      const sessions = m.practice_sessions || 0;
      const daysSince = Math.max(0, (now.getTime() - last.getTime()) / DAY_MS);
      const stored = m.score;
      const nowScore = decay(stored, daysSince, sessions);
      const examIfStop = decay(stored, daysSince + (examActive ? daysLeft : 14), sessions);
      const dueInDays = reviewAfterDays(sessions) - daysSince;
      const read = reads[topic] || null;
      const beh = read ? BEHAVIOUR[read.key] : null;
      return {
        topic, stored, sessions, daysSince, now: nowScore, examIfStop, dueInDays,
        overdueDays: Math.max(0, -dueInDays),
        accuracy: accuracyOf(m),
        read, beh,
      };
    });

  const priority = (t) => {
    const gap = Math.max(0, TARGET - t.examIfStop);
    const fading = Math.max(0, t.now - t.examIfStop);
    const overdue = Math.min(20, t.overdueDays * 2) + (t.dueInDays <= 0.5 ? 8 : 0);
    const start = t.sessions === 0 ? 6 : 0;
    return gap * 0.6 + fading * 0.5 + overdue + start + (t.beh ? t.beh.bonus : 0);
  };
  topics.forEach((t) => { t.priority = priority(t); });

  // ---- today's tasks
  const limit = tasksPerDay(examActive ? daysLeft : null);
  const due = topics.filter((t) => t.dueInDays <= 0.5 || t.sessions === 0 || t.examIfStop < TARGET - 15 || (t.beh && t.beh.kind !== 'keep_sharp'));
  const pool = (due.length >= limit ? due : [...due, ...topics.filter((t) => !due.includes(t))]);
  const todayTasks = pool
    .sort((a, b) => b.priority - a.priority)
    .slice(0, limit)
    .map((t) => {
      const kind = t.beh ? t.beh.kind : t.sessions === 0 ? 'start' : t.overdueDays >= 1 ? 'revise' : 'practise';
      const label = t.beh ? t.beh.label : t.sessions === 0 ? 'Start' : t.overdueDays >= 1 ? 'Revise now' : 'Practise';
      const tips = [];
      if (t.beh) tips.push(t.beh.tip);
      if (slowDown && kind !== 'slow_down') tips.push('Your recent answers were quick, so take at least 15 seconds a question.');
      return {
        topic: t.topic,
        kind,
        label,
        minutes: SESSION_MINUTES,
        scoreNow: Math.round(t.now),
        scoreAtLastPractice: Math.round(t.stored),
        examIfStop: Math.round(t.examIfStop),
        daysSincePractice: Math.round(t.daysSince * 10) / 10,
        overdue: t.overdueDays >= 1,
        why: describeTask(t, examActive ? daysLeft : null),
        tips,
      };
    });

  // ---- calendar simulation
  const sim = topics.map((t) => ({
    topic: t.topic,
    stored: t.stored,
    sessions: t.sessions,
    lastDay: -t.daysSince, // day offset of the last practice, relative to today
    nextDue: -t.daysSince + reviewAfterDays(t.sessions),
    accuracy: t.accuracy,
    weight: t.priority,
    plannedToday: false,
  }));
  const todaySet = new Set(todayTasks.map((t) => t.topic));
  const days = [];
  for (let d = 0; d <= horizon; d++) {
    const date = new Date(today.getTime() + d * DAY_MS);
    const isExam = examActive && d === daysLeft;
    const cap = tasksPerDay(examActive ? daysLeft - d : null);
    const final = examActive && daysLeft - d <= 2 && !isExam;
    let picks = [];
    if (d === 0) {
      picks = sim.filter((s) => todaySet.has(s.topic));
    } else if (!isExam) {
      const dueNow = sim.filter((s) => s.nextDue <= d + 0.01);
      // weak-for-the-exam topics are worth an extra look: pull them forward when they will end below target
      const risky = sim.filter((s) => !dueNow.includes(s) && decay(s.stored, (examActive ? daysLeft : horizon) - s.lastDay, s.sessions) < TARGET - 10 && d - s.lastDay >= 3);
      picks = [...dueNow, ...risky].sort((a, b) => b.weight - a.weight).slice(0, cap);
      // keep a daily rhythm: a day with nothing due still gets one short quiz on the topic that needs it most
      if (picks.length === 0) {
        const rhythm = sim.filter((s) => d - s.lastDay >= 2 && decay(s.stored, d - s.lastDay, s.sessions) < TARGET + 10).sort((a, b) => b.weight - a.weight)[0];
        if (rhythm) picks = [rhythm];
      }
      if (final) {
        const rest = [...sim].sort((a, b) => b.weight - a.weight).filter((s) => !picks.includes(s));
        picks = [...picks, ...rest].slice(0, cap);
      }
    }
    const items = picks.map((s) => {
      const faded = decay(s.stored, d - s.lastDay, s.sessions);
      s.stored = r1(faded + LEARN_RATE * (s.accuracy * 100 - faded));
      s.sessions += 1;
      s.lastDay = d;
      s.nextDue = d + reviewAfterDays(s.sessions);
      return { topic: s.topic, kind: final ? 'final' : d === 0 ? 'today' : 'review' };
    });
    days.push({ date: isoDate(date), offset: d, isToday: d === 0, isExam, finalRevision: final, items });
  }

  // ---- predicted exam score, with and without following the plan
  const endDay = examActive ? daysLeft : horizon;
  const withPlan = sim.map((s) => decay(s.stored, endDay - s.lastDay, s.sessions));
  const without = topics.map((t) => decay(t.stored, t.daysSince + endDay, t.sessions));
  const avg = (a) => (a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : 0);
  const planned = days.reduce((n, d) => n + d.items.length, 0);

  const nextReviews = [...topics]
    .sort((a, b) => a.dueInDays - b.dueInDays)
    .slice(0, 6)
    .map((t) => ({ topic: t.topic, dueInDays: Math.round(t.dueInDays * 10) / 10, scoreNow: Math.round(t.now) }));

  return {
    examDate: exam ? isoDate(exam) : null,
    daysLeft: examActive ? daysLeft : null,
    examPassed: !!exam && daysLeft === null,
    horizonDays: horizon,
    target: TARGET,
    pattern: overall.pattern,
    slowDown,
    predicted: {
      withPlan: avg(withPlan),
      ifYouStop: avg(without),
      gain: avg(withPlan) - avg(without),
      topicsBelowTarget: withPlan.filter((v) => v < TARGET).length,
      topicCount: topics.length,
    },
    today: { limit, tasks: todayTasks, minutes: todayTasks.length * SESSION_MINUTES },
    nextReviews,
    totalPlannedSessions: planned,
    engagement: engagement ? { index: engagement.index, label: engagement.label } : null,
    days,
  };
}

export async function getExamDate(db, studentId) {
  const doc = await db.collection('student_plans').findOne({ student_id: studentId });
  return doc ? doc.exam_date : null;
}

export async function setExamDate(db, studentId, value, now = new Date()) {
  const col = db.collection('student_plans');
  if (value === null || value === '' || value === undefined) {
    await col.deleteOne({ student_id: studentId });
    return null;
  }
  const d = parseDate(value);
  if (!d) throw httpError(400, 'Exam date must look like 2026-11-20');
  const n = daysBetween(now, d);
  if (n < 0) throw httpError(400, 'The exam date cannot be in the past');
  if (n > 365) throw httpError(400, 'Pick an exam date within the next year');
  const exam_date = isoDate(d);
  await col.updateOne({ student_id: studentId }, { $set: { student_id: studentId, exam_date, updated_at: now.toISOString() } }, { upsert: true });
  return exam_date;
}

export async function getPlan(db, studentId, now = new Date()) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');
  const events = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  const examDate = await getExamDate(db, studentId);
  const plan = buildPlan({ mastery: state.mastery, events, examDate, now, practicable: practiceTopics() });
  return { studentId, generatedAt: now.toISOString(), ...plan };
}
