// Quick check of the profile, usage and knowledge level rules, no database needed.
// Run from the backend folder:  node scripts/checkProfile.js
import assert from 'node:assert/strict';
import { getProfile, updateProfile, setAvatar, changePassword, recordUsage, getUsage } from '../src/modules/auth/services/profileService.js';
import { hashPassword } from '../src/modules/auth/services/passwords.js';
import { levelFrom, starsFor, labelFor } from '../src/modules/c1/services/levelService.js';

// a tiny in-memory stand-in for MongoDB
function fakeDb() {
  const data = {};
  const match = (row, f) => Object.entries(f).every(([k, v]) => row[k] === v);
  const col = (name) => ({
    findOne: async (f) => (data[name] ||= []).find((r) => match(r, f)) || null,
    find: (f = {}) => ({ toArray: async () => (data[name] ||= []).filter((r) => match(r, f)) }),
    insertOne: async (r) => { (data[name] ||= []).push(r); },
    updateOne: async (f, u, o = {}) => {
      const rows = (data[name] ||= []);
      let row = rows.find((r) => match(r, f));
      if (!row && o.upsert) { row = { ...f }; rows.push(row); }
      if (!row) return;
      Object.assign(row, u.$set || {});
      for (const k of Object.keys(u.$unset || {})) delete row[k];
      for (const [k, v] of Object.entries(u.$inc || {})) row[k] = (row[k] || 0) + v;
    },
  });
  return { collection: col };
}

const db = fakeDb();
await db.collection('students').insertOne({ student_id: 'IT00000001', name: 'Test Student', email: 'a@x.lk', semester: 'Y3S1', role: 'student', password_hash: hashPassword('oldpassword1') });
await db.collection('students').insertOne({ student_id: 'IT00000002', name: 'Other', email: 'b@x.lk', semester: 'Y3S1', role: 'student', password_hash: hashPassword('x12345678') });
const me = { sub: 'IT00000001', role: 'student' };

// profile: the ID is not part of the update, email must stay unique
assert.equal((await getProfile(db, me)).profile.id, 'IT00000001');
const up = await updateProfile(db, me, { name: 'New Name', email: 'NEW@x.lk', id: 'IT99999999' });
assert.equal(up.profile.id, 'IT00000001', 'the ID cannot be changed');
assert.equal(up.profile.email, 'new@x.lk');
await assert.rejects(() => updateProfile(db, me, { email: 'b@x.lk' }), /already used/);
await assert.rejects(() => updateProfile(db, me, { name: 'x' }), /full name/);

// avatar: only small image data URLs
await assert.rejects(() => setAvatar(db, me, 'https://evil.example/x.png'), /PNG, JPG or WebP/);
await assert.rejects(() => setAvatar(db, me, 'data:image/png;base64,' + 'A'.repeat(130000)), /too large/);
const withPic = await setAvatar(db, me, 'data:image/jpeg;base64,/9j/4AAQSkZJRg==');
assert.ok(withPic.profile.avatar.startsWith('data:image/jpeg'));
assert.equal((await setAvatar(db, me, null)).profile.avatar, null);

// password
await assert.rejects(() => changePassword(db, me, { currentPassword: 'wrong', newPassword: 'newpassword1' }), /not correct/);
await assert.rejects(() => changePassword(db, me, { currentPassword: 'oldpassword1', newPassword: 'short' }), /at least 8/);
await assert.rejects(() => changePassword(db, me, { currentPassword: 'oldpassword1', newPassword: 'oldpassword1' }), /different/);
assert.deepEqual(await changePassword(db, me, { currentPassword: 'oldpassword1', newPassword: 'newpassword1' }), { ok: true });

// usage: pings add up, two pings at the same moment count once, the streak counts days in a row
const t0 = new Date('2026-10-12T10:00:00');
await recordUsage(db, me, 30, t0);
await recordUsage(db, me, 30, new Date(t0.getTime() + 5000)); // too soon, ignored
let u = await recordUsage(db, me, 30, new Date(t0.getTime() + 35000));
assert.equal(u.todaySeconds, 60);
for (const d of [11, 10]) {
  await db.collection('usage_daily').insertOne({ user_id: me.sub, date: `2026-10-${d}`, seconds: 600 });
}
u = await getUsage(db, me, new Date('2026-10-12T12:00:00'));
assert.equal(u.streakDays, 3);
assert.equal(u.week.length, 7);
assert.equal(u.goalSeconds, 1800);

// knowledge level follows the twin
assert.equal(starsFor(0), 0.5); assert.equal(starsFor(100), 5); assert.equal(starsFor(50), 2.5);
assert.equal(labelFor(15), 'Beginner'); assert.equal(labelFor(85), 'Expert');
const now = new Date('2026-10-12T12:00:00');
const fresh = new Date(now.getTime() - 86400000).toISOString();
const low = levelFrom({ a: { score: 20, last_practiced: fresh, practice_sessions: 1 }, b: { score: 30, last_practiced: fresh, practice_sessions: 0 } }, now);
const high = levelFrom({ a: { score: 90, last_practiced: fresh, practice_sessions: 3 }, b: { score: 80, last_practiced: fresh, practice_sessions: 2 } }, now);
assert.ok(high.stars > low.stars, 'a better twin earns more stars');
assert.equal(high.nextLevelAt === null || high.nextLevelAt > high.score, true);
console.log('Profile checks passed. Low twin:', low.score, low.stars, low.label, '| high twin:', high.score, high.stars, high.label);
