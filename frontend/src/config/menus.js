// The side menu and the section cards for each kind of user.
// TEAM: to add your page, add one line to the list for that role, then add the route in App.jsx.
//   { to: '/admin/c3-review', label: 'Marking review' }
// A line with only { heading: '...' } makes a group title.

export const STUDENT_MENU = [
  { heading: 'Digital twin' },
  { to: '/c1/diagnostic', label: 'Diagnostic test', onlyBeforeDiagnostic: true },
  { to: '/c1/dashboard', label: 'My learning state' },
  { heading: 'Exams' },
  { to: '/c2', label: 'Exam intelligence' },
  { heading: 'Marking' },
  { to: '/c3', label: 'Automated marking' },
  { heading: 'Study plan' },
  { to: '/c4', label: 'Adaptive path' },
];

export const LECTURER_MENU = [
  { heading: 'Lecturer area' },
  { to: '/lecturer', label: 'Overview', end: true },
  { heading: 'Components' },
  { to: '/lecturer/c1', label: 'Class learning state' },
  { to: '/lecturer/c2', label: 'Exam intelligence' },
  { to: '/lecturer/c3', label: 'Marking review' },
  { to: '/lecturer/c4', label: 'Adaptive paths' },
];

export const ADMIN_MENU = [
  { heading: 'Admin' },
  { to: '/admin', label: 'Overview', end: true },
  { heading: 'People' },
  { to: '/admin/lecturers', label: 'Lecturer approvals' },
  // TEAM: add your admin pages here.
];

// Cards on the lecturer overview page (one per component).
export const LECTURER_SECTIONS = [
  { to: '/lecturer/c1', title: 'Class learning state', owner: 'Component 1', text: 'See how each student and the whole class is learning, topic by topic.' },
  { to: '/lecturer/c2', title: 'Exam intelligence', owner: 'Component 2', text: 'Question papers, rubrics and exam patterns.' },
  { to: '/lecturer/c3', title: 'Marking review', owner: 'Component 3', text: 'Review automated marks and feedback before students see them.' },
  { to: '/lecturer/c4', title: 'Adaptive paths', owner: 'Component 4', text: 'Check the study plans recommended to students.' },
];

// Cards under "Manage" on the admin overview page.
export const ADMIN_SECTIONS = [
  { to: '/admin/lecturers', title: 'Lecturer approvals', text: 'Approve or reject lecturer registrations.' },
  // TEAM: add a card for your admin page here.
];
