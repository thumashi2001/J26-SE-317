import { MongoClient } from 'mongodb';

let db = null;

export async function connectDb() {
  const uri = process.env.MONGO_URI;
  if (!uri) throw new Error('MONGO_URI is not set (check backend/.env)');
  const client = new MongoClient(uri);
  await client.connect();
  db = client.db(process.env.MONGO_DB || 'adaptivelearnse_dev');
  console.log('MongoDB connected:', db.databaseName);
  return db;
}

export function getDb() {
  if (!db) throw new Error('Database not connected');
  return db;
}

// Lets automated tests plug in a fake database. Not used by the app itself.
export function setDb(testDb) {
  db = testDb;
}