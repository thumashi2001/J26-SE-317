import crypto from 'node:crypto';
import { signToken } from '../../../middleware/auth.js';

const SEMESTERS = ['Y3S1', 'Y3S2'];

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

// ---- passwords: scrypt with a random salt, no extra packages needed ----
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return `scrypt$${salt}$${hash}`;
}

function checkPassword(password, stored) {
  if (!stored) return false;
  const [scheme, salt, hash] = stored.split('$');
  if (scheme !== 'scrypt' || !salt || !hash) return false;
  const given = crypto.scryptSync(password, salt, 64);
  const expected = Buffer.from(hash, 'hex');
  return given.length === expected.length && crypto.timingSafeEqual(given, expected);
}

const publicUser = (s) => ({
  student_id: s.student_id,
  name: s.name,
  email: s.email,
  role: s.role,
  semester: s.semester,
});

export async function register(db, body) {
  const studentId = String(body.studentId || '').trim().toUpperCase();
  const name = String(body.name || '').trim();
  const email = String(body.email || '').trim().toLowerCase();
  const semester = body.semester;
  const password = String(body.password || '');

  if (!/^[A-Z0-9]{4,20}$/.test(studentId)) throw httpError(400, 'Student ID must be 4 to 20 letters or numbers');
  if (name.length < 2) throw httpError(400, 'Please enter your full name');
  if (!/^\S+@\S+\.\S+$/.test(email)) throw httpError(400, 'Please enter a valid email address');
  if (!SEMESTERS.includes(semester)) throw httpError(400, 'Choose Year 3 Semester 1 or Semester 2');
  if (password.length < 8) throw httpError(400, 'Password must be at least 8 characters');

  const students = db.collection('students');
  if (await students.findOne({ student_id: studentId })) throw httpError(409, 'That student ID is already registered');
  if (await students.findOne({ email })) throw httpError(409, 'That email is already registered');

  const student = {
    student_id: studentId,
    name,
    email,
    role: 'student',
    semester,
    enrolled_modules: [],
    password_hash: hashPassword(password),
    created_at: new Date(),
  };
  await students.insertOne(student);
  return { token: signToken({ sub: studentId, role: 'student' }), user: publicUser(student) };
}

export async function login(db, body) {
  const studentId = String(body.studentId || '').trim().toUpperCase();
  const password = String(body.password || '');
  if (!studentId || !password) throw httpError(400, 'Enter your student ID and password');

  const student = await db.collection('students').findOne({ student_id: studentId });
  // Same message for unknown ID and wrong password so nobody can probe for valid IDs.
  if (!student || !checkPassword(password, student.password_hash)) {
    throw httpError(401, 'Student ID or password is incorrect');
  }
  return { token: signToken({ sub: studentId, role: student.role }), user: publicUser(student) };
}

export async function me(db, studentId) {
  const student = await db.collection('students').findOne({ student_id: studentId });
  if (!student) throw httpError(401, 'Please log in again');
  return { user: publicUser(student) };
}
