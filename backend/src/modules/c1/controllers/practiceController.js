import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/practiceService.js';

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

// The student comes from the login token, so nobody can practise as someone else.
export const start = handle(async (req) => {
  const b = req.body || {};
  if (!b.topic || typeof b.topic !== 'string') throw badRequest('topic is required');
  const studentId = resolveStudentId(req, b.studentId);
  return service.startSession(getDb(), studentId, b.topic);
});

export const answer = handle(async (req) => {
  const b = req.body || {};
  if (!b.sessionId || !b.questionId) throw badRequest('sessionId and questionId are required');
  const studentId = resolveStudentId(req, b.studentId);
  return service.answerQuestion(getDb(), studentId, b, AI_URL());
});

// Which topics can be practised, so the screens only offer a Practise button where it works.
export const topics = handle(async () => ({ topics: service.practiceTopics() }));
