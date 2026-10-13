import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/predictionService.js';

const AI_URL = () => process.env.C1_AI_URL || 'http://127.0.0.1:8001';

// GET /predict/:studentId  -> chance of a correct answer on each practised topic (trained model)
export async function getPredictions(req, res) {
  try {
    const studentId = resolveStudentId(req, req.params.studentId);
    res.json(await service.getPredictions(getDb(), studentId, AI_URL()));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
