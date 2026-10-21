/**
 * Minimal in-memory Mongo-like DB for C4 unit tests (no Atlas).
 */

function matches(doc, filter) {
  if (!filter || Object.keys(filter).length === 0) return true;
  return Object.entries(filter).every(([k, v]) => {
    if (v && typeof v === 'object' && !Array.isArray(v) && !(v instanceof Date)) {
      if ('$in' in v) return v.$in.includes(doc[k]);
      return false;
    }
    return doc[k] === v;
  });
}

function makeCollection(store) {
  return {
    async findOne(filter) {
      return store.find((d) => matches(d, filter)) || null;
    },
    async insertOne(doc) {
      store.push(structuredClone(doc));
      return { insertedId: doc._id || doc.path_id || doc.revision_id };
    },
    async replaceOne(filter, doc) {
      const i = store.findIndex((d) => matches(d, filter));
      if (i < 0) {
        store.push(structuredClone(doc));
        return { matchedCount: 0, modifiedCount: 0, upsertedCount: 1 };
      }
      store[i] = structuredClone(doc);
      return { matchedCount: 1, modifiedCount: 1 };
    },
    find(filter) {
      const rows = store.filter((d) => matches(d, filter));
      return {
        async toArray() {
          return rows.map((r) => structuredClone(r));
        },
      };
    },
    async countDocuments(filter) {
      return store.filter((d) => matches(d, filter)).length;
    },
  };
}

export function createMemoryDb() {
  const collections = new Map();
  return {
    collection(name) {
      if (!collections.has(name)) collections.set(name, []);
      return makeCollection(collections.get(name));
    },
    _dump(name) {
      return collections.get(name) || [];
    },
  };
}

/** Seed a minimal C1 twin so path creation can run without Atlas. */
export function seedTwin(db, studentId, mastery) {
  const now = new Date();
  return db.collection('mastery_state').insertOne({
    student_id: studentId,
    semester: 'Y3S2',
    diagnostic_completed: true,
    mastery,
    risk_level: null,
    updated_at: now,
  });
}
