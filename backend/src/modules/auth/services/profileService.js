import { checkPassword, hashPassword } from './passwords.js';

// My profile for students, lecturers and the administrator.
// The ID can never be changed here. Name, email, password and picture can.

const MAX_AVATAR_CHARS = 120000; // the browser shrinks the picture first, so real pictures are much smaller
const AVATAR_RE = /^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/;
export const DAILY_GOAL_MIN = 30;
const MIN_PING_GAP_MS = 20000; // two tabs open at once must not count twice
const MAX_PING_SEC = 60;

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

// Find the account document for a logged-in user. Returns { col, filter, doc }.
async function account(db, user) {
  const isStudent = user.role === 'student';
  const col = db.collection(isStudent ? 'students' : 'staff');
  const filter = isStudent ? { student_id: user.sub } : { staff_id: user.sub };
  const doc = await col.findOne(filter);
  if (!doc) throw httpError(401, 'Please log in again');
  return { col, filter, doc };
}

const view = (doc, role) => ({
  id: doc.student_id || doc.staff_id,
  name: doc.name,
  email: doc.email,
  role,
  semester: doc.semester || null,
  status: doc.status || null,
  avatar: doc.avatar || null,
  joined: doc.created_at || null,
});

export async function getProfile(db, user) {
  const { doc } = await account(db, user);
  return { profile: view(doc, user.role) };
}

export async function updateProfile(db, user, body) {
  const { col, filter, doc } = await account(db, user);
  const name = body.name === undefined ? doc.name : String(body.name).trim();
  const email = body.email === undefined ? doc.email : String(body.email).trim().toLowerCase();
  if (name.length < 2) throw httpError(400, 'Please enter your full name');
  if (name.length > 80) throw httpError(400, 'That name is too long');
  if (!/^\S+@\S+\.\S+$/.test(email)) throw httpError(400, 'Please enter a valid email address');

  if (email !== doc.email) {
    const a = await db.collection('students').findOne({ email });
    const b = await db.collection('staff').findOne({ email });
    if (a || b) throw httpError(409, 'That email is already used by another account');
  }
  await col.updateOne(filter, { $set: { name, email, updated_at: new Date() } });
  return { profile: view({ ...doc, name, email }, user.role) };
}

// image is a small data URL made by the browser, or null to remove the picture.
export async function setAvatar(db, user, image) {
  const { col, filter, doc } = await account(db, user);
  if (image === null || image === undefined || image === '') {
    await col.updateOne(filter, { $unset: { avatar: '' } });
    return { profile: view({ ...doc, avatar: null }, user.role) };
  }
  if (typeof image !== 'string' || !AVATAR_RE.test(image)) throw httpError(400, 'Please choose a PNG, JPG or WebP picture');
  if (image.length > MAX_AVATAR_CHARS) throw httpError(413, 'That picture is too large. Choose a smaller one');
  await col.updateOne(filter, { $set: { avatar: image, updated_at: new Date() } });
  return { profile: view({ ...doc, avatar: image }, user.role) };
}

export async function changePassword(db, user, body) {
  const { col, filter, doc } = await account(db, user);
  const current = String(body.currentPassword || '');
  const next = String(body.newPassword || '');
  if (!checkPassword(current, doc.password_hash)) throw httpError(400, 'Your current password is not correct');
  if (next.length < 8) throw httpError(400, 'The new password must be at least 8 characters');
  if (next === current) throw httpError(400, 'Choose a password that is different from the current one');
  await col.updateOne(filter, { $set: { password_hash: hashPassword(next), updated_at: new Date() } });
  return { ok: true };
}

// ---- time spent on the web app, per day
const dayKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

// The browser sends a ping every 30 seconds while the tab is open and visible.
export async function recordUsage(db, user, seconds, now = new Date()) {
  const sec = Math.max(0, Math.min(MAX_PING_SEC, Math.round(Number(seconds) || 0)));
  const col = db.collection('usage_daily');
  const key = { user_id: user.sub, date: dayKey(now) };
  const row = await col.findOne(key);
  const last = row && row.last_ping ? new Date(row.last_ping).getTime() : 0;
  if (sec > 0 && now.getTime() - last >= MIN_PING_GAP_MS) {
    await col.updateOne(key, { $inc: { seconds: sec }, $set: { last_ping: now.toISOString(), role: user.role } }, { upsert: true });
  }
  return getUsage(db, user, now);
}

export async function getUsage(db, user, now = new Date()) {
  const rows = await db.collection('usage_daily').find({ user_id: user.sub }).toArray();
  const by = Object.fromEntries(rows.map((r) => [r.date, r.seconds || 0]));
  const week = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
    week.push({ date: dayKey(d), seconds: by[dayKey(d)] || 0, today: i === 0 });
  }
  // streak: consecutive days with at least 1 minute, counting back from today (or yesterday if today has none yet)
  let streak = 0;
  let cursor = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if ((by[dayKey(cursor)] || 0) < 60) cursor = new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate() - 1);
  while ((by[dayKey(cursor)] || 0) >= 60 && streak < 3650) {
    streak += 1;
    cursor = new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate() - 1);
  }
  return {
    todaySeconds: by[dayKey(now)] || 0,
    goalSeconds: DAILY_GOAL_MIN * 60,
    totalSeconds: Object.values(by).reduce((a, b) => a + b, 0),
    daysUsed: Object.values(by).filter((s) => s >= 60).length,
    streakDays: streak,
    week,
  };
}
