import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/forecastService.js';

const AI_URL = () => process.env.C1_AI_URL || 'http://127.0.0.1:8001';

function whole(value, fallback, min, max, name) {
  if (value === undefined) return fallback;
  const n = Number(value);
  if (!Number.isInteger(n) || n < min || n > max) {
    const e = new Error(`${name} must be a whole number from ${min} to ${max}`);
    e.status = 400;
    throw e;
  }
  return n;
}

// GET /forecast/:studentId/:topic?days=21&perWeek=3
export async function getForecast(req, res) {
  try {
    const studentId = resolveStudentId(req, req.params.studentId);
    const days = whole(req.query.days, 21, 1, 120, 'days');
    const perWeek = whole(req.query.perWeek, 3, 0, 14, 'perWeek');
    res.json(await service.getForecast(getDb(), studentId, req.params.topic, { days, perWeek }, AI_URL()));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
