// Builds a practice quiz for ONE student from the lecture-based question bank.
// The twin's knowledge level for the topic sets a target difficulty (Easy, Medium, Hard), the quiz mix follows
// from it, and the last finished quiz of the topic moves the level one step. See docs/c1-adaptive-questions.md.
//
// Note: a trial that rebuilt the wrong options from other questions produced options that did not fit the
// question, so it was dropped. Only authored, reviewed questions are shown to students.
//
// No paid service is used. Everything here is plain code that can be run and checked offline.
import { difficultyOf } from '../data/questionMeta.js';

export const LEVELS = ['Easy', 'Medium', 'Hard'];

// Score bands of the twin: under 40 is weak, 40 to 69 is developing, 70 and over is strong (the 70 target).
export function baseLevel(score) {
  if (score < 40) return 'Easy';
  if (score < 70) return 'Medium';
  return 'Hard';
}

// The last finished quiz of the topic moves the level one step: 80% or more right goes up, 40% or less goes down.
export function nextLevel(score, lastRatio) {
  let i = LEVELS.indexOf(baseLevel(score));
  if (typeof lastRatio === 'number') {
    if (lastRatio >= 0.8) i += 1;
    else if (lastRatio <= 0.4) i -= 1;
  }
  return LEVELS[Math.max(0, Math.min(2, i))];
}

// How many of the 7 questions come from each difficulty: mostly the target level, a few above and below.
export function mixFor(level, total = 7) {
  const mix = { Easy: 0, Medium: 0, Hard: 0 };
  if (level === 'Easy') Object.assign(mix, { Easy: total - 2, Medium: 2 });
  else if (level === 'Medium') Object.assign(mix, { Easy: 1, Medium: total - 3, Hard: 2 });
  else Object.assign(mix, { Medium: 2, Hard: total - 2 });
  return mix;
}

// Choose which questions to use. `items` is [{ id, q, lastSeen }]. Questions seen longest ago come first.
export function pickQuestions(items, mix, rng = Math.random) {
  const tagged = items.map((it) => ({ ...it, difficulty: difficultyOf(it.q) }));
  const total = Object.values(mix).reduce((a, b) => a + b, 0);
  const used = new Set();
  const chosen = [];
  const byAge = (list) =>
    [...list]
      .map((x) => ({ x, r: rng() }))
      .sort((a, b) => (a.x.lastSeen || 0) - (b.x.lastSeen || 0) || a.r - b.r)
      .map((e) => e.x);
  for (const d of LEVELS) {
    for (const it of byAge(tagged.filter((t) => t.difficulty === d)).slice(0, mix[d])) {
      chosen.push(it);
      used.add(it.id);
    }
  }
  // A topic may lack questions at some level. Fill from the nearest level first.
  while (chosen.length < total) {
    const need = LEVELS.filter((d) => chosen.filter((c) => c.difficulty === d).length < mix[d]);
    const want = need[0] || 'Medium';
    const rest = tagged.filter((t) => !used.has(t.id));
    if (rest.length === 0) break;
    rest.sort((a, b) => Math.abs(LEVELS.indexOf(a.difficulty) - LEVELS.indexOf(want)) - Math.abs(LEVELS.indexOf(b.difficulty) - LEVELS.indexOf(want)) || (a.lastSeen || 0) - (b.lastSeen || 0));
    chosen.push(rest[0]);
    used.add(rest[0].id);
  }
  return chosen;
}
