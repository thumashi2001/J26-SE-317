
import { getStudentMastery } from './c1MasteryAdapter.js';
import { generateMockExam } from './c2Service.js';
import {
  getApprovedMappingForModule,
} from './c1TopicMappingValidator.js';

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

  const matchedQuestions = Array.isArray(exam?.questions)
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
  getApprovedMapping = getApprovedMappingForModule,
}) {
  if (
    typeof moduleKey !== 'string' ||
    !moduleKey.trim()
  ) {
    throw new C1PersonalizationError(
      'A valid module key is required'
    );
  }

  const mastery = await getMastery(db, studentId);

  // The validator checks C1 topic keys against the C1
  // registry and C2 topic IDs against the verified taxonomy.
  //
  // Passing a mapping here is useful for tests, but it
  // does not bypass the taxonomy validation.
  const mappingOptions =
    mapping === null
      ? undefined
      : { mappingConfig: mapping };

  const mappingResult = await getApprovedMapping(
    moduleKey,
    mappingOptions
  );

  const approvedMapping =
    mappingResult.valid
      ? mappingResult.mapping
      : {};

  // selectWeakTopics expects a complete mapping config,
  // not a single module's mapping object.
  const topicMapping = {
    modules: {
      [moduleKey]: approvedMapping,
    },
  };

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

  let status;

  if (!mastery.available) {
    status = 'unavailable';
  } else if (!mappingResult.valid) {
    status = 'mapping_unverified';
  } else {
    status = evaluation.status;
  }

  let reason = null;

  if (status === 'unavailable') {
    reason = mastery.reason ?? 'C1 mastery is unavailable';
  } else if (status === 'mapping_unverified') {
    reason =
      'No approved C1-to-C2 topic mapping is available';
  } else if (status === 'no_topic_mapping') {
    reason =
      'No mapped C1 topics are below the mastery threshold';
  } else if (status === 'no_verified_questions') {
    reason =
      'No verified exam questions matched the weak topics';
  }

  return {
    ...exam,

    personalization: {
      ...exam.personalization,

      method: 'c1_digital_twin',

      c1_diagnostic_integrated: Boolean(
        mastery.available
      ),

      applied: status === 'applied',

      status,
      reason,

      preferred_topics: preferredTopics,

      matched_question_count:
        evaluation.matchedQuestionCount,

      mastery_threshold: 60,

      mapping_source: 'explicit_reviewed_mapping',

      mapping_validation: {
        valid: mappingResult.valid,
        errors: mappingResult.errors ?? [],
        mapped_count: mappingResult.mapped_count ?? 0,
        approved_topic_count:
          mappingResult.approved_topic_count ?? 0,
      },
    },
  };
}
