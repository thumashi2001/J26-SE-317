import { resolveStudentId } from '../../../middleware/auth.js';
import * as aiClient from '../services/aiClient.js';
import * as submissionSvc from '../services/submissionService.js';
import * as mcqSvc from '../services/mcqMarkingService.js';
import * as batchSvc from '../services/batchMarkingService.js';

const AI_URL = () => process.env.C3_AI_URL || 'http://127.0.0.1:8003';

function isMcqPayload(payload) {
  const type = String(payload?.answer_type || '').toLowerCase();
  return type === 'mcq' || type === 'multiple-choice' || (Boolean(payload?.options) && !payload?.rubric?.criteria?.[0]?.scoring_levels?.some(l => l.required_concepts?.length > 1));
}

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
  if (isMcqPayload(payload)) {
    return mcqSvc.evaluateMcqAnswer(payload);
  }
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

export const unsupportedOcrHandler = handle(async () => {
  const err = new Error(
    'Scanned answer OCR processing is currently unsupported. C3 evaluates natural-language text responses directly. Please provide a typed answer.'
  );
  err.status = 400;
  throw err;
});

export const assessAnswer = handle(async (req) => {
  const { student_id, ...payload } = req.body || {};
  const effectiveStudentId = resolveStudentId(req, student_id);

  if (payload.image || payload.file || payload.scanned_document) {
    const err = new Error(
      'Scanned answer OCR processing is currently unsupported. C3 evaluates natural-language text responses directly. Please provide a typed answer.'
    );
    err.status = 400;
    throw err;
  }

  let aiResult;
  if (isMcqPayload(payload)) {
    payload.answer_type = 'mcq';
    aiResult = mcqSvc.evaluateMcqAnswer(payload);
  } else {
    payload.answer_type = payload.answer_type || 'short';
    aiResult = await aiClient.assessAnswer(AI_URL(), payload);
  }

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

export const createBatchSetup = handle(async (req) => {
  return batchSvc.createBatchSetup({
    lecturerId: req.user.sub,
    setupData: req.body,
  });
});

export const listBatchSetups = handle(async (req) => {
  const setups = await batchSvc.listBatchSetups({
    lecturerId: req.user.sub,
    role: req.user.role,
  });
  return { setups };
});

export const getBatchSetup = handle(async (req) => {
  const { id } = req.params;
  return batchSvc.getBatchSetup(id, req.user.role);
});

export const validateBatchAnswers = handle(async (req) => {
  const { setup_id, items } = req.body || {};
  return batchSvc.validateBatchAnswers({
    setupId: setup_id,
    items,
  });
});

export const processBatchMarking = handle(async (req) => {
  const { setup_id, items } = req.body || {};
  return batchSvc.processBatchMarking({
    lecturerId: req.user.sub,
    setupId: setup_id,
    items,
    aiUrl: AI_URL(),
  });
});

export const finalizeBatchSubmissions = handle(async (req) => {
  const { batchId } = req.params;
  return batchSvc.finalizeBatchSubmissions({
    lecturerId: req.user.sub,
    batchId,
  });
});

