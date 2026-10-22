import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { finalizeSubmission, getSubmission, reviewSubmission } from '../../services/c3Api.js';
import AssessmentResult from './components/AssessmentResult.jsx';
import { ConfirmDialog, Dialog, Notice, PageHeader, SourceBadge, Spinner, StatusPill, friendlyError } from './components/c3ui.jsx';
import './c3.css';

const fmt = (d) => (d ? new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '-');

export default function LecturerReviewPage() {
  const { submissionId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [overrideOpen, setOverrideOpen] = useState(false);
  const [newMark, setNewMark] = useState('');
  const [reason, setReason] = useState('');
  const [markError, setMarkError] = useState(null);
  const [reasonError, setReasonError] = useState(null);
  const [finalizeOpen, setFinalizeOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const resp = await getSubmission(submissionId);
      setData(resp);
      const r = resp.result || {};
      const start = r.final_mark ?? r.automated_mark;
      setNewMark(start != null ? String(start) : '');
      setReason(r.override_reason || '');
    } catch (err) {
      setLoadError(friendlyError(err, 'This submission could not be loaded.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [submissionId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="c3-page">
        <Spinner label="Loading submission..." />
      </div>
    );
  }
  if (loadError || !data) {
    return (
      <div className="c3-page">
        <Notice tone="error" title="Submission unavailable" onRetry={load}>{loadError || 'Submission not found.'}</Notice>
        <div><Link to="/lecturer/c3" className="btn secondary">Back to the queue</Link></div>
      </div>
    );
  }

  const { submission, result } = data;
  const evaluation = result?.ai_evaluation || {};
  const total = result?.total_possible_marks ?? evaluation.marking?.total_possible_marks ?? 0;
  const automatic = result?.automated_mark ?? evaluation.marking?.total_awarded_marks ?? 0;
  const status = result?.status || submission?.status || 'pending_review';
  const decision = result?.lecturer_decision;
  const finalized = status === 'finalized';

  const apply = (patch) => setData((prev) => ({ ...prev, submission: { ...prev.submission, status: patch.status }, result: { ...prev.result, ...patch } }));

  const accept = async () => {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const resp = await reviewSubmission(submission._id, { decision: 'accepted' });
      apply({ ...resp.result, status: 'reviewed', lecturer_decision: 'accepted', final_mark: automatic, override_reason: null });
      setSuccess('Automatic mark accepted. You can now finalize the result.');
    } catch (err) {
      setError(friendlyError(err, 'The mark could not be accepted.'));
    } finally {
      setBusy(false);
    }
  };

  const openOverride = () => {
    setMarkError(null);
    setReasonError(null);
    setOverrideOpen(true);
  };

  const saveOverride = async (e) => {
    e.preventDefault();
    const num = Number(newMark);
    let ok = true;
    if (newMark.trim() === '' || !Number.isFinite(num)) {
      setMarkError('Enter a number.');
      ok = false;
    } else if (num < 0 || num > total) {
      setMarkError(`The mark must be between 0 and ${total}.`);
      ok = false;
    } else setMarkError(null);
    if (!reason.trim()) {
      setReasonError('Give a reason. It is saved with the result.');
      ok = false;
    } else setReasonError(null);
    if (!ok) return;
    setBusy(true);
    try {
      const resp = await reviewSubmission(submission._id, { decision: 'overridden', new_mark: num, override_reason: reason.trim() });
      apply({ ...resp.result, status: 'reviewed', lecturer_decision: 'overridden', final_mark: num, override_reason: reason.trim() });
      setOverrideOpen(false);
      setSuccess(`Mark changed to ${num} / ${total}. The reason has been saved.`);
    } catch (err) {
      setMarkError(friendlyError(err, 'The mark could not be saved.'));
    } finally {
      setBusy(false);
    }
  };

  const finalize = async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await finalizeSubmission(submission._id);
      apply({ ...resp.result, status: 'finalized' });
      setFinalizeOpen(false);
      setSuccess('Result finalized. It is now official and can no longer be changed.');
    } catch (err) {
      setFinalizeOpen(false);
      setError(friendlyError(err, 'The result could not be finalized.'));
    } finally {
      setBusy(false);
    }
  };

  const canFinalize = !finalized && (decision || status === 'reviewed');

  return (
    <div className="c3-page">
      <PageHeader
        title="Review submission"
        subtitle={`${submission.student_id} · ${submission.question_id} · submitted ${fmt(submission.submitted_at)}`}
        actions={<><SourceBadge submission={submission} /><StatusPill status={status} /><Link to="/lecturer/c3" className="btn secondary">Back to the queue</Link></>}
      />

      {success && <Notice tone="success" onDismiss={() => setSuccess(null)}>{success}</Notice>}
      {error && <Notice tone="error" title="Action failed" onDismiss={() => setError(null)}>{error}</Notice>}

      <section className="panel c3-review-panel" aria-label="Decision" style={{ margin: 0 }}>
        <div className="c3-dual">
          <div>
            <div className="c3-dual-label">Automatic mark</div>
            <div className="c3-mark-big">{automatic}<span className="c3-mark-of"> / {total}</span></div>
            <div className="small muted">Proposed by the automated marking. Not official until you decide.</div>
          </div>
          <div>
            <div className="c3-dual-label">{finalized ? 'Final mark' : 'Your mark'}</div>
            {result?.final_mark != null ? (
              <div className="c3-mark-big">{result.final_mark}<span className="c3-mark-of"> / {total}</span></div>
            ) : (
              <div className="muted" style={{ fontSize: '1.1rem', padding: '10px 0' }}>Not decided yet</div>
            )}
            <div className="small muted">
              {decision ? `${decision === 'accepted' ? 'Automatic mark accepted' : 'Mark adjusted'}${result?.reviewed_by ? ` by ${result.reviewed_by}` : ''}${result?.reviewed_at ? ` on ${fmt(result.reviewed_at)}` : ''}.` : 'Accept the automatic mark or change it with a reason.'}
              {finalized && result?.finalized_at ? ` Finalized ${fmt(result.finalized_at)}.` : ''}
            </div>
          </div>
        </div>

        {decision === 'overridden' && (
          <div className="c3-reason"><strong>Reason for the change</strong><p>{result?.override_reason || 'No reason recorded.'}</p></div>
        )}

        <div className="c3-form-actions" style={{ marginTop: 14 }}>
          {finalized ? (
            <span className="muted">This result is finalized and cannot be changed.</span>
          ) : (
            <>
              <button type="button" className="btn" onClick={accept} disabled={busy}>Accept automatic mark</button>
              <button type="button" className="btn secondary" onClick={openOverride} disabled={busy}>Change mark</button>
              <button type="button" className="btn secondary" onClick={() => setFinalizeOpen(true)} disabled={busy || !canFinalize} title={canFinalize ? '' : 'Accept or change the mark first'}>
                Finalize result
              </button>
            </>
          )}
        </div>
      </section>

      <section className="panel" aria-label="Question and answer" style={{ margin: 0 }}>
        <h3 style={{ margin: '0 0 8px' }}>Question and answer</h3>
        <p className="small" style={{ marginTop: 0 }}><strong>Question:</strong> {submission.question_text || submission.question_id}</p>
        <div className="c3-answer-box">{submission.student_answer || 'No answer text was recorded.'}</div>
        {submission.reference_answer && (
          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: 'pointer', color: 'var(--primary-dark)' }}>Reference answer</summary>
            <p className="small muted" style={{ margin: '8px 0 0' }}>{submission.reference_answer}</p>
          </details>
        )}
      </section>

      <AssessmentResult evaluation={result?.ai_evaluation} historicalResult={result} showMarkCard={false} showContext={false} />

      {overrideOpen && (
        <Dialog
          title="Change the mark"
          onClose={() => !busy && setOverrideOpen(false)}
          footer={
            <>
              <button type="button" className="btn secondary" onClick={() => setOverrideOpen(false)} disabled={busy}>Cancel</button>
              <button type="submit" form="override-form" className="btn" disabled={busy}>{busy ? 'Saving...' : 'Save mark'}</button>
            </>
          }
        >
          <form id="override-form" onSubmit={saveOverride} noValidate>
            <p className="small muted" style={{ marginTop: 0 }}>Automatic mark: {automatic} / {total}. The original automatic mark is always kept.</p>
            <div className="c3-field">
              <label htmlFor="ov-mark">New mark (0 to {total})</label>
              <input id="ov-mark" data-autofocus type="number" inputMode="decimal" step="0.5" min="0" max={total} value={newMark} onChange={(e) => setNewMark(e.target.value)} aria-invalid={!!markError} aria-describedby={markError ? 'ov-mark-err' : undefined} />
              {markError && <p id="ov-mark-err" className="c3-error" role="alert">{markError}</p>}
            </div>
            <div className="c3-field">
              <label htmlFor="ov-reason">Reason</label>
              <textarea id="ov-reason" maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={!!reasonError} aria-describedby={reasonError ? 'ov-reason-err' : undefined} style={{ minHeight: 110 }} />
              {reasonError && <p id="ov-reason-err" className="c3-error" role="alert">{reasonError}</p>}
            </div>
          </form>
        </Dialog>
      )}

      {finalizeOpen && (
        <ConfirmDialog
          title="Finalize this result?"
          message={`The final mark will be ${result?.final_mark ?? automatic} / ${total}. Once finalized it is official and cannot be changed.`}
          confirmLabel="Finalize"
          busy={busy}
          onConfirm={finalize}
          onCancel={() => setFinalizeOpen(false)}
        />
      )}
    </div>
  );
}
