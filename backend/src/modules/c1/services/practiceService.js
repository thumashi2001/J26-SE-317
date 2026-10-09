import { randomUUID } from 'crypto';
import { httpError } from './aiClient.js';
import { recordEvent } from './eventService.js';
import { PRACTICE_QUESTIONS, TIPS, TOPIC_ALIASES } from '../data/practiceQuestions.js';

export const QUESTIONS_PER_SESSION = 7;
const OPTIONS_PER_QUESTION = 4;

const bankTopic = (topic) => TOPIC_ALIASES[topic] || topic;
const questionId = (topic, index) => `PQ-${bankTopic(topic)}-${String(index + 1).padStart(2, '0')}`;

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// The practice questions live in code (data/practiceQuestions.js). They are copied into the
// practice_bank collection the first time a topic is practised, so the data also lives in the
// database like the rest of the twin. `node scripts/seedPractice.js` copies all topics at once.
export async function seedTopic(db, topic) {
  const list = PRACTICE_QUESTIONS[bankTopic(topic)] || [];
  const col = db.collection('practice_bank');
  const have = await col.countDocuments({ topic: bankTopic(topic) });
  if (have >= list.length) return list.length;
  for (const [i, q] of list.entries()) {
    await col.replaceOne(
      { question_id: questionId(topic, i) },
      {
        question_id: questionId(topic, i),
        topic: bankTopic(topic),
        question_text: q.text,
        options: q.options,
        correct: q.correct,
        explanation: q.why,
        tip: q.tip,
      },
      { upsert: true }
    );
  }
  return list.length;
}

export async function seedAll(db) {
  let total = 0;
  for (const topic of Object.keys(PRACTICE_QUESTIONS)) {
    const list = PRACTICE_QUESTIONS[topic];
    for (const [i, q] of list.entries()) {
      await db.collection('practice_bank').replaceOne(
        { question_id: questionId(topic, i) },
        {
          question_id: questionId(topic, i),
          topic,
          question_text: q.text,
          options: q.options,
          correct: q.correct,
          explanation: q.why,
          tip: q.tip,
        },
        { upsert: true }
      );
      total += 1;
    }
  }
  return total;
}

// What the browser may see. The answer key is never included.
function publicItem(item, bank) {
  const q = bank[item.question_id];
  return {
    id: item.question_id,
    text: q.question_text,
    options: item.order.map((i) => q.options[i]),
    multi: q.correct.length > 1,
    answered: !!item.answered,
  };
}

function sessionView(session, bank) {
  const answered = session.items.filter((i) => i.answered).length;
  return {
    sessionId: session.session_id,
    topic: session.topic,
    total: session.items.length,
    answered,
    correctCount: session.items.filter((i) => i.correct).length,
    done: !!session.completed,
    scoreStart: session.score_start,
    scoreNow: session.score_now,
    questions: session.items.map((i) => publicItem(i, bank)),
  };
}

async function loadBank(db, ids) {
  const rows = await db.collection('practice_bank').find({ question_id: { $in: ids } }).toArray();
  return Object.fromEntries(rows.map((r) => [r.question_id, r]));
}

// Topic keys (as stored in a student's twin) that have practice questions.
export function practiceTopics() {
  return [...Object.keys(PRACTICE_QUESTIONS), ...Object.keys(TOPIC_ALIASES).filter((k) => PRACTICE_QUESTIONS[TOPIC_ALIASES[k]])];
}

export async function startSession(db, studentId, topic) {
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state || !state.diagnostic_completed) throw httpError(409, 'Complete the diagnostic test first');
  const entry = state.mastery[topic];
  if (!entry) throw httpError(404, `Unknown topic: ${topic}`);

  const count = await seedTopic(db, topic);
  if (count === 0) throw httpError(404, 'There are no practice questions for this topic yet');

  const past = await db.collection('practice_sessions').find({ student_id: studentId, topic }).toArray();

  // Carry on with an unfinished session instead of starting a new one.
  // If two open sessions ever exist (for example a double click), keep the newest and close the rest.
  const opens = past.filter((s) => !s.completed).sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
  for (const stale of opens.slice(1)) {
    stale.completed = true;
    stale.abandoned = true;
    await db.collection('practice_sessions').replaceOne({ session_id: stale.session_id }, stale);
  }
  const open = opens[0];
  if (open) {
    const bank = await loadBank(db, open.items.map((i) => i.question_id));
    return sessionView(open, bank);
  }

  // Pick the questions this student has seen least recently, with a random order inside ties.
  const lastSeen = {};
  for (const s of past) {
    for (const i of s.items) {
      lastSeen[i.question_id] = Math.max(lastSeen[i.question_id] || 0, new Date(s.started_at).getTime());
    }
  }
  const all = Array.from({ length: count }, (_, i) => questionId(topic, i));
  const ranked = shuffle(all).sort((a, b) => (lastSeen[a] || 0) - (lastSeen[b] || 0));
  const chosen = shuffle(ranked.slice(0, Math.min(QUESTIONS_PER_SESSION, count)));

  const session = {
    session_id: randomUUID(),
    student_id: studentId,
    topic,
    started_at: new Date(),
    score_start: entry.score,
    score_now: entry.score,
    completed: false,
    items: chosen.map((id) => ({
      question_id: id,
      order: shuffle([0, 1, 2, 3].slice(0, OPTIONS_PER_QUESTION)), // order the options are shown in
      answered: false,
    })),
  };
  await db.collection('practice_sessions').insertOne(session);
  const bank = await loadBank(db, chosen);
  return sessionView(session, bank);
}

const sameSet = (a, b) => a.length === b.length && a.every((x) => b.includes(x));
const letters = (idxs) => idxs.map((i) => 'ABCD'[i]);

export async function answerQuestion(db, studentId, input, aiUrl) {
  const { sessionId, questionId: qid } = input;
  const session = await db.collection('practice_sessions').findOne({ session_id: sessionId, student_id: studentId });
  if (!session) throw httpError(404, 'Practice session not found');
  const item = session.items.find((i) => i.question_id === qid);
  if (!item) throw httpError(404, 'That question is not part of this session');
  if (item.answered) throw httpError(409, 'This question is already answered');

  const selected = Array.isArray(input.selected) ? input.selected : [];
  const valid =
    selected.length >= 1 &&
    selected.length <= OPTIONS_PER_QUESTION &&
    new Set(selected).size === selected.length &&
    selected.every((n) => Number.isInteger(n) && n >= 0 && n < OPTIONS_PER_QUESTION);
  if (!valid) throw httpError(400, 'Choose at least one answer');

  const bank = await loadBank(db, [qid]);
  const q = bank[qid];
  if (!q) throw httpError(404, 'Question not found');

  // The browser sends positions as shown. Map them back to the original option numbers.
  const picked = selected.map((d) => item.order[d]);
  const isCorrect = sameSet(picked, q.correct);
  const found = picked.filter((p) => q.correct.includes(p)).length;
  const wrongPicked = picked.length - found;
  const correctDisplay = item.order.map((orig, d) => (q.correct.includes(orig) ? d : -1)).filter((d) => d >= 0);

  const timeSec = Math.min(600, Math.max(1, Math.round(Number(input.timeSec) || 30)));
  // How many times the student left the quiz tab for a while during this question, and for how long.
  const tabLeaves = Math.min(50, Math.max(0, Math.round(Number(input.tabLeaves) || 0)));
  const awaySec = Math.min(3600, Math.max(0, Math.round(Number(input.awaySec) || 0)));
  const result = await recordEvent(
    db,
    {
      studentId,
      topic: session.topic,
      correct: isCorrect,
      hintUsed: false,
      timeSec,
      tabLeaves,
      awaySec,
      questionId: qid,
      sessionId,
      newSession: !session.items.some((i) => i.answered), // only the first answer starts a practice session
    },
    aiUrl
  );

  item.answered = true;
  item.selected = selected;
  item.correct = isCorrect;
  item.found = found;
  item.time_sec = timeSec;
  item.tab_leaves = tabLeaves;
  item.away_sec = awaySec;
  session.score_now = result.scoreAfter;
  if (session.items.every((i) => i.answered)) {
    session.completed = true;
    session.completed_at = new Date();
  }
  await db.collection('practice_sessions').replaceOne({ session_id: sessionId }, session);

  return {
    correct: isCorrect,
    found,
    totalCorrect: q.correct.length,
    wrongPicked,
    correctIndexes: correctDisplay,
    correctLetters: letters(correctDisplay),
    explanation: q.explanation,
    tip: TIPS[q.tip] || TIPS.concept,
    afterForgetting: result.afterForgetting,
    scoreAfter: result.scoreAfter,
    tabLeaves,
    session: {
      answered: session.items.filter((i) => i.answered).length,
      total: session.items.length,
      correctCount: session.items.filter((i) => i.correct).length,
      done: session.completed,
      scoreStart: session.score_start,
      scoreNow: session.score_now,
    },
  };
}
