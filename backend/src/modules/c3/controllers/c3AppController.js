/**
 * C3 Application Controller
 *
 * Handles application-level C3 routes:
 *  - Assessment listing and retrieval
 *  - Student submission (orchestrates AI pipeline, stores result)
 *  - Student result retrieval
 *  - Lecturer submission queue + detail
 *  - Lecturer finalization (accept / override)
 *
 * The existing raw AI proxy routes (/c3/analysis, /c3/marking, /c3/feedback, /c3/mindmap)
 * remain untouched in c3Controller.js for direct test usage.
 */

import { getDb } from '../../../config/db.js';
import * as aiClient from '../services/aiClient.js';
import * as assessmentSvc from '../services/assessmentService.js';
import * as submissionSvc from '../services/submissionService.js';

const AI_URL = () => process.env.C3_AI_URL || 'http://127.0.0.1:8003';

function handle(fn) {
  return async (req, res) => {
    try {
      res.json(await fn(req));
    } catch (err) {
      res.status(err.status || 500).json({ error: err.message });
    }
  };
}

// ─── STUDENT: Assessment List ────────────────────────────────────────────────

export const listAssessments = handle(async () => {
  const assessments = await assessmentSvc.listAssessments();
  return { assessments };
});

// ─── STUDENT: Get single assessment (student-visible fields only) ─────────────

export const getAssessment = handle(async (req) => {
  const doc = await assessmentSvc.getAssessment(req.params.id);
  // Strip private fields
  const { reference_answer, rubric, expected_concepts, ...publicDoc } = doc;
  return { assessment: publicDoc };
});

// ─── STUDENT: Submit answer → run AI pipeline → store result ─────────────────

export const submitAnswer = handle(async (req) => {
  const { assessment_id, student_answer } = req.body || {};
  const studentId = req.user.sub;

  if (!assessment_id) throw Object.assign(new Error('assessment_id is required'), { status: 400 });
  if (!student_answer || !String(student_answer).trim()) {
    throw Object.assign(new Error('student_answer cannot be empty'), { status: 400 });
  }

  // Retrieve full assessment (including rubric, concepts, reference answer)
  const assessment = await assessmentSvc.getAssessmentFull(assessment_id);

  // Create submission record
  const submission = await submissionSvc.createSubmission({
    assessmentId: String(assessment._id),
    studentId,
    studentAnswer: String(student_answer).trim(),
  });
  const submissionId = String(submission._id);

  // Build AI payloads
  const analysisPayload = {
    question_id: assessment.question_id,
    question_text: assessment.question_text,
    student_answer: String(student_answer).trim(),
    reference_answer: assessment.reference_answer || null,
    expected_concepts: assessment.expected_concepts || null,
    answer_type: assessment.answer_type || 'essay',
  };

  const markingPayload = {
    ...analysisPayload,
    rubric: assessment.rubric,
  };

  const feedbackPayload = { marking_request: markingPayload };
  const mindmapPayload = { analysis_request: analysisPayload };

  // Call AI pipeline
  let analysis, marking, feedback, mindmap;
  try {
    analysis = await aiClient.analyzeAnswer(AI_URL(), analysisPayload);
    marking = await aiClient.markAnswer(AI_URL(), markingPayload);
    feedback = await aiClient.generateFeedback(AI_URL(), feedbackPayload);
    mindmap = await aiClient.generateMindmap(AI_URL(), mindmapPayload);
  } catch (err) {
    // Mark submission as failed but still respond with error
    await submissionSvc.updateSubmissionStatus(submissionId, 'failed');
    throw Object.assign(new Error(`AI processing failed: ${err.message}`), { status: 502 });
  }

  // Store full AI result
  const result = await submissionSvc.createResult({
    submissionId,
    assessmentId: String(assessment._id),
    studentId,
    aiResult: { analysis, marking, feedback, mindmap },
  });

  // Update submission status
  await submissionSvc.updateSubmissionStatus(submissionId, 'awaiting_review');

  return {
    submission_id: submissionId,
    result_id: String(result._id),
    status: 'awaiting_review',
  };
});

// ─── STUDENT: Get own submission ──────────────────────────────────────────────

export const getMySubmission = handle(async (req) => {
  const submission = await submissionSvc.getSubmission(req.params.id, req.user.sub);
  return { submission };
});

// ─── STUDENT: Get own result ──────────────────────────────────────────────────

export const getMyResult = handle(async (req) => {
  const { submissionId } = req.params;
  // Verify the submission belongs to this student
  const submission = await submissionSvc.getSubmission(submissionId, req.user.sub);
  let result = null;
  try {
    result = await submissionSvc.getResultBySubmissionId(submissionId, req.user.sub);
  } catch (e) {}
  return { submission, result };
});

// ─── STUDENT: List own submissions ────────────────────────────────────────────

export const listMySubmissions = handle(async (req) => {
  const submissions = await submissionSvc.listStudentSubmissions(req.user.sub);
  return { submissions };
});

// ─── LECTURER: List all submissions for review ────────────────────────────────

export const lecturerListSubmissions = handle(async (req) => {
  const filters = {};
  if (req.query.status) filters.status = req.query.status;
  if (req.query.assessment_id) filters.assessment_id = req.query.assessment_id;
  const [submissionsRaw, counts] = await Promise.all([
    submissionSvc.listLecturerSubmissions(filters),
    submissionSvc.countSubmissionsByStatus(),
  ]);

  // Map assessment titles and ai_marks
  const submissions = await Promise.all(submissionsRaw.map(async (sub) => {
    let title = sub.assessment_id;
    try {
      const a = await assessmentSvc.getAssessment(sub.assessment_id);
      if (a) title = a.title;
    } catch (e) {}

    let aiMark = null;
    if (sub.status === 'awaiting_review' || sub.status === 'finalized') {
      try {
        const r = await submissionSvc.getResultBySubmissionId(sub._id);
        if (r && r.ai_result?.marking?.total_awarded_marks !== undefined) {
          aiMark = r.ai_result.marking.total_awarded_marks;
        }
      } catch (e) {}
    }
    return { ...sub, assessment_title: title, ai_mark: aiMark };
  }));

  return { submissions, counts };
});

// ─── LECTURER: Get single submission + result detail ─────────────────────────

export const lecturerGetSubmission = handle(async (req) => {
  const { submissionId } = req.params;
  const { submission, result } = await submissionSvc.getLecturerSubmissionDetail(submissionId);
  // Get assessment info (no private fields needed here for display)
  let assessment = null;
  try {
    assessment = await assessmentSvc.getAssessment(submission.assessment_id);
  } catch (_) {}
  return { submission, result, assessment };
});

// ─── LECTURER: Accept AI mark ────────────────────────────────────────────────

export const lecturerAccept = handle(async (req) => {
  const { submissionId } = req.params;
  const decision = await submissionSvc.acceptAiMark(submissionId, req.user.sub);
  return { decision };
});

// ─── LECTURER: Override AI mark ───────────────────────────────────────────────

export const lecturerOverride = handle(async (req) => {
  const { submissionId } = req.params;
  const { revised_mark, reason } = req.body || {};
  const decision = await submissionSvc.overrideAiMark(submissionId, req.user.sub, revised_mark, reason);
  return { decision };
});

// ─── ADMIN: Submission statistics ────────────────────────────────────────────

export const adminStats = handle(async () => {
  const counts = await submissionSvc.countSubmissionsByStatus();
  return { counts };
});
