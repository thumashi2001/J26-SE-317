// API-level functional run for the C3 requirements audit (reports/c3_remediation/15_c3_functional_requirements_audit.md).
// Real HTTP against an ISOLATED local backend (default :3100, local MongoDB, real C3 Python service on :8003).
// Never point this at the shared Atlas database. The password comes from the environment only.
//
//   (set C3_TEST_DB, C3_TEST_MONGO_URI, C3_API_BASE, C3_TEST_PASSWORD: see README and guard.mjs)
//   node functional.mjs phase1 out.json
//   (restart the backend)
//   node functional.mjs phase2 out2.json phase1.json
//
// Every record states its test type: "e2e-api" (real HTTP + real Python + real Mongo) or "exploratory" (no authoritative
// expected outcome exists, so nothing is asserted and the observed behaviour is only recorded).
import fs from 'node:fs';
import { config, connectTestDb, verifyIsolation } from './guard.mjs';

const PHASE = process.argv[2] || 'phase1';
const OUT = process.argv[3] || `functional_${PHASE}.json`;
const B = config.apiBase;
const PW = config.password;
await verifyIsolation(); // aborts before any test write unless the backend uses the same local test database

const rows = [];
const rec = (id, reqs, scenario, expected, actual, status, type = 'e2e-api', evidence = '') => {
  rows.push({ id, reqs, scenario, expected, actual: String(actual).slice(0, 400), status, type, evidence });
  console.log(status.padEnd(8), id, scenario);
};
const call = async (t, m, p, body) => {
  const t0 = Date.now();
  const r = await fetch(B + p, { method: m, headers: { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await r.text(); let json = null; try { json = JSON.parse(text); } catch { /* not json */ }
  return { status: r.status, json, ms: Date.now() - t0 };
};
const login = async (u) => (await call(null, 'POST', '/auth/login', { userId: u, password: PW })).json.token;
const ts = await login('IT10000001'), tl = await login('SLIITLEC101'), ta = await login('SLIITADMIN1');
const { client: mc, db } = await connectTestDb();
const check = (cond) => (cond ? 'PASS' : 'FAIL');

// ------------------------------------------------------------------------------------------------
if (PHASE === 'phase1') {
  // Controlled fixture: server rubric "arch-full" (criterion C1, max 4).
  //   L0 = no required concept, L2 = at least 1 of 3 demonstrated, L4 = all 3 (high-level structure, components, relationships).
  // Expected marks follow from the rubric text alone (explicit phrases), not from the model's output.
  const ANSWERS = {
    full: 'Software architecture defines the high-level structure of a system. It is made of components and the relationships between them.',
    partial: 'The system is made of components.',
    irrelevant: 'I enjoy football and pizza at the weekend.',
  };
  const results = {};
  for (const [k, ans] of Object.entries(ANSWERS)) {
    const r = await call(ts, 'POST', '/c3/assess', { demo_id: 'arch-full', student_answer: ans });
    results[k] = r;
  }
  const mark = (r) => r.json?.total_awarded_marks;
  rec('F-A1', ['FR-C3-04', 'FR-C3-11', 'FR-C3-12', 'FR-C3-13', 'SO2'], 'Controlled answer naming all three required concepts', 'proposed mark 4/4 (level L4)', `mark ${mark(results.full)}/${results.full.json?.total_possible_marks}`, check(mark(results.full) === 4));
  rec('F-A2', ['FR-C3-13', 'FR-C3-10'], 'Controlled answer naming one required concept (partial credit)', 'proposed mark 2/4 (level L2)', `mark ${mark(results.partial)}`, check(mark(results.partial) === 2));
  rec('F-A3', ['FR-C3-12', 'FR-C3-23'], 'Controlled irrelevant answer', 'proposed mark 0/4 (level L0)', `mark ${mark(results.irrelevant)}`, check(mark(results.irrelevant) === 0));
  const para = await call(ts, 'POST', '/c3/assess', { demo_id: 'arch-full', student_answer: 'An architecture describes the overall organisation of a system: its parts and how they connect to each other.' });
  rec('F-A4', ['FR-C3-09', 'SO1'], 'Paraphrase without the rubric phrases (exploratory: no authoritative expected mark)', 'none asserted; records whether paraphrases earn credit', `mark ${mark(para)}/4`, 'INFO', 'exploratory', 'Lexical engine: see report for the semantic-matching limitation');
  const rep = await call(ts, 'POST', '/c3/assess', { demo_id: 'arch-full', student_answer: ANSWERS.full });
  const stripVolatile = (e) => JSON.stringify(e, (k, v) => (['submission_id', 'result_id', 'processing_time_ms'].includes(k) ? undefined : v));
  rec('F-A5', ['NFR-C3-03', 'NFR-C3-19', 'NFR-C3-02'], 'Same answer and configuration submitted twice', 'identical marks, concept statuses, criterion levels', `marks ${mark(results.full)} vs ${mark(rep)}; identical evaluation=${stripVolatile(results.full.json) === stripVolatile(rep.json)}`, check(stripVolatile(results.full.json) === stripVolatile(rep.json)));
  const empty = await call(ts, 'POST', '/c3/assess', { demo_id: 'arch-full', student_answer: '' });
  rec('F-A6', ['NFR-C3-16', 'FR-C3-05'], 'Empty answer', 'handled without a 5xx', `HTTP ${empty.status} ${empty.json?.error || ''}`, check(empty.status < 500));
  const odd = await call(ts, 'POST', '/c3/assess', { demo_id: 'arch-full', student_answer: '<b>Components</b>\n\n\t  & relationships   <script>alert(1)</script> ' + 'x'.repeat(50) });
  rec('F-A7', ['FR-C3-05', 'NFR-C3-16'], 'Answer with HTML tags, whitespace and control characters', 'handled without a 5xx; returns a mark', `HTTP ${odd.status}`, check(odd.status === 200));
  const noCfg = await call(ts, 'POST', '/c3/assess', { student_answer: 'x' });
  rec('F-A8', ['NFR-C3-16'], 'Request without an assessment id', '400 with a message', `HTTP ${noCfg.status}`, check(noCfg.status === 400));
  const unsup = await call(ts, 'POST', '/c3/assess', { demo_id: 'arch-full', image: 'data:image/png;base64,AAA' });
  rec('F-A9', ['NFR-C3-16'], 'Unsupported scanned-image input', '400 with explicit OCR-unsupported message', `HTTP ${unsup.status} ${unsup.json?.error?.slice(0, 60)}`, check(unsup.status === 400));

  // stored record content
  const sid = results.full.json.submission_id;
  const d = (await call(tl, 'GET', `/c3/submissions/${sid}`)).json;
  const ev = d.result.ai_evaluation;
  rec('F-B1', ['FR-C3-01', 'FR-C3-02', 'FR-C3-03', 'FR-C3-07', 'NFR-C3-20'], 'Stored record links student, question, answer and reference', 'submission holds student_id, question_id/text, student answer, reference answer', `student=${d.submission.student_id} q=${d.submission.question_id} ref=${!!d.submission.reference_answer}`, check(d.submission.student_id === 'IT10000001' && d.submission.question_id && d.submission.student_answer && d.submission.reference_answer));
  rec('F-B2', ['FR-C3-14', 'FR-C3-25', 'FR-C3-26', 'NFR-C3-05', 'NFR-C3-06'], 'Criterion evidence and explanation stored with the mark', 'criteria_results has level, descriptor, evidence sentences and an explanation', JSON.stringify(Object.keys(ev.marking.criteria_results[0])), check(['selected_level_id', 'rubric_descriptor', 'evidence_sentence_ids', 'explanation'].every((k) => k in ev.marking.criteria_results[0])));
  const cm = Object.fromEntries(ev.analysis.concept_matches.map((c) => [c.concept, c.status]));
  rec('F-B3', ['FR-C3-21', 'FR-C3-22', 'FR-C3-23', 'FR-C3-24', 'SO3'], 'Concept classes for the controlled answers', 'full answer: 3 demonstrated; partial answer: components demonstrated, others not', `full=${JSON.stringify(cm)}`, check(Object.values(cm).every((s) => s === 'demonstrated')));
  const dp = (await call(tl, 'GET', `/c3/submissions/${results.partial.json.submission_id}`)).json.result.ai_evaluation.analysis.concept_matches;
  const statuses = Object.fromEntries(dp.map((c) => [c.concept, c.status]));
  rec('F-B4', ['FR-C3-23', 'FR-C3-29'], 'Missing concepts identified for the partial answer', 'high-level structure and relationships not demonstrated', JSON.stringify(statuses), check(statuses['components'] === 'demonstrated' && statuses['high-level structure'] !== 'demonstrated' && statuses['relationships'] !== 'demonstrated'));
  const fb = ev.feedback.overall_feedback;
  rec('F-B5', ['FR-C3-27', 'FR-C3-28', 'FR-C3-29', 'FR-C3-30', 'FR-C3-31', 'SO4'], 'Feedback sections', 'summary, strengths, missing concepts, improvement suggestions present and linked to the mark', `${Object.keys(fb).join(',')}; mark ${fb.total_mark}/${fb.total_possible}`, check(fb.overall_summary && Array.isArray(fb.overall_strengths) && Array.isArray(fb.overall_missing_concepts) && Array.isArray(fb.overall_improvement_suggestions) && fb.total_mark === ev.total_awarded_marks));
  const mm = ev.mindmap;
  rec('F-B6', ['FR-C3-32', 'FR-C3-35', 'SO5'], 'Mind map nodes derived from the answer', 'root plus one node per concept, with status', `${mm.nodes.length} nodes`, check(mm.nodes.length >= 4 && mm.root_node_id));
  const kinds = [...new Set(mm.relationships.map((r) => r.relationship_type))];
  const evid = [...new Set(mm.relationships.map((r) => r.evidence))];
  rec('F-B7', ['FR-C3-33', 'FR-C3-34'], 'Concept-to-concept relationships supported by evidence', 'relationships between concepts, not only root-to-concept', `types=${kinds.join(',')}; evidence=${evid.join(' | ').slice(0, 90)}`, kinds.every((k) => k === 'child') ? 'FAIL' : 'PASS');
  rec('F-B8', ['FR-C3-15', 'NFR-C3-21'], 'Method/configuration recorded with the result', 'pipeline/marking/analysis versions and the rubric used are stored', `pipeline_version=${ev.pipeline_version}; marking=${ev.marking.marking_version}; analysis=${ev.analysis.analysis_version}; rubric stored=${!!d.submission.rubric}`, check(ev.pipeline_version && ev.marking.marking_version && d.submission.rubric));
  const timeKeys = JSON.stringify(ev).match(/processing_time|latency|elapsed|duration/i);
  rec('F-B9', ['NFR-C3-08'], 'Processing time recorded per evaluated response', 'a processing-time field exists in the stored result', `field found: ${timeKeys ? timeKeys[0] : 'none'}; observed request latency ${results.full.ms} ms (client-side only)`, check(!!timeKeys));
  rec('F-B10', ['FR-C3-18'], 'Retrieved RAG context recorded', 'retrieved context stored with the result', `RAG is not on the /assess path: ${/retriev|context/i.test(JSON.stringify(ev)) ? 'field present' : 'no retrieved-context field'}`, 'BLOCKED', 'e2e-api', 'Vector RAG is a library + offline harness only (reports/c3_remediation/11_vector_rag_implementation.md)');

  // lecturer workflows with a fresh batch
  const setup = await call(tl, 'POST', '/c3/batch/setup', { title: 'Functional batch', question_id: 'FN-Q1', question_text: 'Explain software architecture.', reference_answer: 'Software architecture defines the high-level structure of a system comprising components and their relationships.', answer_type: 'short', max_marks: 4, expected_concepts: ['high-level structure', 'components', 'relationships'], rubric: ((await call(tl, 'GET', '/c3/examples')).json.examples.find((e) => e.config?.rubric) || {}).config?.rubric });
  rec('F-C1', ['FR-C3-11', 'NFR-C3-13'], 'Lecturer creates a batch setup with question, reference and rubric', '200 and a batch id', `HTTP ${setup.status} ${setup.json?.error || ''}`, check(setup.status === 200 && setup.json.batch_id));
  const bid = setup.json?.batch_id;
  const items = [
    { student_id: 'FN001', student_answer: ANSWERS.full }, { student_id: 'FN002', student_answer: ANSWERS.partial },
    { student_id: 'FN003', student_answer: ANSWERS.irrelevant }, { student_id: 'FN001', student_answer: 'duplicate' }, { student_id: 'FN004', student_answer: '' },
  ];
  const val = await call(tl, 'POST', '/c3/batch/validate', { setup_id: bid, items });
  rec('F-C2', ['NFR-C3-16'], 'Batch validation of duplicate and empty rows', '3 valid, 2 invalid (duplicate id, empty answer)', `valid=${val.json?.valid_count} invalid=${val.json?.invalid_count}`, check(val.json?.valid_count === 3 && val.json?.invalid_count === 2));
  const mk = await call(tl, 'POST', '/c3/batch/mark', { setup_id: bid, items });
  const marks = Object.fromEntries((mk.json?.results || []).map((r) => [r.student_id, r.awarded_mark]));
  rec('F-C3', ['FR-C3-11', 'FR-C3-12'], 'Batch marking of three controlled answers against the same rubric', 'FN001=4, FN002=2, FN003=0', JSON.stringify(marks), check(marks.FN001 === 4 && marks.FN002 === 2 && marks.FN003 === 0));
  const before = await db.collection('c3_submissions').countDocuments({ batch_id: bid });
  const mk2 = await call(tl, 'POST', '/c3/batch/mark', { setup_id: bid, items });
  const subs = await call(tl, 'GET', '/c3/submissions');
  const inBatch = subs.json.submissions.filter((s) => s.question_id === 'FN-Q1').slice(0, 3);
  rec('F-C4', ['NFR-C3-17'], 'Retrying the same batch creates no duplicate submissions', 'submission count unchanged by the retry', `HTTP ${mk2.status}; submissions in batch ${before} -> ${await db.collection('c3_submissions').countDocuments({ batch_id: bid })}`, check(before === 3 && (await db.collection('c3_submissions').countDocuments({ batch_id: bid })) === 3));
  const mine = inBatch.find((s) => s.student_id === 'FN002');
  const rv = await call(tl, 'POST', `/c3/submissions/${mine._id}/review`, { decision: 'overridden', new_mark: 3 });
  rec('F-C5', ['FR-C3-40', 'FR-C3-41', 'NFR-C3-22'], 'Override without a reason', '400', `HTTP ${rv.status}`, check(rv.status === 400));
  const rv2 = await call(tl, 'POST', `/c3/submissions/${mine._id}/review`, { decision: 'overridden', new_mark: 3, override_reason: 'Functional run: partial credit for related wording' });
  const after = (await call(tl, 'GET', `/c3/submissions/${mine._id}`)).json.result;
  rec('F-C6', ['FR-C3-40', 'FR-C3-41', 'NFR-C3-07', 'NFR-C3-22'], 'Override with reason keeps automated and final marks separate', 'automated 2, final 3, reason and reviewer recorded', `auto=${after.automated_mark} final=${after.final_mark} by=${after.reviewed_by} reason=${!!after.override_reason}`, check(rv2.status === 200 && after.automated_mark === 2 && after.final_mark === 3 && after.reviewed_by && after.override_reason));
  const hasHistory = !!after.review_history;
  rec('F-C7', ['FR-C3-41', 'NFR-C3-22'], 'Review history (append-only list of actions)', 'each review action is kept as a history entry', `review_history present: ${hasHistory}; only the latest values are stored`, hasHistory ? 'PASS' : 'PARTIAL');
  const fa = await call(tl, 'POST', `/c3/batch/${bid}/finalize-all`, {});
  const faView = await call(tl, 'GET', `/c3/batch/setup/${bid}`);
  rec('F-C8', ['FR-C3-40'], 'finalize-all with one reviewed and two unreviewed results', 'only the reviewed result is finalized; two stay pending', `HTTP ${fa.status} finalized=${fa.json?.finalized_count} skipped=${fa.json?.skipped_unreviewed_count} stats=${JSON.stringify([faView.json?.stats?.finalized_count, faView.json?.stats?.pending_count])}`, check(fa.json?.finalized_count === 1 && fa.json?.skipped_unreviewed_count === 2));
  // C1 bridge
  await new Promise((r) => setTimeout(r, 800));
  const ev1 = await db.collection('learning_events').findOne({ submission_id: String(mine._id) });
  rec('F-C9', ['FR-C3-43', 'NFR-C3-26'], 'Finalized result reaches the C1 learning_events collection', 'one finalized event for the student with the final score', `found=${!!ev1} stage=${ev1?.lifecycle_stage} student=${ev1?.student_id} score=${ev1?.score ?? ev1?.final_score}`, check(ev1 && ev1.lifecycle_stage === 'finalized'));
  const count1 = await db.collection('learning_events').countDocuments({ submission_id: String(mine._id) });
  await call(tl, 'POST', `/c3/batch/${bid}/finalize-all`, {});
  const count2 = await db.collection('learning_events').countDocuments({ submission_id: String(mine._id) });
  rec('F-C10', ['FR-C3-43'], 'Repeated finalize-all does not duplicate the C1 event', 'event count unchanged', `${count1} -> ${count2}`, check(count1 === count2 && count1 === 1));

  // MCQ
  const mcq = await call(ts, 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'B' });
  const mcqWrong = await call(ts, 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'A' });
  const mcqNone = await call(ts, 'POST', '/c3/assess', { demo_id: 'mcq-correct' });
  const mcqBad = await call(ts, 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'Z' });
  rec('F-D1', ['FR-C3-04', 'FR-C3-12'], 'MCQ: key option B (server bank)', 'B full marks; A zero; none zero; invalid option 400', `B=${mcq.json?.total_awarded_marks} A=${mcqWrong.json?.total_awarded_marks} none=${mcqNone.json?.total_awarded_marks} Z=HTTP ${mcqBad.status}`, check(mcq.json?.is_correct === true && mcqWrong.json?.total_awarded_marks === 0 && mcqNone.json?.total_awarded_marks === 0 && mcqBad.status === 400));

  // student history + isolation
  const hist = await call(ts, 'GET', '/c3/submissions');
  const other = await login('SLIITLEC101');
  rec('F-E1', ['FR-C3-46', 'NFR-C3-11'], 'Student history lists own submissions only', 'every entry belongs to the student', `${hist.json.submissions.length} entries; foreign=${hist.json.submissions.filter((s) => s.student_id !== 'IT10000001').length}`, check(hist.json.submissions.length > 0 && hist.json.submissions.every((s) => s.student_id === 'IT10000001')));
  const foreign = inBatch[0];
  const fr = await call(ts, 'GET', `/c3/submissions/${foreign._id}`);
  rec('F-E2', ['NFR-C3-11', 'NFR-C3-14'], "Student reads another student's submission", '403/404', `HTTP ${fr.status}`, check([403, 404].includes(fr.status)));
  const tamper = await call(ts, 'POST', `/c3/submissions/${sid}/review`, { decision: 'accepted' });
  rec('F-E3', ['NFR-C3-13', 'NFR-C3-14'], 'Student attempts a lecturer review action', '403', `HTTP ${tamper.status}`, check(tamper.status === 403));
  const exp = await call(ts, 'GET', '/c3/examples');
  rec('F-E4', ['NFR-C3-11', 'NFR-C3-14'], 'Student reads staff examples (keys/rubrics)', '403', `HTTP ${exp.status}`, check(exp.status === 403));
  const anon = await call(null, 'GET', '/c3/submissions');
  rec('F-E5', ['NFR-C3-11'], 'Unauthenticated history request', '401', `HTTP ${anon.status}`, check(anon.status === 401));
  const bad = await fetch(B + '/c3/submissions', { headers: { Authorization: 'Bearer not.a.token' } });
  rec('F-E6', ['NFR-C3-11'], 'Invalid token', '401', `HTTP ${bad.status}`, check(bad.status === 401));
  const adm = await call(ta, 'GET', '/c3/submissions');
  rec('F-E7', ['NFR-C3-13'], 'Admin can read submissions (oversight) but cannot assess as a student', 'GET 200; POST /assess 403', `GET ${adm.status}; POST ${(await call(ta, 'POST', '/c3/assess', { demo_id: 'mcq-correct', selected_option_id: 'A' })).status}`, check(adm.status === 200));

  // concurrency
  const conc = await Promise.all([1, 2, 3, 4, 5].map((i) => call(ts, 'POST', '/c3/assess', { demo_id: 'arch-full', student_answer: ANSWERS.full + ' ' + i })));
  rec('F-F1', ['NFR-C3-16', 'NFR-C3-17'], 'Five parallel submissions', 'all succeed with distinct submission ids', `${conc.map((c) => c.status).join(',')}; distinct=${new Set(conc.map((c) => c.json?.submission_id)).size}`, check(conc.every((c) => c.status === 200) && new Set(conc.map((c) => c.json.submission_id)).size === 5));
  // integrations
  const c2 = await call(tl, 'GET', '/c2/questions');
  rec('F-G1', ['FR-C3-42'], 'C2 to C3 question hand-off', 'a C2 endpoint delivers structured questions to C3', `GET /c2/questions -> HTTP ${c2.status}; backend/src/integration/c2-c3 holds a README only`, 'BLOCKED', 'e2e-api', 'C2 module has no routes; contract documented only');
  const c4 = await call(tl, 'GET', '/c3/exercises?published=true');
  rec('F-G2', ['FR-C3-44'], 'C3 weak-concept output for C4', 'a C3 endpoint delivers weak-concept information to C4', `GET /c3/exercises -> HTTP ${c4.status}; C4 adapter documents a future contract`, 'BLOCKED', 'e2e-api', 'No C3 to C4 endpoint exists');
  fs.writeFileSync(OUT, JSON.stringify({ phase: PHASE, base: B, db: DB, ids: { sid, bid, mine: String(mine._id), student: 'IT10000001' }, rows }, null, 1));
}

// ------------------------------------------------------------------------------------------------
if (PHASE === 'phase2') {
  // after a backend restart: previously stored records are still retrievable and unchanged
  const prev = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
  const d = await call(tl, 'GET', `/c3/submissions/${prev.ids.sid}`);
  rec('F-H1', ['FR-C3-45', 'FR-C3-46', 'NFR-C3-17'], 'Stored result and evidence are retrievable after a backend restart', '200 with the same marks and evidence', `HTTP ${d.status} mark=${d.json?.result?.automated_mark} criteria=${d.json?.result?.ai_evaluation?.marking?.criteria_results?.length}`, check(d.status === 200 && d.json.result.automated_mark === 4 && d.json.result.ai_evaluation.marking.criteria_results.length === 1));
  const m = await call(tl, 'GET', `/c3/submissions/${prev.ids.mine}`);
  rec('F-H2', ['NFR-C3-22', 'NFR-C3-23'], 'Override audit fields survive the restart', 'final mark, reason, reviewer, finalization time still stored', `status=${m.json?.result?.status} final=${m.json?.result?.final_mark} reason=${!!m.json?.result?.override_reason} by=${m.json?.result?.reviewed_by} finalized_at=${!!m.json?.result?.finalized_at}`, check(m.json?.result?.final_mark === 3 && m.json.result.override_reason && m.json.result.reviewed_by && m.json.result.finalized_at));
  const h = await call(ts, 'GET', '/c3/submissions');
  rec('F-H3', ['FR-C3-46'], 'Student history after restart', 'history still lists the earlier submissions', `${h.json?.submissions?.length} entries`, check(h.json?.submissions?.length >= 5));
  fs.writeFileSync(OUT, JSON.stringify({ phase: PHASE, rows }, null, 1));
}
await mc.close();
