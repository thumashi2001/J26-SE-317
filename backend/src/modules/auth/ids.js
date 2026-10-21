// The three kinds of ID this system accepts.
//   student:  IT + 8 numbers           (IT12345678)
//   lecturer: SLIITLEC + 3 numbers    (11 characters, for example SLIITLEC123)
//   admin:    SLIITADMIN + 0 to 9 digits, created only by the seed script
export const STUDENT_RE = /^IT\d{8}$/;
export const LECTURER_RE = /^SLIITLEC\d{3}$/;
export const ADMIN_RE = /^SLIITADMIN\d{0,9}$/;

export const normaliseId = (value) => String(value || '').replace(/\s/g, '').toUpperCase();

export function kindOf(id) {
  if (STUDENT_RE.test(id)) return 'student';
  if (LECTURER_RE.test(id)) return 'lecturer';
  if (ADMIN_RE.test(id)) return 'admin';
  return null;
}
