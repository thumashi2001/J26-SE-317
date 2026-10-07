import { resolveStudentId } from '../../../middleware/auth.js';
import * as aiClient from '../services/aiClient.js';

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
