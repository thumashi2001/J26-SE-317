import { resolveStudentId } from '../../../middleware/auth.js';
import * as aiClient from '../services/aiClient.js';
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

export const analyzeAnswer = handle(async (req) => {
  const { student_id, ...payload } = req.body || {};
  resolveStudentId(req, student_id);
  return aiClient.analyzeAnswer(AI_URL(), payload);
});

export const markAnswer = handle(async (req) => {
  const { student_id, ...payload } = req.body || {};
  resolveStudentId(req, student_id);
  return aiClient.markAnswer(AI_URL(), payload);
});

export const generateFeedback = handle(async (req) => {
  const { student_id, ...payload } = req.body || {};
  resolveStudentId(req, student_id);
  return aiClient.generateFeedback(AI_URL(), payload);
});

export const generateMindmap = handle(async (req) => {
  const { student_id, ...payload } = req.body || {};
  resolveStudentId(req, student_id);
  return aiClient.generateMindmap(AI_URL(), payload);
});

export const assessAnswer = handle(async (req) => {
  const { student_id, ...payload } = req.body || {};
  const effectiveStudentId = resolveStudentId(req, student_id);
  const aiResult = await aiClient.assessAnswer(AI_URL(), payload);

  // If DB persistence is available, store submission and result
  try {
    const { submissionId, resultId } = await submissionSvc.createSubmissionWithResult({
      studentId: effectiveStudentId,
      payload,
      aiResult,
    });
    return {
      ...aiResult,
      submission_id: submissionId,
      result_id: resultId,
      status: 'pending_review',
    };
  } catch (err) {
    // If DB is not connected or in standalone test environment without DB, still return AI result
    return {
      ...aiResult,
      status: 'pending_review',
    };
  }
});

export const listSubmissions = handle(async (req) => {
  const { status } = req.query || {};
  const submissions = await submissionSvc.listSubmissions({
    studentId: req.user.sub,
    role: req.user.role,
    status,
  });
  return { submissions };
});

export const getSubmission = handle(async (req) => {
  const { id } = req.params;
  return submissionSvc.getSubmissionDetail(id, req.user.sub, req.user.role);
});

export const reviewSubmission = handle(async (req) => {
  const { id } = req.params;
  const { decision, new_mark, override_reason } = req.body || {};
  const result = await submissionSvc.reviewSubmission(id, req.user.sub, {
    decision,
    new_mark,
    override_reason,
  });
  return { result };
});

export const finalizeSubmission = handle(async (req) => {
  const { id } = req.params;
  const result = await submissionSvc.finalizeSubmission(id, req.user.sub);
  return { result };
});
