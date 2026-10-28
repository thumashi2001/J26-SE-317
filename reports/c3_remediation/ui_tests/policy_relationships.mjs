// E2E checks for the contradiction policy and typed mind-map relationships (API + browser), against an ISOLATED stack.
//
//   (set the guard variables: see README.md; C3_WEB_BASE is required because this script drives Chrome)
//   Start the C3 Python service with the policy under test, for example
//     C3_CONTRADICTION_POLICY=warn_only        (or leave it unset: the default)
//     C3_CONTRADICTION_POLICY=withhold_credit
//   node policy_relationships.mjs <warn_only|withhold_credit> out.json
//
// The first argument is the policy the service was started with. The script first proves the service really runs that policy
// (analysis.contradiction_check), so a mismatch fails instead of passing by accident. It writes test submissions to the isolated
// database only (guard.mjs refuses anything else). Contradiction detection is a heuristic; these checks assert the wiring and
// the policy behaviour on hand-written answers, not detection accuracy.
import fs from 'node:fs';
import { config, verifyIsolation } from './guard.mjs';
import { ACCOUNTS, BASE, launch, login } from './ui.mjs';

const POLICY = process.argv[2];
const OUT = process.argv[3] || `policy_relationships_${POLICY}.json`;
if (!['warn_only', 'withhold_credit'].includes(POLICY)) { console.error('first argument must be warn_only or withhold_credit'); process.exit(2); }
await verifyIsolation({ needsWeb: true });

const B = config.apiBase;
const rows = [];
const check = (id, desc, ok, note = '') => { rows.push({ id, desc, status: ok ? 'Passed' : 'FAILED', note: String(note).slice(0, 300) }); console.log(ok ? 'PASS' : 'FAIL', id, desc, ok ? '' : `-> ${note}`); };
const call = async (t, m, p, body) => {
  const r = await fetch(B + p, { method: m, headers: { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await r.text(); let json = null; try { json = JSON.parse(text); } catch { /* not json */ }
  return { status: r.status, json };
};
const token = async (u) => (await call(null, 'POST', '/auth/login', { userId: u, password: config.password })).json.token;
const ts = await token(ACCOUNTS.student.id);
const tl = await token(ACCOUNTS.lecturer.id);
const DEMO = 'arch-full'; // server bank: concepts "high-level structure", "components", "relationships"; max 4

const ANSWERS = {
  affirmed: 'Software architecture defines the high-level structure of a system. It organizes components and specifies their relationships clearly.',
  denied: 'Architecture has no high-level structure. It does not organize components and there are no relationships.',
  typed: 'The components are part of the high-level structure.',
  negatedRelation: 'The components are not part of the high-level structure.',
};
const submit = async (answer) => (await call(ts, 'POST', '/c3/assess', { demo_id: DEMO, student_answer: answer }));
const evalOf = (r) => r.json?.ai_evaluation || r.json?.result?.ai_evaluation || r.json;
// ---- API: policy behaviour -------------------------------------------------------------------------------------------
const affirmed = await submit(ANSWERS.affirmed);
const evA = evalOf(affirmed);
check('P0', `service reports the policy under test (${POLICY})`, evA?.analysis?.contradiction_check === `negation-cue-v1/${POLICY}`, evA?.analysis?.contradiction_check);
check('P1', 'affirmed answer: full rubric mark and no flag', evA?.total_awarded_marks === 4 && !evA.analysis.concept_matches.some((c) => c.contradicted), evA?.total_awarded_marks);

const denied = await submit(ANSWERS.denied);
const deniedId = denied.json?.submission_id;
const evD = evalOf(denied);
const flagged = evD?.analysis?.concept_matches?.filter((c) => c.contradicted) || [];
check('P2', 'denied answer: concepts are flagged as possible contradictions', flagged.length === 3, flagged.length);
const expectedMark = POLICY === 'warn_only' ? 4 : 0;
check('P3', POLICY === 'warn_only' ? 'warn_only: the flag does not change the rubric mark (same as the affirmed answer)' : 'withhold_credit: negated concepts earn no credit', evD?.total_awarded_marks === expectedMark, evD?.total_awarded_marks);
check('P4', 'the lecturer-facing warning names the policy effect', (evD?.analysis?.warnings || []).some((w) => /Possible contradiction/.test(w) && (POLICY === 'warn_only' ? /NOT withheld/.test(w) : /no credit given/.test(w))), (evD?.analysis?.warnings || [])[0]);
const fb = evD?.feedback?.criteria_feedback?.[0];
check('P5', 'feedback lists contradicted concepts; missing list matches the policy', fb && fb.contradicted_concepts.length === 3 && (POLICY === 'warn_only' ? (fb.missing_concepts.length === 0 && fb.demonstrated_concepts.length === 3) : fb.demonstrated_concepts.length === 0), JSON.stringify({ c: fb?.contradicted_concepts, m: fb?.missing_concepts, d: fb?.demonstrated_concepts }));
check('P6', 'the student response never exposes the AI estimate or review history', !JSON.stringify(denied.json).includes('ai_estimate') && !JSON.stringify(denied.json).includes('review_history'));

// ---- API: typed relationships -----------------------------------------------------------------------------------------
const typedResponse = await submit(ANSWERS.typed);
const typedId = typedResponse.json?.submission_id;
const typed = evalOf(typedResponse);
const rel = (typed?.mindmap?.relationships || []).filter((r) => r.relationship_type !== 'child');
check('R1', 'a fixed cue phrase gives a typed, directed relation with evidence', rel.length === 1 && rel[0].relationship_type === 'part_of' && /cue phrase/.test(rel[0].evidence || '') && /not whether it is correct/.test(rel[0].evidence || ''), JSON.stringify(rel));
check('R2', 'typing does not change the rubric mark', typed?.marking?.criteria_results?.[0]?.awarded_mark === typed?.total_awarded_marks, typed?.total_awarded_marks);
const negRel = evalOf(await submit(ANSWERS.negatedRelation));
const relN = (negRel?.mindmap?.relationships || []).filter((r) => r.relationship_type !== 'child');
check('R3', 'a negated cue is not typed (stays mentioned together or absent)', relN.every((r) => r.relationship_type === 'co_mentioned'), JSON.stringify(relN.map((r) => r.relationship_type)));

// ---- Browser: lecturer review page and student view --------------------------------------------------------------------
const browser = await launch();
try {
  check('B0', 'the assess responses returned submission ids', Boolean(deniedId && typedId), `${deniedId} ${typedId}`);
  const lec = await login(browser, 'lecturer');
  await lec.page.goto(`${BASE}/lecturer/c3/${deniedId}`);
  await lec.page.waitForLoadState('networkidle');
  const text = await lec.page.innerText('body');
  check('B1', 'lecturer concept table shows the possible-contradiction note', /Possible contradiction: the answer seems to deny this/.test(text));
  check('B2', POLICY === 'warn_only' ? 'warn_only: the lecturer sees the full rubric mark with the warning' : 'withhold_credit: the lecturer sees the withheld mark with the warning', POLICY === 'warn_only' ? /4\s*\/\s*4/.test(text) : /0\s*\/\s*4/.test(text), text.match(/\d+\s*\/\s*4/)?.[0]);
  await lec.page.goto(`${BASE}/lecturer/c3/${typedId}`);
  await lec.page.waitForLoadState('networkidle');
  await lec.page.click('g[aria-label^="components:"]');
  const inspector = await lec.page.innerText('.c3-node-inspector');
  check('B3', 'mind-map inspector lists the typed relation as the student wrote it', /Relationships as the student wrote them/.test(inspector) && /Is part of/.test(inspector) && /not whether it is correct/.test(inspector), inspector.slice(0, 200));
  check('B4', 'no page errors on the review pages', lec.logs.length === 0, lec.logs.join(' | '));
  await lec.ctx.close();
} finally {
  await browser.close();
}

const failed = rows.filter((r) => r.status !== 'Passed').length;
fs.writeFileSync(OUT, JSON.stringify({ policy: POLICY, rows }, null, 2));
console.log(`\nTOTAL ${rows.length}  PASSED ${rows.length - failed}  FAILED ${failed}  (policy ${POLICY})`);
process.exit(failed ? 1 : 0);
