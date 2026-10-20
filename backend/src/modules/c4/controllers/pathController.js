import { getDb } from '../../../config/db.js';
import { resolveC4StudentId } from '../services/c4StudentAccess.js';
import * as service from '../services/pathService.js';

const C1_AI_URL = () => process.env.C1_AI_URL || 'http://127.0.0.1:8001';

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

/** Own-token students only; lecturer cross-student access fails closed (no roster). */
function studentFrom(req, supplied) {
  return resolveC4StudentId(req, supplied);
}

export const create = handle(async (req) => {
  const body = req.body || {};
  const studentId = studentFrom(req, body.studentId);
  return service.createPath(getDb(), studentId, body, C1_AI_URL());
});

export const list = handle(async (req) => {
  const studentId = studentFrom(req, req.query.studentId);
  return service.listPaths(getDb(), studentId);
});

export const active = handle(async (req) => {
  const studentId = studentFrom(req, req.query.studentId);
  return service.getActivePath(getDb(), studentId);
});

export const detail = handle(async (req) => {
  const studentId = studentFrom(req, req.query.studentId);
  return service.getPath(getDb(), studentId, req.params.pathId);
});

export const progress = handle(async (req) => {
  const body = req.body || {};
  const studentId = studentFrom(req, body.studentId);
  return service.recordProgress(getDb(), studentId, req.params.pathId, body);
});

export const replan = handle(async (req) => {
  const body = req.body || {};
  const studentId = studentFrom(req, body.studentId);
  return service.replanPath(getDb(), studentId, req.params.pathId, body, C1_AI_URL());
});

export const refresh = handle(async (req) => {
  const body = req.body || {};
  const studentId = studentFrom(req, body.studentId || req.query.studentId);
  return service.refreshPath(getDb(), studentId, req.params.pathId, C1_AI_URL(), body);
});

export const revisions = handle(async (req) => {
  const studentId = studentFrom(req, req.query.studentId);
  return service.listRevisions(getDb(), studentId, req.params.pathId);
});
