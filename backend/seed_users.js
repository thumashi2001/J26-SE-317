import { MongoClient } from 'mongodb';
import crypto from 'node:crypto';
import dotenv from 'dotenv';
dotenv.config();

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return `scrypt$${salt}$${hash}`;
}

async function seed() {
  const uri = process.env.MONGO_URI;
  if (!uri) throw new Error('MONGO_URI is not set');
  const client = new MongoClient(uri);
  await client.connect();
  const db = client.db(process.env.MONGO_DB || 'adaptivelearnse_dev');
  const students = db.collection('students');

  const users = [
    {
      student_id: 'IT10000001',
      name: 'Test Student',
      email: 'student1@test.com',
      role: 'student',
      semester: 'Y3S1',
      password_hash: hashPassword('password123'),
      created_at: new Date()
    },
    {
      student_id: 'IT20000001',
      name: 'Test Lecturer',
      email: 'lecturer1@test.com',
      role: 'lecturer',
      semester: 'Y3S1',
      password_hash: hashPassword('password123'),
      created_at: new Date()
    },
    {
      student_id: 'IT30000001',
      name: 'Test Admin',
      email: 'admin1@test.com',
      role: 'admin',
      semester: 'Y3S1',
      password_hash: hashPassword('password123'),
      created_at: new Date()
    }
  ];

  for (const user of users) {
    await students.updateOne(
      { student_id: user.student_id },
      { $set: user },
      { upsert: true }
    );
    console.log(`Seeded user: ${user.student_id} / password123 (Role: ${user.role})`);
  }

  await client.close();
}

seed().catch(console.error);
