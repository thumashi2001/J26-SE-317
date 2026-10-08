import { connectDb } from './src/config/db.js';
import * as submissionSvc from './src/modules/c3/services/submissionService.js';
import dotenv from 'dotenv';
dotenv.config();

async function test() {
  const db = await connectDb();
  const sub = await db.collection('c3_submissions').find().toArray();
  const res = await db.collection('c3_results').find().toArray();
  console.log("Sub:", JSON.stringify(sub, null, 2));
  console.log("Res:", JSON.stringify(res, null, 2));
  process.exit(0);
}
test().catch(console.error);
