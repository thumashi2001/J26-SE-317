// Run once from the backend folder:   node scripts/seedAdmin.js
// Reads ADMIN_ID, ADMIN_PASSWORD (and optionally ADMIN_NAME, ADMIN_EMAIL) from backend/.env.
// Safe to run again: it resets the admin password to the one in .env.
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const { connectDb } = await import('../src/config/db.js');
const { ensureAdmin } = await import('../src/modules/auth/services/adminSeed.js');

try {
  const db = await connectDb();
  const result = await ensureAdmin(db, process.env);
  console.log(result.created ? `Admin ${result.id} created.` : `Admin ${result.id} already existed. Password reset from .env.`);
  process.exit(0);
} catch (err) {
  console.error('Seed failed:', err.message);
  process.exit(1);
}
