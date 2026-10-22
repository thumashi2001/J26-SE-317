import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  createBatchSetup,
  finalizeBatchSubmissions,
  finalizeSubmission,
  getBatchSetup,
  getSubmission,
  listBatchSetups,
  listExamples,
  processBatchMarking,
  reviewSubmission,
  validateBatchAnswers,
} from '../../services/c3Api.js';
import SetupForm from './batch/SetupForm.jsx';
import { AnswerInput, InspectDialog, PastBatches, ResultsTable, ValidationSummary } from './batch/Panels.jsx';
import { ConfirmDialog, Notice, PageHeader, Stepper, friendlyError } from './components/c3ui.jsx';
import './c3.css';

const BLANK_SETUP = {
  moduleId: 'SE3010',
  questionId: '',
  title: '',
  questionText: '',
  answerType: 'short',
  maxMarks: '',
  referenceAnswer: '',
  expectedConceptsStr: '',
  rubricTitle: '',
  criteria: [{ criterion_id: 'C1', description: '', max_marks: 1 }],
  mcqOptions: [
    { option_id: 'A', label: 'A', text: '' },
    { option_id: 'B', label: 'B', text: '' },
  ],
  mcqCorrectAnswer: '',
};

const EXAMPLE_ROWS = {
  mcq: 'student_id,selected_option\nIT21001001,B\nIT21001002,A\nIT21001003,\nIT21001004,Z\nIT21001001,B',
  text: 'student_id,answer\nIT21001001,"High cohesion means a module does one well-defined job. Loose coupling reduces dependencies between modules, for example with microservices."\nIT21001002,"Cohesion and coupling are good metrics for modularity."\nIT21001003,""\nIT21001001,"Duplicate row for the first student."',
};

function parseCsv(text) {
  const out = [];
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    const low = line.toLowerCase();
    if (low.startsWith('student_id') || low.startsWith('id,')) continue;
    const i = line.indexOf(',');
    if (i === -1) {
      out.push({ student_id: line, student_answer: '', selected_option_id: '' });
      continue;
    }
    const id = line.slice(0, i).trim().replace(/^["']|["']$/g, '');
    let answer = line.slice(i + 1).trim();
    if (answer.startsWith('"') && answer.endsWith('"')) answer = answer.slice(1, -1).replace(/""/g, '"');
    out.push({ student_id: id, student_answer: answer, selected_option_id: answer });
  }
  return out;
}

function setupErrors(v) {
  const e = {};
  const max = Number(v.maxMarks);
  if (v.title.trim().length < 3) e.title = 'Enter a title of at least 3 characters.';
  if (v.questionText.trim().length < 5) e.questionText = 'Enter the question (at least 5 characters).';
  if (!Number.isFinite(max) || max <= 0) e.maxMarks = 'Enter the total marks as a positive number.';
  if (v.answerType === 'mcq') {
    if (v.mcqOptions.some((o) => !o.text.trim())) e.mcq = 'Give every option some text.';
    else if (!v.mcqCorrectAnswer) e.mcq = 'Choose which option is correct.';
  } else {
    const sum = v.criteria.reduce((s, c) => s + (Number(c.max_marks) || 0), 0);
    if (v.criteria.some((c) => !c.description.trim() || !(Number(c.max_marks) > 0))) e.rubric = 'Every criterion needs a description and marks above 0.';
    if (Math.abs(sum - max) > 0.001) e.rubricSum = true;
    if (e.rubricSum && !e.rubric) e.rubric = 'The criteria marks must add up to the total marks.';
  }
  return e;
}

export default function LecturerBatchMarkingPage() {
  const [tab, setTab] = useState('mark'); // 'mark' | 'history'
  const [step, setStep] = useState('setup'); // 'setup' | 'answers' | 'check' | 'results'

  const [setup, setSetup] = useState(BLANK_SETUP);
  const [showErrors, setShowErrors] = useState(false);
  const [activeSetup, setActiveSetup] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const [mode, setMode] = useState('csv');
  const [csv, setCsv] = useState('');
  const [rows, setRows] = useState([{ student_id: '', student_answer: '' }, { student_id: '', student_answer: '' }]);
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState(null);
  const [answersError, setAnswersError] = useState(null);

  const [marking, setMarking] = useState(false);
  const [runError, setRunError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [resultsError, setResultsError] = useState(null);

  const [confirmAll, setConfirmAll] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [finalizeMsg, setFinalizeMsg] = useState(null);

  const [inspectId, setInspectId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [detailMsg, setDetailMsg] = useState(null);
  const [mark, setMark] = useState('');
  const [reason, setReason] = useState('');
  const [markError, setMarkError] = useState(null);
  const [reasonError, setReasonError] = useState(null);
  const [reviewBusy, setReviewBusy] = useState(false);

  const [pastSetups, setPastSetups] = useState([]);
  const [pastLoading, setPastLoading] = useState(false);
  const [pastError, setPastError] = useState(null);

  const errors = useMemo(() => setupErrors(setup), [setup]);
  const criteriaSum = setup.criteria.reduce((s, c) => s + (Number(c.max_marks) || 0), 0);
  const [examples, setExamples] = useState([]);
  useEffect(() => {
    listExamples().then((d) => setExamples(d.examples || [])).catch(() => setExamples([])); // examples are optional
  }, []);

  const patchSetup = (patch) => setSetup((s) => ({ ...s, ...patch }));

  const loadExample = (id) => {
    const ex = examples.find((x) => x.id === id);
    const p = ex?.config;
    if (!p) return;
    const type = p.answer_type || (p.options ? 'mcq' : 'short');
    setSetup({
      ...BLANK_SETUP,
      questionId: p.question_id || '',
      title: ex.title,
      questionText: p.question_text,
      answerType: type,
      maxMarks: p.max_marks ?? (p.rubric ? p.rubric.criteria.reduce((s, c) => s + c.max_marks, 0) : ''),
      referenceAnswer: p.reference_answer || '',
      expectedConceptsStr: (p.expected_concepts || []).join(', '),
      rubricTitle: p.rubric?.title || '',
      criteria: p.rubric?.criteria || BLANK_SETUP.criteria,
      mcqOptions: p.options || BLANK_SETUP.mcqOptions,
      mcqCorrectAnswer: p.correct_answer || '',
    });
    setShowErrors(false);
    setActiveSetup(null);
    setCheckResult(null);
    setSummary(null);
    setStep('setup');
  };

  const saveSetup = async () => {
    setShowErrors(true);
    if (Object.keys(errors).length > 0) return;
    setSaving(true);
    setSaveError(null);
    try {
      const payload = {
        title: setup.title.trim(),
        module_id: setup.moduleId,
        question_id: setup.questionId.trim() || undefined,
        question_text: setup.questionText.trim(),
        answer_type: setup.answerType,
        max_marks: Number(setup.maxMarks),
        expected_concepts: setup.expectedConceptsStr.split(',').map((s) => s.trim()).filter(Boolean),
      };
      if (setup.answerType === 'mcq') {
        payload.options = setup.mcqOptions;
        payload.correct_answer = setup.mcqCorrectAnswer;
      } else {
        payload.reference_answer = setup.referenceAnswer;
        payload.rubric = { title: setup.rubricTitle || `${setup.title} rubric`, criteria: setup.criteria.map((c) => ({ ...c, max_marks: Number(c.max_marks) })) };
      }
      const res = await createBatchSetup(payload);
      setActiveSetup(res);
      setStep('answers');
    } catch (err) {
      setSaveError(friendlyError(err, 'The setup could not be saved.'));
    } finally {
      setSaving(false);
    }
  };

  const batchId = activeSetup?.batch_id || activeSetup?._id;

  const checkAnswers = async () => {
    setAnswersError(null);
    const list = mode === 'csv' ? parseCsv(csv) : rows.filter((r) => r.student_id.trim());
    if (list.length === 0) {
      setAnswersError('Add at least one student row.');
      return;
    }
    setChecking(true);
    try {
      setCheckResult(await validateBatchAnswers({ setup_id: batchId, items: list }));
      setStep('check');
    } catch (err) {
      setAnswersError(friendlyError(err, 'The answers could not be checked.'));
    } finally {
      setChecking(false);
    }
  };

  const refreshResults = async (id = activeSetup?.batch_id) => {
    if (!id) return;
    setResultsError(null);
    try {
      const data = await getBatchSetup(id);
      setItems(data.items || []);
      setStats(data.stats || null);
    } catch (err) {
      setResultsError(friendlyError(err, 'The results could not be loaded.'));
    }
  };

  const runMarking = async () => {
    if (!checkResult || checkResult.valid_items.length === 0) return;
    setMarking(true);
    setRunError(null);
    try {
      setSummary(await processBatchMarking({ setup_id: batchId, items: checkResult.valid_items }));
      await refreshResults(activeSetup.batch_id);
      setStep('results');
    } catch (err) {
      setRunError(friendlyError(err, 'Marking could not be completed.'));
    } finally {
      setMarking(false);
    }
  };

  const finalizeAll = async () => {
    setFinalizing(true);
    try {
      const res = await finalizeBatchSubmissions(activeSetup.batch_id);
      const left = res.skipped_unreviewed_count || 0;
      setFinalizeMsg(`${res.finalized_count} reviewed result${res.finalized_count === 1 ? '' : 's'} finalized.${left ? ` ${left} not reviewed yet ${left === 1 ? 'was' : 'were'} left pending.` : ''}`);
      setConfirmAll(false);
      await refreshResults();
    } catch (err) {
      setConfirmAll(false);
      setResultsError(friendlyError(err, 'The batch could not be finalized.'));
    } finally {
      setFinalizing(false);
    }
  };

  const openInspect = async (id) => {
    setInspectId(id);
    setDetail(null);
    setDetailError(null);
    setDetailMsg(null);
    setMarkError(null);
    setReasonError(null);
    setDetailLoading(true);
    try {
      const data = await getSubmission(id);
      setDetail(data);
      const r = data.result || {};
      setMark(r.final_mark ?? r.automated_mark ?? '');
      setReason(r.override_reason || '');
    } catch (err) {
      setDetailError(friendlyError(err, 'This result could not be loaded.'));
    } finally {
      setDetailLoading(false);
    }
  };

  const reloadDetail = async () => {
    setDetail(await getSubmission(inspectId));
    await refreshResults();
  };

  const review = async (decision) => {
    setDetailMsg(null);
    setDetailError(null);
    setMarkError(null);
    setReasonError(null);
    const total = detail?.result?.total_possible_marks;
    if (decision === 'overridden') {
      const n = Number(mark);
      let bad = false;
      if (String(mark).trim() === '' || !Number.isFinite(n) || n < 0 || n > total) { setMarkError(`Enter a mark between 0 and ${total}.`); bad = true; }
      if (!reason.trim()) { setReasonError('Give a reason. It is saved with the result.'); bad = true; }
      if (bad) return;
    }
    setReviewBusy(true);
    try {
      await reviewSubmission(inspectId, decision === 'overridden' ? { decision, new_mark: Number(mark), override_reason: reason.trim() } : { decision });
      setDetailMsg(decision === 'accepted' ? 'Automatic mark accepted.' : 'Mark changed and the reason saved.');
      await reloadDetail();
    } catch (err) {
      setDetailError(friendlyError(err, 'The mark could not be saved.'));
    } finally {
      setReviewBusy(false);
    }
  };

  const finalizeOne = async () => {
    setReviewBusy(true);
    setDetailError(null);
    try {
      await finalizeSubmission(inspectId);
      setDetailMsg('Result finalized.');
      await reloadDetail();
    } catch (err) {
      setDetailError(friendlyError(err, 'The result could not be finalized.'));
    } finally {
      setReviewBusy(false);
    }
  };

  const loadPast = async () => {
    setPastLoading(true);
    setPastError(null);
    try {
      setPastSetups((await listBatchSetups()).setups || []);
    } catch (err) {
      setPastError(friendlyError(err, 'Past batches could not be loaded.'));
    } finally {
      setPastLoading(false);
    }
  };

  useEffect(() => {
    if (tab === 'history') loadPast();
  }, [tab]);

  const openPast = async (s) => {
    setTab('mark');
    setActiveSetup(s);
    setSummary(null);
    setFinalizeMsg(null);
    setStep('results');
    await refreshResults(s.batch_id);
  };

  const newBatch = () => {
    setSetup(BLANK_SETUP);
    setShowErrors(false);
    setActiveSetup(null);
    setCheckResult(null);
    setSummary(null);
    setItems([]);
    setStats(null);
    setCsv('');
    setFinalizeMsg(null);
    setTab('mark');
    setStep('setup');
  };

  const filtered = items.filter((it) => {
    if (statusFilter !== 'all' && it.status !== statusFilter) return false;
    const t = search.trim().toLowerCase();
    return !t || (it.student_id || '').toLowerCase().includes(t) || (it.student_answer || '').toLowerCase().includes(t);
  });

  const order = ['setup', 'answers', 'check', 'results'];
  const reached = (k) => order.indexOf(k) <= order.indexOf(step) || (k === 'answers' && !!activeSetup) || (k === 'results' && !!activeSetup && items.length > 0);
  const steps = [
    { key: 'setup', label: 'Assessment setup' },
    { key: 'answers', label: 'Student answers', disabled: !activeSetup },
    { key: 'check', label: 'Validate and confirm', disabled: !checkResult },
    { key: 'results', label: 'Results and review', disabled: !activeSetup || (items.length === 0 && !summary), badge: items.length > 0 ? items.length : null },
  ];

  return (
    <div className="c3-page">
      <PageHeader
        title="Batch Marking"
        subtitle="Set one question and rubric, then mark a whole cohort and review the results."
        actions={
          <>
            <Link to="/lecturer/c3" className="btn secondary">Marking review</Link>
            <div className="tabs" role="group" aria-label="Batch views" style={{ margin: 0 }}>
              <button type="button" className={tab === 'mark' ? 'on' : ''} aria-pressed={tab === 'mark'} onClick={() => setTab('mark')}>Mark a batch</button>
              <button type="button" className={tab === 'history' ? 'on' : ''} aria-pressed={tab === 'history'} onClick={() => setTab('history')}>Past batches</button>
            </div>
          </>
        }
      />

      {tab === 'history' ? (
        <PastBatches setups={pastSetups} loading={pastLoading} error={pastError} onRetry={loadPast} onOpen={openPast} onNew={newBatch} />
      ) : (
        <>
          <Stepper steps={steps.map((s) => ({ ...s, disabled: s.disabled && !reached(s.key) }))} current={step} onSelect={setStep} />

          {step === 'setup' && (
            <SetupForm
              value={setup}
              onChange={patchSetup}
              errors={errors}
              showErrors={showErrors}
              criteriaSum={criteriaSum}
              examples={examples}
              onLoadExample={loadExample}
              onSubmit={saveSetup}
              saving={saving}
              saveError={saveError}
            />
          )}

          {step === 'answers' && activeSetup && (
            <AnswerInput
              setup={activeSetup}
              mode={mode}
              onMode={setMode}
              csv={csv}
              onCsv={setCsv}
              rows={rows}
              onRows={setRows}
              onExample={() => setCsv(activeSetup.answer_type === 'mcq' ? EXAMPLE_ROWS.mcq : EXAMPLE_ROWS.text)}
              onBack={() => setStep('setup')}
              onValidate={checkAnswers}
              busy={checking}
              error={answersError}
            />
          )}

          {step === 'check' && checkResult && <ValidationSummary result={checkResult} onBack={() => setStep('answers')} onRun={runMarking} busy={marking} error={runError} />}

          {step === 'results' && activeSetup && (
            <>
              {resultsError && <Notice tone="error" title="Results unavailable" onRetry={() => refreshResults()}>{resultsError}</Notice>}
              <ResultsTable
                setup={activeSetup}
                summary={summary}
                stats={stats}
                items={filtered}
                search={search}
                onSearch={setSearch}
                status={statusFilter}
                onStatus={setStatusFilter}
                onRefresh={() => refreshResults()}
                onInspect={openInspect}
                onFinalizeAll={() => setConfirmAll(true)}
                finalizing={finalizing}
                finalizeMsg={finalizeMsg}
                onMore={() => { setCheckResult(null); setCsv(''); setStep('answers'); }}
                onNew={newBatch}
              />
            </>
          )}
        </>
      )}

      {inspectId && (
        <InspectDialog
          detail={detail}
          loading={detailLoading}
          error={detailError}
          msg={detailMsg}
          mark={mark}
          onMark={setMark}
          reason={reason}
          onReason={setReason}
          markError={markError}
          reasonError={reasonError}
          busy={reviewBusy}
          onAccept={() => review('accepted')}
          onOverride={() => review('overridden')}
          onFinalize={finalizeOne}
          onClose={() => setInspectId(null)}
        />
      )}

      {confirmAll && (
        <ConfirmDialog
          title="Finalize reviewed results?"
          message={`Results in "${activeSetup?.title || 'this batch'}" that you have already reviewed will become final and can no longer be changed. Results you have not reviewed yet stay pending; review them first.`}
          confirmLabel="Finalize reviewed"
          busy={finalizing}
          onConfirm={finalizeAll}
          onCancel={() => setConfirmAll(false)}
        />
      )}
    </div>
  );
}
