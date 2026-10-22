// Input size limits enforced at the C3 boundary (the shared app only applies Express' default 100 kB body limit).
// Values are conservative for this course tool; each limit is covered by a test.

export const LIMITS = Object.freeze({
  ANSWER_CHARS: 20000,
  TITLE_CHARS: 200,
  QUESTION_CHARS: 5000,
  BATCH_ITEMS: 500,
  OPTIONS: 20,
  CRITERIA: 20,
  EXPECTED_CONCEPTS: 50,
});

function tooLarge(message) {
  return Object.assign(new Error(message), { status: 413 });
}

export function assertMaxChars(value, max, label) {
  if (typeof value === 'string' && value.length > max) {
    throw tooLarge(`${label} is too long (maximum ${max} characters)`);
  }
}

export function assertMaxItems(value, max, label) {
  if (Array.isArray(value) && value.length > max) {
    throw tooLarge(`${label} has too many entries (maximum ${max})`);
  }
}
