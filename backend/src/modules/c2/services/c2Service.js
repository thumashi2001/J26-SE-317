
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

  if (!token) {
    throw new C2ServiceError(
      'C2 internal token is not configured',
      503
    );
  }

  let response;

  try {
    response = await fetch(`${C2_API_URL}${path}`, {
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

    const status = [400, 404, 409].includes(
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

