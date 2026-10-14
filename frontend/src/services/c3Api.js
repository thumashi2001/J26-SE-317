import { api } from './apiClient.js';

/**
 * Execute C3 End-to-End Automated Assessment Pipeline
 * (F1 Answer Processing -> F2 Rubric Marking -> F3 Feedback -> F4 Mind Map)
 *
 * @param {Object} payload - AssessmentRequest matching backend schema
 * @returns {Promise<Object>} AssessmentResponse
 */
export const assessAnswer = (payload) =>
  api('/c3/assess', {
    method: 'POST',
    body: payload,
  });

/**
 * List submissions (students see own; lecturers see all).
 *
 * @param {Object} [params]
 * @param {string} [params.status]
 * @returns {Promise<{ submissions: Array }>}
 */
export const listSubmissions = (params = {}) => {
  const query = new URLSearchParams();
  if (params.status) query.set('status', params.status);
  const qStr = query.toString();
  return api(`/c3/submissions${qStr ? `?${qStr}` : ''}`);
};

/**
 * Get detailed submission and evaluation information.
 *
 * @param {string} id - submission ID
 * @returns {Promise<{ submission: Object, result: Object }>}
 */
export const getSubmission = (id) =>
  api(`/c3/submissions/${id}`);

/**
 * Lecturer Review: Accept AI mark or Override with reason.
 *
 * @param {string} id - submission ID
 * @param {Object} reviewData - { decision: 'accepted'|'overridden', new_mark?: number, override_reason?: string }
 * @returns {Promise<{ result: Object }>}
 */
export const reviewSubmission = (id, reviewData) =>
  api(`/c3/submissions/${id}/review`, {
    method: 'POST',
    body: reviewData,
  });

/**
 * Lecturer Finalization: Finalize assessment result.
 *
 * @param {string} id - submission ID
 * @returns {Promise<{ result: Object }>}
 */
export const finalizeSubmission = (id) =>
  api(`/c3/submissions/${id}/finalize`, {
    method: 'POST',
  });
