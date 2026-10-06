import { api } from './apiClient.js';

export const registerRequest = (form) => api('/auth/register', { method: 'POST', body: form });
export const loginRequest = (studentId, password) =>
  api('/auth/login', { method: 'POST', body: { studentId, password } });
