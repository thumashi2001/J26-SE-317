import { getDb } from '../../../config/db.js';
import { resolveC4StudentId } from '../services/c4StudentAccess.js';
import * as exam from '../services/examService.js';

const C1_AI_URL = () => process.env.C1_AI_URL || 'http://127.0.0.1:8001';

function handle(fn) {
  return async (req, res) => {
    try {
      const data = await fn(req);
      res.json(data);
    } catch (err) {
      const body = { error: err.message };
      if (err.code) body.code = err.code;
      res.status(err.status || 500).json(body);
    }
  };
}

function studentFrom(req, supplied) {
  return resolveC4StudentId(req, supplied);
}

export const sources = handle(async () => exam.getExamSources());

export const create = handle(async (req) => {
  const body = req.body || {};
  const studentId = studentFrom(req, body.studentId);
  return exam.createExamAttempt(getDb(), studentId, body, C1_AI_URL());
});

export const list = handle(async (req) => {
  const studentId = studentFrom(req, req.query.studentId);
  return exam.listAttempts(getDb(), studentId);
});

export const evaluation = handle(async (req) => {
  const studentId = studentFrom(req, req.query.studentId);
  return exam.evaluateStoredPredictions(getDb(), studentId);
});

export const detail = handle(async (req) => {
  const studentId = studentFrom(req, req.query.studentId);
  return exam.getAttempt(getDb(), studentId, req.params.attemptId);
});

export const saveAnswers = handle(async (req) => {
  const body = req.body || {};
  const studentId = studentFrom(req, body.studentId);
  return exam.saveAnswers(getDb(), studentId, req.params.attemptId, body);
});

export const submit = handle(async (req) => {
  const body = req.body || {};
  const studentId = studentFrom(req, body.studentId);
  return exam.submitAttempt(getDb(), studentId, req.params.attemptId, body);
});
