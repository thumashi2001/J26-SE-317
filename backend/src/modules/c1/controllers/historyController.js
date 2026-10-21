import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/historyService.js';

export async function getHistory(req, res) {
  try {
    const studentId = resolveStudentId(req, req.params.studentId);
    res.json(await service.getHistory(getDb(), studentId, req.params.topic));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
