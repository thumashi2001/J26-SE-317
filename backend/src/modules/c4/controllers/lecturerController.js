import { getDb } from '../../../config/db.js';
import { assertAssigned, assertLecturerReader, LIVE_LECTURER_SCOPE } from '../services/lecturerScope.js';
import { lecturerScopeView, listLecturerStudents, readLecturerStudentPlan } from '../services/lecturerPlan.js';

function handle(fn) {
  return async (req, res) => {
    try {
      const data = await fn(req);
      res.json(data);
    } catch (err) {
      const body = { error: err.message };
      if (err.code) body.code = err.code;
      res.status(err.status || 500).json(body);
    }
  };
}

/** Live handlers ignore any client-supplied roster. Scope stays unavailable. */
export const scope = handle(async (req) => {
  assertLecturerReader(req);
  return lecturerScopeView(LIVE_LECTURER_SCOPE);
});

export const students = handle(async (req) => {
  const lecturerId = assertLecturerReader(req);
  return listLecturerStudents(lecturerId, LIVE_LECTURER_SCOPE);
});

export const plan = handle(async (req) => {
  const lecturerId = assertLecturerReader(req);
  assertAssigned(lecturerId, req.params.studentId, LIVE_LECTURER_SCOPE);
  return readLecturerStudentPlan(
    getDb(),
    lecturerId,
    req.params.studentId,
    LIVE_LECTURER_SCOPE
  );
});
