// Negative and positive tests for the environment checks of guard.mjs. They start child processes only; no database,
// backend or browser is contacted (phase 1 of the guard is environment-only), and the credentials below are dummies.
//   node --test reports/c3_remediation/ui_tests/guard.test.mjs
import test from 'node:test';
import assert from 'node:assert';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const guard = fileURLToPath(new URL('./guard.mjs', import.meta.url));
const GOOD = {
  C3_TEST_DB: 'adaptivelearnse_c3_guardtest',
  C3_TEST_MONGO_URI: 'mongodb://127.0.0.1:27017',
  C3_API_BASE: 'http://localhost:3100/api/v1',
  C3_WEB_BASE: 'http://localhost:5174',
  C3_TEST_PASSWORD: 'dummy-value-for-guard-test',
};
const run = (overrides, drop = []) => {
  const env = { PATH: process.env.PATH, SystemRoot: process.env.SystemRoot, ...GOOD, ...overrides };
  for (const k of drop) delete env[k];
  const r = spawnSync(process.execPath, ['--input-type=module', '-e', `import ${JSON.stringify('file:///' + guard.replace(/\\/g, '/'))}`], { env, encoding: 'utf8' });
  return { code: r.status, err: r.stderr, out: r.stdout };
};

test('a fully explicit loopback test environment is accepted (no connection is made)', () => {
  const r = run({});
  assert.strictEqual(r.code, 0, r.err);
});

for (const name of ['C3_TEST_DB', 'C3_TEST_MONGO_URI', 'C3_API_BASE', 'C3_TEST_PASSWORD']) {
  test(`missing ${name} is refused (no silent default)`, () => {
    const r = run({}, [name]);
    assert.strictEqual(r.code, 2);
    assert.match(r.err, new RegExp(`${name} is not set`));
  });
}

test('development / shared / arbitrary database names are refused', () => {
  for (const db of ['adaptivelearnse_dev', 'adaptivelearnse', 'adaptivelearnse_c3', 'ADAPTIVELEARNSE_C3_X', 'admin', 'adaptivelearnse_c3_x;drop', 'adaptivelearnse_c3_' + 'a'.repeat(60)]) {
    const r = run({ C3_TEST_DB: db });
    assert.strictEqual(r.code, 2, `accepted ${db}`);
    assert.match(r.err, /naming convention/);
  }
});

test('MongoDB URIs that are SRV, remote or carry credentials are refused, and credentials are never echoed', () => {
  for (const uri of ['mongodb+srv://cluster0.example.mongodb.net', 'mongodb://10.0.0.5:27017', 'mongodb://example.com:27017', 'mongodb://127.0.0.1:27017,db.example.com:27017', 'mongodb://user:secret-pw@127.0.0.1:27017']) {
    const r = run({ C3_TEST_MONGO_URI: uri });
    assert.strictEqual(r.code, 2, `accepted ${uri}`);
    assert.ok(!r.err.includes('secret-pw'), 'a credential was printed');
  }
});

test('non-loopback or non-http API / web base URLs are refused', () => {
  for (const [k, v] of [['C3_API_BASE', 'https://example.com/api/v1'], ['C3_API_BASE', 'http://192.168.1.10:3100/api/v1'], ['C3_API_BASE', 'http://localhost.evil.com/api'], ['C3_WEB_BASE', 'http://example.com'], ['C3_WEB_BASE', 'not a url']]) {
    const r = run({ [k]: v });
    assert.strictEqual(r.code, 2, `accepted ${k}=${v}`);
  }
});

test('the test password is never printed, even when a check fails', () => {
  const r = run({ C3_TEST_DB: 'adaptivelearnse_dev' });
  assert.ok(!r.err.includes(GOOD.C3_TEST_PASSWORD) && !r.out.includes(GOOD.C3_TEST_PASSWORD));
});
