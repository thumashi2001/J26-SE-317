// INPUT SIZE LIMITS (a kind of "parameter validation" at the Node boundary).
// SIMPLE ENGLISH: refuse absurdly large inputs (a 1 MB answer, 10,000 options) with HTTP 413 before they reach marking.
//
// Input size limits enforced at the C3 boundary (the shared app only applies Express' default 100 kB body limit).
// Values are conservative for this course tool; each limit is covered by a test.

export const LIMITS = Object.freeze({
  ANSWER_CHARS: 20000,   // longest student answer
  TITLE_CHARS: 200,      // lecturer setup title
  QUESTION_CHARS: 5000,  // question text
  BATCH_ITEMS: 500,      // students in one batch-marking request
  OPTIONS: 20,           // MCQ options
  CRITERIA: 20,          // rubric criteria
  EXPECTED_CONCEPTS: 50, // concepts per question
});

// 413 = "payload too large"
function tooLarge(message) {
  return Object.assign(new Error(message), { status: 413 });
}

// Throw if a string is longer than `max` characters (non-strings are ignored here; type checks happen elsewhere).
export function assertMaxChars(value, max, label) {
  if (typeof value === 'string' && value.length > max) {
    throw tooLarge(`${label} is too long (maximum ${max} characters)`);
  }
}

// Throw if an array has more than `max` entries.
export function assertMaxItems(value, max, label) {
  if (Array.isArray(value) && value.length > max) {
    throw tooLarge(`${label} has too many entries (maximum ${max})`);
  }
}
