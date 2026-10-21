import { summarise } from './adminSummaryService.js';
import { levelFrom } from './levelService.js';
import { decay } from './planService.js';

// Class view for lecturers (Component 1).
// Lecturers are not linked to individual students yet, so "the class" is every registered student.
// Names are shown so a lecturer can follow up. Student IDs never leave this file.
const MAX_LISTED = 8;
const RANK = { High: 0, Medium: 1 };
const MAX_HEATMAP_ROWS = 30;
const DAY_MS = 24 * 60 * 60 * 1000;

// Mastery heat map: one row per student, one column per topic, each cell is the estimated score now
// (the twin score after forgetting). A topic the student has not practised stays null (shown grey).
// Rows are ordered weakest student first. Student IDs never leave this file.
export function buildHeatmap({ students, states, now = new Date() }) {
  const info = Object.fromEntries(students.map((s) => [s.student_id, s]));
  const rated = states.filter((s) => s.diagnostic_completed && info[s.student_id]);
  const topics = [...new Set(rated.flatMap((s) => Object.keys(s.mastery || {})))].sort();
  const rows = rated.map((s) => {
    const scores = {};
    let sum = 0;
    let n = 0;
    for (const t of topics) {
      const m = (s.mastery || {})[t];
      if (!m) { scores[t] = null; continue; }
      const days = m.last_practiced ? Math.max(0, (now.getTime() - new Date(m.last_practiced).getTime()) / DAY_MS) : 0;
      scores[t] = Math.round(decay(m.score, days, m.practice_sessions || 0));
      sum += scores[t];
      n += 1;
    }
    return { name: info[s.student_id].name || 'Student', average: n ? Math.round(sum / n) : 0, scores };
  });
  rows.sort((a, b) => a.average - b.average);
  const topicAverage = Object.fromEntries(
    topics.map((t) => {
      const v = rows.map((r) => r.scores[t]).filter((x) => x !== null);
      return [t, v.length ? Math.round(v.reduce((a, b) => a + b, 0) / v.length) : null];
    }),
  );
  return { topics, topicAverage, rows: rows.slice(0, MAX_HEATMAP_ROWS), totalStudents: rows.length };
}

// Pure part, easy to test: the lists in, the class view out.
export function buildClass({ students, states, events, now = new Date() }) {
  const base = summarise({ studentCount: students.length, states, events, sessionCount: 0, now });
  const info = Object.fromEntries(students.map((s) => [s.student_id, s]));

  const lastSeen = {};
  for (const e of events) {
    const t = new Date(e.timestamp).getTime();
    if (!(t <= (lastSeen[e.student_id] || 0))) lastSeen[e.student_id] = t;
  }

  const needAttention = states
    .filter((s) => s.diagnostic_completed && RANK[s.risk_level] !== undefined && info[s.student_id])
    .map((s) => {
      const lv = levelFrom(s.mastery, now);
      return {
        name: info[s.student_id].name || 'Student',
        semester: info[s.student_id].semester || null,
        risk: s.risk_level,
        level: lv.score,
        weakest: lv.weakest,
        lastActive: lastSeen[s.student_id] ? new Date(lastSeen[s.student_id]).toISOString() : null,
      };
    })
    .sort((a, b) => RANK[a.risk] - RANK[b.risk] || a.level - b.level)
    .slice(0, MAX_LISTED);

  return {
    className: 'All registered students',
    students: base.students,
    diagnosticDone: base.diagnosticDone,
    activeThisWeek: base.activeThisWeek,
    answers: base.answers,
    averageLevel: base.averageLevel,
    risk: base.risk,
    // finished the diagnostic but have not answered a practice question yet, so no risk rating exists
    notRated: Math.max(0, base.diagnosticDone - base.risk.Low - base.risk.Medium - base.risk.High),
    weakestTopics: base.weakestTopics,
    needAttention,
    heatmap: buildHeatmap({ students, states, now }),
    generatedAt: base.generatedAt,
  };
}

export async function getClass(db, now = new Date()) {
  const [students, states, events] = await Promise.all([
    db.collection('students').find({}, { projection: { student_id: 1, name: 1, semester: 1 } }).toArray(),
    db.collection('mastery_state').find({}).toArray(),
    db.collection('learning_events').find({ type: 'quiz_answer' }, { projection: { student_id: 1, timestamp: 1 } }).toArray(),
  ]);
  return buildClass({ students, states, events, now });
}
