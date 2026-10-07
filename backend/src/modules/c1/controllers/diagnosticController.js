import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/diagnosticService.js';

const AI_URL = () => process.env.C1_AI_URL || 'http://127.0.0.1:8001';

function handle(fn) {
  return async (req, res) => {
    try {
      res.json(await fn(req));
    } catch (err) {
      res.status(err.status || 500).json({ error: err.message });
    }
  };
}

function badRequest(message) {
  const e = new Error(message);
  e.status = 400;
  return e;
}

// The student ID comes from the login token, so nobody can read another student's data.
export const getDiagnostic = handle(async (req) => {
  const studentId = resolveStudentId(req, req.query.studentId);
  return service.getOrCreateAssignment(getDb(), studentId);
});

export const submitDiagnostic = handle(async (req) => {
  const { studentId: supplied, answers } = req.body || {};
  if (!Array.isArray(answers)) throw badRequest('answers[] is required');
  const studentId = resolveStudentId(req, supplied);
  return service.submitDiagnostic(getDb(), studentId, answers, AI_URL());
});

export const getTwin = handle(async (req) => {
  const studentId = resolveStudentId(req, req.params.studentId);
  return service.getTwin(getDb(), studentId);
});
