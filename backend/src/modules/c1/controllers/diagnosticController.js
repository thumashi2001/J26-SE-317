import { getDb } from '../../../config/db.js';
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

// TODO: when shared login exists, take the student ID from the login token instead of the request.
export const getDiagnostic = handle(async (req) => {
  const studentId = req.query.studentId;
  if (!studentId) throw badRequest('studentId is required');
  return service.getOrCreateAssignment(getDb(), studentId);
});

export const submitDiagnostic = handle(async (req) => {
  const { studentId, answers } = req.body || {};
  if (!studentId || !Array.isArray(answers)) throw badRequest('studentId and answers[] are required');
  return service.submitDiagnostic(getDb(), studentId, answers, AI_URL());
});

export const getTwin = handle(async (req) => {
  return service.getTwin(getDb(), req.params.studentId);
});