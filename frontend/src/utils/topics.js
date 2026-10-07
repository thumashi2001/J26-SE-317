// Turns "quality_assurance" into "Quality Assurance".
const ACRONYMS = { sdlc: 'SDLC', orm: 'ORM', mvc: 'MVC' };

export const prettyTopic = (t) =>
  t
    .split('_')
    .map((w) => ACRONYMS[w] || w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

// Colour band for a mastery score (0-100).
export function scoreBand(score) {
  if (score < 30) return 'weak';
  if (score < 60) return 'fair';
  return 'strong';
}
