import { getDb } from '../../../config/db.js';
import { DEMO_ASSESSMENTS } from '../data/demoAssessments.js';

// Students are untrusted: they may supply only their own answer. The question, answer key, rubric and
// maximum marks always come from the server (a lecturer's batch setup or the built-in demo bank).
// Lecturers and admins are trusted authors and may still send an inline configuration.

const FORBIDDEN_STUDENT_FIELDS = [
  'correct_answer', 'correct_option_id', 'rubric', 'max_marks', 'reference_answer', 'expected_concepts',
  'options', 'answer_type', 'question_text', 'is_demo',
];

function httpError(status, message) {
  return Object.assign(new Error(message), { status });
}

export async function resolveStudentAssessment(payload) {
  const supplied = FORBIDDEN_STUDENT_FIELDS.filter((k) => payload[k] !== undefined && payload[k] !== null);
  if (supplied.length > 0) {
    throw httpError(400, `Students cannot supply assessment configuration (${supplied.join(', ')}). The question and marking scheme are set by the lecturer`);
  }
  const { demo_id, batch_id } = payload;
  if (demo_id !== undefined && typeof demo_id !== 'string') throw httpError(400, 'Invalid demo_id');
  if (batch_id !== undefined && typeof batch_id !== 'string') throw httpError(400, 'Invalid batch_id');

  const answerFields = {
    student_answer: payload.student_answer,
    selected_option_id: payload.selected_option_id,
    selected_options: payload.selected_options,
  };

  if (demo_id) {
    const demo = DEMO_ASSESSMENTS[demo_id];
    if (!demo) throw httpError(404, 'Unknown demo assessment');
    return { ...structuredClone(demo.config), ...answerFields, is_demo: true, config_source: 'server_demo_bank' };
  }

  if (batch_id) {
    const setup = await getDb().collection('c3_batch_setups').findOne({ batch_id });
    if (!setup || (setup.status && setup.status !== 'active')) throw httpError(404, 'Assessment not found');
    const cfg = {
      question_id: setup.question_id,
      question_text: setup.question_text,
      answer_type: setup.answer_type,
      max_marks: setup.max_marks,
      expected_concepts: setup.expected_concepts || [],
      batch_id: setup.batch_id,
    };
    if (setup.options) cfg.options = setup.options;
    if (setup.correct_answer) cfg.correct_answer = setup.correct_answer;
    if (setup.rubric) cfg.rubric = setup.rubric;
    if (setup.reference_answer) cfg.reference_answer = setup.reference_answer;
    return { ...structuredClone(cfg), ...answerFields, config_source: 'lecturer_batch_setup' };
  }

  throw httpError(400, 'Choose an assessment (demo_id or batch_id) before submitting an answer');
}
