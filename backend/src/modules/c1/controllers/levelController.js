import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/levelService.js';

// GET /level/:studentId  -> 5 star knowledge level that follows the twin
export async function getLevel(req, res) {
  try {
    const studentId = resolveStudentId(req, req.params.studentId);
    res.json(await service.getLevel(getDb(), studentId));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
