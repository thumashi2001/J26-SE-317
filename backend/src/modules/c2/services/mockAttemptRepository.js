/**
 * Mock Examination Attempt Repository — C2 Student Exam Intelligence
 * Persists student practice mock exam attempts to MongoDB (c2_mock_attempts)
 * with an in-memory fallback for test and offline environments.
 */

import { getDb } from '../../../config/db.js';

// In-memory fallback map keyed by attemptId
const memoryStore = new Map();

function getCollection(dbOverride) {
  if (dbOverride) {
    return dbOverride.collection('c2_mock_attempts');
  }

  try {
    const db = getDb();
    if (db) {
      return db.collection('c2_mock_attempts');
    }
  } catch {
    // Database not connected; fall back to in-memory store
  }

  return null;
}

export async function saveAttempt(attempt, dbOverride = null) {
  if (!attempt || typeof attempt !== 'object') {
    throw new Error('Attempt object is required');
  }

  const collection = getCollection(dbOverride);

  if (collection) {
    await collection.replaceOne(
      { attemptId: attempt.attemptId },
      attempt,
      { upsert: true }
    );
  } else {
    memoryStore.set(attempt.attemptId, { ...attempt });
  }

  return attempt;
}

export async function getAttemptById(attemptId, studentId, dbOverride = null) {
  if (!attemptId || typeof attemptId !== 'string') {
    return null;
  }

  const collection = getCollection(dbOverride);

  if (collection) {
    const query = { attemptId };
    if (studentId) {
      query.studentId = studentId;
    }
    const doc = await collection.findOne(query);
    if (!doc) return null;
    const { _id, ...rest } = doc;
    return rest;
  }

  const item = memoryStore.get(attemptId);
  if (!item) return null;
  if (studentId && item.studentId !== studentId) {
    return null;
  }
  return { ...item };
}

export async function listAttemptsByStudent(studentId, moduleKey = null, dbOverride = null) {
  if (!studentId || typeof studentId !== 'string') {
    return [];
  }

  const collection = getCollection(dbOverride);

  if (collection) {
    const query = { studentId };
    if (moduleKey) {
      query.moduleKey = moduleKey;
    }
    const cursor = collection.find(query).sort({ submittedAt: -1 });
    const docs = await cursor.toArray();
    return docs.map(({ _id, ...rest }) => rest);
  }

  const results = [];
  for (const item of memoryStore.values()) {
    if (item.studentId === studentId) {
      if (!moduleKey || item.moduleKey === moduleKey) {
        results.push({ ...item });
      }
    }
  }

  results.sort((a, b) => new Date(b.submittedAt) - new Date(a.submittedAt));
  return results;
}

export function resetMemoryStoreForTesting() {
  memoryStore.clear();
}
