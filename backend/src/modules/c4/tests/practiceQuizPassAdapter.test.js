import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { createHash } from 'crypto';
import { assessPracticeQuizPassBundle } from '../services/practiceQuizPassAdapter.js';

function writeBundle(payload) {
  const dir = mkdtempSync(join(tmpdir(), 'c4-quiz-pass-'));
  const raw = Buffer.from(JSON.stringify(payload));
  writeFileSync(join(dir, 'bundle.json'), raw);
  writeFileSync(
    join(dir, 'checksums.json'),
    JSON.stringify({ 'bundle.json': createHash('sha256').update(raw).digest('hex') })
  );
  return dir;
}

const inactive = {
  protocol: 'c4-practice-quiz-pass-v1',
  feature_names: [
    'question_count',
    'topic_count',
    'mean_prior_accuracy',
    'fraction_observed_priors',
    'min_prior_accuracy',
    'cold_start',
    'semester_y3s1',
  ],
  activation_allowed: false,
  serves_students: false,
  reviewed_full_export: false,
};

test('inactive this-quiz bundle is not usable', () => {
  const assessed = assessPracticeQuizPassBundle(writeBundle(inactive));
  assert.equal(assessed.usable, false);
  assert.equal(assessed.code, 'not_activated');
});

test('checksum mismatch is rejected', () => {
  const dir = writeBundle(inactive);
  writeFileSync(join(dir, 'checksums.json'), JSON.stringify({ 'bundle.json': '0'.repeat(64) }));
  assert.equal(assessPracticeQuizPassBundle(dir).code, 'checksum_mismatch');
});
