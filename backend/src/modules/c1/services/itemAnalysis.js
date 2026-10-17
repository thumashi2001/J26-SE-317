// Item analysis for Component 1 questions (classical test theory). Pure functions, no database.
// Input: learning events { student_id, question_id, correct, hint_used }. Output: one row per question.
//
//   n               students counted (first attempt only; answers that used the 50/50 hint are left out)
//   p               difficulty index = share of students who answered correctly (high = easy)
//   discrimination  point-biserial correlation between getting this question right and the student's
//                   score on all OTHER questions they answered (high = separates strong from weak students)
//   calibrated_p    p pulled toward the expected value of the question's prior band when n is small
//                   (shrinkage with weight K), so a question with 3 answers is not trusted too much
//   observed        Easy / Medium / Hard from calibrated_p (>= 0.70 Easy, < 0.45 Hard)
//   flags           things the author should look at
import { PRIOR_P } from '../data/questionMeta.js';

export const MIN_ANSWERS = 15;   // below this a question is reported as "too few answers"
const MIN_OTHER = 5;             // a student needs this many other answers to give a fair rest score
const K = 10;                    // shrinkage weight

export const bandOfP = (p) => (p >= 0.7 ? 'Easy' : p < 0.45 ? 'Hard' : 'Medium');

function pearson(x, y) {
  const n = x.length;
  if (n < 3) return null;
  const mx = x.reduce((a, b) => a + b, 0) / n, my = y.reduce((a, b) => a + b, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
  return sxx === 0 || syy === 0 ? null : sxy / Math.sqrt(sxx * syy);
}

// meta: { [question_id]: { difficulty: 'Easy'|'Medium'|'Hard', ... } }  (the prior band of each question)
export function analyse(events, meta = {}) {
  // first attempt per student and question, no hints
  const seen = new Set();
  const byStudent = new Map();
  const byQuestion = new Map();
  for (const e of [...events].sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0))) {
    if (!e.question_id || e.hint_used) continue;
    const key = `${e.student_id}|${e.question_id}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const c = e.correct ? 1 : 0;
    if (!byStudent.has(e.student_id)) byStudent.set(e.student_id, []);
    byStudent.get(e.student_id).push([e.question_id, c]);
    if (!byQuestion.has(e.question_id)) byQuestion.set(e.question_id, []);
    byQuestion.get(e.question_id).push([e.student_id, c]);
  }
  const totals = new Map([...byStudent].map(([s, a]) => [s, { sum: a.reduce((t, [, c]) => t + c, 0), n: a.length }]));

  const rows = [];
  for (const [qid, list] of byQuestion) {
    const n = list.length;
    const right = list.reduce((t, [, c]) => t + c, 0);
    const p = right / n;
    const x = [], y = [];
    for (const [s, c] of list) {
      const t = totals.get(s);
      if (t.n - 1 >= MIN_OTHER) { x.push(c); y.push((t.sum - c) / (t.n - 1)); }
    }
    const disc = pearson(x, y);
    const prior = meta[qid]?.difficulty || null;
    const priorP = prior ? PRIOR_P[prior] : 0.6;
    const calibrated = (n * p + K * priorP) / (n + K);
    const observed = bandOfP(calibrated);
    const flags = [];
    if (n < MIN_ANSWERS) flags.push('too few answers');
    else {
      if (p > 0.9) flags.push('too easy');
      if (p < 0.2) flags.push(disc !== null && disc >= 0.3 ? 'very hard but discriminates well (often a select-all question)' : 'very hard, check the answer key');
      if (disc !== null && disc < 0) flags.push('negative discrimination, check the answer key');
      else if (disc !== null && disc < 0.1) flags.push('weak discrimination');
      if (prior && prior !== observed) flags.push(`expected ${prior}, observed ${observed}`);
    }
    rows.push({ question_id: qid, n, p: +p.toFixed(3), discrimination: disc === null ? null : +disc.toFixed(3), prior, calibrated_p: +calibrated.toFixed(3), observed, flags });
  }
  return rows.sort((a, b) => a.question_id.localeCompare(b.question_id));
}

// Summary numbers for the report.
export function summarise(rows) {
  const usable = rows.filter((r) => r.n >= MIN_ANSWERS);
  const agree = usable.filter((r) => r.prior && r.prior === r.observed).length;
  const withPrior = usable.filter((r) => r.prior).length;
  return {
    questions: rows.length,
    usable: usable.length,
    flagged: usable.filter((r) => r.flags.length).length,
    priorMatchesObserved: withPrior ? Math.round((agree / withPrior) * 100) : null,
    meanDiscrimination: usable.filter((r) => r.discrimination !== null).length
      ? +(usable.filter((r) => r.discrimination !== null).reduce((t, r) => t + r.discrimination, 0) / usable.filter((r) => r.discrimination !== null).length).toFixed(2) : null,
  };
}
