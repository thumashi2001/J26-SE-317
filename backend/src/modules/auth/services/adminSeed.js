import { ADMIN_RE, normaliseId } from '../ids.js';
import { hashPassword } from './passwords.js';

// Creates the admin account, or resets its password if it already exists.
// The ID and password come from backend/.env, so they are never stored in the code or in GitHub.
export async function ensureAdmin(db, env) {
  const id = normaliseId(env.ADMIN_ID);
  const password = String(env.ADMIN_PASSWORD || '');
  if (!ADMIN_RE.test(id)) throw new Error('ADMIN_ID must be SLIITADMIN followed by 0 to 9 digits, for example SLIITADMIN1');
  if (password.length < 10) throw new Error('ADMIN_PASSWORD must be at least 10 characters');

  const staff = db.collection('staff');
  const fields = {
    name: String(env.ADMIN_NAME || 'Administrator').trim(),
    email: String(env.ADMIN_EMAIL || '').trim().toLowerCase() || null,
    role: 'admin',
    status: 'approved',
    password_hash: hashPassword(password),
  };
  const existing = await staff.findOne({ staff_id: id });
  if (existing) {
    await staff.updateOne({ staff_id: id }, { $set: fields });
    return { id, created: false };
  }
  await staff.insertOne({ staff_id: id, ...fields, created_at: new Date() });
  return { id, created: true };
}
