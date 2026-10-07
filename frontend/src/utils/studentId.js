// SLIIT student IDs: "IT" followed by 8 digits, for example IT********.
export const STUDENT_ID_PATTERN = /^IT\d{8}$/;
export const STUDENT_ID_HELP = 'Student ID must start with IT followed by 8 digits, for example IT********.';

export const cleanStudentId = (value) => value.replace(/\s/g, '').toUpperCase();
export const isValidStudentId = (value) => STUDENT_ID_PATTERN.test(cleanStudentId(value));

// Show only the last 2 digits on screen, for example IT******88.
export const maskStudentId = (id) => (id && id.length > 4 ? `${id.slice(0, 2)}${'*'.repeat(id.length - 4)}${id.slice(-2)}` : id);
