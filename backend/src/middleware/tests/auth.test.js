import test from 'node:test';
import assert from 'node:assert';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import jwt from 'jsonwebtoken';

process.env.AUTH_SECRET = 'auth-test-secret';

const { signToken, requireAuth, requireRole, resolveStudentId } = await import('../auth.js');

const here = path.dirname(fileURLToPath(import.meta.url));
const authUrl = pathToFileURL(path.join(here, '..', 'auth.js')).href;

function mockRes() {
  return {
    statusCode: 200,
    body: null,
    status(code) { this.statusCode = code; return this; },
    json(b) { this.body = b; return this; },
  };
}

function runAuth(headers) {
  const req = { headers };
  const res = mockRes();
  let nextCalled = false;
  requireAuth(req, res, () => { nextCalled = true; });
  return { req, res, nextCalled };
}

test('signToken produces a token that requireAuth accepts (round trip)', () => {
  const token = signToken({ sub: 'u1', role: 'student' });
  const { req, res, nextCalled } = runAuth({ authorization: `Bearer ${token}` });
  assert.strictEqual(nextCalled, true);
  assert.strictEqual(res.statusCode, 200);
  assert.deepStrictEqual(req.user, { sub: 'u1', role: 'student' });
});

test('requireAuth: missing header -> 401', () => {
  const { res, nextCalled } = runAuth({});
  assert.strictEqual(nextCalled, false);
  assert.strictEqual(res.statusCode, 401);
  assert.strictEqual(res.body.error, 'Please log in');
});

test('requireAuth: malformed header (no Bearer prefix / empty token) -> 401', () => {
  const token = signToken({ sub: 'u1', role: 'student' });
  for (const authorization of [token, `Token ${token}`, 'Bearer ', 'bearer ' + token]) {
    const { res, nextCalled } = runAuth({ authorization });
    assert.strictEqual(nextCalled, false, authorization);
    assert.strictEqual(res.statusCode, 401, authorization);
  }
});

test('requireAuth: garbage token -> 401', () => {
  const { res, nextCalled } = runAuth({ authorization: 'Bearer not.a.jwt' });
  assert.strictEqual(nextCalled, false);
  assert.strictEqual(res.statusCode, 401);
  assert.strictEqual(res.body.error, 'Please log in again');
});

test('requireAuth: token signed with a different secret -> 401', () => {
  const bad = jwt.sign({ sub: 'u1', role: 'lecturer' }, 'some-other-secret', { algorithm: 'HS256' });
  const { res, nextCalled } = runAuth({ authorization: `Bearer ${bad}` });
  assert.strictEqual(nextCalled, false);
  assert.strictEqual(res.statusCode, 401);
});

test('requireAuth: tampered payload (signature mismatch) -> 401', () => {
  const token = signToken({ sub: 'u1', role: 'student' });
  const [h, , s] = token.split('.');
  const forged = Buffer.from(JSON.stringify({ sub: 'u1', role: 'admin', iat: 1, exp: 9999999999 })).toString('base64url');
  const { res, nextCalled } = runAuth({ authorization: `Bearer ${h}.${forged}.${s}` });
  assert.strictEqual(nextCalled, false);
  assert.strictEqual(res.statusCode, 401);
});

test('requireAuth: alg=none token is rejected', () => {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ sub: 'u1', role: 'admin' })).toString('base64url');
  const { res, nextCalled } = runAuth({ authorization: `Bearer ${header}.${payload}.` });
  assert.strictEqual(nextCalled, false);
  assert.strictEqual(res.statusCode, 401);
});

test('requireAuth: expired token -> 401 with session-expired message', () => {
  const expired = jwt.sign({ sub: 'u1', role: 'student' }, process.env.AUTH_SECRET, { algorithm: 'HS256', expiresIn: -10 });
  const { res, nextCalled } = runAuth({ authorization: `Bearer ${expired}` });
  assert.strictEqual(nextCalled, false);
  assert.strictEqual(res.statusCode, 401);
  assert.match(res.body.error, /expired/i);
});

test('token expiry: students 7d, lecturers and admins 12h', () => {
  const life = (role) => {
    const p = jwt.decode(signToken({ sub: 'x', role }));
    return p.exp - p.iat;
  };
  assert.strictEqual(life('student'), 7 * 24 * 3600);
  assert.strictEqual(life('lecturer'), 12 * 3600);
  assert.strictEqual(life('admin'), 12 * 3600);
});

test('requireRole: allows listed role, denies others and missing user (403)', () => {
  const mw = requireRole('lecturer', 'admin');
  let called = false;
  const ok = mockRes();
  mw({ user: { sub: 'l', role: 'lecturer' } }, ok, () => { called = true; });
  assert.strictEqual(called, true);

  for (const user of [{ sub: 's', role: 'student' }, undefined]) {
    called = false;
    const res = mockRes();
    mw({ user }, res, () => { called = true; });
    assert.strictEqual(called, false);
    assert.strictEqual(res.statusCode, 403);
    assert.strictEqual(res.body.error, 'You do not have access to this page');
  }
});

test('resolveStudentId: student gets own id; naming self is fine; other -> 403', () => {
  const req = { user: { sub: 's1', role: 'student' } };
  assert.strictEqual(resolveStudentId(req), 's1');
  assert.strictEqual(resolveStudentId(req, 's1'), 's1');
  assert.throws(() => resolveStudentId(req, 's2'), (e) => e.status === 403);
});

test('resolveStudentId: lecturer must name a student (400) and may name any', () => {
  const req = { user: { sub: 'l1', role: 'lecturer' } };
  assert.throws(() => resolveStudentId(req), (e) => e.status === 400);
  assert.throws(() => resolveStudentId(req, ''), (e) => e.status === 400);
  assert.strictEqual(resolveStudentId(req, 's9'), 's9');
});

test('resolveStudentId: admin -> 403', () => {
  const req = { user: { sub: 'a1', role: 'admin' } };
  assert.throws(() => resolveStudentId(req, 's1'), (e) => e.status === 403);
  assert.throws(() => resolveStudentId(req), (e) => e.status === 403);
});

function childSign(env) {
  const code = `
    const m = await import(${JSON.stringify(authUrl)});
    try { console.log(JSON.stringify({ token: m.signToken({ sub: 'x', role: 'admin' }) })); }
    catch (e) { console.log(JSON.stringify({ error: e.message })); }
  `;
  const childEnv = { ...process.env, ...env };
  delete childEnv.AUTH_SECRET;
  if (!('NODE_ENV' in env)) delete childEnv.NODE_ENV;
  const out = execFileSync(process.execPath, ['--input-type=module', '-e', code], {
    env: childEnv,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
  });
  return JSON.parse(out.trim().split('\n').pop());
}

test('production with no AUTH_SECRET refuses to sign tokens', () => {
  const r = childSign({ NODE_ENV: 'production' });
  assert.ok(r.error, 'expected signToken to throw');
  assert.match(r.error, /AUTH_SECRET/);
});

test(
  'AUTH_SECRET unset outside production must NOT silently fall back to a public default secret',
  { todo: 'AUDIT-B1 auth.js:12-21 falls back to hard-coded "dev-only-secret-change-me" when NODE_ENV != production; tokens are forgeable by anyone who reads the source' },
  () => {
    const r = childSign({});
    // Correct behaviour: refuse (throw) rather than issue a token signed with a well-known secret.
    assert.ok(r.error, 'expected signToken to throw when AUTH_SECRET is unset');
    if (r.token) {
      // Bug evidence: the token verifies with the public default.
      assert.doesNotThrow(() => jwt.verify(r.token, 'dev-only-secret-change-me'));
    }
  }
);
