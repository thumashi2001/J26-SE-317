/**
 * C4-owned student feedback (usefulness, problems, suggestions).
 * No fabricated history; ownership on every write.
 */

import { randomUUID } from 'crypto';

export const FEEDBACK_COLLECTION = 'c4_feedback';

function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code;
  return err;
}

const TARGETS = new Set(['study_plan', 'mock_exam', 'simulation_demo', 'overall']);

export async function submitFeedback(db, studentId, body) {
  const target = String(body?.target || 'overall');
  if (!TARGETS.has(target)) {
    throw httpError(400, `target must be one of: ${[...TARGETS].join(', ')}`);
  }
  const usefulness = body?.usefulness != null ? Number(body.usefulness) : null;
  if (usefulness != null && (!Number.isInteger(usefulness) || usefulness < 1 || usefulness > 5)) {
    throw httpError(400, 'usefulness must be an integer 1–5');
  }
  const problem = typeof body?.problem === 'string' ? body.problem.trim().slice(0, 2000) : '';
  const suggestion = typeof body?.suggestion === 'string' ? body.suggestion.trim().slice(0, 2000) : '';
  if (usefulness == null && !problem && !suggestion) {
    throw httpError(400, 'Provide usefulness (1–5) and/or problem/suggestion text');
  }
  const refId = typeof body?.refId === 'string' ? body.refId.slice(0, 80) : null;
  const timingMs = body?.timingMs != null ? Number(body.timingMs) : null;
  if (timingMs != null && (!Number.isFinite(timingMs) || timingMs < 0 || timingMs > 3_600_000)) {
    throw httpError(400, 'timingMs out of range');
  }

  const doc = {
    feedback_id: randomUUID(),
    student_id: studentId,
    target,
    ref_id: refId,
    usefulness,
    problem: problem || null,
    suggestion: suggestion || null,
    timing_ms: timingMs,
    created_at: new Date(),
  };
  await db.collection(FEEDBACK_COLLECTION).insertOne(doc);
  return {
    feedbackId: doc.feedback_id,
    studentId,
    target: doc.target,
    usefulness: doc.usefulness,
    createdAt: doc.created_at,
    note: 'Stored in C4-owned feedback collection only.',
  };
}

export async function listFeedback(db, studentId) {
  const rows = await db.collection(FEEDBACK_COLLECTION).find({ student_id: studentId }).toArray();
  rows.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return {
    studentId,
    items: rows.map((d) => ({
      feedbackId: d.feedback_id,
      target: d.target,
      refId: d.ref_id,
      usefulness: d.usefulness,
      problem: d.problem,
      suggestion: d.suggestion,
      createdAt: d.created_at,
    })),
  };
}
