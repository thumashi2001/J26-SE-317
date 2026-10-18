import { getTwin } from '../../c1/services/diagnosticService.js';

export class C1MasteryAdapterError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = 'C1MasteryAdapterError';
    this.status = status;
  }
}

export function normalizeMastery(twin) {
  if (!twin || typeof twin !== 'object') {
    throw new C1MasteryAdapterError('Invalid C1 Digital Twin data', 502);
  }

  if (!twin.diagnosticCompleted) {
    return {
      available: false,
      reason: 'diagnostic_not_completed',
      topics: [],
    };
  }

  const mastery = twin.mastery;

  if (
    !mastery ||
    typeof mastery !== 'object' ||
    Array.isArray(mastery)
  ) {
    throw new C1MasteryAdapterError('Invalid C1 mastery structure', 502);
  }

  const topics = Object.entries(mastery)
    .filter(([topic, entry]) => {
      return (
        typeof topic === 'string' &&
        topic.trim().length > 0 &&
        entry &&
        typeof entry === 'object' &&
        !Array.isArray(entry) &&
        typeof entry.score === 'number' &&
        Number.isFinite(entry.score) &&
        entry.score >= 0 &&
        entry.score <= 100
      );
    })
    .map(([topic, entry]) => ({
      topic,
      masteryScore: entry.score,
    }))
    .sort((a, b) =>
      a.masteryScore - b.masteryScore ||
      a.topic.localeCompare(b.topic)
    );

  return {
    available: topics.length > 0,
    reason: topics.length > 0 ? null : 'no_valid_mastery_scores',
    topics,
  };
}

export async function getStudentMastery(db, studentId) {
  if (typeof studentId !== 'string' || !studentId.trim()) {
    throw new C1MasteryAdapterError('Valid student ID required');
  }

  const twin = await getTwin(db, studentId);

  return {
    studentId: twin.studentId,
    semester: twin.semester ?? null,
    updatedAt: twin.updatedAt ?? null,
    ...normalizeMastery(twin),
  };
}