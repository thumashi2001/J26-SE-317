// SAMPLE DATA for the lecturer Class insights page (Component 1).
// Lecturers are not linked to students in the database yet, so this page shows examples, not a real class.
// When the link exists, replace getClassInsights() in services/lecturerApi.js with a real API call that
// returns the same shape, and delete this file. The page itself does not need to change.

const day = (n) => new Date(Date.now() - n * 24 * 3600 * 1000).toISOString();

export const SAMPLE_CLASS = {
  className: 'Sample class',
  students: 24,
  diagnosticDone: 21,
  activeThisWeek: 15,
  answers: { total: 1342, thisWeek: 318 },
  averageLevel: { score: 54, label: 'Developing' },
  risk: { Low: 9, Medium: 8, High: 4 },
  weakestTopics: [
    { topic: 'schedule_cost_management', average: 31 },
    { topic: 'project_risk_management', average: 36 },
    { topic: 'unit_integration_testing', average: 42 },
    { topic: 'code_quality_solid', average: 47 },
    { topic: 'project_quality_management', average: 51 },
  ],
  needAttention: [
    { name: 'Sample Student A', semester: 'Y3S1', risk: 'High', level: 22, weakest: 'schedule_cost_management', lastActive: day(9) },
    { name: 'Sample Student B', semester: 'Y3S1', risk: 'High', level: 27, weakest: 'project_risk_management', lastActive: day(6) },
    { name: 'Sample Student C', semester: 'Y3S2', risk: 'High', level: 29, weakest: 'unit_integration_testing', lastActive: day(4) },
    { name: 'Sample Student D', semester: 'Y3S1', risk: 'High', level: 33, weakest: 'code_quality_solid', lastActive: day(3) },
    { name: 'Sample Student E', semester: 'Y3S1', risk: 'Medium', level: 41, weakest: 'schedule_cost_management', lastActive: day(2) },
    { name: 'Sample Student F', semester: 'Y3S2', risk: 'Medium', level: 44, weakest: 'project_quality_management', lastActive: day(1) },
  ],
};
