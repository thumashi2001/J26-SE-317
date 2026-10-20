// Run from the backend folder:   node scripts/pilotForm.js [topic_key topic_key topic_key]
// Makes a Google Form pilot for the item analysis. Writes two files into ../docs/pilot:
//   create-form.gs    paste this into script.google.com and press Run: it builds the whole form for you
//   pilot-key.json    the answer key and question numbers; the analysis reads it later
// Default topics: project_risk_management unit_integration_testing ux_testing_heuristics (10 practice questions each).
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { TOPICS } from '../src/modules/c1/data/content/index.js';

const out = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '..', 'docs', 'pilot');
const topics = process.argv.length > 2 ? process.argv.slice(2) : ['project_risk_management', 'unit_integration_testing', 'ux_testing_heuristics'];
for (const t of topics) if (!TOPICS[t]) { console.error(`Unknown topic key: ${t}`); process.exit(1); }

const key = [];
const sections = [];
let n = 0;
for (const t of topics) {
  const qs = [];
  TOPICS[t].practice.forEach((q, i) => {
    n += 1;
    const multi = q.correct.length > 1;
    const title = `Q${String(n).padStart(2, '0')}. ${q.text}${multi ? ' (select ALL that apply)' : ''}`;
    key.push({ n, question_id: `PQ-${t}-${String(i + 1).padStart(2, '0')}`, topic: t, options: q.options, correct: q.correct, multi });
    qs.push({ title, choices: q.options, multi });
  });
  sections.push({ name: TOPICS[t].label, questions: qs });
}

const gs = `// Paste this whole file into https://script.google.com (New project), press Run, and allow access.
// It creates the pilot form and a response sheet in your Google Drive, then prints the links in the log.
function createPilotForm() {
  const sections = ${JSON.stringify(sections, null, 2)};
  const form = FormApp.create('Question pilot (${n} questions, about 30 minutes)');
  form.setDescription('Please answer on your own, without notes or searching, because your answers only help if they show what you really know. ' +
    'Some questions say "select ALL that apply". There is no name or email in this form. Please submit only once. Thank you!');
  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setConfirmationMessage('Thank you! Your answers were saved.');
  sections.forEach(function (s, si) {
    if (si > 0) form.addPageBreakItem().setTitle(s.name);
    else form.addSectionHeaderItem().setTitle(s.name);
    s.questions.forEach(function (q) {
      const item = q.multi ? form.addCheckboxItem() : form.addMultipleChoiceItem();
      item.setTitle(q.title).setChoiceValues(q.choices).setRequired(true);
    });
  });
  const sheet = SpreadsheetApp.create('Question pilot responses');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());
  Logger.log('SHARE THIS LINK WITH CLASSMATES: ' + form.getPublishedUrl());
  Logger.log('Responses sheet: ' + sheet.getUrl());
  Logger.log('Edit the form: ' + form.getEditUrl());
}
`;
fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, 'create-form.gs'), gs);
fs.writeFileSync(path.join(out, 'pilot-key.json'), JSON.stringify(key, null, 1));
console.log(`Topics: ${topics.map((t) => TOPICS[t].label).join(' | ')}`);
console.log(`${n} questions (${key.filter((k) => k.multi).length} select-all). Wrote docs/pilot/create-form.gs and docs/pilot/pilot-key.json`);
