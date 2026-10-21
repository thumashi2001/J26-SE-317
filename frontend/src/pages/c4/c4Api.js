import { api } from '../../services/apiClient.js';

export const createPath = (body = {}) => api('/c4/paths', { method: 'POST', body });

export const listPaths = (studentId) => {
  const q = studentId ? `?studentId=${encodeURIComponent(studentId)}` : '';
  return api(`/c4/paths${q}`);
};

export const getActivePath = (studentId) => {
  const q = studentId ? `?studentId=${encodeURIComponent(studentId)}` : '';
  return api(`/c4/paths/active${q}`);
};

export const getPath = (pathId, studentId) => {
  const q = studentId ? `?studentId=${encodeURIComponent(studentId)}` : '';
  return api(`/c4/paths/${encodeURIComponent(pathId)}${q}`);
};

export const recordProgress = (pathId, activityId) =>
  api(`/c4/paths/${encodeURIComponent(pathId)}/progress`, {
    method: 'POST',
    body: { activityId, status: 'self_reported_complete' },
  });

export const replanPath = (pathId, body = {}) =>
  api(`/c4/paths/${encodeURIComponent(pathId)}/replan`, { method: 'POST', body });

export const refreshPath = (pathId, body = {}) =>
  api(`/c4/paths/${encodeURIComponent(pathId)}/refresh`, { method: 'POST', body });

export const getPathRevisions = (pathId, studentId) => {
  const q = studentId ? `?studentId=${encodeURIComponent(studentId)}` : '';
  return api(`/c4/paths/${encodeURIComponent(pathId)}/revisions${q}`);
};

/* Mock exams */
export const getExamSources = () => api('/c4/exams/sources');
export const createExam = (body = {}) => api('/c4/exams', { method: 'POST', body });
export const listExams = () => api('/c4/exams');
export const getExam = (attemptId) => api(`/c4/exams/${encodeURIComponent(attemptId)}`);
export const saveExamAnswers = (attemptId, answers) =>
  api(`/c4/exams/${encodeURIComponent(attemptId)}/answers`, {
    method: 'POST',
    body: { answers },
  });
export const submitExam = (attemptId, answers) =>
  api(`/c4/exams/${encodeURIComponent(attemptId)}/submit`, {
    method: 'POST',
    body: answers ? { answers } : {},
  });

/* Feedback */
export const submitFeedback = (body) => api('/c4/feedback', { method: 'POST', body });
export const listFeedback = () => api('/c4/feedback');

export const getLecturerScope = () => api('/c4/lecturer/scope');

/* Synthetic simulation demo (v1) */
export const getSimDemoReady = () => api('/c4/simulation/v1/ready');
export const getSimScenarios = () => api('/c4/simulation/v1/scenarios');
export const predictSimPath = (body) =>
  api('/c4/simulation/v1/path/predict', { method: 'POST', body });
export const predictSimResponse = (body) =>
  api('/c4/simulation/v1/supervised/response', { method: 'POST', body });
export const predictSimExamScore = (body) =>
  api('/c4/simulation/v1/supervised/exam-score', { method: 'POST', body });
export const predictSimPass = (body) =>
  api('/c4/simulation/v1/supervised/pass', { method: 'POST', body });
