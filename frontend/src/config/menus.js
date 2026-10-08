export const getMenuForRole = (role) => {
  if (role === 'lecturer') {
    return [
      { heading: 'Marking' },
      { to: '/lecturer/c3', label: 'Automated Marking Review' },
    ];
  }
  
  if (role === 'admin') {
    return [
      { heading: 'Administration' },
      { to: '/admin/c3', label: 'C3 Administration' },
    ];
  }
  
  // default to student
  return [
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
};
