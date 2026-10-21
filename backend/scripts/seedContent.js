// Run from the backend folder:   node scripts/seedContent.js
// Loads the real, slide-based questions into MongoDB:
//   question_bank  (diagnostic questions, per semester)
//   practice_bank  (practice questions, per topic)
// Safe to run again: existing questions are updated, not duplicated.
// It asks before it removes anything. Nothing is removed unless you type the word it asks for.
import path from 'path';
import readline from 'readline';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.join(__dirname, '..', '.env') });

const { connectDb } = await import('../src/config/db.js');
const { TOPICS } = await import('../src/modules/c1/data/content/index.js');

const LETTERS = ['A', 'B', 'C', 'D'];
const SEMESTERS = [...new Set(Object.values(TOPICS).map((t) => t.semester))];

function diagnosticDocs() {
  const docs = [];
  for (const [topic, t] of Object.entries(TOPICS)) {
    t.diagnostic.forEach((q, i) => {
      docs.push({
        question_id: `DQ-${topic}-${String(i + 1).padStart(2, '0')}`,
        module_code: t.module_code,
        topic,
        semester: t.semester,
        question_text: q.text,
        options: Object.fromEntries(q.options.map((o, k) => [LETTERS[k], o])),
        correct_answer: LETTERS[q.correct[0]],
        explanation: q.why,
      });
    });
  }
  return docs;
}

// Same documents that practiceService.seedAll writes (one per practice question).
function practiceDocs() {
  const docs = [];
  for (const [topic, t] of Object.entries(TOPICS)) {
    t.practice.forEach((q, i) => {
      docs.push({
        question_id: `PQ-${topic}-${String(i + 1).padStart(2, '0')}`,
        topic,
        question_text: q.text,
        options: q.options,
        correct: q.correct,
        explanation: q.why,
        tip: q.tip,
      });
    });
  }
  return docs;
}

// Saves in a few big batches instead of hundreds of single writes, and tries again if the connection drops.
async function saveAll(col, docs, label) {
  const BATCH = 60;
  for (let i = 0; i < docs.length; i += BATCH) {
    const part = docs.slice(i, i + BATCH);
    const ops = part.map((d) => ({ replaceOne: { filter: { question_id: d.question_id }, replacement: d, upsert: true } }));
    for (let attempt = 1; ; attempt++) {
      try {
        await col.bulkWrite(ops, { ordered: false });
        break;
      } catch (err) {
        if (attempt >= 5) throw err;
        console.log(`  ${label}: connection problem (${err.message}), trying again (${attempt}/4)...`);
        await new Promise((r) => setTimeout(r, 1500 * attempt));
      }
    }
    console.log(`  ${label}: ${Math.min(i + BATCH, docs.length)} of ${docs.length} saved`);
  }
}

const ask = (question) =>
  new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question(question, (answer) => { rl.close(); resolve(answer.trim()); });
  });

try {
  const db = await connectDb();
  const docs = diagnosticDocs();

  await saveAll(db.collection('question_bank'), docs, 'Diagnostic bank');
  console.log(`Diagnostic bank: ${docs.length} questions saved (${Object.keys(TOPICS).length} topics).`);

  const pdocs = practiceDocs();
  await saveAll(db.collection('practice_bank'), pdocs, 'Practice bank');
  console.log(`Practice bank: ${pdocs.length} questions saved.`);

  // 1) Old sample questions
  const keep = docs.map((d) => d.question_id);
  const oldDiag = await db.collection('question_bank').countDocuments({ semester: { $in: SEMESTERS }, question_id: { $nin: keep } });
  const keepPractice = new Set(Object.entries(TOPICS).flatMap(([k, t]) => t.practice.map((_, i) => `PQ-${k}-${String(i + 1).padStart(2, '0')}`)));
  const oldPractice = (await db.collection('practice_bank').find({}).toArray()).filter((r) => !keepPractice.has(r.question_id));
  if (oldDiag + oldPractice.length > 0) {
    console.log(`\nFound ${oldDiag} old sample diagnostic questions and ${oldPractice.length} old sample practice questions.`);
    const a = await ask('Type REMOVE to delete the old sample questions (or press Enter to keep them): ');
    if (a === 'REMOVE') {
      const r1 = await db.collection('question_bank').deleteMany({ semester: { $in: SEMESTERS }, question_id: { $nin: keep } });
      const r2 = await db.collection('practice_bank').deleteMany({ question_id: { $in: oldPractice.map((r) => r.question_id) } });
      console.log(`Removed ${r1.deletedCount} diagnostic and ${r2.deletedCount} practice sample questions.`);
    } else {
      console.log('Kept. Note: students will still be given the old sample topics until they are removed.');
    }
  }

  // 2) Test students' twin data (old topics no longer exist)
  const COLS = ['mastery_state', 'mastery_history', 'learning_events', 'diagnostic_assignments', 'practice_sessions', 'alerts'];
  const counts = {};
  for (const c of COLS) counts[c] = await db.collection(c).countDocuments({});
  console.log('\nTwin data currently in the database:', counts);
  const b = await ask('Type RESET to clear ALL twin data above for every student so everyone starts fresh with the real topics (or press Enter to skip): ');
  if (b === 'RESET') {
    for (const c of COLS) await db.collection(c).deleteMany({});
    console.log('Twin data cleared. Student accounts are kept. Each student will take the new diagnostic test.');
  } else {
    console.log('Skipped. Students who already finished the diagnostic keep their old topics.');
  }
  process.exit(0);
} catch (err) {
  console.error('Seed failed:', err.message);
  process.exit(1);
}
