
const C2_API_URL =
  process.env.C2_API_URL || 'http://127.0.0.1:8002';

export class C2ServiceError extends Error {
  constructor(message, status = 502) {
    super(message);
    this.name = 'C2ServiceError';
    this.status = status;
  }
}

async function requestC2(path, options = {}) {
  const token = process.env.C2_INTERNAL_TOKEN;
  const baseUrl = process.env.C2_API_URL || 'http://127.0.0.1:8002';

  if (!token) {
    throw new C2ServiceError(
      'C2 internal token is not configured',
      503
    );
  }

  let response;

  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-C2-Internal-Token': token,
      },
      body: options.body
        ? JSON.stringify(options.body)
        : undefined,
      signal: AbortSignal.timeout(30000),
    });
  } catch {
    throw new C2ServiceError(
      'C2 Python service is unavailable',
      503
    );
  }

  let data;

  try {
    data = await response.json();
  } catch {
    throw new C2ServiceError(
      'Invalid response from C2 Python service'
    );
  }

  if (!response.ok) {
    const message =
      typeof data.detail === 'string'
        ? data.detail
        : 'C2 request failed';

    const status = [400, 403, 404, 409, 503].includes(
      response.status
    )
      ? response.status
      : 502;

    throw new C2ServiceError(message, status);
  }

  return data;
}

export function getModules() {
  return requestC2('/modules');
}

export function getReviewQueue(
  moduleKey,
  { page = 1, pageSize = 25, includeReviewed = false } = {}
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    include_reviewed: String(includeReviewed),
  });

  return requestC2(
    `/reviews/${encodeURIComponent(moduleKey)}?${params}`
  );
}

export function getExcludedCandidates(moduleKey) {
  return requestC2(
    `/reviews/${encodeURIComponent(moduleKey)}/excluded`
  );
}

export function submitReviewDecision({
  moduleKey,
  candidateId,
  decision,
  reviewNotes,
  reviewerId,
}) {
  return requestC2('/reviews/decision', {
    method: 'POST',
    body: {
      module_key: moduleKey,
      candidate_id: candidateId,
      decision,
      review_notes: reviewNotes,
      reviewer_id: reviewerId,
    },
  });
}


export function getReviewStatistics(moduleKey) {
  return requestC2(
    `/reviews/${encodeURIComponent(moduleKey)}/stats`
  );
}


export function getStudentQuestions(
  { moduleKey, page = 1, pageSize = 10 } = {}
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  if (moduleKey) {
    params.set('module_key', moduleKey);
  }

  return requestC2(`/questions?${params.toString()}`);
}

// --------------------------------------------------
// M11.1 - Historical Exam Pattern Analysis
// --------------------------------------------------

export function getExamPatterns(moduleKey) {
  const params = new URLSearchParams({
    module_key: moduleKey,
  });

  return requestC2(`/exam-patterns?${params.toString()}`);
}


// --------------------------------------------------
// M12.1 - Evidence-Aware Topic Predictions
// --------------------------------------------------

export function getTopicPredictions(moduleKey) {
  const params = new URLSearchParams({
    module_key: moduleKey,
  });

  return requestC2(
    `/topic-predictions?${params.toString()}`
  );
}

// --------------------------------------------------
// M12.2.1 - Personalized Practice Mock Examinations
// --------------------------------------------------

export function generateMockExam(payload) {
  return requestC2('/mock-exams/generate', {
    method: 'POST',
    body: payload,
  });
}

// --------------------------------------------------
// M12.4.2 - Staff-Only Synthetic Development Preview
// --------------------------------------------------

export function generateSyntheticPracticePreview({
  moduleKey,
  seed = 42,
}) {
  return requestC2('/internal/synthetic-practice-preview', {
    method: 'POST',
    body: {
      module_key: moduleKey,
      seed,
    },
  });
}

// M14.3.3.2 - Lecturer Question Classification Review
export function submitQuestionClassificationReview({
  questionId,
  moduleKey,
  topicId,
  decision,
  reviewNotes,
  reviewerId,
}) {
  return requestC2(
    '/question-classification-reviews/decision',
    {
      method: 'POST',
      body: {
        question_id: questionId,
        module_key: moduleKey,
        topic_id: topicId,
        decision,
        review_notes: reviewNotes,
        reviewer_id: reviewerId,
      },
    }
  );
}

// M15.3 - List Question Classification Reviews
export function getQuestionClassificationReviews({
  moduleKey,
  page = 1,
  pageSize = 10,
  includeReviewed = false,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    include_reviewed: String(includeReviewed),
  });

  if (moduleKey) {
    params.set('module_key', moduleKey);
  }

  return requestC2(
    `/question-classification-reviews?${params.toString()}`
  );
}

// M18.2 - Experimental Topic Classification
export function classifyTopicExperimental({
  moduleKey,
  questionText,
  abstentionThreshold,
}) {
  return requestC2('/api/v1/experimental/classify-topic', {
    method: 'POST',
    body: {
      module_key: moduleKey,
      question_text: questionText,
      abstention_threshold: abstentionThreshold,
    },
  });
}

