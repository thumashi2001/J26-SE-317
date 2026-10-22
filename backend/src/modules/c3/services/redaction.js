// What a student may receive about a marked answer.
//
// Lecturers and admins get the full stored evaluation. For multiple-choice results the stored evaluation names the
// correct option in many places (labels, rubric descriptor, explanation, feedback, concept names, map node), so a
// student copy is rebuilt from the outcome only (correct / not correct / not answered, marks). Subjective (written
// answer) evaluations contain no answer key and are returned unchanged.

export function isMcqEvaluation(evaluation) {
  if (!evaluation || typeof evaluation !== 'object') return false;
  const type = String(evaluation.answer_type || '').toLowerCase();
  const version = String(evaluation.marking?.marking_version || '');
  return type === 'mcq' || type === 'multiple-choice' || version.startsWith('mcq-');
}

export function redactEvaluationForStudent(evaluation) {
  if (!isMcqEvaluation(evaluation)) return evaluation;

  const awarded = evaluation.total_awarded_marks ?? evaluation.marking?.total_awarded_marks ?? 0;
  const possible = evaluation.total_possible_marks ?? evaluation.marking?.total_possible_marks ?? 0;
  const percentage = evaluation.percentage ?? evaluation.marking?.percentage ?? null;
  const unanswered = evaluation.is_unanswered === true;
  const correct = evaluation.is_correct === true;

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
    selected_option_ids: evaluation.selected_option_ids,
    selected_labels: evaluation.selected_labels,
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
    redacted: true,
  };
}
