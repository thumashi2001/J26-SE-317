import { signToken } from '../../../middleware/auth.js';
import { STUDENT_RE, LECTURER_RE, kindOf, normaliseId } from '../ids.js';
import { hashPassword, checkPassword } from './passwords.js';

const SEMESTERS = ['Y3S1', 'Y3S2'];
const BAD_LOGIN = 'ID or password is incorrect';

function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code; // lets the website show a designed notice for this case
  return err;
}

// What the browser is allowed to see about a user. Never the password hash.
const publicStudent = (s) => ({
  id: s.student_id,
  student_id: s.student_id,
  name: s.name,
  email: s.email,
  role: s.role || 'student',
  semester: s.semester,
});

const publicStaff = (s) => ({
  id: s.staff_id,
  name: s.name,
  email: s.email,
  role: s.role,
  status: s.status,
});

function checkCommon({ name, email, password }) {
  if (name.length < 2) throw httpError(400, 'Please enter your full name');
  if (!/^\S+@\S+\.\S+$/.test(email)) throw httpError(400, 'Please enter a valid email address');
  if (password.length < 8) throw httpError(400, 'Password must be at least 8 characters');
}

async function emailTaken(db, email) {
  const a = await db.collection('students').findOne({ email });
  const b = await db.collection('staff').findOne({ email });
  return !!(a || b);
}

export async function register(db, body) {
  const studentId = normaliseId(body.studentId);
  const name = String(body.name || '').trim();
  const email = String(body.email || '').trim().toLowerCase();
  const semester = body.semester;
  const password = String(body.password || '');

  if (!STUDENT_RE.test(studentId)) throw httpError(400, 'Please enter a valid student ID');
  checkCommon({ name, email, password });
  if (!SEMESTERS.includes(semester)) throw httpError(400, 'Choose Year 3 Semester 1 or Semester 2');

  const students = db.collection('students');
  if (await students.findOne({ student_id: studentId })) throw httpError(409, 'That student ID is already registered');
  if (await emailTaken(db, email)) throw httpError(409, 'That email is already registered');

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
  return { token: signToken({ sub: studentId, role: 'student' }), user: publicStudent(student) };
}

// Lecturers register, but cannot log in until an admin approves them.
export async function registerLecturer(db, body) {
  const lecturerId = normaliseId(body.lecturerId);
  const name = String(body.name || '').trim();
  const email = String(body.email || '').trim().toLowerCase();
  const password = String(body.password || '');

  if (!LECTURER_RE.test(lecturerId)) throw httpError(400, 'Please enter a valid lecturer ID');
  checkCommon({ name, email, password });

  const staff = db.collection('staff');
  if (await staff.findOne({ staff_id: lecturerId })) throw httpError(409, 'That lecturer ID is already registered');
  if (await emailTaken(db, email)) throw httpError(409, 'That email is already registered');

  const lecturer = {
    staff_id: lecturerId,
    name,
    email,
    role: 'lecturer',
    status: 'pending',
    password_hash: hashPassword(password),
    created_at: new Date(),
  };
  await staff.insertOne(lecturer);
  return {
    pending: true,
    message: 'Your registration was sent to the administrator. You can log in once it is approved.',
    user: publicStaff(lecturer),
  };
}

export async function login(db, body) {
  const id = normaliseId(body.userId || body.studentId);
  const password = String(body.password || '');
  if (!id || !password) throw httpError(400, 'Enter your ID and password');

  const kind = kindOf(id);
  // Same message for an unknown ID, a wrong password and an ID of the wrong shape,
  // so nobody can probe for valid IDs.
  if (!kind) throw httpError(401, BAD_LOGIN);

  if (kind === 'student') {
    const student = await db.collection('students').findOne({ student_id: id });
    if (!student || !checkPassword(password, student.password_hash)) throw httpError(401, BAD_LOGIN);
    return { token: signToken({ sub: id, role: student.role || 'student' }), user: publicStudent(student) };
  }

  const person = await db.collection('staff').findOne({ staff_id: id });
  if (!person || !checkPassword(password, person.password_hash)) throw httpError(401, BAD_LOGIN);
  // Only someone who knows the password learns the approval status.
  if (person.status === 'pending') throw httpError(403, 'Your account is waiting for the administrator to approve it.', 'pending_approval');
  if (person.status === 'rejected') throw httpError(403, 'Your registration was not approved. Please contact the administrator.', 'not_approved');
  return { token: signToken({ sub: id, role: person.role }), user: publicStaff(person) };
}

export async function me(db, user) {
  if (user.role === 'student') {
    const student = await db.collection('students').findOne({ student_id: user.sub });
    if (!student) throw httpError(401, 'Please log in again');
    return { user: publicStudent(student) };
  }
  const person = await db.collection('staff').findOne({ staff_id: user.sub });
  if (!person) throw httpError(401, 'Please log in again');
  if (person.status !== 'approved') throw httpError(403, 'Your account is not approved');
  return { user: publicStaff(person) };
}
