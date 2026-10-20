
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

export const getC2TopicPredictions = (moduleKey, targetPeriod = null, experimentalDemo = false) => {
  const params = new URLSearchParams({
    moduleKey,
  });
  if (targetPeriod) {
    params.set('targetPeriod', targetPeriod);
  }
  if (experimentalDemo) {
    params.set('experimental_demo', 'true');
  }

  return api(
    `${base}/topic-predictions?${params.toString()}`
  );
};

export const getC2ExperimentalTopicPredictions = (moduleKey, targetPeriod = null) => {
  const params = new URLSearchParams({
    moduleKey,
  });
  if (targetPeriod) {
    params.set('targetPeriod', targetPeriod);
  }

  return api(
    `${base}/topic-predictions/experimental-demo?${params.toString()}`
  );
};

// --------------------------------------------------
// M20 - Prediction Readiness and Evaluation Diagnostics
// --------------------------------------------------

export const getC2PredictionReadiness = (moduleKey = null) => {
  const params = moduleKey ? `?moduleKey=${encodeURIComponent(moduleKey)}` : '';
  return api(`${base}/predictions/readiness${params}`);
};

export const getC2PredictionEvaluation = (moduleKey) => {
  const params = new URLSearchParams({ moduleKey });
  return api(`${base}/predictions/evaluation?${params.toString()}`);
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

  
// --------------------------------------------------
// M15.1 - C1 Digital Twin Personalized Mock Exams
// --------------------------------------------------

export const generateC2MockFromTwin = ({
  moduleKey,
  targetMarks = 100,
  maxQuestions = 20,
  seed = 42,
}) =>
  api(`${base}/mock-exams/generate-from-twin`, {
    method: 'POST',
    body: {
      moduleKey,
      targetMarks,
      maxQuestions,
      seed,
    },
  });

// --------------------------------------------------
// M19.2 - Synthetic Practice (Experimental) Mock Exams
// --------------------------------------------------

export const generateC2SyntheticMockExam = ({
  moduleKey,
  questionCount = 5,
  seed = 42,
}) =>
  api(`${base}/mock-exams/synthetic`, {
    method: 'POST',
    body: {
      moduleKey,
      questionCount,
      seed,
    },
  });


// --------------------------------------------------
// M15.3 - Lecturer Question Classification Review
// --------------------------------------------------

export const getC2QuestionClassificationReviews = ({
  moduleKey,
  page = 1,
  pageSize = 10,
  includeReviewed = false,
  statusFilter,
} = {}) => {
  const params = new URLSearchParams({
    page: String(page),
    pageSize: String(pageSize),
    includeReviewed: String(includeReviewed),
  });

  if (moduleKey) {
    params.set('moduleKey', moduleKey);
  }
  if (statusFilter) {
    params.set('statusFilter', statusFilter);
  }

  return api(
    `${base}/question-classification-reviews?${params.toString()}`
  );
};

export const submitC2QuestionClassificationReview = (
  questionId,
  { moduleKey, topicId, decision, reviewNotes = '', isCorrection = false, allowManual = false }
) =>
  api(
    `${base}/question-classification-reviews/${encodeURIComponent(questionId)}/decision`,
    {
      method: 'POST',
      body: {
        moduleKey,
        topicId,
        decision,
        reviewNotes,
        isCorrection,
        allowManual,
      },
    }
  );

export const getC2QuestionClassificationReviewAnalytics = (moduleKey = null) => {
  const params = moduleKey ? `?moduleKey=${encodeURIComponent(moduleKey)}` : '';
  return api(`${base}/question-classification-reviews/analytics${params}`);
};

export const getC2TaxonomyReview = (moduleKey) =>
  api(`${base}/taxonomy-reviews/${encodeURIComponent(moduleKey)}`);

export const submitC2TaxonomyDecision = (
  moduleKey,
  { decision, reviewNotes = '' }
) =>
  api(`${base}/taxonomy-reviews/${encodeURIComponent(moduleKey)}/decision`, {
    method: 'POST',
    body: {
      decision,
      reviewNotes,
    },
  });

export const getC2QuestionClassificationEvaluations = (moduleKey = null) => {
  const params = moduleKey ? `?moduleKey=${encodeURIComponent(moduleKey)}` : '';
  return api(`${base}/question-classification-evaluations${params}`);
};

// --------------------------------------------------
// M18.2 - Experimental Topic Classification
// --------------------------------------------------

export const classifyC2TopicExperimental = ({
  moduleKey,
  questionText,
  abstentionThreshold,
}) =>
  api(`${base}/experimental/classify-topic`, {
    method: 'POST',
    body: {
      moduleKey,
      questionText,
      abstentionThreshold,
    },
  });

// --------------------------------------------------
// M19 - Student Practice Mock Attempts
// --------------------------------------------------

export const submitC2MockAttempt = ({
  mockId,
  moduleKey,
  questions,
  answers,
  timeSpentSeconds = 0,
  sourceType,
}) =>
  api(`${base}/mock-exams/attempts`, {
    method: 'POST',
    body: {
      mockId,
      moduleKey,
      questions,
      answers,
      timeSpentSeconds,
      ...(sourceType ? { sourceType } : {}),
    },
  });

export const getC2MockAttempts = ({ moduleKey } = {}) => {
  const params = new URLSearchParams();
  if (moduleKey) {
    params.set('moduleKey', moduleKey);
  }
  const query = params.toString();
  return api(`${base}/mock-exams/attempts${query ? `?${query}` : ''}`);
};

export const getC2MockAttempt = (attemptId) =>
  api(`${base}/mock-exams/attempts/${encodeURIComponent(attemptId)}`);

// --------------------------------------------------
// M21 - Bloom's Taxonomy-Controlled Question Generation
// --------------------------------------------------

export const getC2GenerationTopics = (moduleKey) =>
  api(`${base}/question-generation/topics?moduleKey=${encodeURIComponent(moduleKey)}`);

export const generateC2BloomQuestion = ({
  moduleKey,
  topicId,
  bloomLevel = 'apply',
  difficulty = 'medium',
  questionType = 'structured',
  marks = 10,
  lecturerInstructions = '',
}) =>
  api(`${base}/question-generation/generate`, {
    method: 'POST',
    body: {
      moduleKey,
      topicId,
      bloomLevel,
      difficulty,
      questionType,
      marks,
      lecturerInstructions,
    },
  });

export const submitC2BloomQuestionDecision = ({
  decision,
  question,
  reviewNotes = '',
  updatedText,
  updatedMarks,
}) =>
  api(`${base}/question-generation/decision`, {
    method: 'POST',
    body: {
      decision,
      question,
      reviewNotes,
      updatedText,
      updatedMarks,
    },
  });

export const getC2ApprovedGeneratedQuestions = (moduleKey = null) => {
  const params = moduleKey ? `?moduleKey=${encodeURIComponent(moduleKey)}` : '';
  return api(`${base}/question-generation/approved${params}`);
};

export const getC2BloomClassifierEvaluation = () =>
  api(`${base}/question-generation/bloom-evaluation`);

