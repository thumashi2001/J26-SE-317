import { api } from './apiClient.js';

export const getStats = () => api('/admin/stats');
export const getLecturers = (status) => api(`/admin/lecturers${status ? `?status=${encodeURIComponent(status)}` : ''}`);
export const approveLecturer = (id) => api(`/admin/lecturers/${encodeURIComponent(id)}/approve`, { method: 'POST', body: {} });
export const rejectLecturer = (id, note) =>
  api(`/admin/lecturers/${encodeURIComponent(id)}/reject`, { method: 'POST', body: { note } });
