/**
 * C4-owned student identity resolution for path/exam/feedback APIs.
 *
 * Shared `resolveStudentId` (middleware/auth.js) lets any lecturer JWT supply
 * an arbitrary studentId with no roster check — that is identification only.
 * C4 has no approved lecturer–student assignment store. Until a product-owned
 * scope policy exists, lecturer (and non-student) access to student C4 records
 * fails closed here. Do not invent roster membership in C4.
 */

import { resolveStudentId } from '../../../middleware/auth.js';

const LECTURER_UNAVAILABLE =
  'Lecturer access to student C4 records is unavailable until an approved class-roster or assignment scope exists. Passing studentId alone is not authorization.';

/**
 * @param {import('express').Request} req
 * @param {string} [supplied]
 * @returns {string} student id for the request
 */
export function resolveC4StudentId(req, supplied) {
  const fail = (status, message, code) =>
    Object.assign(new Error(message), { status, code });

  if (!req?.user) throw fail(401, 'Please log in', 'unauthenticated');

  if (req.user.role === 'lecturer') {
    throw fail(403, LECTURER_UNAVAILABLE, 'lecturer_scope_unavailable');
  }

  // Students (and any other roles shared resolveStudentId rejects) use shared rules.
  return resolveStudentId(req, supplied);
}

export const LECTURER_SCOPE_UNAVAILABLE_MESSAGE = LECTURER_UNAVAILABLE;
