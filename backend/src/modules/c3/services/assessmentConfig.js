import { DEMO_ASSESSMENTS } from '../data/demoAssessments.js';

// Students are untrusted: they may supply only their own answer. The question, answer key, rubric and
// maximum marks always come from the server's built-in demo bank (students never resolve lecturer batches).
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
  // Student workflow is demo-only: lecturer batches are a lecturer-side feature and are never resolved for students.
  if (batch_id !== undefined && batch_id !== null) {
    throw httpError(400, 'Lecturer batches are not available in the student assessment flow. Choose one of the listed demo assessments');
  }
  if (demo_id === undefined || demo_id === null || demo_id === '') {
    throw httpError(400, 'Choose an assessment (demo_id) before submitting an answer');
  }
  if (typeof demo_id !== 'string') throw httpError(400, 'Invalid demo_id');

  const answerFields = {
    student_answer: payload.student_answer,
    selected_option_id: payload.selected_option_id,
    selected_options: payload.selected_options,
  };

  // Own properties only: names such as "constructor" or "__proto__" must not resolve.
  if (!Object.hasOwn(DEMO_ASSESSMENTS, demo_id)) throw httpError(404, 'Unknown demo assessment');
  const demo = DEMO_ASSESSMENTS[demo_id];
  return { ...structuredClone(demo.config), ...answerFields, is_demo: true, config_source: 'server_demo_bank' };
}

// What a student may see about an assessment: the question and, for MCQ, the options. Never the answer key,
// rubric levels, reference answer or expected concepts.
function publicOptions(options) {
  if (!Array.isArray(options)) return null;
  return options.map((o) => ({ option_id: o.option_id, label: o.label, text: o.text }));
}

// Honest integration status shown to students. C2 has no assessment export yet (contract documented in
// backend/src/integration/c2-c3/README.md; C2 exposes no routes). Nothing in the list below originates from C2.
export const C2_INTEGRATION = Object.freeze({
  available: false,
  reason: 'No C2 assessment export is available yet',
});

// Student-facing list: ONLY the built-in demo bank. Lecturer batch setups are a lecturer-side marking feature and are
// not offered to students for selection (they stay in MongoDB and in the lecturer pages, untouched).
export async function listPublicAssessments() {
  return Object.entries(DEMO_ASSESSMENTS).map(([id, demo]) => ({
    id,
    kind: 'demo',
    title: demo.title,
    question_text: demo.config.question_text,
    answer_type: demo.config.answer_type || 'short',
    max_marks: demo.config.max_marks ?? demo.config.rubric?.criteria?.reduce((sum, c) => sum + Number(c.max_marks || 0), 0) ?? null,
    options: publicOptions(demo.config.options),
  }));
}

// Full example setups (with answer keys and rubrics) for lecturers who want to start a batch from an example.
// Only served to lecturer/admin roles (see routes).
export function listExampleSetups() {
  return Object.entries(DEMO_ASSESSMENTS).map(([id, demo]) => ({ id, title: demo.title, config: structuredClone(demo.config) }));
}
