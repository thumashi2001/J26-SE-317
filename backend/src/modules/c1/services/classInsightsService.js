import { summarise } from './adminSummaryService.js';
import { levelFrom } from './levelService.js';

// Class view for lecturers (Component 1).
// Lecturers are not linked to individual students yet, so "the class" is every registered student.
// Names are shown so a lecturer can follow up. Student IDs never leave this file.
const MAX_LISTED = 8;
const RANK = { High: 0, Medium: 1 };

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
