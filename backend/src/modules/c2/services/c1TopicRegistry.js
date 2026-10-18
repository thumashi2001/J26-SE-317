import { MODULES } from '../../c1/data/content/index.js';

export const C1_TO_C2_MODULES = Object.freeze({
  SE3070: 'case_studies_software_engineering',
  SE3080: 'software_project_management',
  SE3050: 'user_experience_engineering',
  SE3060: 'database_systems',
  SE3020: 'distributed_systems',
  SE3030: 'software_architecture',
  SEPQM: 'software_engineering_process_quality_management',
  SE3040: 'application_frameworks',
});

export function buildC1TopicRegistry(modules = MODULES) {
  const registry = {};
  const seenTopics = new Set();

  for (const module of modules) {
    const moduleKey = C1_TO_C2_MODULES[module.module_code];

    if (!moduleKey) {
      throw new Error(
        `Unmapped C1 module: ${module.module_code}`
      );
    }

    if (registry[moduleKey]) {
      throw new Error(
        `Duplicate C2 module mapping: ${moduleKey}`
      );
    }

    const topics = {};

    for (const [topicKey, topic] of Object.entries(module.topics)) {
      if (seenTopics.has(topicKey)) {
        throw new Error(
          `Duplicate C1 topic key: ${topicKey}`
        );
      }

      seenTopics.add(topicKey);

      if (!topic.label?.trim()) {
        throw new Error(
          `Missing label for C1 topic: ${topicKey}`
        );
      }

      topics[topicKey] = {
        label: topic.label,
        lectures: topic.lectures ?? null,
      };
    }

    registry[moduleKey] = {
      c1_module_code: module.module_code,
      c1_module_name: module.module_name,
      c2_module_key: moduleKey,
      topics,
    };
  }

  return registry;
}

export const C1_TOPIC_REGISTRY = buildC1TopicRegistry();

export function getC1ModuleTopics(moduleKey) {
  return C1_TOPIC_REGISTRY[moduleKey] ?? null;
}

export function validateC1TopicMapping(moduleKey, mapping) {
  const module = getC1ModuleTopics(moduleKey);

  if (!module) {
    throw new Error(`Unknown C2 module: ${moduleKey}`);
  }

  if (
    mapping === null ||
    typeof mapping !== 'object' ||
    Array.isArray(mapping)
  ) {
    throw new Error('Topic mapping must be an object');
  }

  const errors = [];

  for (const [c1TopicKey, c2TopicId] of Object.entries(mapping)) {
    if (!Object.hasOwn(module.topics, c1TopicKey)) {
      errors.push(`Unknown C1 topic: ${c1TopicKey}`);
    }

    if (
      typeof c2TopicId !== 'string' ||
      !c2TopicId.trim()
    ) {
      errors.push(
        `Invalid C2 topic ID for: ${c1TopicKey}`
      );
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    mapped_count: Object.keys(mapping).length,
    total_c1_topics: Object.keys(module.topics).length,
  };
}