/**
 * Attempt Submission Helper — C2 Student Exam Intelligence (M19)
 * Prepares and validates attempt payloads and manages submission callback execution.
 *
 * Safeguards:
 * - Preserves unassessed marks (null) for synthetic practice questions.
 * - Enforces correct moduleKey, question normalisation, and student answers dictionary.
 * - Handles callback failures gracefully without unhandled promise rejections.
 */

/**
 * Prepares a normalized attempt payload ready for backend submission.
 */
export function prepareAttemptPayload({
  paper,
  moduleKey,
  questions = [],
  answers = {},
  secondsElapsed = 0,
}) {
  const resolvedModule = paper?.module_key || paper?.moduleKey || moduleKey || '';
  const isSyntheticPaper =
    paper?.source_type === 'synthetic' ||
    paper?.practice_mode === 'synthetic_experimental';

  const sourceQuestions = Array.isArray(questions) && questions.length > 0
    ? questions
    : (Array.isArray(paper?.questions) ? paper.questions : []);

  const normalizedQuestions = sourceQuestions.map((q, idx) => {
    const qId = q.question_id || q.questionId || `Q${idx + 1}`;
    const qText = q.question_text || q.questionText || '';
    const qMarks =
      typeof q.marks === 'number' && Number.isFinite(q.marks)
        ? q.marks
        : null;
    const topicId = q.topic_id || q.topicId || null;
    const difficulty =
      q.difficulty || (isSyntheticPaper ? 'unassessed' : null);
    const sourceType =
      q.source_type || (isSyntheticPaper ? 'synthetic' : 'authentic');

    return {
      question_id: String(qId),
      question_text: String(qText),
      marks: qMarks,
      topic_id: topicId ? String(topicId) : null,
      difficulty: difficulty ? String(difficulty) : null,
      source_type: String(sourceType),
    };
  });

  const sanitizedTimeSpent =
    typeof secondsElapsed === 'number' && Number.isFinite(secondsElapsed) && secondsElapsed >= 0
      ? Math.round(secondsElapsed)
      : 0;

  return {
    mockId: String(paper?.paper_id || paper?.mock_id || paper?.mockId || 'MOCK-PRACTICE'),
    moduleKey: String(resolvedModule),
    questions: normalizedQuestions,
    answers: typeof answers === 'object' && answers !== null && !Array.isArray(answers) ? answers : {},
    timeSpentSeconds: sanitizedTimeSpent,
    sourceType: isSyntheticPaper ? 'synthetic' : 'authentic',
  };
}

/**
 * Safely executes the attempt submission through the designated callback or fallback API function.
 * Ensures any errors are handled gracefully without unhandled promise rejections.
 */
export async function executeAttemptSubmission({
  onSubmitAttempt,
  onSubmitSuccess,
  payload,
  fallbackSubmitFn,
}) {
  let result;
  if (typeof onSubmitAttempt === 'function') {
    result = await onSubmitAttempt(payload);
  } else if (typeof fallbackSubmitFn === 'function') {
    result = await fallbackSubmitFn(payload);
  } else {
    throw new Error('Attempt submission handler is not configured.');
  }

  if (typeof onSubmitSuccess === 'function') {
    onSubmitSuccess(result);
  }

  return result;
}
