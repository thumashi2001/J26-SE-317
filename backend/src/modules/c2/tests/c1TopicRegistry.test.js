import test from 'node:test';
import assert from 'node:assert/strict';

import {
  C1_TOPIC_REGISTRY,
  C1_TO_C2_MODULES,
  buildC1TopicRegistry,
  getC1ModuleTopics,
  validateC1TopicMapping,
} from '../services/c1TopicRegistry.js';

test('maps all eight C1 modules to C2', () => {
  assert.equal(Object.keys(C1_TOPIC_REGISTRY).length, 8);
  assert.equal(Object.keys(C1_TO_C2_MODULES).length, 8);
});

test('maps Database Systems to its correct C1 module', () => {
  const module = getC1ModuleTopics('database_systems');

  assert.equal(module.c1_module_code, 'SE3060');
  assert.equal(module.c2_module_key, 'database_systems');
  assert.equal(Object.keys(module.topics).length, 6);

  assert.ok(module.topics.object_relational_db);
  assert.ok(module.topics.transactions_concurrency);
});

test('contains the 46 C1 topics across eight modules', () => {
  const total = Object.values(C1_TOPIC_REGISTRY)
    .reduce(
      (sum, module) => sum + Object.keys(module.topics).length,
      0
    );

  assert.equal(total, 46);
});

test('rejects unknown C1 topic keys', () => {
  const result = validateC1TopicMapping('database_systems', {
    invented_topic: 'some_c2_topic',
  });

  assert.equal(result.valid, false);
  assert.match(result.errors[0], /Unknown C1 topic/);
});

test('accepts structurally valid mappings', () => {
  const result = validateC1TopicMapping('database_systems', {
    object_relational_db: 'object_relational_db',
  });

  assert.equal(result.valid, true);
  assert.equal(result.mapped_count, 1);
});

test('rejects empty C2 topic IDs', () => {
  const result = validateC1TopicMapping('database_systems', {
    object_relational_db: '',
  });

  assert.equal(result.valid, false);
});

test('rejects unknown modules', () => {
  assert.throws(
    () => validateC1TopicMapping('unknown_module', {}),
    /Unknown C2 module/
  );
});

test('rejects duplicate C1 topic keys', () => {
  const modules = [
    {
      module_code: 'SE3060',
      module_name: 'Database Systems',
      topics: {
        duplicate_topic: { label: 'First topic' },
      },
    },
    {
      module_code: 'SE3020',
      module_name: 'Distributed Systems',
      topics: {
        duplicate_topic: { label: 'Second topic' },
      },
    },
  ];

  assert.throws(
    () => buildC1TopicRegistry(modules),
    /Duplicate C1 topic key/
  );
});

test('rejects unknown C1 module codes', () => {
  assert.throws(
    () => buildC1TopicRegistry([
      {
        module_code: 'UNKNOWN',
        module_name: 'Unknown',
        topics: {},
      },
    ]),
    /Unmapped C1 module/
  );
});