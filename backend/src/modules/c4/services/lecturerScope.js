/**
 * Lecturer access to C4 plans.
 *
 * A studentId names the requested student. It does not authorize access.
 * Live HTTP handlers must pass LIVE_LECTURER_SCOPE. Test fixtures are
 * in-memory only and are not an approved roster.
 */

export const LIVE_LECTURER_SCOPE = Object.freeze({
  mode: 'unavailable',
  source: null,
});

export const LECTURER_SCOPE_REASON =
  'Lecturer access to student C4 plans is unavailable. No approved class roster, module assignment, or documented all-students rule exists for C4. A supplied studentId is not authorization.';

function fail(status, message, code) {
  return Object.assign(new Error(message), { status, code });
}

export function assertLecturerReader(req) {
  if (!req?.user) throw fail(401, 'Please log in', 'unauthenticated');
  if (req.user.role !== 'lecturer') {
    throw fail(403, 'This C4 view is for lecturer accounts.', 'role_not_lecturer');
  }
  if (!req.user.sub) throw fail(401, 'Please log in', 'unauthenticated');
  return req.user.sub;
}

export function describeLecturerScope(scope = LIVE_LECTURER_SCOPE) {
  if (scope?.mode === 'test_fixture' && Array.isArray(scope.assignments)) {
    return {
      available: true,
      operational: false,
      source: 'test_fixture',
      code: 'test_fixture_only',
      reason:
        'In-memory test fixture only. HTTP handlers do not use it, and it is not a live roster.',
    };
  }
  return {
    available: false,
    operational: false,
    source: null,
    code: 'lecturer_scope_unavailable',
    reason: LECTURER_SCOPE_REASON,
  };
}

/** Student ids this lecturer may read. Throws before any database lookup when scope is closed. */
export function assignedStudentIds(lecturerId, scope = LIVE_LECTURER_SCOPE) {
  const described = describeLecturerScope(scope);
  if (!described.available) {
    throw fail(403, described.reason, described.code);
  }
  return scope.assignments
    .filter((row) => row && row.lecturerId === lecturerId && row.studentId)
    .map((row) => row.studentId);
}

export function assertAssigned(lecturerId, studentId, scope = LIVE_LECTURER_SCOPE) {
  if (!studentId || typeof studentId !== 'string') {
    throw fail(400, 'studentId is required', 'student_id_required');
  }
  const allowed = assignedStudentIds(lecturerId, scope);
  if (!allowed.includes(studentId)) {
    throw fail(
      403,
      'This lecturer is not authorized to read that student.',
      'lecturer_student_forbidden'
    );
  }
  return studentId;
}
