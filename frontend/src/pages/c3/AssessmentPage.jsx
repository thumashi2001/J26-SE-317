import React, { useEffect, useRef, useState } from 'react';
import { assessAnswer, getSubmission, listAssessments, listSubmissions } from '../../services/c3Api.js';
import { SAMPLE_ANSWERS } from './samples.js';
import AssessmentResult from './components/AssessmentResult.jsx';
import { EmptyState, Notice, PageHeader, Spinner, StatusPill, friendlyError } from './components/c3ui.jsx';
import './c3.css';

// Student page: choose an assessment, write an answer, see the proposed mark with evidence and feedback.
// The question, rubric and answer key stay on the server; this page only ever sends the answer.
export default function AssessmentPage() {
  const [tab, setTab] = useState('answer'); // 'answer' | 'history'
  const [assessments, setAssessments] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [answer, setAnswer] = useState('');
  const [optionId, setOptionId] = useState(null);
  const [fieldError, setFieldError] = useState(null);

  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [result, setResult] = useState(null); // { evaluation, submissionId, question, answer }

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailBusy, setDetailBusy] = useState(false);
  const resultRef = useRef(null);
  // Only an explicit {available: true} from the server would ever hide the notice; nothing here is C2-originated today.
  const [c2Available, setC2Available] = useState(false);

  // Ask the server which demo questions exist (question text and options only, never keys or rubrics).
  const loadAssessments = async () => {
    setLoadError(null);
    setAssessments(null); // shows the loading state again, so "Try again" visibly re-requests
    try {
      const data = await listAssessments();
      const list = data.assessments || [];
      setC2Available(data.integrations?.c2?.available === true);
      setAssessments(list);
      // Nothing is preselected: a student only answers an assessment they explicitly chose.
      setSelectedId((cur) => (cur && list.some((a) => a.id === cur) ? cur : null));
    } catch (err) {
      setAssessments([]);
      setLoadError(
        err.status === 404
          ? 'The assessments list was not found on the server. The backend is probably running an older version: restart it (npm run dev in the backend folder) and try again.'
          : friendlyError(err, 'The assessments could not be loaded.')
      );
    }
  };

  // The student's own earlier submissions (the server filters to the signed-in student).
  const loadHistory = async () => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const data = await listSubmissions();
      setHistory(data.submissions || []);
    } catch (err) {
      setHistoryError(friendlyError(err, 'Your submissions could not be loaded.'));
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadAssessments();
    loadHistory();
  }, []);

  const selected = (assessments || []).find((a) => a.id === selectedId) || null;
  const isMcq = selected && (selected.answer_type === 'mcq' || selected.answer_type === 'multiple-choice');
  const sample = selected && !isMcq ? SAMPLE_ANSWERS[selected.id] : null;

  // Pick a question; nothing is preselected, and the previous answer/result is cleared.
  const choose = (a) => {
    setSelectedId(a.id);
    setAnswer('');
    setOptionId(null);
    setFieldError(null);
    setSubmitError(null);
    setResult(null);
  };

  // Sends ONLY demo_id plus the answer (or chosen option). The server looks up the rubric/key itself, marks the answer
  // and saves it as pending_review; the page then shows the returned evaluation.
  const submit = async (e) => {
    e.preventDefault();
    if (!selected) return;
    if (isMcq ? !optionId : !answer.trim()) {
      setFieldError(isMcq ? 'Choose one option before submitting.' : 'Write your answer before submitting.');
      return;
    }
    setFieldError(null);
    setSubmitError(null);
    setBusy(true);
    try {
      const body = { demo_id: selected.id };
      if (isMcq) body.selected_option_id = optionId;
      else body.student_answer = answer.trim();
      const data = await assessAnswer(body);
      setResult({
        evaluation: data,
        submissionId: data.submission_id,
        question: selected.question_text,
        answer: isMcq ? selected.options?.find((o) => o.option_id === optionId)?.text || optionId : answer.trim(),
      });
      loadHistory();
      setTimeout(() => resultRef.current?.focus(), 50);
    } catch (err) {
      if (err.status === 404) {
        // The server does not know this demo assessment: usually a backend still running an older version.
        setSubmitError('This demo assessment was not found on the server. The server may be running an older version: restart the backend (npm run dev in the backend folder), then refresh this page and choose an assessment again.');
        loadAssessments();
      } else {
        setSubmitError(friendlyError(err, 'Your answer could not be marked. Please try again.'));
      }
    } finally {
      setBusy(false);
    }
  };

  // Open an earlier submission; the server returns a redacted copy for students.
  const openSubmission = async (id) => {
    setDetailBusy(true);
    setHistoryError(null);
    try {
      setDetail(await getSubmission(id));
    } catch (err) {
      setHistoryError(friendlyError(err, 'This submission could not be opened.'));
    } finally {
      setDetailBusy(false);
    }
  };

  return (
    <div className="c3-page">
      <PageHeader title="Automated Marking & Answer Analysis" subtitle="Answer a question and get a proposed mark with the evidence, feedback and concept map behind it." />

      <div className="tabs" role="tablist" aria-label="Marking sections" style={{ margin: 0 }}>
        <button type="button" role="tab" aria-selected={tab === 'answer'} className={tab === 'answer' ? 'on' : ''} onClick={() => setTab('answer')}>
          Answer a question
        </button>
        <button type="button" role="tab" aria-selected={tab === 'history'} className={tab === 'history' ? 'on' : ''} onClick={() => { setTab('history'); setDetail(null); }}>
          My submissions <span className="tab-count">{history.length}</span>
        </button>
      </div>

      {tab === 'answer' && (
        <>
          {loadError && <Notice tone="error" title="Assessments unavailable" onRetry={loadAssessments}>{loadError}</Notice>}

          {assessments === null && !loadError && <Spinner label="Loading assessments..." />}

          {assessments && assessments.length === 0 && !loadError && (
            <EmptyState title="No assessments available yet">No demo assessments are available right now. Check back later.</EmptyState>
          )}

          {assessments && assessments.length > 0 && (
            <>
              <section aria-labelledby="pick-h">
                <h2 id="pick-h" style={{ margin: '0 0 10px' }}>Choose an assessment</h2>
                {!c2Available && (
                  <Notice tone="info">C2 assessments are not available yet. The assessments currently shown are demo assessments.</Notice>
                )}
                <div role="group" aria-label="Demo assessments (practice examples)" style={{ marginTop: 12 }}>
                  <h3 className="small muted" style={{ margin: '0 0 8px' }}>Demo assessments (practice examples)</h3>
                  <div className="c3-picker">
                    {assessments.map((a) => (
                      <button key={a.id} type="button" className="c3-pick" data-source="demo" aria-pressed={a.id === selectedId} onClick={() => choose(a)}>
                        <strong>{a.title}</strong>
                        <span>
                          <span className="c3-source-badge demo">Demo</span>{' '}
                          {a.answer_type === 'mcq' ? 'Multiple choice' : 'Written answer'}
                          {a.max_marks != null ? ` · ${a.max_marks} marks` : ''}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </section>

              {!selected && !result && (
                <p className="c3-choose-hint muted" role="status" style={{ margin: '4px 0 0' }}>Choose an assessment to start.</p>
              )}

              {selected && !result && (
                <form className="panel" onSubmit={submit} noValidate aria-label="Your answer">
                  <h2 style={{ margin: '0 0 12px' }}>Your answer</h2>
                  <div className="c3-question">
                    <strong>Question</strong>
                    <p style={{ margin: '4px 0 0' }}>{selected.question_text}</p>
                  </div>

                  {isMcq ? (
                    <fieldset className="c3-field" style={{ border: 0, padding: 0, margin: '0 0 14px' }} aria-describedby={fieldError ? 'ans-err' : undefined}>
                      <legend className="c3-label">Choose one option</legend>
                      <div className="c3-options">
                        {(selected.options || []).map((o) => (
                          <label key={o.option_id} className="c3-option">
                            <input type="radio" name="option" value={o.option_id} checked={optionId === o.option_id} onChange={() => { setOptionId(o.option_id); setFieldError(null); }} />
                            <span>
                              <strong>{o.label}.</strong> {o.text}
                            </span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  ) : (
                    <div className="c3-field">
                      <label htmlFor="ans">Write your answer</label>
                      <textarea id="ans" value={answer} onChange={(e) => { setAnswer(e.target.value); setFieldError(null); }} aria-invalid={!!fieldError} aria-describedby={fieldError ? 'ans-err' : 'ans-hint'} />
                      <span id="ans-hint" className="hint" style={{ margin: 0 }}>
                        {answer.trim() ? answer.trim().split(/\s+/).length : 0} words
                        {sample && (
                          <>
                            {' · '}
                            <button type="button" className="btn-link-dark" onClick={() => { setAnswer(sample); setFieldError(null); }}>
                              Insert an example answer
                            </button>
                          </>
                        )}
                      </span>
                    </div>
                  )}
                  {fieldError && <p id="ans-err" className="c3-error" role="alert" style={{ margin: '0 0 12px', color: 'var(--red-ink)' }}>{fieldError}</p>}
                  {submitError && <Notice tone="error" title="Could not mark your answer" onRetry={() => submit({ preventDefault() {} })} onDismiss={() => setSubmitError(null)}>{submitError}</Notice>}

                  <div className="c3-form-actions" style={{ marginTop: 12 }}>
                    <button className="btn" type="submit" disabled={busy}>
                      {busy ? 'Marking your answer...' : 'Submit answer'}
                    </button>
                    {busy && <Spinner />}
                    {!busy && (answer || optionId) && (
                      <button type="button" className="btn secondary" onClick={() => { setAnswer(''); setOptionId(null); setFieldError(null); }}>
                        Clear
                      </button>
                    )}
                  </div>
                </form>
              )}
            </>
          )}

          {result && (
            <div ref={resultRef} tabIndex={-1} style={{ outline: 'none' }}>
              <AssessmentResult evaluation={result.evaluation} historicalResult={{ status: 'pending_review' }} submissionId={result.submissionId} question={result.question} answer={result.answer} />
              <div className="c3-form-actions" style={{ marginTop: 16 }}>
                <button type="button" className="btn" onClick={() => { setResult(null); setAnswer(''); setOptionId(null); }}>
                  Answer another question
                </button>
                <button type="button" className="btn secondary" onClick={() => setTab('history')}>
                  View my submissions
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {tab === 'history' && !detail && (
        <section aria-label="My submissions">
          {historyError && <Notice tone="error" title="Submissions unavailable" onRetry={loadHistory}>{historyError}</Notice>}
          {historyLoading && history.length === 0 ? (
            <Spinner label="Loading your submissions..." />
          ) : history.length === 0 && !historyError ? (
            <EmptyState title="No submissions yet" action={<button type="button" className="btn" onClick={() => setTab('answer')}>Answer a question</button>}>
              Your marked answers will appear here.
            </EmptyState>
          ) : (
            history.length > 0 && (
              <div className="panel flush">
                <div className="table-wrap">
                  <table className="data-table c3-table" style={{ margin: 0 }}>
                    <thead>
                      <tr>
                        <th>Question</th>
                        <th>Submitted</th>
                        <th>Mark</th>
                        <th>Status</th>
                        <th>
                          <span className="c3-sr">Open</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((s) => {
                        const finalized = s.status === 'finalized' && s.final_mark != null;
                        const mark = finalized ? s.final_mark : s.automated_mark;
                        return (
                          <tr key={s._id}>
                            <td>
                              <div className="c3-trunc" title={s.question_text}>{s.question_text || s.question_id}</div>
                            </td>
                            <td className="small muted">{s.submitted_at ? new Date(s.submitted_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '-'}</td>
                            <td>
                              {mark != null ? (
                                <>
                                  <strong>{mark} / {s.total_possible_marks}</strong>
                                  {!finalized && <span className="small muted"> proposed</span>}
                                </>
                              ) : (
                                <span className="muted">-</span>
                              )}
                            </td>
                            <td><StatusPill status={s.status} /></td>
                            <td>
                              <button type="button" className="btn secondary c3-sm" disabled={detailBusy} onClick={() => openSubmission(s._id)}>
                                Open
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          )}
        </section>
      )}

      {tab === 'history' && detail && (
        <section aria-label="Submission detail">
          <button type="button" className="btn secondary back" onClick={() => setDetail(null)} style={{ marginBottom: 12 }}>
            Back to my submissions
          </button>
          <AssessmentResult
            evaluation={detail.result?.ai_evaluation || detail.result}
            historicalResult={detail.result}
            submissionId={detail.submission?._id}
            question={detail.submission?.question_text}
            answer={detail.submission?.student_answer}
          />
        </section>
      )}
    </div>
  );
}
