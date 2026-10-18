
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
// Get Module-Wide Review Statistics
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

// --------------------------------------------------
// M10 - Student Question Bank
// --------------------------------------------------

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

// --------------------------------------------------
// M12.1 - Evidence-Aware Topic Predictions
// --------------------------------------------------

export const getC2TopicPredictions = (moduleKey) => {
  const params = new URLSearchParams({
    moduleKey,
  });

  return api(
    `${base}/topic-predictions?${params.toString()}`
  );
};

// --------------------------------------------------
// M12.2 - Personalized Practice Mock Exams
// --------------------------------------------------

export const generateC2MockExam = ({
  moduleKey,
  targetMarks = 100,
  maxQuestions = 20,
  preferredTopics = [],
  difficulty = null,
  seed = 42,
}) =>
  api(`${base}/mock-exams/generate`, {
    method: 'POST',
    body: {
      moduleKey,
      targetMarks,
      maxQuestions,
      preferredTopics,
      difficulty,
      seed,
    },
  });

  // --------------------------------------------------
// M12.4.3 - Lecturer Synthetic Practice Preview
// Development-only, staff-authorized backend endpoint.
// --------------------------------------------------

export const generateC2SyntheticPracticePreview = ({
  moduleKey,
  seed = 42,
}) =>
  api(`${base}/internal/synthetic-practice-preview`, {
    method: 'POST',
    body: {
      moduleKey,
      seed,
    },
  });