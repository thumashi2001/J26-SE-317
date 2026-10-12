import { httpError } from './aiClient.js';
import { behaviourFrom, topicReads } from './behaviourService.js';
import { practiceTopics } from './practiceService.js';
import { TOPICS } from '../data/content/index.js';

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
// EXAM DATES   every module has its own exam date. A topic is planned against the exam of its module.
//   Topics of a module with no date are planned for the next 14 days. Once a module's exam day has passed
//   its topics leave the plan. The daily task count follows the nearest upcoming exam.
//
// TODAY'S TASKS   the number of topics scales with the days left (more as the exam gets closer)
//   a student who is rushing or guessing is told to slow down on every task
//
// CALENDAR   the plan is simulated day by day. Each practice is assumed to keep the topic's accuracy
//   (at least 60%), moves the score by the same expected-value rule as the forecast, and makes the
//   topic fade more slowly, so the review spacing grows. The last 2 days before a module's exam are final
//   revision for that module's topics.
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

export const DEFAULT_HORIZON = 14;

const moduleOfTopic = (topic) => (TOPICS[topic] ? TOPICS[topic].module_code : null);
const moduleNameOf = (code) => {
  const hit = Object.values(TOPICS).find((t) => t.module_code === code);
  return hit ? hit.module_name : '';
};
export const knownModules = () => [...new Set(Object.values(TOPICS).map((t) => t.module_code))];

// Build the plan from plain data so it can be tested without a database.
// examDates is { moduleCode: 'YYYY-MM-DD' }. moduleOf(topic) gives the module code of a topic.
export function buildPlan({ mastery, events, examDates = {}, now = new Date(), practicable = null, engagement = null, moduleOf = moduleOfTopic, moduleName = moduleNameOf }) {
  const today = startOfDay(now);
  const reads = topicReads(events || []);
  const overall = behaviourFrom(events || [], now);
  const slowDown = overall.pattern === 'Rushing' || overall.pattern === 'Guessing';

  const offsetOf = (code) => {
    const d = examDates && examDates[code] ? parseDate(examDates[code]) : null;
    return d ? daysBetween(today, d) : null; // negative = the exam has passed
  };

  const all = Object.entries(mastery || {})
    .filter(([t]) => !practicable || practicable.includes(t))
    .map(([topic, m]) => {
      const module = moduleOf(topic) || 'Other';
      const off = offsetOf(module);
      const last = m.last_practiced ? new Date(m.last_practiced) : today;
      return { topic, m, module, examOffset: off !== null && off >= 0 ? off : null, passed: off !== null && off < 0, last };
    });
  const live = all.filter((t) => !t.passed);

  const offsets = live.map((t) => t.examOffset).filter((o) => o !== null);
  const horizon = offsets.length ? Math.min(Math.max(...offsets), MAX_HORIZON) : DEFAULT_HORIZON;
  const nearestDays = offsets.length ? Math.min(...offsets) : null;

  const topics = live.map(({ topic, m, module, examOffset, last }) => {
    const sessions = m.practice_sessions || 0;
    const daysSince = Math.max(0, (now.getTime() - last.getTime()) / DAY_MS);
    const stored = m.score;
    const end = examOffset !== null ? examOffset : DEFAULT_HORIZON;
    const nowScore = decay(stored, daysSince, sessions);
    const examIfStop = decay(stored, daysSince + end, sessions);
    const dueInDays = reviewAfterDays(sessions) - daysSince;
    const read = reads[topic] || null;
    const beh = read ? BEHAVIOUR[read.key] : null;
    return {
      topic, module, examOffset, end, stored, sessions, daysSince, now: nowScore, examIfStop, dueInDays,
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
    // a nearer exam makes the same gap more urgent
    const near = t.examOffset !== null ? Math.max(0, 14 - t.examOffset) * 0.8 : 0;
    return gap * 0.6 + fading * 0.5 + overdue + start + near + (t.beh ? t.beh.bonus : 0);
  };
  topics.forEach((t) => { t.priority = priority(t); });

  // ---- today's tasks
  const limit = tasksPerDay(nearestDays);
  const due = topics.filter((t) => t.dueInDays <= 0.5 || t.sessions === 0 || t.examIfStop < TARGET - 15 || (t.beh && t.beh.kind !== 'keep_sharp'));
  const pool = due.length >= limit ? due : [...due, ...topics.filter((t) => !due.includes(t))];
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
        module: t.module,
        examInDays: t.examOffset,
        kind,
        label,
        minutes: SESSION_MINUTES,
        scoreNow: Math.round(t.now),
        scoreAtLastPractice: Math.round(t.stored),
        examIfStop: Math.round(t.examIfStop),
        daysSincePractice: Math.round(t.daysSince * 10) / 10,
        overdue: t.overdueDays >= 1,
        why: describeTask(t, t.examOffset),
        tips,
      };
    });

  // ---- calendar simulation
  const sim = topics.map((t) => ({
    topic: t.topic,
    module: t.module,
    examOffset: t.examOffset,
    end: t.examOffset !== null ? t.examOffset : horizon,
    stored: t.stored,
    sessions: t.sessions,
    lastDay: -t.daysSince, // day offset of the last practice, relative to today
    nextDue: -t.daysSince + reviewAfterDays(t.sessions),
    accuracy: t.accuracy,
    weight: t.priority,
  }));
  const todaySet = new Set(todayTasks.map((t) => t.topic));
  const examsOn = {};
  Object.keys(examDates || {}).forEach((code) => {
    const o = offsetOf(code);
    if (o !== null && o >= 0 && o <= horizon && live.some((t) => t.module === code)) (examsOn[o] ||= []).push(code);
  });

  const days = [];
  for (let d = 0; d <= horizon; d++) {
    const date = new Date(today.getTime() + d * DAY_MS);
    const open = sim.filter((s) => s.examOffset === null || d < s.examOffset); // the exam day itself has no quiz
    const upcoming = sim.map((s) => s.examOffset).filter((o) => o !== null && o >= d);
    const cap = tasksPerDay(upcoming.length ? Math.min(...upcoming) - d : null);
    const inFinal = (s) => s.examOffset !== null && s.examOffset - d <= 2 && s.examOffset > d;
    let picks = [];
    if (d === 0) {
      picks = open.filter((s) => todaySet.has(s.topic));
    } else if (open.length) {
      const dueNow = open.filter((s) => s.nextDue <= d + 0.01);
      // topics that will end below target are worth an extra look: pull them forward
      const risky = open.filter((s) => !dueNow.includes(s) && decay(s.stored, s.end - s.lastDay, s.sessions) < TARGET - 10 && d - s.lastDay >= 3);
      picks = [...dueNow, ...risky].sort((a, b) => b.weight - a.weight).slice(0, cap);
      if (picks.length === 0) {
        // keep a daily rhythm: a day with nothing due still gets one short quiz on the topic that needs it most
        const rhythm = open.filter((s) => d - s.lastDay >= 2 && decay(s.stored, d - s.lastDay, s.sessions) < TARGET + 10).sort((a, b) => b.weight - a.weight)[0];
        if (rhythm) picks = [rhythm];
      }
      const finals = open.filter(inFinal).sort((a, b) => b.weight - a.weight).filter((s) => !picks.includes(s));
      picks = [...picks, ...finals].slice(0, Math.max(cap, picks.length));
    }
    const items = picks.map((s) => {
      const faded = decay(s.stored, d - s.lastDay, s.sessions);
      s.stored = r1(faded + LEARN_RATE * (s.accuracy * 100 - faded));
      s.sessions += 1;
      s.lastDay = d;
      s.nextDue = d + reviewAfterDays(s.sessions);
      return { topic: s.topic, module: s.module, kind: d === 0 ? 'today' : inFinal(s) ? 'final' : 'review' };
    });
    const exams = (examsOn[d] || []).map((code) => ({ module: code, name: moduleName(code) }));
    days.push({ date: isoDate(date), offset: d, isToday: d === 0, isExam: exams.length > 0, exams, finalRevision: items.some((i) => i.kind === 'final'), items });
  }

  // ---- predicted exam level, per module and overall, with and without following the plan
  const avg = (a) => (a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : 0);
  const withPlanOf = (s) => decay(s.stored, s.end - s.lastDay, s.sessions);
  const withoutOf = (t) => decay(t.stored, t.daysSince + t.end, t.sessions);
  const codes = [...new Set([...all.map((t) => t.module), ...Object.keys(examDates || {}).filter((c) => all.some((t) => t.module === c))])];
  const modules = codes.map((code) => {
    const off = offsetOf(code);
    const sims = sim.filter((s) => s.module === code);
    const tops = topics.filter((t) => t.module === code);
    return {
      code,
      name: moduleName(code),
      examDate: examDates && examDates[code] ? examDates[code] : null,
      daysLeft: off !== null && off >= 0 ? off : null,
      passed: off !== null && off < 0,
      topicCount: all.filter((t) => t.module === code).length,
      predicted: sims.length ? { withPlan: avg(sims.map(withPlanOf)), ifYouStop: avg(tops.map(withoutOf)) } : null,
    };
  }).sort((a, b) => (a.examDate && !b.examDate ? -1 : !a.examDate && b.examDate ? 1 : a.examDate && b.examDate ? a.examDate.localeCompare(b.examDate) : a.code.localeCompare(b.code)));

  const withPlan = sim.map(withPlanOf);
  const without = topics.map(withoutOf);
  const nextMod = modules.filter((m) => m.daysLeft !== null).sort((a, b) => a.daysLeft - b.daysLeft)[0] || null;

  const nextReviews = [...topics]
    .sort((a, b) => a.dueInDays - b.dueInDays)
    .slice(0, 6)
    .map((t) => ({ topic: t.topic, dueInDays: Math.round(t.dueInDays * 10) / 10, scoreNow: Math.round(t.now) }));

  return {
    modules,
    nextExam: nextMod ? { module: nextMod.code, name: nextMod.name, date: nextMod.examDate, daysLeft: nextMod.daysLeft } : null,
    daysLeft: nextMod ? nextMod.daysLeft : null,
    hasExamDates: offsets.length > 0,
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
    totalPlannedSessions: days.reduce((n, d) => n + d.items.length, 0),
    engagement: engagement ? { index: engagement.index, label: engagement.label } : null,
    days,
  };
}

export async function getExamDates(db, studentId) {
  const doc = await db.collection('student_plans').findOne({ student_id: studentId });
  return doc && doc.exam_dates ? doc.exam_dates : {};
}

// Save (or clear, with null) the exam date of one module.
export async function setExamDate(db, studentId, module, value, now = new Date()) {
  if (!module || !knownModules().includes(module)) throw httpError(400, 'Unknown module');
  const col = db.collection('student_plans');
  const key = `exam_dates.${module}`;
  if (value === null || value === '' || value === undefined) {
    await col.updateOne({ student_id: studentId }, { $unset: { [key]: '' }, $set: { updated_at: now.toISOString() } }, { upsert: true });
    return null;
  }
  const d = parseDate(value);
  if (!d) throw httpError(400, 'Exam date must look like 2026-11-20');
  const n = daysBetween(now, d);
  if (n < 0) throw httpError(400, 'The exam date cannot be in the past');
  if (n > 365) throw httpError(400, 'Pick an exam date within the next year');
  const exam_date = isoDate(d);
  await col.updateOne({ student_id: studentId }, { $set: { [key]: exam_date, student_id: studentId, updated_at: now.toISOString() } }, { upsert: true });
  return exam_date;
}

export async function getPlan(db, studentId, now = new Date()) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');
  const events = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  const examDates = await getExamDates(db, studentId);
  const plan = buildPlan({ mastery: state.mastery, events, examDates, now, practicable: practiceTopics() });
  return { studentId, generatedAt: now.toISOString(), ...plan };
}
