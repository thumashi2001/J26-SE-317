import { getDb } from '../../../config/db.js';
import { ObjectId } from 'mongodb';
import { syncC3AssessmentToC1 } from '../../../integration/c3-c1/index.js';

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

function parseId(id) {
  if (!id) return null;
  if (ObjectId.isValid(id) && typeof id === 'string' && id.length === 24) {
    return new ObjectId(id);
  }
  return id;
}

function submissionsCol() {
  return getDb().collection('c3_submissions');
}

function resultsCol() {
  return getDb().collection('c3_results');
}

/**
 * Creates a submission record and associated AI result record.
 * Status starts as 'pending_review' (AI Proposed) — human-in-the-loop requirement.
 */
export async function createSubmissionWithResult({ studentId, payload, aiResult }) {
  const now = new Date();
  const subDoc = {
    student_id: studentId,
    question_id: payload.question_id,
    question_text: payload.question_text,
    student_answer: payload.student_answer,
    reference_answer: payload.reference_answer || null,
    expected_concepts: payload.expected_concepts || null,
    answer_type: payload.answer_type || 'short',
    rubric: payload.rubric || null,
    status: 'pending_review',
    submitted_at: now,
    updated_at: now,
  };

  const subRes = await submissionsCol().insertOne(subDoc);
  const submissionId = String(subRes.insertedId);

  const automatedMark = aiResult?.total_awarded_marks ?? aiResult?.marking?.total_awarded_marks ?? 0;
  const totalPossible = aiResult?.total_possible_marks ?? aiResult?.marking?.total_possible_marks ?? 0;
  const percentage = aiResult?.percentage ?? (totalPossible > 0 ? Math.round((automatedMark / totalPossible) * 1000) / 10 : 0);

  const resDoc = {
    submission_id: submissionId,
    student_id: studentId,
    question_id: payload.question_id,
    question_text: payload.question_text,
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
    resultId: String(resResult.insertedId),
  };
}

/**
 * Lists submissions.
 * Students only see their own submissions; lecturers see all submissions.
 */
export async function listSubmissions({ studentId, role, status }) {
  const query = {};
  if (role !== 'lecturer' && role !== 'admin') {
    query.student_id = studentId;
  }
  if (status) {
    query.status = status;
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
    };
  });
}

/**
 * Retrieves single submission and complete evaluation details.
 */
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

  return {
    submission: {
      _id: sId,
      student_id: submission.student_id,
      question_id: submission.question_id || 'SE-DB-001',
      question_text: submission.question_text || '',
      student_answer: submission.student_answer || '',
      reference_answer: submission.reference_answer || null,
      expected_concepts: submission.expected_concepts || null,
      answer_type: submission.answer_type || 'short',
      rubric: submission.rubric || null,
      status: result?.status || submission.status || 'pending_review',
      submitted_at: submission.submitted_at,
      updated_at: submission.updated_at,
    },
    result: {
      _id: result ? String(result._id) : null,
      submission_id: sId,
      automated_mark: automatedMark,
      total_possible_marks: totalPossible,
      percentage: percentage,
      ai_evaluation: aiEvaluation,
      lecturer_decision: result?.lecturer_decision || null,
      final_mark: result?.final_mark ?? null,
      override_reason: result?.override_reason || null,
      reviewed_by: result?.reviewed_by || result?.lecturer_id || null,
      reviewed_at: result?.reviewed_at || null,
      finalized_at: result?.finalized_at || null,
      status: result?.status || submission.status || 'pending_review',
    },
  };
}

/**
 * Lecturer Review: Accept AI mark or Override AI mark with mandatory reason.
 * Status becomes 'reviewed'.
 */
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
    if (new_mark === undefined || new_mark === null || isNaN(Number(new_mark))) {
      throw httpError(400, 'A valid new mark is required for an override');
    }
    const num = Number(new_mark);
    if (num < 0) {
      throw httpError(400, 'Mark cannot be negative');
    }
    finalMark = num;

    if (!override_reason || !String(override_reason).trim()) {
      throw httpError(400, 'An override reason is required when overriding the AI mark');
    }
    reason = String(override_reason).trim();
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

  await resultsCol().updateOne(
    { _id: result._id },
    { $set: updateData }
  );

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
  await resultsCol().updateOne(
    { _id: result._id },
    {
      $set: {
        status: 'finalized',
        finalized_at: now,
        updated_at: now,
      },
    }
  );

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
