import { getDb } from '../../../config/db.js';
import { resolveC4StudentId } from '../services/c4StudentAccess.js';
import * as feedback from '../services/feedbackService.js';

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

export const create = handle(async (req) => {
  const body = req.body || {};
  const studentId = resolveC4StudentId(req, body.studentId);
  return feedback.submitFeedback(getDb(), studentId, body);
});

export const list = handle(async (req) => {
  const studentId = resolveC4StudentId(req, req.query.studentId);
  return feedback.listFeedback(getDb(), studentId);
});
