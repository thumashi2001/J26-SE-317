import { api } from './apiClient.js';

export const getStats = () => api('/admin/stats');
export const getLecturers = (status) => api(`/admin/lecturers${status ? `?status=${encodeURIComponent(status)}` : ''}`);
export const approveLecturer = (id) => api(`/admin/lecturers/${encodeURIComponent(id)}/approve`, { method: 'POST', body: {} });
export const rejectLecturer = (id, note) =>
  api(`/admin/lecturers/${encodeURIComponent(id)}/reject`, { method: 'POST', body: { note } });

// Component 1 totals for the admin card (no student names or IDs)
export const getC1Summary = () => api('/admin/c1/summary');

// Students active in the last 7 days: name, picture and activity (no IDs)
export const getC1Active = () => api('/admin/c1/active');
