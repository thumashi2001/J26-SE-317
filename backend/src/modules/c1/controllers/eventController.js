import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/eventService.js';

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

// The student ID comes from the login token, so nobody can write to another student's twin.
export const recordEvent = handle(async (req) => {
  const b = req.body || {};
  if (!b.topic || typeof b.correct !== 'boolean') {
    throw badRequest('topic and correct (true/false) are required');
  }
  const studentId = resolveStudentId(req, b.studentId);
  return service.recordEvent(getDb(), { ...b, studentId }, AI_URL());
});

export const getAlerts = handle(async (req) => {
  const studentId = resolveStudentId(req, req.params.studentId);
  return service.getAlerts(getDb(), studentId);
});
