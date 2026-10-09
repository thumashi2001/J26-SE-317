import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/insightsService.js';

const AI_URL = () => process.env.C1_AI_URL || 'http://127.0.0.1:8001';

// GET /insights/:studentId  -> engagement index, topic confidence, estimated score now
export async function getInsights(req, res) {
  try {
    const studentId = resolveStudentId(req, req.params.studentId);
    res.json(await service.getInsights(getDb(), studentId, AI_URL()));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
