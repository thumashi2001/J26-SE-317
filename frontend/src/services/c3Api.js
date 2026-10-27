// C3 API CLIENT: one small function per backend route under /api/v1/c3. Each returns the parsed JSON, or throws an error
// carrying the HTTP status (see apiClient.js). The login token is added by apiClient, not here.
// Student calls: listAssessments, assessAnswer, listSubmissions, getSubmission.
// Lecturer/admin calls: listExamples, reviewSubmission, finalizeSubmission and the batch functions.

import { api } from './apiClient.js';

/**
 * Assessments a student can answer: the question and options only (never answer keys, rubrics or reference answers).
 * @returns {Promise<{ assessments: Array }>}
 */
export const listAssessments = () => api('/c3/assessments');

/**
 * Example setups with keys and rubrics (lecturer/admin only).
 * @returns {Promise<{ examples: Array }>}
 */
export const listExamples = () => api('/c3/examples');

/**
 * Mark one answer and save it for lecturer review.
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

/**
 * Create a shared question & rubric/answer-key setup for batch marking.
 *
 * @param {Object} setupData
 * @returns {Promise<Object>}
 */
export const createBatchSetup = (setupData) =>
  api('/c3/batch/setup', {
    method: 'POST',
    body: setupData,
  });

/**
 * List all batch setups created by lecturer.
 *
 * @returns {Promise<{ setups: Array }>}
 */
export const listBatchSetups = () =>
  api('/c3/batch/setup');

/**
 * Get batch setup details, statistics, and student submissions.
 *
 * @param {string} id - setup ID or batch_id
 * @returns {Promise<{ setup: Object, items: Array, stats: Object }>}
 */
export const getBatchSetup = (id) =>
  api(`/c3/batch/setup/${id}`);

/**
 * Pre-validate student answer rows against the shared setup.
 *
 * @param {Object} payload - { setup_id, items: Array }
 * @returns {Promise<Object>}
 */
export const validateBatchAnswers = (payload) =>
  api('/c3/batch/validate', {
    method: 'POST',
    body: payload,
  });

/**
 * Execute automated batch marking for student answers using the shared setup.
 *
 * @param {Object} payload - { setup_id, items: Array }
 * @returns {Promise<Object>}
 */
export const processBatchMarking = (payload) =>
  api('/c3/batch/mark', {
    method: 'POST',
    body: payload,
  });

/**
 * Finalize all reviewed/eligible submissions in a batch in one confirmed operation.
 *
 * @param {string} batchId
 * @returns {Promise<{ batch_id: string, finalized_count: number, skipped_unreviewed_count?: number, already_finalized_count?: number }>}
 */
export const finalizeBatchSubmissions = (batchId) =>
  api(`/c3/batch/${batchId}/finalize-all`, {
    method: 'POST',
  });

