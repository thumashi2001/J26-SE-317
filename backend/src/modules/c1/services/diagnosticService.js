const QUESTIONS_PER_TOPIC = 2;

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

export async function submitDiagnostic(db, studentId, answers, aiUrl) {
  const student = await getStudent(db, studentId);
  const assignment = await db.collection('diagnostic_assignments').findOne({ student_id: studentId, completed: false });
  if (!assignment) throw httpError(404, 'No open diagnostic test for this student');

  const bank = await db.collection('question_bank').find({ question_id: { $in: assignment.question_ids } }).toArray();
  const chosen = {};
  for (const a of answers) chosen[a.question_id] = a.selected;

  // Grade on the server using the stored answer key. Unanswered counts as wrong.
  const now = new Date();
  const graded = bank.map((q) => ({ topic: q.topic, correct: chosen[q.question_id] === q.correct_answer }));
  const events = bank.map((q, i) => ({
    student_id: studentId,
    timestamp: now,
    type: 'diagnostic_answer',
    question_id: q.question_id,
    topic: q.topic,
    correct: graded[i].correct,
    hint_used: false,
  }));

  const ai = await callAiScore(aiUrl, studentId, graded);

  const mastery = {};
  for (const [topic, m] of Object.entries(ai.mastery)) {
    mastery[topic] = { ...m, last_practiced: now, practice_sessions: 1 };
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
  await db.collection('diagnostic_assignments').updateOne(
    { student_id: studentId, completed: false },
    { $set: { completed: true, completed_at: now } }
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