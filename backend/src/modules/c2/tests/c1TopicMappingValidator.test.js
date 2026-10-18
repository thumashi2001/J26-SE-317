import test from 'node:test';
import assert from 'node:assert/strict';

import {
  validateApprovedTopicMapping,
  getApprovedMappingForModule,
} from '../services/c1TopicMappingValidator.js';

const moduleKey = 'database_systems';

const mapping = {
  object_relational_db: 'db_object_relational',
};

const verifiedTaxonomy = {
  taxonomies: [
    {
      module_key: moduleKey,
      verification_status: 'verified',
      topics: [
        {
          topic_id: 'db_object_relational',
          topic_name: 'Object-Relational Databases',
          subtopics: [],
        },
      ],
    },
  ],
};

test('accepts matching topics in a verified taxonomy', () => {
  const result = validateApprovedTopicMapping({
    moduleKey,
    mapping,
    taxonomy: verifiedTaxonomy,
  });

  assert.equal(result.valid, true);
});

test('rejects an unverified taxonomy', () => {
  const result = validateApprovedTopicMapping({
    moduleKey,
    mapping,
    taxonomy: {
      taxonomies: [
        {
          ...verifiedTaxonomy.taxonomies[0],
          verification_status: 'unverified',
        },
      ],
    },
  });

  assert.equal(result.valid, false);
});

test('rejects unknown C2 topic IDs', () => {
  const result = validateApprovedTopicMapping({
    moduleKey,
    mapping: {
      object_relational_db: 'invented_topic',
    },
    taxonomy: verifiedTaxonomy,
  });

  assert.equal(result.valid, false);
});

test('rejects unknown C1 topic keys', () => {
  const result = validateApprovedTopicMapping({
    moduleKey,
    mapping: {
      invented_c1_topic: 'db_object_relational',
    },
    taxonomy: verifiedTaxonomy,
  });

  assert.equal(result.valid, false);
});

test('rejects missing module taxonomy', () => {
  const result = validateApprovedTopicMapping({
    moduleKey,
    mapping,
    taxonomy: {
      taxonomies: [],
    },
  });

  assert.equal(result.valid, false);
});

test('does not expose invalid mappings', () => {
  const result = getApprovedMappingForModule(
    moduleKey,
    {
      mappingConfig: {
        modules: {
          [moduleKey]: mapping,
        },
      },
      taxonomy: {
        taxonomies: [],
      },
    }
  );

  assert.equal(result.valid, false);
  assert.deepEqual(result.mapping, {});
});