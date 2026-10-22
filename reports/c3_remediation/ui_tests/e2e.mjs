import fs from 'node:fs';
import { config, connectTestDb, verifyIsolation } from './guard.mjs';
import { BASE, ACCOUNTS, launch, login } from './ui.mjs';

const OUT = process.argv[2];
fs.mkdirSync(OUT, { recursive: true });
const results = [];
const FORBIDDEN_TEXT = /Component 3|integrated-v1|Function 1|F1 →|PP1 Demo|Curriculum Benchmarks|Test Fixtures|baseline-v1|pipeline_version/i;

async function step(id, role, desc, fn) {
  const t0 = Date.now();
  try {
    const note = await fn();
    results.push({ id, role, desc, status: 'Passed', note: note || '' , ms: Date.now() - t0 });
    console.log('PASS', id, desc);
  } catch (e) {
    results.push({ id, role, desc, status: 'Failed', note: String(e.message).split('\n')[0].slice(0, 300), ms: Date.now() - t0 });
    console.log('FAIL', id, desc, '::', String(e.message).split('\n')[0].slice(0, 200));
  }
}
const expect = (cond, msg) => { if (!cond) throw new Error(msg); };
const shot = (page, name) => page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true }).catch(() => {});
const bodyText = (page) => page.evaluate(() => document.body.textContent.replace(/\s+/g, ' '));
async function apiLogin(role) {
  const r = await fetch(`${config.apiBase}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ userId: ACCOUNTS[role].id, password: ACCOUNTS[role].pw }) });
  return (await r.json()).token;
}
async function http(token, method, path, body) {
  const r = await fetch(`${config.apiBase}${path}`, { method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }, body: body ? JSON.stringify(body) : undefined });
  let j = null; try { j = await r.json(); } catch { /* none */ }
  return { status: r.status, json: j };
}
const KEY_LEAK = /authoritative|answer key|Correct: Option|Key: |requires_key|correct_labels/i;
const SECTIONS = ['Marking by criterion', 'Concept diagnosis', 'Feedback', 'Concept map'];
async function mongo() {
  const { client, db } = await connectTestDb(); // loopback-only URI and a validated disposable database name
  return { c: client, db };
}
const go = async (page, path) => { await page.goto(BASE + path); await page.waitForLoadState('networkidle'); await page.waitForTimeout(400); };

// Abort before any test write unless the backend is proven to use the same local test database.
await verifyIsolation({ needsWeb: true });

let browser = await launch();

// ============================== STUDENT ==============================
{
  const { ctx, page, logs } = await login(browser, 'student');
  const posts = [];
  page.on('request', (r) => { if (r.method() === 'POST' && r.url().includes('/c3/assess')) posts.push(r.postData()); });

  logs.length = 0; // C1 dashboard errors from the empty local fixture database are out of scope for C3
  await step('S1', 'student', 'Landing page /c3 shows the task title and the assessment picker', async () => {
    await go(page, '/c3');
    const t = await bodyText(page);
    expect(/Automated Marking & Answer Analysis/.test(t), 'title missing');
    expect(await page.locator('.c3-pick').count() >= 5, 'assessment picker has fewer than 5 items');
    await shot(page, 'student_01_landing');
    return `${await page.locator('.c3-pick').count()} assessments`;
  });
  await step('S1b', 'student', 'Nothing is preselected: no answer form and no selected card before the student chooses, and the instruction is shown', async () => {
    await go(page, '/c3');
    await page.locator('.c3-pick').first().waitFor({ timeout: 8000 });
    expect(await page.locator('form[aria-label="Your answer"]').count() === 0, 'an answer form is shown before any selection');
    expect(await page.locator('.c3-pick[aria-pressed=true]').count() === 0, 'a card is preselected');
    expect(await page.locator('#ans, input[type=radio][name=option]').count() === 0, 'answer inputs are present before selection');
    const t = await bodyText(page);
    expect(t.includes('Choose an assessment to start.'), 'instruction missing');
    expect(t.includes('C2 assessments are not available yet.'), 'C2 notice missing');
    expect(posts.length === 0, 'a request was sent before the student chose');
    await shot(page, 'student_00_nothing_preselected');
  });
  await step('S2', 'student', 'No component/version/prototype labels on student screen', async () => {
    const t = await bodyText(page);
    expect(!FORBIDDEN_TEXT.test(t), 'forbidden label found: ' + (t.match(FORBIDDEN_TEXT) || [])[0]);
  });
  await step('S3', 'student', 'No reference answer, rubric editor, answer key or expected concepts on the answer form', async () => {
    await page.locator('.c3-pick[data-source=demo]', { hasText: 'Written answer' }).first().click();
    await page.locator('form[aria-label="Your answer"]').waitFor({ timeout: 5000 });
    const t = await bodyText(page);
    expect(!/Reference|Inspect Rubric|Expected Domain Concepts|Active Rubric|correct answer/i.test(t), 'protected wording visible');
  });
  await step('S4', 'student', 'Empty submission shows an inline error and sends nothing', async () => {
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await page.locator('#ans-err').waitFor({ timeout: 3000 });
    expect(posts.length === 0, 'a request was sent for an empty answer');
    await shot(page, 'student_02_empty_error');
  });
  await step('S5', 'student', 'Submit example answer for the first written assessment: result, criteria, concept diagnosis, map', async () => {
    // choose a demo written assessment explicitly: nothing is preselected
    await page.locator('.c3-pick[data-source=demo]', { hasText: 'Written answer' }).first().click();
    await page.getByRole('button', { name: 'Insert an example answer' }).click();
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await page.locator('.c3-mark-card').first().waitFor({ timeout: 20000 });
    const t = await bodyText(page);
    expect(/Marking by criterion/.test(t), 'criteria section missing');
    expect(/Concept diagnosis/.test(t), 'concept diagnosis missing');
    expect(await page.locator('.c3-mindmap-container').count() === 1, 'concept map missing');
    expect(/Awaiting review/.test(t), 'status pill missing');
    expect(!FORBIDDEN_TEXT.test(t), 'forbidden label in result');
    await shot(page, 'student_03_result');
    const m = t.match(/(\d+(?:\.\d+)?)\s*\/\s*(\d+)/);
    return `mark ${m ? m[0] : '?'}`;
  });
  await step('S6', 'student', 'Assess request body contains only the preset id and the answer', async () => {
    expect(posts.length >= 1, 'no assess request captured');
    const keys = Object.keys(JSON.parse(posts[0])).sort();
    expect(JSON.stringify(keys) === JSON.stringify(['demo_id', 'student_answer']), 'body keys: ' + keys.join(','));
    return keys.join(',');
  });
  await step('S7', 'student', 'Concept map: select a node shows evidence panel; list alternative exists', async () => {
    await page.locator('.c3-mm-node.demonstrated, .c3-mm-node.partial, .c3-mm-node.missing').first().click();
    await page.locator('.c3-node-inspector').waitFor({ timeout: 3000 });
    expect(await page.locator('details.c3-mm-list').count() === 1, 'list alternative missing');
  });
  await step('S8', 'student', 'MCQ assessment: pick option, submit, result shown', async () => {
    await page.getByRole('button', { name: 'Answer another question' }).click();
    await page.locator('.c3-pick', { hasText: 'Multiple choice' }).first().click();
    await page.locator('input[type=radio]').first().check();
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await page.locator('.c3-mark-card').first().waitFor({ timeout: 20000 });
    await shot(page, 'student_04_mcq_result');
    expect(logs.filter((l) => l.includes('pageerror') && !l.includes('@/c1/')).length === 0, 'page error: ' + logs.join(' | '));
  });
  await step('S9', 'student', 'My submissions lists both and opens a detail view without reference answer', async () => {
    await page.getByRole('tab', { name: /My submissions/ }).click();
    await page.locator('table.c3-table tbody tr').first().waitFor({ timeout: 5000 });
    expect(await page.locator('table.c3-table tbody tr').count() >= 2, 'fewer than 2 history rows');
    await page.getByRole('button', { name: 'Open' }).first().click();
    await page.getByText('Marking by criterion').first().waitFor({ timeout: 8000 });
    const t = await bodyText(page);
    expect(!/Reference answer/i.test(t), 'reference answer visible to student');
    await shot(page, 'student_05_history_detail');
  });
  await step('S17', 'student', 'MCQ result and MCQ history detail contain no correct-option information and no concept map', async () => {
    await go(page, '/c3');
    await page.locator('.c3-pick', { hasText: 'Multiple choice' }).first().click();
    await page.locator('input[type=radio]').first().check();
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await page.locator('.c3-mark-card').first().waitFor({ timeout: 20000 });
    let t = await bodyText(page);
    expect(!KEY_LEAK.test(t), 'live MCQ result leaks: ' + (t.match(KEY_LEAK) || [])[0]);
    expect(/Your selected option is (not )?correct/.test(t), 'outcome sentence missing');
    expect(/Not produced for multiple-choice questions/.test(t), 'unavailable note for concepts/map missing');
    expect(await page.locator('.c3-mindmap-container').count() === 0, 'MCQ map drawn');
    await shot(page, 'student_09_mcq_result_redacted');
    await page.getByRole('button', { name: 'View my submissions' }).click();
    await page.locator('table.c3-table tbody tr').first().waitFor();
    await page.getByRole('button', { name: 'Open' }).first().click();
    await page.locator('.c3-mark-card').first().waitFor({ timeout: 8000 });
    t = await bodyText(page);
    expect(!KEY_LEAK.test(t), 'MCQ history detail leaks: ' + (t.match(KEY_LEAK) || [])[0]);
    await shot(page, 'student_10_mcq_history_redacted');
  });
  await step('S19', 'student', 'Assessments list 404 shows an explicit message; Try again re-requests and then loads the list', async () => {
    let calls = 0;
    let failing = true; // the dev server runs effects twice (StrictMode), so fail every call until we flip this
    await page.route('**/api/v1/c3/assessments', (r) => {
      calls += 1;
      if (failing) return r.fulfill({ status: 404, contentType: 'text/html', body: '<html>Cannot GET</html>' });
      return r.continue();
    });
    await go(page, '/c3');
    await page.getByText('Assessments unavailable').waitFor({ timeout: 5000 });
    const t = await bodyText(page);
    expect(/restart it/.test(t) && !/We could not find that item/.test(t), 'message not explicit: ' + t.slice(0, 200));
    expect(await page.locator('.c3-pick').count() === 0, 'list shown despite the error');
    await shot(page, 'student_11_assessments_404');
    const before = calls;
    failing = false;
    await page.getByRole('button', { name: 'Try again' }).click();
    await page.locator('.c3-pick').first().waitFor({ timeout: 8000 });
    expect(calls > before, 'retry did not re-request: ' + calls);
    await page.unroute('**/api/v1/c3/assessments');
  });
  await step('S20', 'student', 'Only demo assessments are listed (no lecturer group or badge even though a lecturer batch exists), the C2-unavailable notice is shown, nothing claims C2, no key or rubric is visible, and a demo MCQ can be selected and submitted', async () => {
    const tl0 = await apiLogin('lecturer');
    const mk = await http(tl0, 'POST', '/c3/batch/setup', { title: 'Lecturer batch must stay hidden', question_id: 'SRC-1', question_text: 'Which style uses independently deployable services?', answer_type: 'mcq', max_marks: 2, correct_answer: 'B', options: [{ option_id: 'A', label: 'A', text: 'Monolith' }, { option_id: 'B', label: 'B', text: 'Microservices' }] });
    expect(mk.status === 200, 'could not create the lecturer batch ' + mk.status);
    await go(page, '/c3');
    await page.locator('.c3-pick').first().waitFor({ timeout: 8000 });
    const t = await bodyText(page);
    expect(t.includes('C2 assessments are not available yet. The assessments currently shown are demo assessments.'), 'C2 notice missing');
    expect(!/Set by your lecturer|Lecturer-created|Lecturer batch must stay hidden/.test(t), 'a lecturer group, badge or batch is visible to the student');
    const groups = await page.evaluate(() => [...document.querySelectorAll('[role=group]')].map((g) => ({ name: g.getAttribute('aria-label'), cards: [...g.querySelectorAll('.c3-pick')].map((c) => ({ src: c.dataset.source, badge: c.querySelector('.c3-source-badge')?.textContent })) })));
    expect(groups.length === 1 && groups[0].name === 'Demo assessments (practice examples)', 'expected exactly one demo group: ' + JSON.stringify(groups.map((g) => g.name)));
    expect(groups[0].cards.length === 7 && groups[0].cards.every((c) => c.src === 'demo' && c.badge === 'Demo'), 'demo cards wrong: ' + JSON.stringify(groups[0].cards));
    expect(await page.locator('.c3-pick[aria-pressed=true]').count() === 0, 'a card is preselected');
    const cardText = await page.locator('.c3-picker').allInnerTexts();
    expect(!cardText.some((x) => /C2/.test(x)), 'a card mentions C2');
    expect(!/correct_answer|scoring_level|required_concepts|reference answer|answer key/i.test(t), 'protected marking information is visible');
    await shot(page, 'student_12_assessment_sources');
    await page.locator('.c3-pick[data-source=demo]', { hasText: 'Multiple choice' }).first().click();
    await page.locator('input[type=radio]').first().check();
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await page.locator('.c3-mark-card').waitFor({ timeout: 10000 });
    const rt = await bodyText(page);
    expect(!/Authoritative key|correct_option|answer key/i.test(rt), 'key visible in the result');
  });
  await step('S21', 'student', 'Explicitly selecting a demo card opens exactly that assessment (two different demo cards checked)', async () => {
    await go(page, '/c3');
    await page.locator('.c3-pick').first().waitFor({ timeout: 8000 });
    expect(await page.locator('form[aria-label="Your answer"]').count() === 0, 'form visible before selection');
    const api = (await http(await apiLogin('student'), 'GET', '/c3/assessments')).json.assessments;
    expect(api.length === 7 && api.every((a) => a.kind === 'demo'), 'API must list only the 7 demo assessments');
    for (const card of [api[0], api[api.length - 1]]) {
      await page.locator('.c3-pick', { hasText: card.title }).first().click();
      await page.locator('form[aria-label="Your answer"]').waitFor({ timeout: 5000 });
      const shown = (await page.locator('.c3-question p').first().innerText()).trim();
      expect(shown === card.question_text.trim(), `wrong question opened for "${card.title}": ${shown.slice(0, 60)}`);
      expect(await page.locator('.c3-pick[aria-pressed=true]').count() === 1, 'exactly one card must be selected');
    }
  });
  await step('S22', 'student', 'A 404 on submit shows an actionable message (not the generic "could not find that item") and re-requests the list', async () => {
    await go(page, '/c3');
    await page.locator('.c3-pick[data-source=demo]', { hasText: 'Written answer' }).first().click();
    await page.locator('#ans').fill('Architecture has components.');
    let listCalls = 0;
    await page.route('**/api/v1/c3/assess', (r) => r.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: 'Unknown demo assessment' }) }));
    await page.route('**/api/v1/c3/assessments', (r) => { listCalls += 1; return r.continue(); });
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await page.getByText(/restart the backend/).waitFor({ timeout: 5000 });
    const t = await bodyText(page);
    expect(!/We could not find that item/.test(t), 'generic message still shown');
    expect(listCalls >= 1, 'the list was not re-requested');
    await page.unroute('**/api/v1/c3/assess');
    await page.unroute('**/api/v1/c3/assessments');
  });
  await step('S10', 'student', 'API failure on submit shows a friendly message with retry (no stack, no port)', async () => {
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.route('**/api/v1/c3/assess', (r) => r.fulfill({ status: 502, contentType: 'application/json', body: JSON.stringify({ error: 'AI service unreachable at http://127.0.0.1:8003' }) }));
    await page.locator('.c3-pick[data-source=demo]', { hasText: 'Written answer' }).first().click();
    await page.getByRole('button', { name: 'Insert an example answer' }).click();
    await page.getByRole('button', { name: 'Submit answer' }).click();
    await page.getByText('Could not mark your answer').waitFor({ timeout: 5000 });
    const t = await bodyText(page);
    expect(!/8003|127\.0\.0\.1|stack/i.test(t), 'internal detail exposed: ' + (t.match(/8003|127\.0\.0\.1|stack/i) || [])[0]);
    expect(await page.getByRole('button', { name: 'Try again' }).count() === 1, 'retry missing');
    await shot(page, 'student_06_api_error');
    await page.unroute('**/api/v1/c3/assess');
  });
  await step('S11', 'student', 'Assessments list failure shows retry', async () => {
    await page.route('**/api/v1/c3/assessments', (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"x"}' }));
    await page.reload();
    await page.getByText('Assessments unavailable').waitFor({ timeout: 5000 });
    await page.unroute('**/api/v1/c3/assessments');
  });
  for (const [id, path] of [['S12a', '/lecturer'], ['S12b', '/lecturer/c3'], ['S12c', '/lecturer/c3/batch'], ['S12d', '/c3/batch'], ['S12e', '/c3/review'], ['S12f', '/admin'], ['S12g', '/admin/lecturers']]) {
    await step(id, 'student', `Direct URL ${path} does not open lecturer/admin pages`, async () => {
      await go(page, path);
      const url = new URL(page.url()).pathname;
      const t = await bodyText(page);
      expect(!/^\/(lecturer|admin)/.test(url), 'stayed on ' + url);
      expect(!/Batch Marking|Marking Review|Lecturer approvals/i.test(t), 'lecturer/admin content rendered');
      return `redirected to ${url}`;
    });
  }
  await step('S13', 'student', 'Responsive layout at 375px and 768px: no horizontal scroll', async () => {
    for (const w of [375, 768]) {
      await page.setViewportSize({ width: w, height: 800 });
      await go(page, '/c3');
      const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      await shot(page, `student_resp_${w}`);
      expect(over <= 2, `horizontal overflow ${over}px at ${w}px`);
    }
    await page.setViewportSize({ width: 1280, height: 800 });
  });
  await step('S14', 'student', 'Dark theme renders the picker and result with readable colours', async () => {
    await go(page, '/c3');
    await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
    await page.waitForTimeout(300);
    await shot(page, 'student_07_dark');
    const bg = await page.evaluate(() => getComputedStyle(document.querySelector('.c3-pick')).backgroundColor);
    expect(bg !== 'rgb(255, 255, 255)', 'picker card still white in dark mode: ' + bg);
    await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  });
  await step('S15', 'student', 'Keyboard: assessment cards and Submit are reachable with Tab; focus ring visible', async () => {
    await go(page, '/c3');
    await page.keyboard.press('Tab');
    let hit = false;
    for (let i = 0; i < 30 && !hit; i++) { await page.keyboard.press('Tab'); hit = await page.evaluate(() => document.activeElement?.classList?.contains('c3-pick')); }
    expect(hit, 'could not reach an assessment card with Tab');
  });
  console.log('student console errors:', logs);
  results.push({ id: 'S-console', role: 'student', desc: 'Browser console/page errors during student session', status: logs.filter((l) => l.includes('pageerror') && !l.includes('@/c1/')).length ? 'Failed' : 'Passed', note: logs.slice(0, 4).join(' | ').slice(0, 300), ms: 0 });
  await ctx.close();
}

// ============================== LECTURER ==============================
await browser.close(); browser = await launch();
{
  const { ctx, page, logs } = await login(browser, 'lecturer');
  await step('L1', 'lecturer', 'Overview shows tool cards without "Component N" chips', async () => {
    await go(page, '/lecturer');
    const t = await bodyText(page);
    expect(!/Component [1-4]/.test(t), 'component chip still shown');
    await shot(page, 'lecturer_01_overview');
  });
  await step('L2', 'lecturer', 'Batch Marking header, stepper present; no component/version labels', async () => {
    await go(page, '/lecturer/c3/batch');
    const t = await bodyText(page);
    expect(/Batch Marking/.test(t) && /Assessment setup/.test(t) && /Student answers/.test(t) && /Validate and confirm/.test(t) && /Results and review/.test(t), 'headings/steps missing');
    expect(!FORBIDDEN_TEXT.test(t), 'forbidden label: ' + (t.match(FORBIDDEN_TEXT) || [])[0]);
    await shot(page, 'lecturer_02_batch_setup');
  });
  await step('L3', 'lecturer', 'Saving an empty setup shows inline validation errors', async () => {
    await page.getByRole('button', { name: 'Save setup and add answers' }).click();
    await page.locator('#title-err').waitFor({ timeout: 3000 });
    expect(await page.locator('#questionText-err').count() === 1 && await page.locator('#maxMarks-err').count() === 1, 'missing field errors');
    await shot(page, 'lecturer_03_setup_errors');
  });
  await step('L4', 'lecturer', 'Rubric marks mismatch is flagged before saving', async () => {
    await page.getByRole('button', { name: 'Start from an example' }).count();
    await page.getByRole('button', { name: /Software Architecture — Comprehensive Analysis/ }).click();
    await page.locator('#b-max').fill('9');
    await page.getByRole('button', { name: 'Save setup and add answers' }).click();
    await page.getByText('must add up to the total marks').first().waitFor({ timeout: 3000 });
    await page.locator('#b-max').fill('4');
  });
  await step('L5', 'lecturer', 'Valid setup saves and opens Student answers', async () => {
    await page.getByRole('button', { name: 'Save setup and add answers' }).click();
    await page.getByRole('heading', { name: 'Student answers' }).waitFor({ timeout: 8000 });
  });
  await step('L6', 'lecturer', 'Example rows are checked: invalid and duplicate rows are listed', async () => {
    await page.getByRole('button', { name: 'Fill example rows' }).click();
    await page.getByRole('button', { name: 'Check answers' }).click();
    await page.getByRole('heading', { name: 'Check results' }).waitFor({ timeout: 8000 });
    const t = await bodyText(page);
    expect(/Duplicate student ID/.test(t) && /empty/i.test(t), 'duplicate/empty problems not listed');
    await shot(page, 'lecturer_04_check');
  });
  await step('L7', 'lecturer', 'Marking runs and the results table lists students with automatic marks', async () => {
    await page.getByRole('button', { name: /^Mark \d+ answer/ }).click();
    await page.getByText('Marking complete').waitFor({ timeout: 60000 });
    expect(await page.locator('table.c3-table tbody tr').count() >= 2, 'fewer than 2 result rows');
    await shot(page, 'lecturer_05_results');
  });
  await step('L22', 'lecturer', 'Batch "View analysis" dialog shows submitted answer, marks/status and the full analysis', async () => {
    await page.getByRole('button', { name: 'View analysis', exact: true }).first().click();
    const dlg = page.getByRole('dialog');
    await dlg.waitFor();
    await page.locator('.c3-mark-big').first().waitFor();
    const t = await dlg.evaluate((el) => el.textContent.replace(/\s+/g, ' '));
    expect(/Question and answer/.test(t) && /(cohesion|coupling|modules|architecture)/i.test(t), 'submitted answer missing in dialog');
    for (const sec of SECTIONS) expect(t.includes(sec), 'dialog missing section: ' + sec);
    expect(/Automatic mark/.test(t) && /Awaiting review|Reviewed|Finalized/.test(t), 'marks/status missing');
    expect(/Evidence in the answer/.test(t), 'criterion evidence missing');
    expect(await dlg.locator('.c3-mindmap-container').count() === 1, 'map missing in dialog');
    await page.setViewportSize({ width: 1280, height: 2600 });
    await page.waitForTimeout(300);
    await shot(page, 'lecturer_15_batch_inspect_analysis');
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({ state: 'detached', timeout: 3000 });
  });
  await step('L8', 'lecturer', 'Review dialog: invalid override shows errors; valid override saves', async () => {
    await page.getByRole('button', { name: 'View analysis', exact: true }).first().click();
    await page.getByRole('dialog').waitFor();
    await page.locator('#i-mark').fill('999');
    await page.getByRole('button', { name: 'Save changed mark' }).click();
    await page.getByText(/Enter a mark between 0 and/).waitFor({ timeout: 3000 });
    await page.getByText(/Give a reason/).waitFor({ timeout: 3000 });
    await page.locator('#i-mark').fill('1');
    await page.locator('#i-reason').fill('Checked by hand against the rubric');
    await page.getByRole('button', { name: 'Save changed mark' }).click();
    await page.getByText('Mark changed and the reason saved.').waitFor({ timeout: 8000 });
    await shot(page, 'lecturer_06_dialog_override');
  });
  await step('L9', 'lecturer', 'Finalize one result from the dialog; finalized result cannot be edited', async () => {
    await page.getByRole('button', { name: 'Finalize', exact: true }).click();
    await page.getByText('Result finalized.').waitFor({ timeout: 8000 });
    expect(await page.getByRole('button', { name: 'Save changed mark' }).count() === 0, 'edit controls still present after finalize');
  });
  await step('L10', 'lecturer', 'Escape closes the dialog and returns focus', async () => {
    await page.keyboard.press('Escape');
    await page.getByRole('dialog').waitFor({ state: 'detached', timeout: 3000 });
  });
  await step('L11', 'lecturer', 'Finalize reviewed asks for confirmation; cancel keeps results unfinalized', async () => {
    await page.getByRole('button', { name: 'Finalize reviewed' }).click();
    await page.getByRole('dialog', { name: /Finalize reviewed results/ }).waitFor();
    await page.getByRole('button', { name: 'Cancel' }).click();
    await page.getByRole('dialog').waitFor({ state: 'detached', timeout: 3000 });
  });
  await step('L11b', 'lecturer', 'Finalize reviewed refuses to finalize results the lecturer has not reviewed (409 shown)', async () => {
    await page.getByRole('button', { name: 'Finalize reviewed' }).click();
    await page.getByRole('button', { name: 'Finalize reviewed' }).last().click();
    await page.getByText(/No reviewed results to finalize/).waitFor({ timeout: 8000 });
    await page.getByRole('button', { name: 'Refresh' }).click();
    await page.waitForTimeout(600);
    const pills = await page.locator('table.c3-table tbody .pill').allInnerTexts();
    expect(pills.some((p) => p !== 'Finalized'), 'unreviewed results must stay pending, got: ' + pills.join(','));
  });
  await step('L12', 'lecturer', 'After the lecturer reviews the remaining results, Finalize reviewed finalizes every result', async () => {
    const n = await page.getByRole('button', { name: 'View analysis', exact: true }).count();
    for (let i = 1; i < n; i++) {
      await page.getByRole('button', { name: 'View analysis', exact: true }).nth(i).click();
      await page.getByRole('dialog').waitFor();
      await page.getByRole('button', { name: 'Accept automatic mark' }).click();
      await page.getByText(/Automatic mark accepted|accepted/i).first().waitFor({ timeout: 8000 });
      await page.keyboard.press('Escape');
      await page.getByRole('dialog').waitFor({ state: 'detached', timeout: 3000 });
    }
    await page.getByRole('button', { name: 'Finalize reviewed' }).click();
    await page.getByRole('button', { name: 'Finalize reviewed' }).last().click();
    await page.getByText(/reviewed results? finalized\./).waitFor({ timeout: 8000 });
    await page.getByRole('button', { name: 'Refresh' }).click();
    await page.waitForTimeout(600);
    const pills = await page.locator('table.c3-table tbody .pill').allInnerTexts();
    expect(pills.length > 0 && pills.every((p) => p === 'Finalized'), 'not all finalized: ' + pills.join(','));
    await shot(page, 'lecturer_07_all_finalized');
  });
  await step('L13', 'lecturer', 'Past batches lists the batch and reopens its results', async () => {
    await page.getByRole('button', { name: 'Past batches' }).click();
    await page.locator('table.c3-table tbody tr').first().waitFor({ timeout: 5000 });
    await shot(page, 'lecturer_08_past');
    await page.getByRole('button', { name: 'Open' }).first().click();
    await page.getByText('Marked answers').first().waitFor({ state: 'attached', timeout: 8000 });
  });
  await step('L14', 'lecturer', 'MCQ batch: setup, check, mark and inspect without page errors', async () => {
    await page.getByRole('button', { name: 'New batch', exact: true }).click();
    await page.getByRole('button', { name: /Multiple Choice|MCQ/i }).first().click();
    await page.getByRole('button', { name: 'Save setup and add answers' }).click();
    await page.getByRole('heading', { name: 'Student answers' }).waitFor({ timeout: 8000 });
    await page.getByRole('button', { name: 'Fill example rows' }).click();
    await page.getByRole('button', { name: 'Check answers' }).click();
    await page.getByRole('heading', { name: 'Check results' }).waitFor();
    await page.getByRole('button', { name: /^Mark \d+ answer/ }).click();
    await page.getByText('Marking complete').waitFor({ timeout: 30000 });
    await page.getByRole('button', { name: 'View analysis', exact: true }).first().click();
    await page.getByRole('dialog').waitFor();
    await page.waitForTimeout(800);
    const dt = await page.getByRole('dialog').evaluate((el) => el.textContent.replace(/\s+/g, ' '));
    expect(/Answer key match/.test(dt) && /Not produced for multiple-choice questions/.test(dt), 'MCQ dialog notes missing');
    expect(logs.filter((l) => l.includes('pageerror') && !l.includes('@/c1/')).length === 0, 'page error: ' + logs.filter((l) => l.includes('pageerror') && !l.includes('@/c1/')).join('|'));
    await shot(page, 'lecturer_09_mcq_inspect');
    await page.keyboard.press('Escape');
  });
  await step('L15', 'lecturer', 'Marking Review queue lists submissions (student + batch) with filters', async () => {
    await go(page, '/lecturer/c3');
    await page.locator('table.c3-table tbody tr').first().waitFor({ timeout: 8000 });
    const n = await page.locator('table.c3-table tbody tr').count();
    expect(n >= 3, 'expected at least 3 rows, got ' + n);
    const t = await bodyText(page);
    expect(!FORBIDDEN_TEXT.test(t), 'forbidden label: ' + (t.match(FORBIDDEN_TEXT) || [])[0]);
    await page.getByRole('button', { name: /Awaiting review/ }).last().click();
    await page.waitForTimeout(700);
    await shot(page, 'lecturer_10_queue');
    return `${n} rows`;
  });
  await step('L16', 'lecturer', 'Queue search with no match shows empty state with Clear filters', async () => {
    await page.locator('#q-search').fill('zzzz-no-match');
    await page.getByText('No submissions found').waitFor({ timeout: 3000 });
    await page.getByRole('button', { name: 'Clear filters' }).click();
  });
  await step('L17', 'lecturer', 'Review page: accept, change with validation, finalize with confirmation', async () => {
    await go(page, '/lecturer/c3');
    await page.getByRole('button', { name: 'Awaiting review' }).first().click().catch(() => {});
    await page.waitForTimeout(600);
    const link = page.locator('a.btn', { hasText: 'Review' }).first();
    await link.click();
    await page.getByRole('heading', { name: 'Review submission' }).waitFor({ timeout: 8000 });
    await shot(page, 'lecturer_11_review_page');
    await page.getByRole('button', { name: 'Change mark' }).click();
    await page.locator('#ov-reason').fill('');
    await page.locator('#ov-mark').fill('99999');
    await page.getByRole('button', { name: 'Save mark' }).click();
    await page.locator('#ov-mark-err').waitFor({ timeout: 3000 });
    await page.locator('#ov-reason-err').waitFor({ timeout: 3000 });
    await page.getByRole('button', { name: 'Cancel' }).click();
    await page.getByRole('button', { name: 'Accept automatic mark' }).click();
    await page.getByText('Automatic mark accepted.').waitFor({ timeout: 8000 });
    await page.getByRole('button', { name: 'Finalize result' }).click();
    await page.getByRole('dialog', { name: /Finalize this result/ }).waitFor();
    await page.getByRole('button', { name: 'Finalize', exact: true }).click();
    await page.getByText(/Result finalized\./).waitFor({ timeout: 8000 });
    await shot(page, 'lecturer_12_review_finalized');
  });
  await step('L23', 'lecturer', 'Review page (opened from the queue) shows submitted answer, criteria with evidence, concepts, feedback and the map', async () => {
    await go(page, '/lecturer/c3');
    await page.locator('#q-search').fill('IT21001001');
    await page.waitForTimeout(500);
    await page.locator('table.c3-table tbody tr', { hasText: 'IT21001001' }).filter({ hasNotText: 'MCQ' }).first().locator('a.btn').click();
    await page.getByRole('heading', { name: 'Review submission' }).waitFor({ timeout: 8000 });
    await page.locator('.c3-mindmap-container').first().waitFor({ timeout: 8000 });
    const t = await bodyText(page);
    expect(/Question and answer/.test(t), 'question/answer missing');
    for (const sec of SECTIONS) expect(t.includes(sec), 'review page missing section: ' + sec);
    expect(/Evidence in the answer/.test(t) && /Why this mark/.test(t), 'criterion evidence/explanation missing');
    expect(/Automatic mark/.test(t) && /Your mark|Final mark/.test(t), 'proposed vs final mark panels missing');
    await shot(page, 'lecturer_16_review_analysis');
    return page.url();
  });
  await step('L24', 'lecturer', 'MCQ result (review page and batch dialog) shows answer-key match, MCQ feedback and explicit not-produced notes', async () => {
    await go(page, '/lecturer/c3');
    await page.locator('#q-search').fill('MCQ');
    await page.waitForTimeout(500);
    await page.locator('a.btn', { hasText: /Review|Finalize|View/ }).first().click();
    await page.getByRole('heading', { name: 'Review submission' }).waitFor({ timeout: 8000 });
    const t = await bodyText(page);
    expect(/Answer key match/.test(t), 'answer key match missing');
    expect(/Feedback/.test(t) && /(Review the lecture notes|Consolidate this knowledge)/.test(t), 'MCQ feedback missing');
    expect(/Not produced for multiple-choice questions/.test(t), 'not-produced note missing');
    expect(await page.locator('.c3-mindmap-container').count() === 0, 'MCQ map drawn');
    await shot(page, 'lecturer_17_mcq_review_analysis');
  });
  await step('L26', 'lecturer', 'A submission saved without analysis shows an explicit notice on the review page (no crash, no empty page)', async () => {
    const { c, db } = await mongo();
    const sub = await db.collection('c3_submissions').insertOne({ student_id: 'IT10000001', question_id: 'FIX-NOAI', question_text: 'Fixture question without a saved analysis', student_answer: 'fixture answer text', answer_type: 'short', status: 'pending_review', submitted_at: new Date(), updated_at: new Date(), is_demo: false });
    await db.collection('c3_results').insertOne({ submission_id: String(sub.insertedId), student_id: 'IT10000001', question_id: 'FIX-NOAI', automated_mark: 1, total_possible_marks: 4, percentage: 25, status: 'pending_review', created_at: new Date(), updated_at: new Date() });
    await c.close();
    global.NOAI_ID = String(sub.insertedId);
    await go(page, `/lecturer/c3/${global.NOAI_ID}`);
    await page.getByRole('heading', { name: 'Review submission' }).waitFor({ timeout: 8000 });
    const t = await bodyText(page);
    expect(/No analysis available/.test(t) && /No analysis was saved for this submission/.test(t), 'unavailable notice missing');
    expect(/fixture answer text/.test(t), 'submitted answer missing');
    expect(await page.locator('.c3-mindmap-container').count() === 0, 'fabricated map shown');
    await shot(page, 'lecturer_18_no_analysis');
    expect(logs.filter((l) => l.includes('pageerror') && !l.includes('@/c1/')).length === 0, 'page error');
  });
  await step('L27', 'lecturer', 'Review page at 375px: no horizontal page scroll; map scrolls inside its container and list fallback exists', async () => {
    await page.setViewportSize({ width: 375, height: 800 });
    await go(page, '/lecturer/c3');
    await page.locator('#q-search').fill('IT21001001');
    await page.waitForTimeout(500);
    await page.locator('table.c3-table tbody tr', { hasText: 'IT21001001' }).filter({ hasNotText: 'MCQ' }).first().locator('a.btn').click();
    await page.locator('.c3-mindmap-container').first().waitFor({ timeout: 8000 });
    const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    const scrollInfo = await page.evaluate(() => { const el = document.querySelector('.c3-svg-scroll'); return { sw: el.scrollWidth, cw: el.clientWidth, ox: getComputedStyle(el).overflowX }; });
    await shot(page, 'lecturer_19_review_mobile');
    expect(over <= 2, `page overflow ${over}px`);
    expect(scrollInfo.ox === 'auto' || scrollInfo.sw <= scrollInfo.cw, 'map container neither scrolls nor fits');
    expect(await page.locator('details.c3-mm-list').count() === 1, 'list fallback missing');
    await page.setViewportSize({ width: 1280, height: 800 });
    return JSON.stringify(scrollInfo);
  });
  // ---- Regression: real keystrokes in the "Change the mark" dialog (Playwright .fill hides focus-stealing bugs) ----
  let KEYS_SUB = null;
  await step('L28', 'lecturer', 'Change-the-mark dialog: reason accepts real keystrokes, keeps focus, newline and paste; Escape keeps the draft; Tab stays inside; save persists', async () => {
    const ts0 = await apiLogin('student');
    const made = await http(ts0, 'POST', '/c3/assess', { demo_id: 'arch-full', student_answer: 'Software architecture defines the high-level structure of a system made of components.' });
    expect(made.status === 200, 'could not create the submission ' + made.status);
    KEYS_SUB = made.json.submission_id;
    await go(page, `/lecturer/c3/${KEYS_SUB}`);
    await page.getByRole('heading', { name: 'Review submission' }).waitFor({ timeout: 8000 });
    await page.getByRole('button', { name: 'Change mark' }).click();
    const dlg = page.getByRole('dialog', { name: 'Change the mark' });
    await dlg.waitFor();
    const focusedId = () => page.evaluate(() => document.activeElement && document.activeElement.id);
    expect(await focusedId() === 'ov-mark', 'the mark field should take focus when the dialog opens');
    await page.locator('#ov-mark').press('Control+A');
    await page.keyboard.type('3');
    await page.locator('#ov-reason').click();
    const first = 'Checked each criterion by hand against the rubric';
    await page.keyboard.type(first, { delay: 12 });
    expect(await focusedId() === 'ov-reason', 'focus left the reason box while typing: ' + await focusedId());
    expect(await page.locator('#ov-reason').inputValue() === first, 'typed text was lost: ' + await page.locator('#ov-reason').inputValue());
    await page.keyboard.press('Enter');
    await page.keyboard.type('Second line', { delay: 8 });
    await page.keyboard.insertText(' (pasted)');
    const expected = first + '\nSecond line (pasted)';
    expect(await page.locator('#ov-reason').inputValue() === expected, 'multiline/paste mismatch');
    await page.keyboard.press('Control+A');
    await page.keyboard.type('Reason v2, replaced after select-all', { delay: 8 });
    expect(await page.locator('#ov-reason').inputValue() === 'Reason v2, replaced after select-all', 'select-all replace failed');
    // Tab order stays inside the dialog
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => !!document.activeElement.closest('[role=dialog]')), 'Tab left the dialog');
    // Escape closes; the draft is kept for the next open (state lives in the page, not the dialog)
    await page.keyboard.press('Escape');
    await dlg.waitFor({ state: 'detached', timeout: 3000 });
    await page.getByRole('button', { name: 'Change mark' }).click();
    expect(await page.locator('#ov-reason').inputValue() === 'Reason v2, replaced after select-all', 'draft reason was discarded when the dialog closed');
    await shot(page, 'lecturer_20_change_mark_typed');
    await page.getByRole('button', { name: 'Save mark' }).click();
    await page.getByText(/Mark changed to 3/).waitFor({ timeout: 8000 });
    // Reopen the submission: adjusted mark, reason and the original automatic mark are all there
    await go(page, `/lecturer/c3/${KEYS_SUB}`);
    await page.getByRole('heading', { name: 'Review submission' }).waitFor({ timeout: 8000 });
    const t = await bodyText(page);
    expect(/Reason v2, replaced after select-all/.test(t), 'reason not persisted');
    expect(/Automatic mark/.test(t) && /Mark adjusted/.test(t), 'automatic mark / adjustment notice missing');
    const stored = (await http(await apiLogin('lecturer'), 'GET', `/c3/submissions/${KEYS_SUB}`)).json.result;
    expect(stored.final_mark === 3 && stored.automated_mark !== 3 && stored.override_reason === 'Reason v2, replaced after select-all', `stored: auto=${stored.automated_mark} final=${stored.final_mark}`);
    await page.getByRole('button', { name: 'Finalize result' }).click();
    await page.getByRole('button', { name: 'Finalize', exact: true }).click();
    await page.getByText(/Result finalized\./).waitFor({ timeout: 8000 });
  });
  await step('L28b', 'student', 'The student sees the finalized adjusted mark and the adjustment notice with the reason', async () => {
    const b3 = await launch();
    const { ctx, page: sp } = await login(b3, 'student');
    await go(sp, '/c3');
    await sp.getByRole('tab', { name: /My submissions/ }).click();
    await sp.locator('table.c3-table tbody tr').first().waitFor();
    const rows = await sp.locator('table.c3-table tbody tr').allInnerTexts();
    const idx = rows.findIndex((r) => /Finalized/.test(r) && /3 \/ /.test(r));
    expect(idx >= 0, 'finalized adjusted row not found in history');
    await sp.getByRole('button', { name: 'Open' }).nth(idx).click();
    await sp.locator('.c3-mark-card').waitFor();
    const tt = await bodyText(sp);
    expect(/Final result/.test(tt) && /Reason v2, replaced after select-all/.test(tt) && /adjusted the automatic mark/.test(tt), 'final result / adjustment notice not shown to the student');
    await ctx.close(); await b3.close();
  });
  await step('L29', 'lecturer', 'Sample badge stays inline in the queue row and in the review header (static, no overlap) at 1280/768/375 px', async () => {
    for (const vp of [{ width: 1280, height: 800 }, { width: 768, height: 900 }, { width: 375, height: 800 }]) {
      await page.setViewportSize(vp);
      await go(page, '/lecturer/c3');
      await page.locator('.c3-source-badge').first().waitFor({ timeout: 8000 });
      const bad = await page.evaluate(() => {
        const out = [];
        for (const b of document.querySelectorAll('.c3-source-badge')) {
          const cs = getComputedStyle(b);
          const row = b.closest('tr');
          const r = b.getBoundingClientRect();
          const rr = row && row.getBoundingClientRect();
          if (cs.position !== 'static') out.push('position ' + cs.position);
          if (!row) out.push('not inside a table row');
          else if (r.top < rr.top - 1 || r.bottom > rr.bottom + 1) out.push('outside its row');
        }
        const loose = [...document.querySelectorAll('body *')].filter((e) => e.children.length === 0 && /^\s*Sample\s*$/.test(e.textContent) && !e.closest('tr') && !e.closest('button') && !e.closest('[role=tab]') && !e.closest('label'));
        if (loose.length) out.push('Sample text outside a row: ' + loose.length);
        if (document.querySelectorAll('.c3-page .chip').length) out.push('global .chip used inside the C3 page');
        return out;
      });
      expect(bad.length === 0, `${vp.width}px queue: ${bad.join('; ')}`);
    }
    const demoSub = (await http(await apiLogin('lecturer'), 'GET', '/c3/submissions')).json.submissions.find((x) => x.is_demo && x.status === 'pending_review');
    expect(demoSub, 'no pending sample submission available');
    for (const vp of [{ width: 1280, height: 800 }, { width: 375, height: 800 }]) {
      await page.setViewportSize(vp);
      await go(page, `/lecturer/c3/${demoSub._id}`);
      await page.getByRole('heading', { name: 'Review submission' }).waitFor({ timeout: 8000 });
      const info = await page.evaluate(() => {
        const b = document.querySelector('.c3-source-badge');
        if (!b) return 'badge missing';
        const cs = getComputedStyle(b); const r = b.getBoundingClientRect();
        const vis = r.right <= window.innerWidth + 1 && r.left >= 0;
        return cs.position !== 'static' ? 'position ' + cs.position : (!vis ? 'outside viewport' : (document.querySelectorAll('.c3-source-badge').length !== 1 ? 'duplicated' : 'ok'));
      });
      expect(info === 'ok', `${vp.width}px review page badge: ${info}`);
      // the badge must not cover the dialog controls
      await page.getByRole('button', { name: 'Change mark' }).click();
      const covered = await page.evaluate(() => { const el = document.querySelector('#ov-reason'); const r = el.getBoundingClientRect(); const top = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return top !== el; });
      expect(!covered, 'something overlaps the reason box');
      await page.keyboard.press('Escape');
    }
    await page.setViewportSize({ width: 1280, height: 800 });
  });
  await step('L18', 'lecturer', 'Queue failure shows error notice with Try again', async () => {
    await page.route('**/api/v1/c3/submissions**', (r) => r.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"boom"}' }));
    await go(page, '/lecturer/c3');
    await page.getByText('Queue unavailable').waitFor({ timeout: 5000 });
    await page.unroute('**/api/v1/c3/submissions**');
  });
  for (const [id, path] of [['L19a', '/admin'], ['L19b', '/admin/lecturers'], ['L19c', '/c3']]) {
    await step(id, 'lecturer', `Direct URL ${path} does not open for a lecturer`, async () => {
      await go(page, path);
      const url = new URL(page.url()).pathname;
      expect(!/^\/admin/.test(url) && url !== '/c3', 'stayed on ' + url);
      return `redirected to ${url}`;
    });
  }
  await step('L20', 'lecturer', 'Responsive: batch page and queue at 375px and 768px without horizontal scroll', async () => {
    for (const w of [375, 768]) {
      await page.setViewportSize({ width: w, height: 800 });
      for (const p of ['/lecturer/c3/batch', '/lecturer/c3']) {
        await go(page, p);
        const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        await shot(page, `lecturer_resp_${w}_${p.split('/').pop()}`);
        expect(over <= 2, `overflow ${over}px at ${w}px on ${p}`);
      }
    }
    await page.setViewportSize({ width: 1280, height: 800 });
  });
  await step('L21', 'lecturer', 'Dark theme on batch setup and queue', async () => {
    await go(page, '/lecturer/c3');
    await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
    await page.waitForTimeout(300);
    await shot(page, 'lecturer_13_queue_dark');
    await go(page, '/lecturer/c3/batch');
    await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
    await page.waitForTimeout(300);
    await shot(page, 'lecturer_14_batch_dark');
    await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
  });
  results.push({ id: 'L-console', role: 'lecturer', desc: 'Browser page errors during lecturer session', status: logs.filter((l) => l.includes('pageerror') && !l.includes('@/c1/')).length ? 'Failed' : 'Passed', note: logs.slice(0, 4).join(' | ').slice(0, 300), ms: 0 });
  await ctx.close();
}

// ============================== ADMIN ==============================
await browser.close(); browser = await launch();
{
  const { ctx, page, logs } = await login(browser, 'admin');
  await step('A1', 'admin', 'Admin lands on /admin; sidebar has no marking (C3) entry', async () => {
    const url = new URL(page.url()).pathname;
    expect(url === '/admin', 'landed on ' + url);
    const nav = await page.locator('nav').first().innerText();
    expect(!/marking|batch/i.test(nav), 'marking entry in admin menu: ' + nav.replace(/\n/g, ' | '));
    await shot(page, 'admin_01_landing');
    return 'menu: ' + nav.replace(/\n/g, ' | ');
  });
  await step('A2', 'admin', '/admin/lecturers (approvals) loads', async () => {
    await go(page, '/admin/lecturers');
    expect(!/^\/login/.test(new URL(page.url()).pathname), 'redirected to login');
    await shot(page, 'admin_02_lecturers');
  });
  await step('A3', 'admin', 'Direct URL /lecturer/c3 (marking review) - observed behaviour', async () => {
    await go(page, '/lecturer/c3');
    const url = new URL(page.url()).pathname;
    const t = await bodyText(page);
    await shot(page, 'admin_03_direct_marking_review');
    return `${url}; Marking Review rendered: ${/Marking Review/.test(t)}; layout menu: lecturer`;
  });
  await step('A4', 'admin', 'Direct URL /lecturer/c3/batch - observed behaviour', async () => {
    await go(page, '/lecturer/c3/batch');
    const t = await bodyText(page);
    return `Batch Marking rendered: ${/Batch Marking/.test(t)}`;
  });
  await step('A5', 'admin', 'Student page /c3 is not available to an admin', async () => {
    await go(page, '/c3');
    const url = new URL(page.url()).pathname;
    expect(url !== '/c3', 'admin stayed on /c3');
    return 'redirected to ' + url;
  });
  results.push({ id: 'A-console', role: 'admin', desc: 'Browser page errors during admin session', status: logs.filter((l) => l.includes('pageerror') && !l.includes('@/c1/')).length ? 'Failed' : 'Passed', note: logs.slice(0, 4).join(' | ').slice(0, 300), ms: 0 });
  await ctx.close();
}

// ============================== API PERMISSION MATRIX ==============================
{
  const T = { student: await apiLogin('student'), lecturer: await apiLogin('lecturer'), admin: await apiLogin('admin') };
  const none = null;
  const rows = [];
  const check = async (label, role, method, path, body, expectStatuses) => {
    const r = await http(role === 'anon' ? none : T[role], method, path, body);
    const ok = expectStatuses.includes(r.status);
    rows.push({ label, role, method, path, status: r.status, expected: expectStatuses.join('/'), ok });
    results.push({ id: `API-${rows.length}`, role, desc: `${method} ${path} as ${role}: ${label}`, status: ok ? 'Passed' : 'Failed', note: `HTTP ${r.status} (expected ${expectStatuses.join('/')})`, ms: 0 });
    return r;
  };
  await check('assessments list needs login', 'anon', 'GET', '/c3/assessments', undefined, [401]);
  const list = await check('student may list assessments', 'student', 'GET', '/c3/assessments', undefined, [200]);
  const leaked = /correct_answer|reference_answer|expected_concepts|scoring_levels|required_concepts|"rubric"/.test(JSON.stringify(list.json));
  results.push({ id: 'API-leak', role: 'student', desc: 'GET /c3/assessments exposes no key/rubric/reference fields', status: leaked ? 'Failed' : 'Passed', note: '', ms: 0 });
  await check('student cannot supply own key', 'student', 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'B', correct_answer: 'B' }, [400]);
  await check('student assess with demo id', 'student', 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'A' }, [200]);
  const subs = await http(T.student, 'GET', '/c3/submissions');
  const sid = subs.json.submissions[0]._id;
  const lecSubs = await http(T.lecturer, 'GET', '/c3/submissions');
  await check('student cannot review', 'student', 'POST', `/c3/submissions/${sid}/review`, { decision: 'accepted' }, [403]);
  await check('student cannot finalize', 'student', 'POST', `/c3/submissions/${sid}/finalize`, {}, [403]);
  await check('student cannot create batch', 'student', 'POST', '/c3/batch/setup', { title: 'x' }, [403]);
  await check('student cannot mark batch', 'student', 'POST', '/c3/batch/mark', { setup_id: 'x', items: [] }, [403]);
  await check('student cannot read staff examples (keys/rubrics)', 'student', 'GET', '/c3/examples', undefined, [403]);
  await check('lecturer can read examples', 'lecturer', 'GET', '/c3/examples', undefined, [200]);
  await check('student cannot list batches', 'student', 'GET', '/c3/batch/setup', undefined, [403]);
  await check('lecturer can list submissions', 'lecturer', 'GET', '/c3/submissions', undefined, [200]);
  await check('lecturer can list batches', 'lecturer', 'GET', '/c3/batch/setup', undefined, [200]);
  await check('admin can list batches (policy: admin oversees)', 'admin', 'GET', '/c3/batch/setup', undefined, [200]);
  await check('admin can read any submission detail', 'admin', 'GET', `/c3/submissions/${sid}`, undefined, [200]);
  await check('admin may NOT assess as a student', 'admin', 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'A' }, [403]);
  for (const ep of ['analysis', 'marking', 'feedback', 'mindmap']) {
    await check(`raw /c3/${ep}: student denied`, 'student', 'POST', `/c3/${ep}`, { question_id: 'X', student_id: 'IT10000001' }, [403]);
    await check(`raw /c3/${ep}: admin denied`, 'admin', 'POST', `/c3/${ep}`, { question_id: 'X', student_id: 'IT10000001' }, [403]);
    await check(`raw /c3/${ep}: anonymous denied`, 'anon', 'POST', `/c3/${ep}`, {}, [401]);
    await check(`raw /c3/${ep}: lecturer reaches validation`, 'lecturer', 'POST', `/c3/${ep}`, {}, [400]);
  }
  const unk = await check('unknown C3 path is a JSON 404', 'student', 'GET', '/c3/does-not-exist', undefined, [404]);
  results.push({ id: 'API-404json', role: 'student', desc: 'Unknown C3 path returns JSON {error}', status: unk.json && unk.json.error ? 'Passed' : 'Failed', note: '', ms: 0 });
  await check('finalize-all by a student is denied', 'student', 'POST', '/c3/batch/x/finalize-all', {}, [403]);
  const detail = await http(T.student, 'GET', `/c3/submissions/${sid}`);
  const redacted = ['reference_answer', 'expected_concepts', 'correct_options', 'rubric'].every((k) => !(k in detail.json.submission));
  results.push({ id: 'API-redact', role: 'student', desc: 'Student submission detail omits reference/rubric/concepts/key fields', status: redacted ? 'Passed' : 'Failed', note: '', ms: 0 });
  // second student isolation: lecturer-created submission id belongs to lecturer-run batch; student must not read others' submissions
  const other = lecSubs.json.submissions.find((s) => s.student_id !== 'IT10000001');
  if (other) await check("student cannot read another student's submission", 'student', 'GET', `/c3/submissions/${other._id}`, undefined, [403]);
  fs.writeFileSync(`${OUT}/api_matrix.json`, JSON.stringify(rows, null, 1));
}


// ============================== STUDENT SEES FINALIZED RESULT ==============================
{
  await step('S16', 'student', 'After the lecturer finalizes a student submission the student sees Final result with the lecturer mark', async () => {
    const tl = await apiLogin('lecturer');
    const ts = await apiLogin('student');
    const mine = (await http(ts, 'GET', '/c3/submissions')).json.submissions.find((x) => x.status === 'pending_review' && x.automated_mark != null);
    expect(mine, 'no pending submission for the student');
    const rv = await http(tl, 'POST', `/c3/submissions/${mine._id}/review`, { decision: 'overridden', new_mark: 1, override_reason: 'Partial credit after manual check' });
    expect(rv.status === 200, 'review failed ' + rv.status);
    const fz = await http(tl, 'POST', `/c3/submissions/${mine._id}/finalize`, {});
    expect(fz.status === 200, 'finalize failed ' + fz.status);
    const b2 = await launch();
    const { ctx, page } = await login(b2, 'student');
    await go(page, '/c3');
    await page.getByRole('tab', { name: /My submissions/ }).click();
    await page.locator('table.c3-table tbody tr').first().waitFor();
    const rows = await page.locator('table.c3-table tbody tr').allInnerTexts();
    expect(rows.some((r) => /Finalized/.test(r)), 'no Finalized row in history');
    const idx = rows.findIndex((r) => /Finalized/.test(r));
    await page.getByRole('button', { name: 'Open' }).nth(idx).click();
    await page.locator('.c3-mark-card').waitFor();
    const t = await bodyText(page);
    expect(/Final result/.test(t) && /Partial credit after manual check/.test(t) && /adjusted the automatic mark/.test(t), 'final result / override reason not shown');
    await shot(page, 'student_08_finalized_result');
    await ctx.close(); await b2.close();
  });
}

await browser.close();
fs.writeFileSync(`${OUT}/results.json`, JSON.stringify(results, null, 1));
const f = results.filter((r) => r.status === 'Failed');
console.log(`\nTOTAL ${results.length}  PASSED ${results.filter((r) => r.status === 'Passed').length}  FAILED ${f.length}`);
f.forEach((r) => console.log('FAILED', r.id, r.desc, '::', r.note));
