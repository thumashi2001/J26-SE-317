import { connectDb, getDb } from './src/config/db.js';
import { seedDevAssessment } from './src/modules/c3/services/assessmentService.js';
import dotenv from 'dotenv';
dotenv.config();

async function run() {
  await connectDb();
  await getDb().collection('c3_assessments').deleteMany({});
  await seedDevAssessment();
  console.log("Deleted old assessments and seeded a new one with correct rubric!");
  process.exit(0);
}
run().catch(console.error);
