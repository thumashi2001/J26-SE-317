import { getDb } from '../../../config/db.js';
import * as service from '../services/adminService.js';

function handle(fn) {
  return async (req, res) => {
    try {
      res.json(await fn(req));
    } catch (err) {
      res.status(err.status || 500).json({ error: err.message });
    }
  };
}

export const stats = handle(() => service.getStats(getDb()));
export const lecturers = handle((req) => service.listLecturers(getDb(), req.query.status));
export const approve = handle((req) => service.approveLecturer(getDb(), req.user.sub, req.params.id));
export const reject = handle((req) => service.rejectLecturer(getDb(), req.user.sub, req.params.id, (req.body || {}).note));
