// Component tests for the shared C3 result view. They render the real component (bundled with esbuild, which ships
// with Vite) to static HTML using responses captured from the running C3 service (tests/fixtures/*.json), so no
// browser and no new dependency is needed. Browser workflows are covered separately by reports/c3_remediation/ui_tests.
import test, { before } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const here = path.dirname(fileURLToPath(import.meta.url));
const fx = (n) => JSON.parse(fs.readFileSync(path.join(here, 'fixtures', n + '.json'), 'utf8'));
let render;
let normaliseEvaluation;
let SourceBadge;
let sourceKind;
let h;

const ENTRY = [
  "import React from 'react';",
  "import { renderToStaticMarkup } from 'react-dom/server';",
  "import AssessmentResult from '../src/pages/c3/components/AssessmentResult.jsx';",
  "export { normaliseEvaluation } from '../src/pages/c3/analysis.js';",
  "export { SourceBadge, sourceKind } from '../src/pages/c3/components/c3ui.jsx';",
  "export { renderToStaticMarkup }; export { default as React } from 'react';",
  'export const render = (props) => renderToStaticMarkup(React.createElement(AssessmentResult, props));',
].join('\n');

before(async () => {
  const entry = path.join(here, '.entry.jsx');
  fs.writeFileSync(entry, ENTRY);
  const out = path.join(here, '.entry.bundle.mjs');
  await build({ entryPoints: [entry], outfile: out, bundle: true, platform: 'node', format: 'esm', packages: 'external', jsx: 'transform', loader: { '.jsx': 'jsx' }, logLevel: 'silent' });
  const mod = await import(pathToFileURL(out).href + '?t=' + Date.now());
  render = mod.render;
  normaliseEvaluation = mod.normaliseEvaluation;
  SourceBadge = mod.SourceBadge;
  sourceKind = mod.sourceKind;
  h = (props) => mod.renderToStaticMarkup(mod.React.createElement(SourceBadge, props));
  fs.rmSync(entry);
  fs.rmSync(out);
});

const text = (html) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
const KEY_LEAK = /authoritative|answer key|Correct: Option|Key: |requires_key|correct_labels/i;

test('lecturer view of a written answer shows submitted answer, criterion evidence, concepts, feedback and the map', () => {
  const d = fx('subjective_lecturer_detail');
  const html = render({ evaluation: d.result.ai_evaluation, historicalResult: d.result, question: d.submission.question_text, answer: d.submission.student_answer, showMarkCard: false, showContext: true });
  const t = text(html);
  assert.ok(t.includes(d.submission.student_answer), 'submitted answer missing');
  assert.ok(t.includes('Marking by criterion') && t.includes('Evidence in the answer') && t.includes('Why this mark'), 'criterion evidence/explanation missing');
  for (const c of d.result.ai_evaluation.analysis.concept_matches) assert.ok(t.includes(c.concept), `concept ${c.concept} missing`);
  assert.ok(/Demonstrated|Partial|Missing/.test(t), 'concept statuses missing');
  assert.ok(t.includes('Feedback') && t.includes('Strengths') || t.includes('How to improve') || t.includes('Concepts to revisit'), 'feedback missing');
  assert.ok(html.includes('c3-mindmap-container') && html.includes('c3-mm-node'), 'concept map missing');
  assert.ok(!/unavailable|No analysis available/i.test(t), 'unexpected unavailable note');
  assert.ok(!/Function \d/.test(t), 'internal jargon still shown');
});

test('written answer: every stored concept status is rendered', () => {
  const d = fx('subjective_lecturer_detail');
  const a = normaliseEvaluation(d.result.ai_evaluation);
  assert.strictEqual(a.kind, 'subjective');
  assert.ok(a.concepts.available && a.map.available && a.feedback.available);
  const label = { demonstrated: 'Demonstrated', partial: 'Partial', not_demonstrated: 'Missing' };
  const html = render({ evaluation: d.result.ai_evaluation, historicalResult: d.result, showMarkCard: false, showContext: false });
  for (const c of d.result.ai_evaluation.analysis.concept_matches) assert.ok(html.includes(label[c.status]), `status ${c.status} not rendered`);
});

test('MCQ lecturer view: answer key match and MCQ feedback shown; concept diagnosis and map explicitly not produced', () => {
  const d = fx('mcq_lecturer_detail');
  const html = render({ evaluation: d.result.ai_evaluation, historicalResult: d.result, question: d.submission.question_text, answer: d.submission.student_answer, showMarkCard: false, showContext: true });
  const t = text(html);
  assert.ok(t.includes('Answer key match') && t.includes('Not correct'), 'answer key match missing');
  assert.ok(t.includes('Feedback') && /incorrect|Review the lecture notes/i.test(t), 'MCQ feedback not rendered');
  assert.ok(t.includes('Concept diagnosis') && t.includes('Not produced for multiple-choice questions'), 'concept diagnosis note missing');
  assert.ok(t.includes('Concept map'), 'concept map section missing');
  assert.ok(!html.includes('c3-mindmap-container'), 'degenerate MCQ map must not be drawn');
  assert.ok(!t.includes('Evidence in the answer'), 'sentence evidence block should not appear for MCQ');
  assert.ok(d.result.ai_evaluation.correct_labels.every((l) => t.includes(l)), 'lecturer lost the correct option');
});

test('MCQ student responses (live and history) contain no correct-option information', () => {
  for (const name of ['mcq_student_live', 'mcq_student_detail']) {
    const f = fx(name);
    const evaluation = f.result ? f.result.ai_evaluation : f;
    const html = render({ evaluation, historicalResult: f.result || { status: 'pending_review' }, question: 'q', answer: 'Selected Option: A', showMarkCard: true, showContext: true });
    assert.ok(!KEY_LEAK.test(JSON.stringify(f)), `${name}: raw response leaks the key: ${JSON.stringify(f).match(KEY_LEAK)?.[0]}`);
    assert.ok(!KEY_LEAK.test(text(html)), `${name}: rendered view leaks the key`);
    assert.ok(!text(html).includes('Answer key match'), `${name}: answer key table shown to a student`);
    assert.ok(text(html).includes('Your selected option is not correct'), `${name}: outcome missing`);
    assert.ok(!html.includes('c3-mindmap-container'));
  }
});

test('missing or empty analysis is explained, never blank, and never throws', () => {
  for (const ev of [null, undefined, {}, { warnings: [] }]) {
    const html = render({ evaluation: ev, historicalResult: { status: 'pending_review', automated_mark: 2, total_possible_marks: 4 }, showMarkCard: true, showContext: true, answer: 'my answer' });
    const t = text(html);
    assert.ok(t.includes('No analysis available') && t.includes('No analysis was saved for this submission'), 'explanation missing');
    assert.ok(t.includes('my answer'));
    assert.ok(!html.includes('c3-mindmap-container') && !t.includes('Concept diagnosis'));
  }
});

test('partial analysis: missing feedback and map are reported as unavailable, criteria still render', () => {
  const d = fx('subjective_lecturer_detail');
  const ev = JSON.parse(JSON.stringify(d.result.ai_evaluation));
  delete ev.feedback;
  delete ev.mindmap;
  const t = text(render({ evaluation: ev, historicalResult: d.result, showMarkCard: false, showContext: false }));
  assert.ok(t.includes('No feedback was saved for this submission'));
  assert.ok(t.includes('No concept map was saved for this submission'));
  assert.ok(t.includes('Marking by criterion') && t.includes('Concept diagnosis'));
  const ev2 = JSON.parse(JSON.stringify(d.result.ai_evaluation));
  ev2.mindmap = { nodes: [] };
  ev2.analysis.concept_matches = [];
  const t2 = text(render({ evaluation: ev2, historicalResult: d.result, showMarkCard: false, showContext: false }));
  assert.ok(t2.includes('No concepts were found in the answer to build a map from'));
  assert.ok(t2.includes('no expected concepts'));
});

test('proposed versus final mark and status are labelled from the stored result', () => {
  const d = fx('subjective_lecturer_detail');
  const ev = d.result.ai_evaluation;
  const pending = text(render({ evaluation: ev, historicalResult: { ...d.result, status: 'pending_review', final_mark: null }, showMarkCard: true, showContext: false }));
  assert.ok(pending.includes('Proposed mark') && pending.includes('Awaiting review') && !pending.includes('Final result'));
  const reviewed = text(render({ evaluation: ev, historicalResult: { ...d.result, status: 'reviewed', lecturer_decision: 'accepted', final_mark: d.result.automated_mark }, showMarkCard: true, showContext: false }));
  assert.ok(reviewed.includes('Reviewed') && reviewed.includes('Proposed mark'));
  const fin = text(render({ evaluation: ev, historicalResult: { ...d.result, status: 'finalized', lecturer_decision: 'overridden', final_mark: 1, override_reason: 'Checked by hand', reviewed_by: 'lecturer1' }, showMarkCard: true, showContext: false }));
  assert.ok(fin.includes('Final result') && fin.includes('Finalized') && fin.includes('Checked by hand') && fin.includes('Automatic mark:'));
});

test('student fixtures match the current API contract: protected configuration keys are absent, not null', () => {
  const detail = fx('mcq_student_detail');
  for (const k of ['reference_answer', 'expected_concepts', 'correct_options', 'rubric']) {
    assert.ok(!(k in detail.submission), `${k} must not appear in a student submission`);
  }
});

test('source badge: only sample/test submissions get a badge, as an inline c3-source-badge (never the global .chip)', () => {
  assert.strictEqual(sourceKind({ is_demo: true }), 'sample');
  assert.strictEqual(sourceKind({ provenance: 'pp1_demo' }), 'sample');
  assert.strictEqual(sourceKind({ provenance: 'test_fixture' }), 'test');
  assert.strictEqual(sourceKind({ status: 'failed' }), 'test');
  assert.strictEqual(sourceKind({ student_id: 'IT1' }), 'student');
  assert.strictEqual(h({ submission: { student_id: 'IT1' } }), '');
  const html = h({ submission: { is_demo: true } });
  assert.ok(/class="c3-source-badge sample"/.test(html) && text(html).trim() === 'Sample', html);
  assert.ok(!/chip/.test(html), 'must not use the global .chip class');
  const css = fs.readFileSync(path.join(here, '..', 'src', 'pages', 'c3', 'c3.css'), 'utf8');
  const rule = css.match(/\.c3-source-badge \{[^}]*\}/)[0];
  assert.ok(/position:\s*static/.test(rule) && !/(absolute|fixed|animation)/.test(rule), 'badge must stay in normal flow');
});

// Static guard only: the behavioural proof is browser step L28 (real keystrokes), because server rendering cannot run effects.
test('Dialog keeps the latest onClose in a ref so typing does not re-run its focus set-up', () => {
  const src = fs.readFileSync(path.join(here, '..', 'src', 'pages', 'c3', 'components', 'c3ui.jsx'), 'utf8');
  const dialog = src.slice(src.indexOf('export function Dialog'), src.indexOf('export function ConfirmDialog'));
  assert.ok(/closeRef\.current = onClose/.test(dialog), 'onClose must be stored in a ref');
  assert.ok(!/\},\s*\[onClose\]\)/.test(dialog), 'the focus effect must not depend on onClose (it is a new function on every render)');
});
