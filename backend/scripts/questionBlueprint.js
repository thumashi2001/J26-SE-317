// Run from the backend folder:   node scripts/questionBlueprint.js
// Builds the question blueprint for Component 1: every question with its topic, type, thinking level (Bloom)
// and expected difficulty. Prints a summary and writes two files into ../docs:
//   c1-question-blueprint.csv     one row per question (598 rows)
//   c1-review-sheet.csv           a sample of 40 questions with empty columns for a lecturer to fill in
// No database is needed.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { MODULES } from '../src/modules/c1/data/content/index.js';
import { BLOOM, DIFFICULTY, describeQuestion } from '../src/modules/c1/data/questionMeta.js';

const docs = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'docs');
const csv = (v) => `"${String(v).replace(/"/g, '""')}"`;

const rows = [];
for (const m of MODULES) {
  for (const [topic, t] of Object.entries(m.topics)) {
    const add = (set, prefix, list) => list.forEach((q, i) => rows.push({
      question_id: `${prefix}-${topic}-${String(i + 1).padStart(2, '0')}`,
      module: m.module_code, semester: m.semester, topic, label: t.label, set,
      type: q.tip, format: q.correct.length > 1 ? 'select all' : 'single answer',
      ...describeQuestion(q), text: q.text, options: q.options, correct: q.correct, why: q.why,
    }));
    add('practice', 'PQ', t.practice);
    add('diagnostic', 'DQ', t.diagnostic);
  }
}

// ---- summary ----
const count = (list, key) => list.reduce((a, r) => ((a[r[key]] = (a[r[key]] || 0) + 1), a), {});
console.log(`Questions: ${rows.length} (${rows.filter((r) => r.set === 'practice').length} practice, ${rows.filter((r) => r.set === 'diagnostic').length} diagnostic)\n`);
const pad = (s, n) => String(s).padEnd(n);
console.log(pad('Module', 10) + BLOOM.map((b) => pad(b, 12)).join('') + DIFFICULTY.map((d) => pad(d, 9)).join(''));
for (const m of MODULES) {
  const r = rows.filter((x) => x.module === m.module_code);
  const b = count(r, 'bloom'), d = count(r, 'difficulty');
  console.log(pad(m.module_code, 10) + BLOOM.map((x) => pad(b[x] || 0, 12)).join('') + DIFFICULTY.map((x) => pad(d[x] || 0, 9)).join(''));
}
const b = count(rows, 'bloom'), d = count(rows, 'difficulty');
console.log(pad('ALL', 10) + BLOOM.map((x) => pad(`${b[x] || 0} (${Math.round(((b[x] || 0) / rows.length) * 100)}%)`, 12)).join('') + DIFFICULTY.map((x) => pad(`${d[x] || 0}`, 9)).join(''));

// Coverage check: every topic should offer more than one thinking level and at least two difficulty bands.
const weak = [];
for (const topic of new Set(rows.map((r) => r.topic))) {
  const r = rows.filter((x) => x.topic === topic && x.set === 'practice');
  if (new Set(r.map((x) => x.bloom)).size < 2 || new Set(r.map((x) => x.difficulty)).size < 2) weak.push(topic);
}
console.log(weak.length ? `\nTopics with a narrow practice mix: ${weak.join(', ')}` : '\nEvery topic has at least 2 thinking levels and 2 difficulty bands in practice.');

// ---- files ----
fs.mkdirSync(docs, { recursive: true });
const head = ['question_id', 'module', 'topic', 'set', 'type', 'format', 'bloom', 'difficulty'];
fs.writeFileSync(path.join(docs, 'c1-question-blueprint.csv'), [head.join(','), ...rows.map((r) => head.map((h) => csv(r[h])).join(','))].join('\n') + '\n');

// Review sample: 5 per module, taken evenly across thinking levels. Fixed order, so the sample is repeatable.
const sample = [];
for (const m of MODULES) {
  const r = rows.filter((x) => x.module === m.module_code && x.set === 'practice');
  const byBloom = BLOOM.map((x) => r.filter((q) => q.bloom === x));
  for (let i = 0; sample.filter((s) => s.module === m.module_code).length < 5 && i < 50; i++) {
    const pool = byBloom[i % 4];
    if (pool.length) { const q = pool[Math.floor((i / 4) * 7 + 3) % pool.length]; if (!sample.includes(q)) sample.push(q); }
  }
}
const rh = ['question_id', 'module', 'topic', 'question', 'options (* = marked correct)', 'bloom', 'expected difficulty',
  'matches the slides? (Y/N)', 'exactly the right answer(s)? (Y/N)', 'wrong options believable? (Y/N)', 'difficulty fair? (Easy/Medium/Hard)', 'comments or fix'];
const letters = 'ABCD';
fs.writeFileSync(path.join(docs, 'c1-review-sheet.csv'), [rh.join(','), ...sample.map((q) => [
  q.question_id, q.module, q.label, q.text, q.options.map((o, i) => `${letters[i]}) ${o}${q.correct.includes(i) ? ' *' : ''}`).join('  '), q.bloom, q.difficulty, '', '', '', '', '',
].map(csv).join(','))].join('\n') + '\n');
console.log(`\nWrote docs/c1-question-blueprint.csv (${rows.length} rows) and docs/c1-review-sheet.csv (${sample.length} questions).`);
