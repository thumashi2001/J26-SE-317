import { readFileSync } from 'node:fs';

import { getStudentMastery } from './c1MasteryAdapter.js';
import { generateMockExam } from './c2Service.js';

const mappingPath = new URL(
  '../config/c1TopicMapping.json',
  import.meta.url
);

export class C1PersonalizationError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = 'C1PersonalizationError';
    this.status = status;
  }
}

export function selectWeakTopics(
  mastery,
  moduleKey,
  mapping,
  threshold = 60
) {
  if (
    !mastery ||
    !Array.isArray(mastery.topics) ||
    typeof moduleKey !== 'string' ||
    !moduleKey.trim()
  ) {
    throw new C1PersonalizationError(
      'Invalid mastery or module data'
    );
  }

  const moduleMapping = mapping?.modules?.[moduleKey] ?? {};

  const selected = [];
  const seen = new Set();

  for (const entry of mastery.topics) {
    if (
      !entry ||
      typeof entry.topic !== 'string' ||
      typeof entry.masteryScore !== 'number' ||
      !Number.isFinite(entry.masteryScore) ||
      entry.masteryScore < 0 ||
      entry.masteryScore > 100 ||
      entry.masteryScore >= threshold
    ) {
      continue;
    }

    const mapped = moduleMapping[entry.topic];

    if (
      typeof mapped !== 'string' ||
      !mapped.trim() ||
      seen.has(mapped)
    ) {
      continue;
    }

    seen.add(mapped);

    selected.push({
      c1Topic: entry.topic,
      c2TopicId: mapped,
      masteryScore: entry.masteryScore,
    });
  }

  return selected;
}

export function evaluatePersonalization(
  exam,
  preferredTopics
) {
  const preferred = new Set(preferredTopics);

  const matchedQuestions = Array.isArray(exam.questions)
    ? exam.questions.filter(
        (question) =>
          typeof question.topic_id === 'string' &&
          preferred.has(question.topic_id)
      )
    : [];

  return {
    status:
      preferredTopics.length === 0
        ? 'no_topic_mapping'
        : matchedQuestions.length > 0
          ? 'applied'
          : 'no_verified_questions',
    matchedQuestionCount: matchedQuestions.length,
  };
}

export async function generateC1PersonalizedMock({
  db,
  studentId,
  moduleKey,
  targetMarks = 100,
  maxQuestions = 20,
  seed = 42,
  mapping = null,
  getMastery = getStudentMastery,
  generate = generateMockExam,
}) {
  const mastery = await getMastery(db, studentId);

  let topicMapping = mapping;

  if (topicMapping === null) {
    topicMapping = JSON.parse(
      readFileSync(mappingPath, 'utf8')
    );
  }

  const weakTopics = mastery.available
    ? selectWeakTopics(
        mastery,
        moduleKey,
        topicMapping
      )
    : [];

  const preferredTopics = weakTopics.map(
    (entry) => entry.c2TopicId
  );

  const exam = await generate({
    module_key: moduleKey,
    target_marks: targetMarks,
    max_questions: maxQuestions,
    preferred_topics: preferredTopics,
    difficulty: null,
    seed,
  });

  const evaluation = evaluatePersonalization(
    exam,
    preferredTopics
  );

  const status = !mastery.available
    ? 'unavailable'
    : evaluation.status;

  return {
    ...exam,
    personalization: {
      ...exam.personalization,
      method: 'c1_digital_twin',
      c1_diagnostic_integrated: true,
      applied: status === 'applied',
      status,
      reason:
        status === 'unavailable'
          ? mastery.reason
          : null,
      preferred_topics: preferredTopics,
      matched_question_count:
        evaluation.matchedQuestionCount,
      mastery_threshold: 60,
      mapping_source: 'explicit_reviewed_mapping',
    },
  };
}