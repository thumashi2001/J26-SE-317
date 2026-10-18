import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import {
  C1_TOPIC_REGISTRY,
  validateC1TopicMapping,
} from './c1TopicRegistry.js';

const DEFAULT_MAPPING_URL = new URL(
  '../config/c1TopicMapping.json',
  import.meta.url
);

const DEFAULT_TAXONOMY_URL = new URL(
  '../../../../../ai-services/c2/config/topic_taxonomies.json',
  import.meta.url
);

export function loadC1TopicMapping() {
  return JSON.parse(
    readFileSync(DEFAULT_MAPPING_URL, 'utf8')
  );
}

export function loadC2Taxonomy() {
  return JSON.parse(
    readFileSync(DEFAULT_TAXONOMY_URL, 'utf8')
  );
}

export function validateApprovedTopicMapping({
  moduleKey,
  mapping,
  taxonomy,
}) {
  const c1Validation = validateC1TopicMapping(
    moduleKey,
    mapping
  );

  const errors = [...c1Validation.errors];

  const moduleTaxonomy = taxonomy?.taxonomies?.find(
    (item) => item.module_key === moduleKey
  );

  if (!moduleTaxonomy) {
    errors.push(
      `C2 taxonomy missing for module: ${moduleKey}`
    );
  } else if (
    moduleTaxonomy.verification_status !== 'verified'
  ) {
    errors.push(
      `C2 taxonomy is not verified: ${moduleKey}`
    );
  }

  const approvedTopicIds = new Set(
    moduleTaxonomy?.topics?.map((topic) => topic.topic_id) ?? []
  );

  for (const [c1Key, c2Id] of Object.entries(mapping ?? {})) {
    if (!approvedTopicIds.has(c2Id)) {
      errors.push(
        `C2 topic is not approved: ${c1Key} -> ${c2Id}`
      );
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    module_key: moduleKey,
    mapped_count: Object.keys(mapping ?? {}).length,
    approved_topic_count: approvedTopicIds.size,
  };
}

export function getApprovedMappingForModule(
  moduleKey,
  {
    mappingConfig = loadC1TopicMapping(),
    taxonomy = loadC2Taxonomy(),
  } = {}
) {
  if (!Object.hasOwn(C1_TOPIC_REGISTRY, moduleKey)) {
    throw new Error(`Unknown C2 module: ${moduleKey}`);
  }

  const proposed = mappingConfig.modules?.[moduleKey] ?? {};

  const result = validateApprovedTopicMapping({
    moduleKey,
    mapping: proposed,
    taxonomy,
  });

  return {
    ...result,
    mapping: result.valid ? proposed : {},
  };
}