import { getDb } from '../../../config/db.js';
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

// TODO: when shared login exists, take the student ID from the login token instead of the request.
export const recordEvent = handle(async (req) => {
  const b = req.body || {};
  if (!b.studentId || !b.topic || typeof b.correct !== 'boolean') {
    throw badRequest('studentId, topic and correct (true/false) are required');
  }
  return service.recordEvent(getDb(), b, AI_URL());
});

export const getAlerts = handle(async (req) => {
  return service.getAlerts(getDb(), req.params.studentId);
});