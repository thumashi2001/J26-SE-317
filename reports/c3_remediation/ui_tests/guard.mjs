// Fail-closed safety guard shared by e2e.mjs, functional.mjs and capture.mjs.
//
// These scripts WRITE to the database behind the backend they drive. They must therefore never run against a
// shared or development database. Nothing here chooses a database for you: every setting below must be provided
// explicitly, and the run is refused (exit code 2) when any check fails.
//
//   C3_TEST_DB          disposable local database name, must match ^adaptivelearnse_c3_[a-z0-9_]{2,40}$
//   C3_TEST_MONGO_URI   mongodb://127.0.0.1:27017 (loopback only, no credentials, never mongodb+srv)
//   C3_API_BASE         e.g. http://localhost:3100/api/v1   (loopback only)
//   C3_WEB_BASE         e.g. http://localhost:5174          (loopback only; browser suite only)
//   C3_TEST_PASSWORD    password of the seeded test accounts (never printed)
//
// Phase 1 (this module is imported): environment-only checks, no network or database access.
// Phase 2 (verifyIsolation(), called before the first write): proves that the backend is reading the SAME local
// database as the test setup, using a canary student that exists only there, and aborts otherwise. It never falls back to backend/.env and
// never drops or cleans up any database.
import { createRequire } from 'node:module';
import crypto from 'node:crypto';

const DB_PATTERN = /^adaptivelearnse_c3_[a-z0-9_]{2,40}$/;
const LOOPBACK = new Set(['localhost', '127.0.0.1', '[::1]', '::1']);

function refuse(message) {
  console.error(`[c3-test-guard] REFUSING TO RUN: ${message}`);
  console.error('[c3-test-guard] See ui_tests/README.md for the required environment variables.');
  process.exit(2);
}

function requireEnv(name) {
  const value = process.env[name];
  if (value === undefined || value.trim() === '') refuse(`${name} is not set (no default is used on purpose)`);
  return value.trim();
}

export function assertLoopbackHttp(urlText, name) {
  let u;
  try { u = new URL(urlText); } catch { refuse(`${name} is not a valid URL`); }
  if (u.protocol !== 'http:') refuse(`${name} must use http:// on the loopback interface`);
  if (!LOOPBACK.has(u.hostname)) refuse(`${name} must point to localhost/127.0.0.1 (found host "${u.hostname}")`);
  return urlText.replace(/\/+$/, '');
}

export function assertLocalMongoUri(uri) {
  if (!uri.startsWith('mongodb://')) refuse('C3_TEST_MONGO_URI must start with mongodb:// (mongodb+srv:// is never allowed)');
  const rest = uri.slice('mongodb://'.length);
  const authority = rest.split(/[/?]/)[0];
  if (authority.includes('@')) refuse('C3_TEST_MONGO_URI must not contain credentials (the test database needs none)');
  for (const hostPort of authority.split(',')) {
    const host = hostPort.startsWith('[') ? hostPort.slice(0, hostPort.indexOf(']') + 1) : hostPort.split(':')[0];
    if (!LOOPBACK.has(host)) refuse(`C3_TEST_MONGO_URI host "${host}" is not loopback`);
  }
  return uri;
}

export function assertTestDbName(name) {
  if (!DB_PATTERN.test(name)) refuse(`C3_TEST_DB "${name}" does not match the disposable test naming convention ${DB_PATTERN}`);
  return name;
}

// ---- Phase 1: environment only ----------------------------------------------------------------------------------
export const config = {
  dbName: assertTestDbName(requireEnv('C3_TEST_DB')),
  mongoUri: assertLocalMongoUri(requireEnv('C3_TEST_MONGO_URI')),
  apiBase: assertLoopbackHttp(requireEnv('C3_API_BASE'), 'C3_API_BASE'),
  webBase: process.env.C3_WEB_BASE ? assertLoopbackHttp(process.env.C3_WEB_BASE, 'C3_WEB_BASE') : null,
  password: requireEnv('C3_TEST_PASSWORD'), // value is never printed
};

// Resolves the mongodb driver from the repository (backend/package.json) unless C3_BACKEND_DIR is given.
export function loadMongoDriver() {
  const base = process.env.C3_BACKEND_DIR
    ? new URL('file:///' + process.env.C3_BACKEND_DIR.replace(/\\/g, '/').replace(/\/?$/, '/') + 'package.json')
    : new URL('../../../backend/package.json', import.meta.url);
  try { return createRequire(base)('mongodb'); } catch { refuse('cannot load the mongodb driver; run from the repository or set C3_BACKEND_DIR to the backend folder'); }
}

export async function connectTestDb() {
  const { MongoClient } = loadMongoDriver();
  const client = new MongoClient(config.mongoUri, { serverSelectionTimeoutMS: 5000 });
  try { await client.connect(); } catch { refuse('cannot reach the local test MongoDB'); }
  return { client, db: client.db(config.dbName) };
}

// ---- Phase 2: prove the backend uses the same database -----------------------------------------------------------
// The proof uses a throw-away CANARY student that exists only in the local test database, with a random password.
// The test accounts' real credentials are never sent to a backend whose database is still unproven: a backend that
// was started without local MONGO_URI/MONGO_DB (and would therefore use backend/.env) does not know the canary, so
// the lookup simply fails and the run is refused. The canary is removed again in all cases.
function scryptHash(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  return `scrypt$${salt}$${crypto.scryptSync(password, salt, 64).toString('hex')}`; // same format as backend/seed_users.js
}

export async function verifyIsolation({ needsWeb = false } = {}) {
  if (needsWeb && !config.webBase) refuse('C3_WEB_BASE is not set (required for the browser suite)');
  const { client, db } = await connectTestDb();
  // The backend only accepts student IDs shaped IT + 8 digits; use a random one and never reuse an existing account.
  const id = `IT99${String(crypto.randomInt(0, 1_000_000)).padStart(6, '0')}`;
  const canaryPassword = crypto.randomBytes(18).toString('hex');
  let inserted = false;
  let problem = null; // refuse() exits the process immediately, so record the problem and clean the canary up first
  try {
    // The database must already have been seeded with the test accounts (reads only).
    const student = await db.collection('students').findOne({ student_id: 'IT10000001' }, { projection: { _id: 1 } });
    if (!student) problem = `database ${config.dbName} has no seeded test student (seed the local test database first)`;
    else if (await db.collection('students').findOne({ student_id: id }, { projection: { _id: 1 } })) problem = 'the random canary id already exists; run again';
    if (!problem) {
      await db.collection('students').insertOne({
        student_id: id, name: 'Isolation canary', email: `${id.toLowerCase()}@guard.invalid`, role: 'student', semester: 'Y3S1',
        password_hash: scryptHash(canaryPassword), is_guard_canary: true, created_at: new Date(),
      });
      inserted = true;
      const login = await fetch(`${config.apiBase}/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ userId: id, password: canaryPassword }),
      }).catch(() => null);
      if (!login || !login.ok) {
        problem = `the backend does not know the canary account stored in ${config.dbName}: it is unreachable or it is not using that database. Start it with MONGO_URI/MONGO_DB set to the same local test database; nothing was run`;
      }
    }
  } finally {
    if (inserted) await db.collection('students').deleteOne({ student_id: id, is_guard_canary: true }).catch(() => {});
    await client.close().catch(() => {});
  }
  if (problem) refuse(problem);
  console.log(`[c3-test-guard] isolation verified for local database ${config.dbName}`);
}
