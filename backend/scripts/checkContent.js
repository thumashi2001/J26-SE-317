// Run from the backend folder:   node scripts/checkContent.js [file-name-without-.js ...]
// Checks the question content files in src/modules/c1/data/content for mistakes.
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { TIPS } from '../src/modules/c1/data/content/tips.js';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'src', 'modules', 'c1', 'data', 'content');
const wanted = process.argv.slice(2);
const files = fs.readdirSync(dir).filter((f) => f.endsWith('.js') && !['helpers.js', 'index.js', 'tips.js'].includes(f))
  .filter((f) => !wanted.length || wanted.includes(f.replace('.js', '')));

const seen = new Set();
const PRACTICE_SINGLE = 6, PRACTICE_MULTI = 4, DIAG = 3;
let problems = 0, total = 0;
const bad = (where, msg) => { problems += 1; console.log(`  PROBLEM ${where}: ${msg}`); };

for (const f of files) {
  const mod = (await import(pathToFileURL(path.join(dir, f)).href)).default;
  console.log(`${f}: ${mod.module_code} ${mod.semester}, ${Object.keys(mod.topics).length} topics`);
  const pos = [0, 0, 0, 0];
  let longest = 0, n = 0;
  for (const [key, t] of Object.entries(mod.topics)) {
    if (!/^[a-z0-9_]+$/.test(key)) bad(key, 'topic key must be lower snake_case');
    if (!t.label || !t.lectures) bad(key, 'label and lectures are required');
    const sOk = t.practice.filter((q) => q.correct.length === 1).length;
    const mOk = t.practice.filter((q) => q.correct.length > 1).length;
    if (sOk !== PRACTICE_SINGLE || mOk !== PRACTICE_MULTI) bad(key, `practice needs ${PRACTICE_SINGLE} single + ${PRACTICE_MULTI} multi, has ${sOk} + ${mOk}`);
    if (t.diagnostic.length !== DIAG) bad(key, `diagnostic needs ${DIAG}, has ${t.diagnostic.length}`);
    const all = [...t.practice.map((q, i) => ['P' + (i + 1), q]), ...t.diagnostic.map((q, i) => ['D' + (i + 1), q])];
    for (const [id, q] of all) {
      const w = `${key} ${id}`;
      total += 1;
      if (typeof q.text !== 'string' || q.text.length < 15) bad(w, 'question text missing or too short');
      if (!Array.isArray(q.options) || q.options.length !== 4) { bad(w, 'needs exactly 4 options'); continue; }
      if (new Set(q.options.map((o) => String(o).trim().toLowerCase())).size !== 4) bad(w, 'options are not all different');
      if (!q.correct.length || q.correct.some((c) => !Number.isInteger(c) || c < 0 || c > 3)) bad(w, 'bad correct index');
      if (new Set(q.correct).size !== q.correct.length) bad(w, 'repeated correct index');
      if (id.startsWith('D') && q.correct.length !== 1) bad(w, 'diagnostic must have exactly one correct answer');
      if (q.correct.length > 1 && q.correct.length > 3) bad(w, 'multi answer must leave at least one wrong option');
      if (!q.why || q.why.length < 15) bad(w, 'explanation missing');
      if (!TIPS[q.tip]) bad(w, `unknown tip kind ${q.tip}`);
      const blob = [q.text, q.why, ...q.options].join(' ');
      if (/[\u2014\u2013]/.test(blob)) bad(w, 'contains a dash character (em or en dash)');
      if (/\b(all|none) of the above\b/i.test(blob)) bad(w, 'uses all/none of the above');
      if (q.options.some((o) => /^\s*(i{1,3}|iv|v)\s*[.)]/i.test(o)) || /\b(i{2,3}|iv)\s*(,|and|&)\s*(i{1,3}|iv)\b/i.test(q.text)) bad(w, 'looks like a Roman numeral question');
      if (/\b(statement|statements)\s+(i|ii|iii)\b/i.test(blob)) bad(w, 'Roman numeral statements');
      const norm = q.text.trim().toLowerCase();
      if (seen.has(norm)) bad(w, 'duplicate question text'); seen.add(norm);
      if (q.correct.length === 1) {
        pos[q.correct[0]] += 1; n += 1;
        const lens = q.options.map((o) => o.length);
        if (lens[q.correct[0]] === Math.max(...lens) && lens.filter((l) => l === Math.max(...lens)).length === 1) longest += 1;
      }
    }
  }
  const spread = pos.map((p) => Math.round((p / n) * 100));
  console.log(`  single-answer correct position A-D (%): ${spread.join(' / ')}  | correct is the longest option: ${Math.round((longest / n) * 100)}%`);
  if (longest / n > 0.5) bad(mod.module_code, 'correct answer is the longest option too often; vary option lengths');
}
console.log(problems ? `\n${problems} problem(s) found out of ${total} questions.` : `\nAll good: ${total} questions checked.`);
process.exit(problems ? 1 : 0);
