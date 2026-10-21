/**
 * Node-side check for a c4-practice-quiz-pass-v1 bundle.
 * Smoke and synthetic exports stay unusable. Exam UI must keep the heuristic.
 */

import { createHash } from 'crypto';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

export const PRACTICE_QUIZ_PASS_PROTOCOL = 'c4-practice-quiz-pass-v1';
export const PRACTICE_QUIZ_PASS_FEATURES = Object.freeze([
  'question_count',
  'topic_count',
  'mean_prior_accuracy',
  'fraction_observed_priors',
  'min_prior_accuracy',
  'cold_start',
  'semester_y3s1',
]);

export function assessPracticeQuizPassBundle(directory) {
  const bundlePath = join(directory, 'bundle.json');
  const checksumPath = join(directory, 'checksums.json');
  if (!existsSync(bundlePath) || !existsSync(checksumPath)) {
    return { usable: false, code: 'missing_bundle' };
  }
  const raw = readFileSync(bundlePath);
  const digest = createHash('sha256').update(raw).digest('hex');
  const recorded = JSON.parse(readFileSync(checksumPath, 'utf8'))['bundle.json'];
  if (recorded !== digest) return { usable: false, code: 'checksum_mismatch' };
  const payload = JSON.parse(raw.toString('utf8'));
  const names = payload.feature_names || [];
  if (
    payload.protocol !== PRACTICE_QUIZ_PASS_PROTOCOL ||
    names.length !== PRACTICE_QUIZ_PASS_FEATURES.length ||
    names.some((name, index) => name !== PRACTICE_QUIZ_PASS_FEATURES[index])
  ) {
    return { usable: false, code: 'schema_mismatch' };
  }
  if (
    payload.activation_allowed !== true ||
    payload.serves_students !== true ||
    payload.reviewed_full_export !== true
  ) {
    return {
      usable: false,
      code: 'not_activated',
      reason:
        'Insufficient evidence for this-quiz pass probability. The heuristic remains in use.',
    };
  }
  return { usable: true, code: 'reviewed_full_export' };
}
