import { getDb } from '../../../config/db.js';
import { ObjectId } from 'mongodb';

function httpError(status, message) {
  return Object.assign(new Error(message), { status });
}

function submissionsCol() {
  return getDb().collection('c3_submissions');
}

function resultsCol() {
  return getDb().collection('c3_results');
}

/** Create a new submission record (before AI processing). */
export async function createSubmission({ assessmentId, studentId, studentAnswer }) {
  const doc = {
    assessment_id: String(assessmentId),
    student_id: studentId,
    student_answer: studentAnswer,
    status: 'processing',
    submitted_at: new Date(),
    updated_at: new Date(),
  };
  const r = await submissionsCol().insertOne(doc);
  return { ...doc, _id: r.insertedId };
}

/** Update submission status. */
export async function updateSubmissionStatus(submissionId, status) {
  await submissionsCol().updateOne(
    { _id: new ObjectId(submissionId) },
    { $set: { status, updated_at: new Date() } }
  );
}

/** Store the full AI result tied to a submission. */
export async function createResult({ submissionId, assessmentId, studentId, aiResult }) {
  const doc = {
    submission_id: String(submissionId),
    assessment_id: String(assessmentId),
    student_id: studentId,
    ai_result: aiResult,
    lecturer_decision: null,
    final_mark: null,
    override_reason: null,
    lecturer_id: null,
    finalized_at: null,
    status: 'awaiting_review',
    created_at: new Date(),
    updated_at: new Date(),
  };
  const r = await resultsCol().insertOne(doc);
  return { ...doc, _id: r.insertedId };
}

/** Get a submission by ID. Students can only see their own. */
export async function getSubmission(submissionId, studentId = null) {
  if (!ObjectId.isValid(submissionId)) throw httpError(404, 'Submission not found');
  const query = { _id: new ObjectId(submissionId) };
  if (studentId) query.student_id = studentId;
  const doc = await submissionsCol().findOne(query);
  if (!doc) throw httpError(404, 'Submission not found');
  return doc;
}

/** Get a result by submission ID. */
export async function getResultBySubmissionId(submissionId, studentId = null) {
  const query = { submission_id: String(submissionId) };
  if (studentId) query.student_id = studentId;
  const doc = await resultsCol().findOne(query);
  if (!doc) throw httpError(404, 'Result not found');
  return doc;
}

/** List submissions for a student. */
export async function listStudentSubmissions(studentId) {
  return submissionsCol()
    .find({ student_id: studentId })
    .sort({ submitted_at: -1 })
    .toArray();
}

/** List all submissions for lecturer review (can filter by status). */
export async function listLecturerSubmissions(filters = {}) {
  const query = {};
  if (filters.status) query.status = filters.status;
  if (filters.assessment_id) query.assessment_id = filters.assessment_id;
  return submissionsCol()
    .find(query)
    .sort({ submitted_at: -1 })
    .limit(100)
    .toArray();
}

/** Count submissions by status for summary. */
export async function countSubmissionsByStatus() {
  const agg = await submissionsCol()
    .aggregate([{ $group: { _id: '$status', count: { $sum: 1 } } }])
    .toArray();
  const counts = {};
  for (const { _id, count } of agg) counts[_id] = count;
  return {
    processing: counts.processing || 0,
    ai_assessed: counts.ai_assessed || 0,
    awaiting_review: counts.awaiting_review || 0,
    finalized: counts.finalized || 0,
  };
}

/** Accept the AI mark — lecturer approves without override. */
export async function acceptAiMark(submissionId, lecturerId) {
  if (!ObjectId.isValid(submissionId)) throw httpError(404, 'Submission not found');
  const result = await resultsCol().findOne({ submission_id: String(submissionId) });
  if (!result) throw httpError(404, 'Result not found');
  if (result.status === 'finalized') throw httpError(409, 'Already finalized');

  const finalMark = result.ai_result?.marking?.total_awarded_marks ?? 0;
  const now = new Date();

  await resultsCol().updateOne(
    { submission_id: String(submissionId) },
    {
      $set: {
        lecturer_decision: 'accepted',
        final_mark: finalMark,
        override_reason: null,
        lecturer_id: lecturerId,
        finalized_at: now,
        status: 'finalized',
        updated_at: now,
      },
    }
  );
  await submissionsCol().updateOne(
    { _id: new ObjectId(submissionId) },
    { $set: { status: 'finalized', updated_at: now } }
  );
  return { submissionId, lecturerId, decision: 'accepted', final_mark: finalMark, finalized_at: now };
}

/** Override the AI mark with a lecturer-specified mark. */
export async function overrideAiMark(submissionId, lecturerId, revisedMark, reason) {
  if (!ObjectId.isValid(submissionId)) throw httpError(404, 'Submission not found');
  if (revisedMark === undefined || revisedMark === null || isNaN(Number(revisedMark))) {
    throw httpError(400, 'A valid revised mark is required');
  }
  if (!reason || !String(reason).trim()) {
    throw httpError(400, 'An override reason is required');
  }
  const result = await resultsCol().findOne({ submission_id: String(submissionId) });
  if (!result) throw httpError(404, 'Result not found');
  if (result.status === 'finalized') throw httpError(409, 'Already finalized');

  const now = new Date();
  const finalMark = Number(revisedMark);

  await resultsCol().updateOne(
    { submission_id: String(submissionId) },
    {
      $set: {
        lecturer_decision: 'overridden',
        final_mark: finalMark,
        override_reason: String(reason).trim(),
        lecturer_id: lecturerId,
        finalized_at: now,
        status: 'finalized',
        updated_at: now,
      },
    }
  );
  await submissionsCol().updateOne(
    { _id: new ObjectId(submissionId) },
    { $set: { status: 'finalized', updated_at: now } }
  );
  return { submissionId, lecturerId, decision: 'overridden', final_mark: finalMark, override_reason: reason, finalized_at: now };
}

/** Get lecturer submission detail (submission + result joined). */
export async function getLecturerSubmissionDetail(submissionId) {
  if (!ObjectId.isValid(submissionId)) throw httpError(404, 'Submission not found');
  const submission = await submissionsCol().findOne({ _id: new ObjectId(submissionId) });
  if (!submission) throw httpError(404, 'Submission not found');
  const result = await resultsCol().findOne({ submission_id: String(submissionId) });
  return { submission, result: result || null };
}
