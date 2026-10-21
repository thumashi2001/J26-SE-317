import { callAi, httpError } from './aiClient.js';
import { TOPICS } from '../data/content/index.js';

const DAY_MS = 24 * 60 * 60 * 1000;

const bandFor = (pct) => (pct >= 70 ? 'likely' : pct >= 50 ? 'unsure' : 'unlikely');

// Turns the student's logged answers into the format the trained model expects.
export function toModelEvents(logged) {
  const sorted = [...logged].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  if (!sorted.length) return { events: [], start: null };
  const start = new Date(sorted[0].timestamp).getTime();
  const position = {};
  const events = sorted.map((e) => {
    const t = new Date(e.timestamp).getTime();
    const day = (t - start) / DAY_MS;
    const session = e.session_id || `day${Math.floor(day)}`;
    const q = (position[session] = (position[session] ?? -1) + 1);
    return {
      day,
      topic: e.topic,
      module: (TOPICS[e.topic] && TOPICS[e.topic].module_code) || 'OTHER',
      source: 'quiz',
      session_id: String(session),
      q_in_session: q,
      question_type: 'single',
      correct: e.correct ? 1 : 0,
      time_sec: Number(e.time_sec) || 30,
      hint_used: e.hint_used ? 1 : 0,
      tab_leaves: Number(e.tab_leaves) || 0,
    };
  });
  return { events, start };
}

// For every topic the student has answered: the chance they get the next question on it right, from the trained model.
export async function getPredictions(db, studentId, aiUrl, now = new Date(), ai = callAi) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');

  const logged = await db.collection('learning_events').find({ student_id: studentId, type: 'quiz_answer' }).toArray();
  const { events, start } = toModelEvents(logged);
  const base = { studentId, model: 'Gradient boosting', trainedOn: 'synthetic students', generatedAt: now.toISOString() };
  if (!events.length) return { ...base, topics: {} };
    // Sends the student's logged answers to the Python AI service, which builds the same 22 features used in
  // training and runs the gradient boosting model. It replies with a chance (0 to 1) for each topic. 
  const reply = await ai(aiUrl, '/twin/predict-correct', { as_of_day: (now.getTime() - start) / DAY_MS, events });
  const topics = {};
  for (const [topic, r] of Object.entries(reply.topics || {})) {
    const chance = Math.round(r.p * 100);
    topics[topic] = { chance, band: bandFor(chance), answers: r.answers };
  }
  return { ...base, topics };
}
