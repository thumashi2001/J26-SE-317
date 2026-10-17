
import { api } from './apiClient.js';

const base = '/c2';

export const getC2Modules = () =>
  api(`${base}/modules`);

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

export const getC2ExcludedCandidates = (moduleKey) =>
  api(
    `${base}/reviews/${encodeURIComponent(moduleKey)}/excluded`
  );

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
