import { api } from './apiClient.js';

export const getDiagnostic = (studentId) =>
  api(`/c1/diagnostic?studentId=${encodeURIComponent(studentId)}`);

export const submitDiagnostic = (studentId, answers, meta = {}) =>
  api('/c1/diagnostic/submit', { method: 'POST', body: { studentId, answers, ...meta } });

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

export const hintPractice = ({ sessionId, questionId }) =>
  api('/c1/practice/hint', { method: 'POST', body: { sessionId, questionId } });

// Engagement index, confidence per topic and the estimated score now.
export const getInsights = (studentId) => api(`/c1/insights/${encodeURIComponent(studentId)}`);

// How the student answers: fast, slow, guessing.
export const getBehaviour = (studentId) => api(`/c1/behaviour/${encodeURIComponent(studentId)}`);

export const getPracticeTopics = () => api('/c1/practice/topics');

// Study plan: today's tasks, calendar and predicted exam score, built from forgetting, behaviour and the exam date.
export const getPlan = (studentId) => api(`/c1/plan/${encodeURIComponent(studentId)}`);

// Every module has its own exam date. examDate is "YYYY-MM-DD", or null to clear it.
export const saveExamDate = (studentId, module, examDate) => api('/c1/exam-date', { method: 'PUT', body: { studentId, module, examDate } });

// 5 star knowledge level that follows the twin.
export const getLevel = (studentId) => api(`/c1/level/${encodeURIComponent(studentId)}`);

// Trained model (gradient boosting): chance of a correct answer on each topic the student has practised.
export const getPrediction = (studentId) => api(`/c1/predict/${encodeURIComponent(studentId)}`);
