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

// PUT /exam-date  { studentId, module: "SE3020", examDate: "2026-11-20" | null }  (each module has its own exam date)
export async function setExamDate(req, res) {
  try {
    const studentId = resolveStudentId(req, req.body && req.body.studentId);
    const body = req.body || {};
    const saved = await service.setExamDate(getDb(), studentId, body.module, body.examDate);
    res.json({ studentId, module: body.module, examDate: saved });
  } catch (err) {
    res.status(err.status || 500).json({ error: err.message });
  }
}
