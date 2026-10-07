import { api } from './apiClient.js';

export const registerRequest = (form) => api('/auth/register', { method: 'POST', body: form });
export const registerLecturerRequest = (form) => api('/auth/register-lecturer', { method: 'POST', body: form });
export const loginRequest = (userId, password) =>
  api('/auth/login', { method: 'POST', body: { userId, password } });
export const getMe = () => api('/auth/me');
