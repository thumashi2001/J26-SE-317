// SUBMISSION SERVICE: saving results to MongoDB and the lecturer review workflow.
//
// WHAT IS STORED (two collections per submission):
//   c3_submissions  one document per student answer: who, which question, the answer text, status
//   c3_results      one document per submission: the automated mark, the WHOLE AI response in `ai_evaluation`
//                   (marking, analysis, feedback, mind map), and the lecturer decision fields
//                   (lecturer_decision, final_mark, override_reason, reviewed_by/at, finalized_by/at, review_history)
// MongoDB therefore only STORES results. It never calculates or supplies a mark.
//
// STATUS LIFE CYCLE: pending_review (automatic proposal) -> reviewed (lecturer accepted/changed) -> finalized (locked).
// The automatic mark (automated_mark) is never overwritten: a lecturer change goes into final_mark with a reason.

import { getDb } from '../../../config/db.js';
import { ObjectId } from 'mongodb';
import { redactEvaluationForStudent } from './redaction.js';
import { syncC3AssessmentToC1 } from '../../../integration/c3-c1/index.js';

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

// Mongo ids are ObjectId objects; this turns a 24-character hex string into one (other values are returned unchanged).
function parseId(id) {
  if (!id) return null;
  if (ObjectId.isValid(id) && typeof id === 'string' && id.length === 24) {
    return new ObjectId(id);
  }
  return id;
}

// Shortcuts to the two collections.
function submissionsCol() {
  return getDb().collection('c3_submissions');
}

function resultsCol() {
  return getDb().collection('c3_results');
}

// Label a submission as a real student answer, a PP1 demo, or a test fixture (the lecturer queue shows a badge for the last two).
export function detectProvenance(s) {
  if (!s) return 'student';
  if (s.is_demo === true) return 'pp1_demo';
  const qId = String(s.question_id || '').toUpperCase();
  const sId = String(s.student_id || '').toUpperCase();
  const status = String(s.status || '');
  if (status === 'failed' || qId === 'Q1' || sId === 'STUDENT1' || qId.startsWith('TEST_')) {
    return 'test_fixture';
  }
  const knownDemoQIds = ['SE3010-Q01', 'SE-ARCH-001', 'SE2020-Q03', 'SE3040-Q02', 'SE-ARCH-VERIFY-01', 'SE-ARCH-E2E-01'];
  if (knownDemoQIds.some(k => qId.includes(k))) {
    return 'pp1_demo';
  }
  return 'student';
}

/**
 * Creates a submission record and associated AI result record.
 * Status starts as 'pending_review' (AI Proposed) — human-in-the-loop requirement.
 */
// (called by c3Controller.assessAnswer and by batch marking)
export async function createSubmissionWithResult({ studentId, payload, aiResult }) {
  const now = new Date();
  const isDemo = Boolean(payload.is_demo) || ['SE3010-Q01', 'SE-ARCH-001', 'SE2020-Q03', 'SE3040-Q02'].includes(payload.question_id);
  const studentAnswerText = payload.student_answer || (
    aiResult?.selected_labels?.length ? `Selected Option: ${aiResult.selected_labels.join(', ')}` :
    (payload.selected_option_id || payload.selected_options ? String(payload.selected_option_id || payload.selected_options) : '')
  );
  // The submission document. For MCQ the reference_answer / correct_options fields are filled from the full evaluation;
  // they are staff-only and are removed again when a student reads their submission (see getSubmissionDetail).
  const subDoc = {
    student_id: studentId,
    question_id: payload.question_id,
    question_text: payload.question_text,
    batch_id: payload.batch_id || null,
    student_answer: studentAnswerText,
    reference_answer: payload.reference_answer || (aiResult?.correct_labels?.length ? `Correct Option: ${aiResult.correct_labels.join(', ')}` : null),
    expected_concepts: payload.expected_concepts || null,
    options: payload.options || aiResult?.options || null,
    selected_options: aiResult?.selected_option_ids || payload.selected_options || (payload.selected_option_id ? [payload.selected_option_id] : null),
    correct_options: aiResult?.correct_option_ids || (payload.correct_answer ? [payload.correct_answer] : null),
    answer_type: payload.answer_type || aiResult?.answer_type || 'short',
    rubric: payload.rubric || null,
    is_demo: isDemo,
    status: 'pending_review',
    submitted_at: now,
    updated_at: now,
  };

  // The automated mark is read from the AI/MCQ result; it is stored unchanged as automated_mark.
  const automatedMark = aiResult?.total_awarded_marks ?? aiResult?.marking?.total_awarded_marks ?? 0;
  const totalPossible = aiResult?.total_possible_marks ?? aiResult?.marking?.total_possible_marks ?? 0;
  const percentage = aiResult?.percentage ?? (totalPossible > 0 ? Math.round((automatedMark / totalPossible) * 1000) / 10 : 0);

  // (Only batch marking uses batch_id; a demo submission has none, so every demo answer creates a new submission.)
  // Check if a submission already exists for this student in this batch to prevent duplicates
  let existingSub = null;
  if (payload.batch_id && studentId) {
    existingSub = await submissionsCol().findOne({
      student_id: studentId,
      batch_id: payload.batch_id,
    });
  }

  let submissionId;
  let resultId;

  if (existingSub) {
    // A reviewed or finalized submission is the lecturer's record; it can never be silently reopened or overwritten.
    const existingStatus = existingSub.status || 'pending_review';
    const priorRes = await resultsCol().findOne({ submission_id: String(existingSub._id) });
    if (existingStatus !== 'pending_review' || (priorRes && priorRes.status && priorRes.status !== 'pending_review')) {
      throw httpError(409, 'This submission has already been reviewed or finalized and cannot be resubmitted');
    }
    submissionId = String(existingSub._id);
    await submissionsCol().updateOne(
      { _id: existingSub._id },
      { $set: { ...subDoc, submitted_at: existingSub.submitted_at, updated_at: now } }
    );

    const existingRes = await resultsCol().findOne({ submission_id: submissionId });
    if (existingRes) {
      resultId = String(existingRes._id);
      await resultsCol().updateOne(
        { _id: existingRes._id },
        {
          $set: {
            automated_mark: automatedMark,
            total_possible_marks: totalPossible,
            percentage: percentage,
            ai_evaluation: aiResult,
            status: 'pending_review',
            updated_at: now,
          },
        }
      );
    } else {
      const resDoc = {
        submission_id: submissionId,
        student_id: studentId,
        question_id: payload.question_id,
        question_text: payload.question_text,
        batch_id: payload.batch_id || null,
        automated_mark: automatedMark,
        total_possible_marks: totalPossible,
        percentage: percentage,
        ai_evaluation: aiResult,
        lecturer_decision: null,
        final_mark: null,
        override_reason: null,
        reviewed_by: null,
        reviewed_at: null,
        finalized_at: null,
        status: 'pending_review',
        created_at: now,
        updated_at: now,
      };
      const resResult = await resultsCol().insertOne(resDoc);
      resultId = String(resResult.insertedId);
    }
  } else {
    const subRes = await submissionsCol().insertOne(subDoc);
    submissionId = String(subRes.insertedId);

    const resDoc = {
      submission_id: submissionId,
      student_id: studentId,
      question_id: payload.question_id,
      question_text: payload.question_text,
      batch_id: payload.batch_id || null,
      automated_mark: automatedMark,
      total_possible_marks: totalPossible,
      percentage: percentage,
      ai_evaluation: aiResult,
      lecturer_decision: null,
      final_mark: null,
      override_reason: null,
      reviewed_by: null,
      reviewed_at: null,
      finalized_at: null,
      status: 'pending_review',
      created_at: now,
      updated_at: now,
    };

    const resResult = await resultsCol().insertOne(resDoc);
    resultId = String(resResult.insertedId);
  }

  // Best-effort hand-off to Component 1 (Cognitive Digital Twin); a failure here must not fail the student's submission.
  // Synchronize initial assessment evidence to C1 (Cognitive Digital Twin)
  syncC3AssessmentToC1({
    studentId,
    submissionId,
    questionId: payload.question_id,
    questionText: payload.question_text,
    score: automatedMark,
    totalPossible,
    percentage,
    conceptMatches: aiResult?.analysis?.concept_matches || [],
    finalized: false,
  }).catch(() => {});

  return {
    submissionId,
    resultId,
  };
}

/**
 * Lists submissions.
 * Students only see their own submissions; lecturers see all submissions.
 */
// Students automatically get only their own rows (the filter is applied on the server, not in the browser).
export async function listSubmissions({ studentId, role, status, batchId }) {
  if ((status !== undefined && typeof status !== 'string') || (batchId !== undefined && typeof batchId !== 'string')) {
    throw httpError(400, 'Invalid filter');
  }
  const query = {};
  if (role !== 'lecturer' && role !== 'admin') {
    query.student_id = studentId;
  }
  if (status) {
    query.status = status;
  }
  if (batchId) {
    query.batch_id = batchId;
  }

  const submissions = await submissionsCol()
    .find(query)
    .sort({ submitted_at: -1 })
    .limit(100)
    .toArray();

  if (submissions.length === 0) return [];

  const subIds = submissions.map((s) => String(s._id));
  const results = await resultsCol()
    .find({ submission_id: { $in: subIds } })
    .toArray();

  const resultMap = new Map();
  for (const r of results) {
    resultMap.set(String(r.submission_id), r);
  }

  return submissions.map((s) => {
    const sId = String(s._id);
    const r = resultMap.get(sId);
    const automatedMark = r?.automated_mark ?? r?.ai_evaluation?.total_awarded_marks ?? r?.ai_result?.marking?.total_awarded_marks ?? null;
    const totalPossible = r?.total_possible_marks ?? r?.ai_evaluation?.total_possible_marks ?? r?.ai_result?.marking?.total_possible_marks ?? null;
    return {
      _id: sId,
      student_id: s.student_id,
      question_id: s.question_id || 'SE-DB-001',
      question_text: s.question_text || '',
      status: r?.status || s.status || 'pending_review',
      submitted_at: s.submitted_at,
      automated_mark: automatedMark,
      total_possible_marks: totalPossible,
      percentage: r?.percentage ?? (totalPossible > 0 && automatedMark !== null ? Math.round((automatedMark / totalPossible) * 1000) / 10 : null),
      final_mark: r?.final_mark ?? null,
      lecturer_decision: r?.lecturer_decision ?? null,
      override_reason: r?.override_reason ?? null,
      reviewed_by: r?.reviewed_by || r?.lecturer_id || null,
      reviewed_at: r?.reviewed_at || null,
      finalized_at: r?.finalized_at || null,
      is_demo: s.is_demo === true || detectProvenance(s) === 'pp1_demo',
      provenance: detectProvenance(s),
    };
  });
}

/**
 * Retrieves single submission and complete evaluation details.
 */
// The detail view. The role decides how much is returned: staff get everything, a student gets their own answer and a
// redacted evaluation (no answer key, rubric or reference answer).
export async function getSubmissionDetail(submissionId, studentId, role) {
  const parsed = parseId(submissionId);
  const submission = await submissionsCol().findOne({
    $or: [{ _id: parsed }, { _id: String(submissionId) }],
  });

  if (!submission) throw httpError(404, 'Submission not found');

  if (role !== 'lecturer' && role !== 'admin' && submission.student_id !== studentId) {
    throw httpError(403, 'You can only see your own submissions');
  }

  const sId = String(submission._id);
  const result = await resultsCol().findOne({
    $or: [{ submission_id: sId }, { submission_id: parsed }],
  });

  // Normalize AI evaluation payload from either ai_evaluation or legacy ai_result
  let aiEvaluation = result?.ai_evaluation || result?.ai_result || null;
  if (aiEvaluation && !aiEvaluation.marking && aiEvaluation.ai_result) {
    aiEvaluation = aiEvaluation.ai_result;
  }

  const automatedMark =
    result?.automated_mark ??
    aiEvaluation?.total_awarded_marks ??
    aiEvaluation?.marking?.total_awarded_marks ??
    null;

  const totalPossible =
    result?.total_possible_marks ??
    aiEvaluation?.total_possible_marks ??
    aiEvaluation?.marking?.total_possible_marks ??
    null;

  const percentage =
    result?.percentage ??
    aiEvaluation?.percentage ??
    (totalPossible > 0 && automatedMark !== null
      ? Math.round((automatedMark / totalPossible) * 1000) / 10
      : null);

  // ---- role-based projection of the stored record -------------------------------------------------------------
  // Students see their own answer and results, never the authoritative configuration (reference answer, rubric,
  // expected concepts, answer key). Lecturers and admins receive everything for review.
  const isStaff = role === 'lecturer' || role === 'admin';
  return {
    submission: {
      _id: sId,
      student_id: submission.student_id,
      question_id: submission.question_id || 'SE-DB-001',
      question_text: submission.question_text || '',
      student_answer: submission.student_answer || '',
      options: submission.options || aiEvaluation?.options || null,
      selected_options: submission.selected_options || aiEvaluation?.selected_option_ids || null,
      answer_type: submission.answer_type || 'short',
      // Authoritative configuration exists in the response for staff only; for students the keys are absent.
      ...(isStaff && {
        reference_answer: submission.reference_answer || null,
        expected_concepts: submission.expected_concepts || null,
        correct_options: submission.correct_options || aiEvaluation?.correct_option_ids || null,
        rubric: submission.rubric || null,
      }),
      status: result?.status || submission.status || 'pending_review',
      submitted_at: submission.submitted_at,
      updated_at: submission.updated_at,
      is_demo: submission.is_demo === true || detectProvenance(submission) === 'pp1_demo',
      provenance: detectProvenance(submission),
    },
    result: {
      _id: result ? String(result._id) : null,
      submission_id: sId,
      automated_mark: automatedMark,
      total_possible_marks: totalPossible,
      percentage: percentage,
      ai_evaluation: isStaff ? aiEvaluation : redactEvaluationForStudent(aiEvaluation),
      lecturer_decision: result?.lecturer_decision || null,
      final_mark: result?.final_mark ?? null,
      override_reason: result?.override_reason || null,
      reviewed_by: result?.reviewed_by || result?.lecturer_id || null,
      reviewed_at: result?.reviewed_at || null,
      finalized_at: result?.finalized_at || null,
      ...(isStaff && { review_history: Array.isArray(result?.review_history) ? result.review_history : [] }),
      status: result?.status || submission.status || 'pending_review',
    },
  };
}

/**
 * Lecturer Review: Accept AI mark or Override AI mark with mandatory reason.
 * Status becomes 'reviewed'.
 */
// Review rules: accept keeps the automatic mark; override needs a number within 0..total and a written reason.
// Each review appends an entry to review_history so earlier decisions stay visible.
export async function reviewSubmission(submissionId, lecturerId, { decision, new_mark, override_reason }) {
  const parsed = parseId(submissionId);
  const submission = await submissionsCol().findOne({
    $or: [{ _id: parsed }, { _id: String(submissionId) }],
  });
  if (!submission) throw httpError(404, 'Submission not found');

  const sId = String(submission._id);
  const result = await resultsCol().findOne({
    $or: [{ submission_id: sId }, { submission_id: parsed }],
  });
  if (!result) throw httpError(404, 'Assessment result not found');

  if (result.status === 'finalized') {
    throw httpError(409, 'This assessment has already been finalized and cannot be modified');
  }

  if (decision !== 'accepted' && decision !== 'overridden') {
    throw httpError(400, "Review decision must be either 'accepted' or 'overridden'");
  }

  const automatedMark =
    result.automated_mark ??
    result.ai_evaluation?.total_awarded_marks ??
    result.ai_result?.marking?.total_awarded_marks ??
    0;

  let finalMark;
  let reason = null;

  if (decision === 'accepted') {
    finalMark = automatedMark;
  } else {
    // Overridden
    const markIsNumeric = (typeof new_mark === 'number') || (typeof new_mark === 'string' && new_mark.trim() !== '');
    const num = markIsNumeric ? Number(new_mark) : NaN;
    if (!Number.isFinite(num)) {
      throw httpError(400, 'A valid new mark is required for an override');
    }
    if (num < 0) {
      throw httpError(400, 'Mark cannot be negative');
    }
    const possible = Number(result.total_possible_marks);
    if (Number.isFinite(possible) && possible > 0 && num > possible) {
      throw httpError(400, `Mark cannot exceed the total possible marks (${possible})`);
    }
    finalMark = num;

    if (!override_reason || !String(override_reason).trim()) {
      throw httpError(400, 'An override reason is required when overriding the AI mark');
    }
    reason = String(override_reason).trim();
    if (reason.length > 2000) throw httpError(400, 'Override reason is too long (maximum 2000 characters)');
  }

  const now = new Date();
  const updateData = {
    lecturer_decision: decision,
    final_mark: finalMark,
    override_reason: reason,
    reviewed_by: lecturerId,
    reviewed_at: now,
    status: 'reviewed',
    updated_at: now,
  };

  // The filter `status != finalized` makes the update atomic: a result finalized a moment earlier cannot be changed.
  const reviewWrite = await resultsCol().updateOne(
    { _id: result._id, status: { $ne: 'finalized' } },
    {
      $set: updateData,
      // Append-only audit trail (NFR-C3-22): earlier decisions stay visible after a later change
      $push: { review_history: { action: 'reviewed', by: lecturerId, at: now, decision, automated_mark: automatedMark, final_mark: finalMark, override_reason: reason } },
    }
  );
  if (reviewWrite && reviewWrite.matchedCount === 0) {
    throw httpError(409, 'This assessment has already been finalized and cannot be modified');
  }

  await submissionsCol().updateOne(
    { _id: submission._id },
    { $set: { status: 'reviewed', updated_at: now } }
  );

  return {
    submission_id: sId,
    decision,
    automated_mark: automatedMark,
    final_mark: finalMark,
    override_reason: reason,
    reviewed_by: lecturerId,
    reviewed_at: now,
    status: 'reviewed',
  };
}

/**
 * Lecturer Finalization: Finalizes the assessment result.
 * Status becomes 'finalized'.
 */
// Finalize locks the result. Only a reviewed result can be finalized; the C1 hand-off then sends the FINAL mark.
export async function finalizeSubmission(submissionId, lecturerId) {
  const parsed = parseId(submissionId);
  const submission = await submissionsCol().findOne({
    $or: [{ _id: parsed }, { _id: String(submissionId) }],
  });
  if (!submission) throw httpError(404, 'Submission not found');

  const sId = String(submission._id);
  const result = await resultsCol().findOne({
    $or: [{ submission_id: sId }, { submission_id: parsed }],
  });
  if (!result) throw httpError(404, 'Assessment result not found');

  if (result.status === 'finalized') {
    throw httpError(409, 'This assessment has already been finalized');
  }

  if (!result.lecturer_decision && result.status !== 'reviewed') {
    throw httpError(400, 'Assessment must be reviewed (accepted or overridden) before finalization');
  }

  const now = new Date();
  // Conditional write: only one of several concurrent finalize requests can win.
  const finalizeWrite = await resultsCol().updateOne(
    { _id: result._id, status: { $ne: 'finalized' } },
    {
      $set: {
        status: 'finalized',
        finalized_at: now,
        finalized_by: lecturerId,
        updated_at: now,
      },
      $push: { review_history: { action: 'finalized', by: lecturerId, at: now, decision: result.lecturer_decision, final_mark: result.final_mark } },
    }
  );
  if (finalizeWrite && finalizeWrite.matchedCount === 0) {
    throw httpError(409, 'This assessment has already been finalized');
  }

  await submissionsCol().updateOne(
    { _id: submission._id },
    {
      $set: {
        status: 'finalized',
        updated_at: now,
      },
    }
  );

  // Synchronize finalized assessment evidence to C1 (Cognitive Digital Twin)
  const finalPercentage = result.total_possible_marks > 0
    ? Math.round((Number(result.final_mark) / Number(result.total_possible_marks)) * 1000) / 10
    : 0;

  syncC3AssessmentToC1({
    studentId: submission.student_id,
    submissionId: sId,
    questionId: submission.question_id,
    questionText: submission.question_text,
    score: result.final_mark,
    totalPossible: result.total_possible_marks,
    percentage: finalPercentage,
    conceptMatches: result.ai_evaluation?.analysis?.concept_matches || [],
    finalized: true,
    lecturerDecision: result.lecturer_decision,
    overrideReason: result.override_reason,
    reviewedBy: result.reviewed_by || lecturerId,
  }).catch(() => {});

  return {
    submission_id: sId,
    decision: result.lecturer_decision,
    automated_mark: result.automated_mark,
    final_mark: result.final_mark,
    override_reason: result.override_reason,
    reviewed_by: result.reviewed_by || lecturerId,
    finalized_at: now,
    status: 'finalized',
  };
}
