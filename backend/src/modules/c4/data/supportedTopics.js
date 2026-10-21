/**
 * SE topics that have an actual C1 practice flow today.
 * Source of truth: backend/src/modules/c1/data/practiceQuestions.js (PRACTICE_QUESTIONS keys).
 * Do not invent IDs or ASSISTments mappings here.
 */
import { PRACTICE_QUESTIONS } from '../../c1/data/practiceQuestions.js';

/** Canonical topic IDs with practice questions (ordered for stable display ties). */
export const SUPPORTED_PRACTICE_TOPICS = Object.freeze(Object.keys(PRACTICE_QUESTIONS));

export const PRACTICE_LAUNCH_PATH = (topic) => `/c1/practice/${encodeURIComponent(topic)}`;

export function isSupportedPracticeTopic(topic) {
  return Object.prototype.hasOwnProperty.call(PRACTICE_QUESTIONS, topic);
}
