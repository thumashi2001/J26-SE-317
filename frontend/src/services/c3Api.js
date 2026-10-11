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
