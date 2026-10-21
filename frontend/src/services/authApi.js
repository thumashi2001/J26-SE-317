import { api } from './apiClient.js';

export const registerRequest = (form) => api('/auth/register', { method: 'POST', body: form });
export const registerLecturerRequest = (form) => api('/auth/register-lecturer', { method: 'POST', body: form });
export const loginRequest = (userId, password) =>
  api('/auth/login', { method: 'POST', body: { userId, password } });
export const getMe = () => api('/auth/me');

// My profile (every role). The ID can never be changed.
export const getProfile = () => api('/auth/profile');
export const updateProfile = (fields) => api('/auth/profile', { method: 'PATCH', body: fields });
export const saveAvatar = (image) => api('/auth/profile/avatar', { method: 'PUT', body: { image } }); // image = data URL, or null to remove
export const changePassword = (currentPassword, newPassword) => api('/auth/change-password', { method: 'POST', body: { currentPassword, newPassword } });

// Time on the web app: a ping every 30 seconds while the tab is open and visible.
export const pingUsage = (seconds) => api('/auth/usage', { method: 'POST', body: { seconds } });
export const getUsage = () => api('/auth/usage');
