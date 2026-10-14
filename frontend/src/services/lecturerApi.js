import { SAMPLE_CLASS } from '../pages/lecturer/classInsightsSample.js';

// Class insights for the logged-in lecturer.
// For now this returns SAMPLE data (isSample: true) because lecturers are not linked to students yet.
// TODO: when the link exists, call the backend here and return { ...data, isSample: false }.
export async function getClassInsights() {
  return { ...SAMPLE_CLASS, isSample: true };
}
