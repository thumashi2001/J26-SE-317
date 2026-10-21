import { api } from './apiClient.js';

// Class insights for the logged-in lecturer: real data from the backend.
// Lecturers are not linked to individual students yet, so the class is every registered student.
export async function getClassInsights() {
  const data = await api('/c1/class');
  return { ...data, isSample: false };
}
