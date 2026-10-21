const STATUSES = ['pending', 'approved', 'rejected'];

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

const view = (s) => ({
  id: s.staff_id,
  name: s.name,
  email: s.email,
  status: s.status,
  registeredAt: s.created_at,
  reviewedBy: s.reviewed_by || null,
  reviewedAt: s.reviewed_at || null,
  note: s.review_note || '',
});

export async function getStats(db) {
  const lecturers = await db.collection('staff').find({ role: 'lecturer' }).toArray();
  const count = (status) => lecturers.filter((l) => l.status === status).length;
  const students = await db.collection('students').find({}).toArray();
  return {
    lecturers: { pending: count('pending'), approved: count('approved'), rejected: count('rejected'), total: lecturers.length },
    students: students.length,
  };
}

export async function listLecturers(db, status) {
  if (status && !STATUSES.includes(status)) throw httpError(400, 'status must be pending, approved or rejected');
  const query = { role: 'lecturer' };
  if (status) query.status = status;
  const rows = await db.collection('staff').find(query).toArray();
  rows.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  return { lecturers: rows.map(view) };
}

async function review(db, adminId, lecturerId, status, note) {
  const staff = db.collection('staff');
  const person = await staff.findOne({ staff_id: lecturerId, role: 'lecturer' });
  if (!person) throw httpError(404, `Lecturer ${lecturerId} not found`);
  await staff.updateOne(
    { staff_id: lecturerId },
    { $set: { status, reviewed_by: adminId, reviewed_at: new Date(), review_note: note } }
  );
  return { lecturer: view({ ...person, status, reviewed_by: adminId, reviewed_at: new Date(), review_note: note }) };
}

export const approveLecturer = (db, adminId, lecturerId) => review(db, adminId, lecturerId, 'approved', '');
export const rejectLecturer = (db, adminId, lecturerId, note) =>
  review(db, adminId, lecturerId, 'rejected', String(note || '').trim().slice(0, 300));
