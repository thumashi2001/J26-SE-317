import { httpError } from './aiClient.js';
import { decay } from './planService.js';

// KNOWLEDGE LEVEL, 5 stars. It follows the twin, so it moves when the twin moves.
//   level score = average of the topic scores after forgetting (the estimated score now)
//   stars       = level score / 20, rounded to the nearest half star (0.5 to 5)
//   label       = under 20 Beginner, 20 to 39 Building, 40 to 59 Developing, 60 to 79 Strong, 80 and above Expert
const DAY_MS = 24 * 60 * 60 * 1000;

export const labelFor = (score) => (score < 20 ? 'Beginner' : score < 40 ? 'Building' : score < 60 ? 'Developing' : score < 80 ? 'Strong' : 'Expert');
export const starsFor = (score) => Math.max(0.5, Math.min(5, Math.round((score / 20) * 2) / 2));

export function levelFrom(mastery, now = new Date()) {
  const rows = Object.entries(mastery || {}).map(([topic, m]) => {
    const days = m.last_practiced ? Math.max(0, (now.getTime() - new Date(m.last_practiced).getTime()) / DAY_MS) : 0;
    return { topic, score: decay(m.score, days, m.practice_sessions || 0), sessions: m.practice_sessions || 0 };
  });
  const score = rows.length ? Math.round(rows.reduce((a, r) => a + r.score, 0) / rows.length) : 0;
  const sorted = [...rows].sort((a, b) => b.score - a.score);
  return {
    score,
    stars: starsFor(score),
    label: labelFor(score),
    topics: rows.length,
    practised: rows.filter((r) => r.sessions > 0).length,
    strongest: sorted[0] ? sorted[0].topic : null,
    weakest: sorted.length ? sorted[sorted.length - 1].topic : null,
    nextLevelAt: score >= 80 ? null : Math.floor(score / 20) * 20 + 20,
  };
}

export async function getLevel(db, studentId, now = new Date()) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');
  return { studentId, ...levelFrom(state.mastery, now) };
}
