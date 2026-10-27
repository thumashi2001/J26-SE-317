// HIDING THE ANSWER KEY FROM STUDENTS (MCQ).
//
// SIMPLE ENGLISH
//   The full stored result of a multiple-choice question names the correct option in many places (labels, explanation,
//   feedback text, the mind map). Lecturers must see all of that, but a student must not learn the answer key from
//   the response. So the student gets a REBUILT, smaller copy that contains only the outcome (correct / not correct /
//   not answered) and the marks. The stored record in MongoDB is never changed by this file.
//
// This is an "allowlist": the student copy is constructed field by field, so a field that is not written here can
// never leak.
//
// Lecturers and admins get the full stored evaluation. For multiple-choice results the stored evaluation names the
// correct option in many places (labels, rubric descriptor, explanation, feedback, concept names, map node), so a
// student copy is rebuilt from the outcome only (correct / not correct / not answered, marks). Subjective (written
// answer) evaluations contain no answer key and are returned unchanged.

// Is this stored evaluation an MCQ result? (by answer_type or by the marking version label "mcq-...")
export function isMcqEvaluation(evaluation) {
  if (!evaluation || typeof evaluation !== 'object') return false;
  const type = String(evaluation.answer_type || '').toLowerCase();
  const version = String(evaluation.marking?.marking_version || '');
  return type === 'mcq' || type === 'multiple-choice' || version.startsWith('mcq-');
}

const AI_WARNING = /AI score estimate/i;

// Remove the staff-only advisory estimate. Returns the SAME object when there is nothing to remove.
function stripAiEstimate(evaluation) {
  if (!evaluation || typeof evaluation !== 'object') return evaluation;
  const warningsOf = (w) => (Array.isArray(w) ? w.filter((x) => !AI_WARNING.test(String(x))) : w);
  const hasWarning = Array.isArray(evaluation.warnings) && evaluation.warnings.some((x) => AI_WARNING.test(String(x)));
  if (!('ai_estimate' in evaluation) && !hasWarning) return evaluation;
  const { ai_estimate: _removed, ...rest } = evaluation;
  return { ...rest, warnings: warningsOf(evaluation.warnings) };
}

// Build the student-safe copy of an evaluation.
export function redactEvaluationForStudent(evaluation) {
  // Written answers contain no answer key, so they are returned unchanged, except for the advisory AI estimate: it is a
  // lecturer review aid (not a mark), so students never receive it or the warning it adds.
  if (!isMcqEvaluation(evaluation)) return stripAiEstimate(evaluation);

  const awarded = evaluation.total_awarded_marks ?? evaluation.marking?.total_awarded_marks ?? 0;
  const possible = evaluation.total_possible_marks ?? evaluation.marking?.total_possible_marks ?? 0;
  const percentage = evaluation.percentage ?? evaluation.marking?.percentage ?? null;
  const unanswered = evaluation.is_unanswered === true;
  const correct = evaluation.is_correct === true;

  // Neutral wording that says whether the choice was right, but never WHICH option is the right one.
  const outcome = correct ? 'Your selected option is correct.' : unanswered ? 'No option was selected.' : 'Your selected option is not correct.';
  const level = correct ? { id: 'MCQ-CORRECT', label: 'Correct' } : unanswered ? { id: 'MCQ-UNANSWERED', label: 'Unanswered' } : { id: 'MCQ-INCORRECT', label: 'Incorrect' };
  const explanation = `${outcome} Mark: ${awarded} / ${possible}.`;

  return {
    question_id: evaluation.question_id,
    answer_type: 'mcq',
    is_correct: evaluation.is_correct,
    is_unanswered: evaluation.is_unanswered,
    total_awarded_marks: awarded,
    total_possible_marks: possible,
    percentage,
    // What the student chose (their own selection), not the key.
    selected_option_ids: evaluation.selected_option_ids,
    selected_labels: evaluation.selected_labels,
    // Options are copied with only id/label/text (no correctness markers).
    options: Array.isArray(evaluation.options) ? evaluation.options.map((o) => ({ option_id: o.option_id, label: o.label, text: o.text })) : null,
    marking: {
      question_id: evaluation.question_id,
      total_awarded_marks: awarded,
      total_possible_marks: possible,
      percentage,
      marking_version: evaluation.marking?.marking_version,
      overall_explanation: explanation,
      warnings: [],
      criteria_results: [
        {
          criterion_id: 'MCQ',
          criterion_description: 'Multiple-choice answer',
          selected_level_id: level.id,
          selected_level_label: level.label,
          rubric_descriptor: outcome,
          awarded_mark: awarded,
          max_marks: possible,
          evidence_sentence_ids: [],
          supporting_concepts: [],
          explanation,
          warnings: [],
        },
      ],
    },
    // MCQ has no concept analysis or map for students (they would reveal the key).
    analysis: null,
    feedback: {
      question_id: evaluation.question_id,
      summary: outcome,
      strengths: correct ? ['You chose the correct option.'] : [],
      missing_concepts: [],
      misconceptions: [],
      actionable_guidance: correct
        ? 'Consolidate this knowledge by practising related application questions.'
        : 'Review the lecture notes on this topic before trying again.',
      rubric_alignment: `Mark: ${awarded} / ${possible}${percentage != null ? ` (${percentage}%)` : ''}.`,
      warnings: [],
    },
    mindmap: null,
    redacted: true,   // lets the UI show "details withheld" instead of an empty analysis
  };
}
