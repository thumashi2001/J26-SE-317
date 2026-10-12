// Practice questions for Component 1 now come from the real lecture-slide content files
// in ./content (one file per module). See content/helpers.js for how a question is written
// and `node scripts/checkContent.js` to check the files for mistakes.
import { TOPICS } from './content/index.js';
export { TIPS } from './content/tips.js';

// Kept so old topic spellings still work. No aliases are needed for the real topics.
export const TOPIC_ALIASES = {};

export const PRACTICE_QUESTIONS = Object.fromEntries(Object.entries(TOPICS).map(([key, t]) => [key, t.practice]));
