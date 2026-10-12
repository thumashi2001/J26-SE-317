import { getDb } from '../../../config/db.js';
import { resolveStudentId } from '../../../middleware/auth.js';
import * as service from '../services/planService.js';

// GET /plan/:studentId  -> today's tasks, calendar and predicted exam score
export async function getPlan(req, res) {
  try {
    const studentId = resolveStudentId(req, req.params.studentId);
    res.json(await service.getPlan(getDb(), studentId));
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}

// PUT /exam-date  { studentId, examDate: "2026-11-20" | null }
export async function setExamDate(req, res) {
  try {
    const studentId = resolveStudentId(req, req.body && req.body.studentId);
    const saved = await service.setExamDate(getDb(), studentId, req.body ? req.body.examDate : null);
    res.json({ studentId, examDate: saved });
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
