import test from 'node:test';
import assert from 'node:assert/strict';
import { resolveStudentId } from '../../../middleware/auth.js';

test('resolveStudentId forces student to own token identity', () => {
  const req = { user: { sub: 'IT20261234', role: 'student' } };
  assert.equal(resolveStudentId(req), 'IT20261234');
  assert.equal(resolveStudentId(req, 'IT20261234'), 'IT20261234');
  assert.throws(() => resolveStudentId(req, 'IT20269999'), (e) => e.status === 403);
});

test('resolveStudentId requires lecturer to name a student', () => {
  const req = { user: { sub: 'SLIITLEC001', role: 'lecturer' } };
  assert.throws(() => resolveStudentId(req), (e) => e.status === 400);
  assert.equal(resolveStudentId(req, 'IT20261234'), 'IT20261234');
});

test('resolveStudentId refuses admin for student data', () => {
  const req = { user: { sub: 'SLIITADMIN1', role: 'admin' } };
  assert.throws(() => resolveStudentId(req, 'IT20261234'), (e) => e.status === 403);
});
