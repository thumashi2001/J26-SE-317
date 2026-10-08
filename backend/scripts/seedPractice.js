// Run from the backend folder:   node scripts/seedPractice.js
// Copies every practice question from src/modules/c1/data/practiceQuestions.js into the
// practice_bank collection. Safe to run again: existing questions are updated, not duplicated.
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const { connectDb } = await import('../src/config/db.js');
const { seedAll } = await import('../src/modules/c1/services/practiceService.js');

try {
  const db = await connectDb();
  const total = await seedAll(db);
  console.log(`Practice bank ready: ${total} questions.`);
  process.exit(0);
} catch (err) {
  console.error('Seed failed:', err.message);
  process.exit(1);
}
