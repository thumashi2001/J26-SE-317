import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { levelFrom, labelFor } from './levelService.js';

// Component 1 numbers for the admin dashboard. Totals only: no student names, IDs or answers leave this file.
const DAY_MS = 24 * 60 * 60 * 1000;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const RESULTS = path.resolve(HERE, '../../../../../ai-services/c1/ml/reports/results.json');

// Pure part, easy to test: the lists in, the summary out.
export function summarise({ studentCount, states, events, sessionCount, now = new Date() }) {
  const done = states.filter((s) => s.diagnostic_completed);
  const risk = { Low: 0, Medium: 0, High: 0 };
  const perTopic = {};
  let levelSum = 0;
  for (const s of done) {
    if (risk[s.risk_level] !== undefined) risk[s.risk_level] += 1;
    levelSum += levelFrom(s.mastery, now).score;
    for (const [topic, m] of Object.entries(s.mastery || {})) {
      const t = (perTopic[topic] = perTopic[topic] || { sum: 0, n: 0 });
      t.sum += Number(m.score) || 0;
      t.n += 1;
    }
  }
  const avgScore = done.length ? Math.round(levelSum / done.length) : null;
  const weakest = Object.entries(perTopic)
    .map(([topic, t]) => ({ topic, average: Math.round(t.sum / t.n), students: t.n }))
    .sort((a, b) => a.average - b.average)
    .slice(0, 5);

  const weekAgo = now.getTime() - 7 * DAY_MS;
  const recent = events.filter((e) => new Date(e.timestamp).getTime() >= weekAgo);
  return {
    students: studentCount,
    diagnosticDone: done.length,
    activeThisWeek: new Set(recent.map((e) => e.student_id)).size,
    answers: { total: events.length, thisWeek: recent.length },
    practiceSessions: sessionCount,
    averageLevel: avgScore === null ? null : { score: avgScore, label: labelFor(avgScore) },
    risk,
    weakestTopics: weakest,
    generatedAt: now.toISOString(),
  };
}

// What the trained model is and how well it did (read from the training report; null if the report is missing).
export function modelInfo(file = RESULTS) {
  try {
    const r = JSON.parse(fs.readFileSync(file, 'utf8')).next_answer;
    return {
      name: 'Gradient boosting',
      measure: 'AUC on students it had not seen',
      score: Math.round(r.gbm.auc * 1000) / 1000,
      ruleBasedScore: Math.round(r.rule_twin.auc * 1000) / 1000,
      trainedOn: 'synthetic students',
    };
  } catch {
    return null;
  }
}

// Is the Python AI service answering? (a short timeout, never throws)
export async function aiStatus(aiUrl, fetchFn = fetch) {
  try {
    const res = await fetchFn(`${aiUrl}/health`, { signal: AbortSignal.timeout(1500) });
    return res.ok ? 'online' : 'offline';
  } catch {
    return 'offline';
  }
}

// Students who answered a question in the last 7 days, most active first. Name, picture and activity only (no IDs).
export function activeFrom(events, students, now = new Date()) {
  const weekAgo = now.getTime() - 7 * DAY_MS;
  const by = {};
  for (const e of events) {
    const t = new Date(e.timestamp).getTime();
    if (t < weekAgo) continue;
    const a = (by[e.student_id] = by[e.student_id] || { answers: 0, last: 0 });
    a.answers += 1;
    a.last = Math.max(a.last, t);
  }
  const info = Object.fromEntries(students.map((s) => [s.student_id, s]));
  return Object.entries(by)
    .map(([id, a]) => ({
      name: (info[id] && info[id].name) || 'Student',
      semester: (info[id] && info[id].semester) || null,
      avatar: (info[id] && info[id].avatar) || null,
      answersThisWeek: a.answers,
      lastActive: new Date(a.last).toISOString(),
    }))
    .sort((a, b) => b.answersThisWeek - a.answersThisWeek || b.lastActive.localeCompare(a.lastActive));
}

export async function getActive(db, now = new Date()) {
  const weekAgo = new Date(now.getTime() - 7 * DAY_MS);
  const events = await db
    .collection('learning_events')
    .find({ type: 'quiz_answer', timestamp: { $gte: weekAgo } }, { projection: { student_id: 1, timestamp: 1 } })
    .toArray();
  const ids = [...new Set(events.map((e) => e.student_id))];
  const students = ids.length
    ? await db.collection('students').find({ student_id: { $in: ids } }, { projection: { student_id: 1, name: 1, semester: 1, avatar: 1 } }).toArray()
    : [];
  return { students: activeFrom(events, students, now), generatedAt: now.toISOString() };
}

export async function getSummary(db, aiUrl, now = new Date()) {
  const [studentCount, states, events, sessionCount] = await Promise.all([
    db.collection('students').countDocuments({}),
    db.collection('mastery_state').find({}).toArray(),
    db.collection('learning_events').find({ type: 'quiz_answer' }, { projection: { student_id: 1, timestamp: 1 } }).toArray(),
    db.collection('practice_sessions').countDocuments({}),
  ]);
  return { ...summarise({ studentCount, states, events, sessionCount, now }), model: modelInfo(), aiService: await aiStatus(aiUrl) };
}
