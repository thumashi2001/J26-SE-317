import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveStudentId } from '../../../middleware/auth.js';
import {
  resolveC4StudentId,
  LECTURER_SCOPE_UNAVAILABLE_MESSAGE,
} from '../services/c4StudentAccess.js';

test('resolveC4StudentId keeps student own-token behaviour', () => {
  const req = { user: { sub: 'IT20261234', role: 'student' } };
  assert.equal(resolveC4StudentId(req), 'IT20261234');
  assert.equal(resolveC4StudentId(req, 'IT20261234'), 'IT20261234');
  assert.throws(() => resolveC4StudentId(req, 'IT20269999'), (e) => e.status === 403);
});

test('resolveC4StudentId fails closed for lecturer even with studentId', () => {
  const req = { user: { sub: 'SLIITLEC001', role: 'lecturer' } };
  assert.throws(
    () => resolveC4StudentId(req, 'IT20261234'),
    (e) =>
      e.status === 403 &&
      e.code === 'lecturer_scope_unavailable' &&
      e.message === LECTURER_SCOPE_UNAVAILABLE_MESSAGE
  );
  assert.throws(() => resolveC4StudentId(req), (e) => e.status === 403);
});

test('shared resolveStudentId still allows lecturer+studentId (identification only)', () => {
  // Documents the shared middleware gap; C4 must not rely on this for authorization.
  const req = { user: { sub: 'SLIITLEC001', role: 'lecturer' } };
  assert.equal(resolveStudentId(req, 'IT20261234'), 'IT20261234');
});
