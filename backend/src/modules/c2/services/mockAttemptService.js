/**
 * Mock Examination Attempt Service — C2 Student Exam Intelligence (M19)
 * Handles attempt submission, validation, persistence, and genuine status reporting.
 *
 * Safeguards:
 * - Never fabricates marks or simulates grading when C3 marking is pending.
 * - Enforces student data isolation (students can only access their own attempts).
 * - Distinguishes synthetic practice questions from authentic examination questions.
 */

import {
  saveAttempt,
  getAttemptById,
  listAttemptsByStudent,
} from './mockAttemptRepository.js';

const VALID_MODULES = new Set([
  'application_frameworks',
  'case_studies_software_engineering',
  'database_systems',
  'distributed_systems',
  'software_architecture',
  'software_engineering_process_quality_management',
  'software_project_management',
  'user_experience_engineering',
]);

export class MockAttemptError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = 'MockAttemptError';
    this.status = status;
  }
}

function generateAttemptId() {
  const ts = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).slice(2, 8).toUpperCase();
  return `ATT-${ts}-${rand}`;
}

export async function submitMockAttempt({
  studentId,
  mockId,
  moduleKey,
  questions,
  answers = {},
  timeSpentSeconds = 0,
  sourceType = null,
  dbOverride = null,
}) {
  if (!studentId || typeof studentId !== 'string' || !studentId.trim()) {
    throw new MockAttemptError('A valid student identity is required', 401);
  }

  if (!moduleKey || typeof moduleKey !== 'string' || !VALID_MODULES.has(moduleKey.trim())) {
    throw new MockAttemptError(
      `Invalid module key '${moduleKey}'. Must be one of the 8 supported Year 3 modules.`,
      400
    );
  }

  if (!mockId || typeof mockId !== 'string' || !mockId.trim()) {
    throw new MockAttemptError('A valid mockId is required', 400);
  }

  if (!Array.isArray(questions) || questions.length === 0) {
    throw new MockAttemptError('Mock examination must contain at least one question', 400);
  }

  if (typeof answers !== 'object' || answers === null || Array.isArray(answers)) {
    throw new MockAttemptError('Answers must be a key-value object of question ID to answer text', 400);
  }

  const sanitizedTimeSpent =
    typeof timeSpentSeconds === 'number' && Number.isFinite(timeSpentSeconds) && timeSpentSeconds >= 0
      ? Math.round(timeSpentSeconds)
      : 0;

  let totalMarks = 0;
  let hasNumericMarks = false;

  const processedQuestions = questions.map((q, index) => {
    const qId = q.question_id || q.questionId || `Q${index + 1}`;
    const qText = q.question_text || q.questionText || '';
    const marks =
      typeof q.marks === 'number' && Number.isFinite(q.marks)
        ? q.marks
        : null; // Safely preserve null when marks are unassessed!
    const topicId = q.topic_id || q.topicId || null;
    const difficulty =
      q.difficulty ||
      (q.source_type === 'synthetic' || q.sourceType === 'synthetic'
        ? 'unassessed'
        : null);
    const sourceType = q.source_type || q.sourceType || 'authentic';

    if (marks !== null) {
      totalMarks += marks;
      hasNumericMarks = true;
    }

    const rawAnswer = answers[qId];
    const studentAnswer = typeof rawAnswer === 'string' ? rawAnswer.trim() : '';

    return {
      questionId: String(qId),
      questionText: String(qText),
      marks,
      topicId: topicId ? String(topicId) : null,
      difficulty: difficulty ? String(difficulty) : null,
      sourceType: String(sourceType),
      studentAnswer,
      isAnswered: studentAnswer.length > 0,
      marksAwarded: null, // Strictly null: Never fabricate marks!
      markingStatus: 'pending_marking',
      feedback: 'Pending evaluation',
    };
  });

  const answeredCount = processedQuestions.filter((q) => q.isAnswered).length;

  const isSyntheticAttempt =
    sourceType === 'synthetic' ||
    processedQuestions.some((q) => q.sourceType === 'synthetic');

  const attemptRecord = {
    attemptId: generateAttemptId(),
    studentId: studentId.trim(),
    mockId: mockId.trim(),
    moduleKey: moduleKey.trim(),
    sourceType: isSyntheticAttempt ? 'synthetic' : 'authentic',
    totalMarks: hasNumericMarks ? totalMarks : null,
    hasUnassessedMarks: !hasNumericMarks,
    marksAwarded: null, // Academic integrity safeguard
    questionCount: processedQuestions.length,
    answeredCount,
    timeSpentSeconds: sanitizedTimeSpent,
    status: 'pending_marking',
    c3MarkingStatus: 'pending_marking',
    academicIntegrityNotice:
      'Component 3 automated marking is pending. To preserve research integrity, no estimated or simulated grades are shown until verified.',
    submittedAt: new Date().toISOString(),
    questions: processedQuestions,
  };

  const saved = await saveAttempt(attemptRecord, dbOverride);
  return saved;
}

export async function listMockAttempts(studentId, moduleKey = null, dbOverride = null) {
  if (!studentId || typeof studentId !== 'string' || !studentId.trim()) {
    throw new MockAttemptError('A valid student identity is required', 401);
  }

  const normalizedModule =
    typeof moduleKey === 'string' && moduleKey.trim() && VALID_MODULES.has(moduleKey.trim())
      ? moduleKey.trim()
      : null;

  return listAttemptsByStudent(studentId.trim(), normalizedModule, dbOverride);
}

export async function getMockAttempt(attemptId, studentId, dbOverride = null) {
  if (!attemptId || typeof attemptId !== 'string' || !attemptId.trim()) {
    throw new MockAttemptError('A valid attemptId is required', 400);
  }

  if (!studentId || typeof studentId !== 'string' || !studentId.trim()) {
    throw new MockAttemptError('A valid student identity is required', 401);
  }

  const attempt = await getAttemptById(attemptId.trim(), studentId.trim(), dbOverride);

  if (!attempt) {
    throw new MockAttemptError('Mock examination attempt not found', 404);
  }

  return attempt;
}
