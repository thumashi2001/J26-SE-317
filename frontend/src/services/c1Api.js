import { api } from './apiClient.js';

export const getDiagnostic = (studentId) =>
  api(`/c1/diagnostic?studentId=${encodeURIComponent(studentId)}`);

export const submitDiagnostic = (studentId, answers) =>
  api('/c1/diagnostic/submit', { method: 'POST', body: { studentId, answers } });

export const getTwin = (studentId) => api(`/c1/twin/${encodeURIComponent(studentId)}`);

export const recordEvent = (event) => api('/c1/events', { method: 'POST', body: event });

export const getAlerts = (studentId) => api(`/c1/alerts/${encodeURIComponent(studentId)}`);

export const getHistory = (studentId, topic) =>
  api(`/c1/history/${encodeURIComponent(studentId)}/${encodeURIComponent(topic)}`);

export const getForecast = (studentId, topic, { days, perWeek }) =>
  api(`/c1/forecast/${encodeURIComponent(studentId)}/${encodeURIComponent(topic)}?days=${days}&perWeek=${perWeek}`);

export const startPractice = (topic) => api('/c1/practice/start', { method: 'POST', body: { topic } });

export const answerPractice = ({ sessionId, questionId, selected, timeSec, tabLeaves, awaySec }) =>
  api('/c1/practice/answer', { method: 'POST', body: { sessionId, questionId, selected, timeSec, tabLeaves, awaySec } });

// Engagement index, confidence per topic and the estimated score now.
export const getInsights = (studentId) => api(`/c1/insights/${encodeURIComponent(studentId)}`);

// How the student answers: fast, slow, guessing.
export const getBehaviour = (studentId) => api(`/c1/behaviour/${encodeURIComponent(studentId)}`);

export const getPracticeTopics = () => api('/c1/practice/topics');
