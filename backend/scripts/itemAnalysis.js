// Run from the backend folder:
//   node scripts/itemAnalysis.js            real answers from MongoDB (learning_events)
//   node scripts/itemAnalysis.js --csv responses.csv   Google Form pilot (see docs/pilot): no database needed
//   node scripts/itemAnalysis.js --demo     PIPELINE TEST on simulated answers (no database, not evidence)
// Writes ../docs/c1-item-analysis.csv and prints a summary.
// A question needs at least 15 first-attempt answers before its numbers are trusted, so collect answers from
// classmates first (a pilot), then run this on the real data.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { MODULES } from '../src/modules/c1/data/content/index.js';
import { describeQuestion, PRIOR_P } from '../src/modules/c1/data/questionMeta.js';
import { analyse, summarise, MIN_ANSWERS } from '../src/modules/c1/services/itemAnalysis.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const demo = process.argv.includes('--demo');
const csvAt = process.argv.indexOf('--csv');
const csvFile = csvAt > -1 ? process.argv[csvAt + 1] : null;

// prior band for every question id
const meta = {};
for (const m of MODULES) {
  for (const [topic, t] of Object.entries(m.topics)) {
    t.practice.forEach((q, i) => { meta[`PQ-${topic}-${String(i + 1).padStart(2, '0')}`] = describeQuestion(q); });
    t.diagnostic.forEach((q, i) => { meta[`DQ-${topic}-${String(i + 1).padStart(2, '0')}`] = describeQuestion(q); });
  }
}

let events = [];
if (csvFile) {
  const { parseCsv, eventsFromResponses, screenCopies } = await import('../src/modules/c1/services/pilotCsv.js');
  const key = JSON.parse(fs.readFileSync(path.join(here, '..', '..', 'docs', 'pilot', 'pilot-key.json'), 'utf8'));
  const res = eventsFromResponses(parseCsv(fs.readFileSync(csvFile, 'utf8')), key);
  events = res.events;
  console.log(`Pilot file: ${res.respondents} respondents, ${events.length} answers.`);
  if (!process.argv.includes('--no-screen')) {
    const sc = screenCopies(events);
    if (sc.groups.length) {
      console.log(`SCREENING: ${sc.groups.length} group(s) of near-identical answer sheets found (sheet rows ${sc.groups.map((g) => g.join(', ')).join(' | ')}).`);
      console.log(`Kept the earliest sheet of each group and left out ${sc.dropped} copies. Use --no-screen to keep everything.`);
    } else console.log('SCREENING: no near-identical answer sheets found.');
    events = sc.events;
  }
  // Optional effort screening: --min-score N leaves out respondents who got fewer than N questions fully right.
  // Random guessing on this form gives about 5 out of 30 (sd about 2), so 10 is a sensible limit.
  const ms = process.argv.indexOf('--min-score');
  if (ms > -1) {
    const limit = Number(process.argv[ms + 1]);
    const total = {};
    events.forEach((e) => { total[e.student_id] = (total[e.student_id] || 0) + (e.correct ? 1 : 0); });
    const low = new Set(Object.keys(total).filter((id) => total[id] < limit));
    console.log(`EFFORT SCREENING: ${low.size} of ${Object.keys(total).length} respondents scored below ${limit} of ${key.length} (chance level is about ${Math.round(key.reduce((t, k) => t + (k.multi ? 1 / 15 : 0.25), 0))}). Left them out.`);
    events = events.filter((e) => !low.has(e.student_id));
    console.log(`Respondents analysed: ${Object.keys(total).length - low.size}${Object.keys(total).length - low.size < 15 ? ' (fewer than 15, so treat the numbers as indicative only)' : ''}`);
  }
  if (res.missingColumns.length) console.log(`WARNING: no column found for Q${res.missingColumns.join(', Q')}. Is this the right file?`);
  console.log('');
} else if (demo) {
  // Simulated class: 300 students, each answers 60 random questions. The chance of a right answer depends on the
  // student's ability and on a question difficulty that is NOT the prior band (it is random around it), so the
  // analysis has something to find. This only proves the script runs end to end.
  let seed = 7;
  const rnd = () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);
  const ids = Object.keys(meta);
  const hidden = Object.fromEntries(ids.map((id) => [id, PRIOR_P[meta[id].difficulty] + (rnd() - 0.5) * 0.3]));
  for (let s = 0; s < 300; s++) {
    const ability = (rnd() - 0.5) * 0.5;
    for (let k = 0; k < 60; k++) {
      const id = ids[Math.floor(rnd() * ids.length)];
      events.push({ student_id: `S${s}`, question_id: id, correct: rnd() < Math.min(0.98, Math.max(0.02, hidden[id] + ability)), timestamp: new Date(1e12 + s * 1e6 + k) });
    }
  }
  console.log('DEMO MODE: simulated answers, only a test of the script.\n');
} else {
  const dotenv = (await import('dotenv')).default;
  dotenv.config({ path: path.join(here, '..', '.env') });
  const { connectDb } = await import('../src/config/db.js');
  const db = await connectDb();
  events = await db.collection('learning_events').find({ question_id: { $exists: true } }).toArray();
  console.log(`Read ${events.length} answers from learning_events.\n`);
  if (!events.length) { console.log('No answers with a question id yet. Run a pilot first.'); process.exit(0); }
}

const rows = analyse(events, meta);
const sum = summarise(rows);
console.log(`Questions answered: ${sum.questions}. With at least ${MIN_ANSWERS} answers: ${sum.usable}.`);
console.log(`Flagged for a look: ${sum.flagged}. Mean discrimination: ${sum.meanDiscrimination}. Expected band matched observed band: ${sum.priorMatchesObserved}%.\n`);
const bad = rows.filter((r) => r.n >= MIN_ANSWERS && r.flags.length).slice(0, 12);
for (const r of bad) console.log(`${r.question_id}  n=${r.n} p=${r.p} d=${r.discrimination}  ${r.flags.join('; ')}`);

const out = path.join(here, '..', '..', 'docs', demo ? 'c1-item-analysis-DEMO.csv' : csvFile ? 'pilot/c1-item-analysis-pilot.csv' : 'c1-item-analysis.csv');
const head = ['question_id', 'n', 'p', 'discrimination', 'prior', 'calibrated_p', 'observed', 'flags'];
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, [head.join(','), ...rows.map((r) => head.map((h) => `"${Array.isArray(r[h]) ? r[h].join('; ') : r[h] ?? ''}"`).join(','))].join('\n') + '\n');
console.log(`\nWrote ${path.relative(process.cwd(), out)}`);
process.exit(0);
