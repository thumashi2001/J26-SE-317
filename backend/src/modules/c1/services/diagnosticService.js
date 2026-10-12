import { recordSnapshot } from './historyService.js';
import { FAST_SEC, gainWeight } from './behaviourService.js';

const QUESTIONS_PER_TOPIC = 1;
// Same pace as the practice quiz (7 questions in 5 minutes). 28 questions = 20 minutes.
export const SECONDS_PER_QUESTION = 43;
// The starting score of a topic with no evidence is 40 (the AI scorer adds 0.8 correct out of 2).
const PRIOR_SCORE = 40;
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, Number.isFinite(n) ? n : lo));

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// Never send the answer key to the browser.
function publicQuestion(q) {
  return {
    question_id: q.question_id,
    module_code: q.module_code,
    topic: q.topic,
    question_text: q.question_text,
    options: q.options,
  };
}

async function getStudent(db, studentId) {
  const student = await db.collection('students').findOne({ student_id: studentId });
  if (!student) throw httpError(404, `Student ${studentId} not found`);
  return student;
}

// Returns the student's open diagnostic test, creating a random one for their semester if needed.
export async function getOrCreateAssignment(db, studentId) {
  const student = await getStudent(db, studentId);

  const done = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (done && done.diagnostic_completed) {
    throw httpError(409, 'Diagnostic already completed for this student');
  }

  let assignment = await db.collection('diagnostic_assignments').findOne({ student_id: studentId, completed: false });
  let questions;

  if (assignment) {
    const found = await db.collection('question_bank').find({ question_id: { $in: assignment.question_ids } }).toArray();
    // keep the exact order the student was first given
    const byId = Object.fromEntries(found.map((q) => [q.question_id, q]));
    questions = assignment.question_ids.map((id) => byId[id]).filter(Boolean);
  } else {
    const pool = await db.collection('question_bank').find({ semester: student.semester }).toArray();
    if (pool.length === 0) throw httpError(404, `No questions found for ${student.semester}`);

    const byTopic = {};
    for (const q of pool) (byTopic[q.topic] = byTopic[q.topic] || []).push(q);

    questions = [];
    for (const topic of Object.keys(byTopic)) {
      questions.push(...shuffle(byTopic[topic]).slice(0, QUESTIONS_PER_TOPIC));
    }
    questions = shuffle(questions);

    assignment = {
      student_id: studentId,
      semester: student.semester,
      question_ids: questions.map((q) => q.question_id),
      assigned_at: new Date(),
      completed: false,
    };
    const result = await db.collection('diagnostic_assignments').insertOne(assignment);
    assignment._id = result.insertedId;
  }

  return {
    assignmentId: String(assignment._id),
    studentId,
    semester: student.semester,
    questions: questions.map(publicQuestion),
    timeLimitSec: Math.round((questions.length * SECONDS_PER_QUESTION) / 30) * 30, // to the nearest half minute
  };
}

async function callAiScore(aiUrl, studentId, graded) {
  let res;
  try {
    res = await fetch(`${aiUrl}/diagnostic/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ student_id: studentId, answers: graded }),
    });
  } catch (e) {
    throw httpError(502, `AI service unreachable at ${aiUrl}. Is it running?`);
  }
  if (!res.ok) throw httpError(502, `AI service returned ${res.status}`);
  return res.json();
}

export async function submitDiagnostic(db, studentId, answers, aiUrl, meta = {}) {
  const student = await getStudent(db, studentId);
  const assignment = await db.collection('diagnostic_assignments').findOne({ student_id: studentId, completed: false });
  if (!assignment) throw httpError(404, 'No open diagnostic test for this student');

  const bank = await db.collection('question_bank').find({ question_id: { $in: assignment.question_ids } }).toArray();
  const chosen = {};
  const given = {};
  for (const a of answers) {
    chosen[a.question_id] = a.selected;
    given[a.question_id] = a;
  }

  // Grade on the server using the stored answer key. Unanswered counts as wrong.
  const now = new Date();
  const graded = bank.map((q) => ({ topic: q.topic, correct: chosen[q.question_id] === q.correct_answer }));
  // Time and tab leaves per question. Fast answers and tab leaves count less (same rule as the practice quiz).
  const events = bank.map((q, i) => {
    const a = given[q.question_id] || {};
    const answered = chosen[q.question_id] != null;
    const timeSec = answered && a.time_sec != null ? Math.round(clamp(Number(a.time_sec), 0, 3600)) : null;
    const tabLeaves = Math.round(clamp(Number(a.tab_leaves) || 0, 0, 99));
    const correct = graded[i].correct;
    const weight = answered ? gainWeight({ correct, timeSec, tabLeaves }, null) : 1;
    return {
      student_id: studentId,
      timestamp: now,
      type: 'diagnostic_answer',
      question_id: q.question_id,
      topic: q.topic,
      correct,
      answered,
      time_sec: timeSec,
      tab_leaves: tabLeaves,
      likely_guess: answered && !correct && timeSec != null && timeSec < FAST_SEC,
      weight,
      hint_used: false,
    };
  });

  const ai = await callAiScore(aiUrl, studentId, graded);

  const mastery = {};
  for (const [topic, m] of Object.entries(ai.mastery)) {
    // A correct answer that was very fast, or given after leaving the tab, counts for less of the gain above the start score.
    const correctWeights = events.filter((e) => e.topic === topic && e.correct).map((e) => e.weight);
    let score = m.score;
    if (correctWeights.length && score > PRIOR_SCORE) {
      const w = correctWeights.reduce((x, y) => x + y, 0) / correctWeights.length;
      score = Math.round((PRIOR_SCORE + w * (score - PRIOR_SCORE)) * 10) / 10;
    }
    mastery[topic] = { ...m, score, last_practiced: now, practice_sessions: 1 };
  }

  const state = {
    student_id: studentId,
    semester: student.semester,
    diagnostic_completed: true,
    mastery,
    risk_level: null,
    updated_at: now,
  };
  await db.collection('mastery_state').replaceOne({ student_id: studentId }, state, { upsert: true });
  await db.collection('learning_events').insertMany(events);
  for (const [topic, m] of Object.entries(mastery)) {
    await recordSnapshot(db, { studentId, topic, score: m.score, source: 'diagnostic', when: now });
  }
  await db.collection('diagnostic_assignments').updateOne(
    { student_id: studentId, completed: false },
    { $set: { completed: true, completed_at: now, total_sec: meta.totalSec ?? null, timed_out: !!meta.timedOut } }
  );

  return { studentId, semester: student.semester, mastery };
}

export async function getTwin(db, studentId) {
  await getStudent(db, studentId);
  const state = await db.collection('mastery_state').findOne({ student_id: studentId });
  if (!state) return { studentId, diagnosticCompleted: false, mastery: {} };
  return {
    studentId,
    semester: state.semester,
    diagnosticCompleted: !!state.diagnostic_completed,
    mastery: state.mastery,
    riskLevel: state.risk_level,
    updatedAt: state.updated_at,
  };
}
