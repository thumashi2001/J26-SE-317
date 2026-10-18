
import { api } from './apiClient.js';

const base = '/c2';

// --------------------------------------------------
// Get Supported Modules
// --------------------------------------------------

export const getC2Modules = () =>
  api(`${base}/modules`);

// --------------------------------------------------
// Get Syllabus Review Queue
// --------------------------------------------------

export const getC2ReviewQueue = (
  moduleKey,
  { page = 1, pageSize = 10, includeReviewed = false } = {}
) => {
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
    includeReviewed: String(includeReviewed),
  });

  return api(
    `${base}/reviews/${encodeURIComponent(moduleKey)}?${params}`
  );
};

// --------------------------------------------------
// Get Excluded Syllabus Candidates
// --------------------------------------------------

export const getC2ExcludedCandidates = (moduleKey) =>
  api(
    `${base}/reviews/${encodeURIComponent(moduleKey)}/excluded`
  );

// --------------------------------------------------
// M8 - Get Module-Wide Review Statistics
// --------------------------------------------------

export const getC2ReviewStatistics = (moduleKey) =>
  api(
    `${base}/reviews/${encodeURIComponent(moduleKey)}/stats`
  );

// --------------------------------------------------
// Submit Lecturer Approval / Rejection
// --------------------------------------------------

export const submitC2Review = (
  moduleKey,
  candidateId,
  { decision, reviewNotes = '' }
) =>
  api(
    `${base}/reviews/${encodeURIComponent(moduleKey)}/${encodeURIComponent(candidateId)}/decision`,
    {
      method: 'POST',
      body: { decision, reviewNotes },
    }
  );


  
/**
 * M10 - Student Question Bank
 */
export const getC2StudentQuestions = (
  { moduleKey, page = 1, pageSize = 10 } = {}
) => {
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
  });

  if (moduleKey) {
    params.set('moduleKey', moduleKey);
  }

  return api(`${base}/questions?${params.toString()}`);
};
