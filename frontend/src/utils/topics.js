import { TOPIC_INFO } from './topicLabels.js';

// Real topic names come from the lecture-slide content. Unknown keys fall back to a tidy version of the key.
const ACRONYMS = { sdlc: 'SDLC', orm: 'ORM', mvc: 'MVC' };

export const prettyTopic = (t) =>
  TOPIC_INFO[t]?.label ||
  t
    .split('_')
    .map((w) => ACRONYMS[w] || w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

// Module code (for example SE3070) and lecture range for a topic, if known.
export const topicModule = (t) => TOPIC_INFO[t]?.module || '';
export const topicLectures = (t) => TOPIC_INFO[t]?.lectures || '';

// Colour band for a mastery score (0-100).
export function scoreBand(score) {
  if (score < 30) return 'weak';
  if (score < 60) return 'fair';
  return 'strong';
}
