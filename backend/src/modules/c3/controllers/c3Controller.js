// C3 CONTROLLER: the thin layer between HTTP and the services. Each exported function handles one route
// (see routes/index.js). Controllers read the request, call a service, and return JSON; the real work lives in
// services/*.
//
// THE LIVE FLOW FOR A STUDENT ANSWER IS `assessAnswer` BELOW:
//   1 check who is calling and reject scanned files / oversize text
//   2 STUDENT: look up the question + rubric + answer key from the server's built-in demo bank (never from the browser)
//   3 MCQ  -> mark inside Node (deterministic key comparison)      WRITTEN -> ask the Python service (POST /c3/assess)
//   4 save the full result in MongoDB (pending lecturer review)
//   5 STUDENT: hide any MCQ answer key from the response copy; return it
import { resolveStudentId } from '../../../middleware/auth.js';
import * as aiClient from '../services/aiClient.js';
import * as submissionSvc from '../services/submissionService.js';
import * as mcqSvc from '../services/mcqMarkingService.js';
import * as batchSvc from '../services/batchMarkingService.js';
import { resolveStudentAssessment, listPublicAssessments, listExampleSetups, C2_INTEGRATION } from '../services/assessmentConfig.js';
import { redactEvaluationForStudent } from '../services/redaction.js';
import { LIMITS, assertMaxChars, assertMaxItems } from '../services/limits.js';

// Address of the Python AI service (default port 8003); override with the C3_AI_URL environment variable.
const AI_URL = () => process.env.C3_AI_URL || 'http://127.0.0.1:8003';

// Decide whether a payload is a multiple-choice question (these never go to Python).
function isMcqPayload(payload) {
  const type = String(payload?.answer_type || '').toLowerCase();
  return type === 'mcq' || type === 'multiple-choice' || (Boolean(payload?.options) && !payload?.rubric?.criteria?.[0]?.scoring_levels?.some(l => l.required_concepts?.length > 1));
}

// Never expose internal addresses; unexpected (status-less) failures get a generic message.
function publicMessage(err) {
  if (!err.status) {
    console.error('[c3] unexpected error:', err.message);
    return 'The request could not be completed';
  }
  return String(err.message).replace(/https?:\/\/[^\s)]+/g, '[internal service]');
}

// Wrap a handler so thrown errors become a clean JSON error (status from err.status, default 500).
function handle(fn) {
  return async (req, res) => {
    try {
      res.json(await fn(req));
    } catch (err) {
      res.status(err.status || 500).json({ error: publicMessage(err) });
    }
  };
}

// ---- Lecturer-only raw endpoints: forward to the matching Python endpoint (not used by the student page) ----------
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

// Scanned images / OCR are not supported: always a 400 with an explanation.
export const unsupportedOcrHandler = handle(async () => {
  const err = new Error(
    'Scanned answer OCR processing is currently unsupported. C3 evaluates natural-language text responses directly. Please provide a typed answer.'
  );
  err.status = 400;
  throw err;
});

// ---- THE STUDENT SUBMISSION: POST /api/v1/c3/assess ---------------------------------------------------------------
export const assessAnswer = handle(async (req) => {
  // A student may only submit for themselves; a lecturer must name the student (resolveStudentId enforces this).
  const { student_id, ...rawPayload } = req.body || {};
  const effectiveStudentId = resolveStudentId(req, student_id);

  if (rawPayload.image || rawPayload.file || rawPayload.scanned_document) {
    const err = new Error(
      'Scanned answer OCR processing is currently unsupported. C3 evaluates natural-language text responses directly. Please provide a typed answer.'
    );
    err.status = 400;
    throw err;
  }

  // Input limits (413 when exceeded) protect the marking service from huge payloads.
  assertMaxChars(rawPayload.student_answer, LIMITS.ANSWER_CHARS, 'Answer');
  assertMaxItems(rawPayload.selected_options, LIMITS.OPTIONS, 'Selected options');

  // Students never choose the question, answer key or rubric: those come from the server.
  // (resolveStudentAssessment returns the demo's question, rubric and key plus ONLY the student's own answer fields)
  const payload = req.user.role === 'student'
    ? await resolveStudentAssessment(rawPayload)
    : { ...rawPayload, config_source: 'lecturer_supplied' };

  const startedAt = Date.now();
  let aiResult;
  if (isMcqPayload(payload)) {
    // MCQ: deterministic answer-key comparison done here in Node. Python is NOT called.
    payload.answer_type = 'mcq';
    aiResult = mcqSvc.evaluateMcqAnswer(payload);
  } else {
    // Written answer: ONE HTTP call to the Python service (POST {C3_AI_URL}/c3/assess). It returns marks, evidence,
    // feedback and the mind map computed by the rubric engine.
    payload.answer_type = payload.answer_type || 'short';
    aiResult = await aiClient.assessAnswer(AI_URL(), payload);
  }

  // NFR-C3-08: record how long the response took to evaluate
  if (aiResult && typeof aiResult === 'object') aiResult.processing_time_ms = Date.now() - startedAt;

  // Persistence must succeed: never report an unsaved result as saved.
  try {
    // Saves one document in c3_submissions and one in c3_results (the whole aiResult is kept as ai_evaluation).
    const { submissionId, resultId } = await submissionSvc.createSubmissionWithResult({
      studentId: effectiveStudentId,
      payload,
      aiResult,
    });
    // The stored evaluation is complete; students receive a copy without any multiple-choice answer key.
    const visible = req.user.role === 'student' ? redactEvaluationForStudent(aiResult) : aiResult;
    return {
      ...visible,
      submission_id: submissionId,
      result_id: resultId,
      persisted: true,
      status: 'pending_review',   // always: a lecturer reviews before anything is final
    };
  } catch (err) {
    if (err.status && err.status < 500) throw err;
    console.error('[c3] could not save assessment:', err.message);
    const failure = new Error('The assessment was marked but could not be saved. Please try again');
    failure.status = 503;
    throw failure;
  }
});

// ---- Assessment lists ---------------------------------------------------------------------------------------------
// Students: the built-in demo assessments only (no keys), plus the honest "C2 not available" status.
export const listAssessments = handle(async () => ({ assessments: await listPublicAssessments(), integrations: { c2: C2_INTEGRATION } }));

// Staff only: demo setups WITH rubrics and keys, used to start a lecturer batch from an example.
export const listExamples = handle(async () => ({ examples: listExampleSetups() }));

// ---- Submission history and lecturer review ------------------------------------------------------------------------
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

// Lecturer accepts the automatic mark or overrides it (an override needs a reason; the automatic mark is kept).
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

// Lecturer makes a reviewed result final (only a reviewed result can be finalized).
export const finalizeSubmission = handle(async (req) => {
  const { id } = req.params;
  const result = await submissionSvc.finalizeSubmission(id, req.user.sub);
  return { result };
});

// ---- Lecturer batch marking (a lecturer marks many students' answers against one setup) ---------------------------
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
  return batchSvc.getBatchSetup(id, req.user.role, req.user.sub);
});

export const validateBatchAnswers = handle(async (req) => {
  const { setup_id, items } = req.body || {};
  return batchSvc.validateBatchAnswers({
    setupId: setup_id,
    items,
    lecturerId: req.user.sub,
    role: req.user.role,
  });
});

export const processBatchMarking = handle(async (req) => {
  const { setup_id, items } = req.body || {};
  return batchSvc.processBatchMarking({
    lecturerId: req.user.sub,
    role: req.user.role,
    setupId: setup_id,
    items,
    aiUrl: AI_URL(),
  });
});

// Finalizes only the results the lecturer has already reviewed; unreviewed ones stay pending.
export const finalizeBatchSubmissions = handle(async (req) => {
  const { batchId } = req.params;
  return batchSvc.finalizeBatchSubmissions({
    lecturerId: req.user.sub,
    role: req.user.role,
    batchId,
  });
});
