/**
 * C3 Frontend API service
 *
 * Two layers:
 *  1. Application API — assessment listing, submission, results, lecturer queue
 *  2. Raw AI proxy calls — used internally by the submit flow (now via Node)
 */
import { api } from './apiClient.js';

// ── Application APIs ─────────────────────────────────────────────────────────

/** List all active assessments visible to the student. */
export async function listAssessments() {
  return api('/c3/assessments');
}

/** Get a single assessment by ID (student-safe fields only). */
export async function getAssessment(id) {
  return api(`/c3/assessments/${id}`);
}

/**
 * Submit a typed answer. Node orchestrates the full AI pipeline
 * and stores results in MongoDB.
 */
export async function submitAnswer(assessmentId, studentAnswer) {
  return api('/c3/submissions', {
    method: 'POST',
    body: { assessment_id: assessmentId, student_answer: studentAnswer },
  });
}

/** Get the AI/final result for a submission. */
export async function getResult(submissionId) {
  return api(`/c3/results/${submissionId}`);
}

/** List the current student's own submissions. */
export async function listMySubmissions() {
  return api('/c3/submissions/me');
}

// ── Lecturer APIs ─────────────────────────────────────────────────────────────

/** List submissions available for lecturer review. */
export async function lecturerListSubmissions(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return api(`/c3/lecturer/submissions${qs ? '?' + qs : ''}`);
}

/** Get a full submission + result detail for lecturer review. */
export async function lecturerGetSubmission(submissionId) {
  return api(`/c3/lecturer/submissions/${submissionId}`);
}

/** Accept the AI mark as final. */
export async function lecturerAccept(submissionId) {
  return api(`/c3/lecturer/submissions/${submissionId}/accept`, { method: 'POST' });
}

/** Override the AI mark with a revised mark and reason. */
export async function lecturerOverride(submissionId, revisedMark, reason) {
  return api(`/c3/lecturer/submissions/${submissionId}/override`, {
    method: 'POST',
    body: { revised_mark: revisedMark, reason },
  });
}

// ── Admin APIs ────────────────────────────────────────────────────────────────

/** Get C3 submission statistics for admin. */
export async function getAdminStats() {
  return api('/c3/admin/stats');
}
