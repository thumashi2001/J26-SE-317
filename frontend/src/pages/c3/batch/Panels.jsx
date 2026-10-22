import React from 'react';
import { Link } from 'react-router-dom';
import AssessmentResult from '../components/AssessmentResult.jsx';
import { Dialog, EmptyState, Notice, Spinner, StatusPill } from '../components/c3ui.jsx';

const fmt = (d) => (d ? new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : '-');

// Step 2: paste a CSV or type rows.
export function AnswerInput({ setup, mode, onMode, csv, onCsv, rows, onRows, onExample, onBack, onValidate, busy, error }) {
  const isMcq = setup.answer_type === 'mcq';
  const upd = (i, patch) => onRows(rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  return (
    <section className="panel" aria-label="Student answers">
      <h2 style={{ margin: '0 0 4px' }}>Student answers</h2>
      <p className="muted" style={{ margin: '0 0 12px' }}>
        {setup.title} · {setup.question_id} · {isMcq ? 'multiple choice' : 'written answers'} · {setup.max_marks} marks
      </p>
      <div className="tabs" role="group" aria-label="Entry method" style={{ margin: '0 0 12px' }}>
        <button type="button" className={mode === 'csv' ? 'on' : ''} aria-pressed={mode === 'csv'} onClick={() => onMode('csv')}>Paste CSV</button>
        <button type="button" className={mode === 'grid' ? 'on' : ''} aria-pressed={mode === 'grid'} onClick={() => onMode('grid')}>Type rows</button>
      </div>

      {mode === 'csv' ? (
        <div className="c3-field">
          <label htmlFor="csv">{isMcq ? 'One row per student: student_id,selected_option' : 'One row per student: student_id,"answer text"'}</label>
          <textarea id="csv" style={{ minHeight: 200, fontFamily: 'ui-monospace, Consolas, monospace', fontSize: '0.88rem' }} value={csv} onChange={(e) => onCsv(e.target.value)} />
          <span className="hint" style={{ margin: 0 }}>A header row is optional. <button type="button" className="btn-link-dark" onClick={onExample}>Fill example rows</button> (not real students) to try the checks.</span>
        </div>
      ) : (
        <div className="c3-grid-rows">
          {rows.map((r, i) => (
            <div key={i} className="c3-crit-row">
              <div className="c3-field">
                <label htmlFor={`g-id-${i}`}>Student ID</label>
                <input id={`g-id-${i}`} value={r.student_id} onChange={(e) => upd(i, { student_id: e.target.value })} />
              </div>
              <div className="c3-field c3-grow">
                <label htmlFor={`g-a-${i}`}>{isMcq ? 'Selected option' : 'Answer'}</label>
                <input id={`g-a-${i}`} value={isMcq ? r.selected_option_id || '' : r.student_answer} onChange={(e) => upd(i, isMcq ? { selected_option_id: e.target.value, student_answer: e.target.value } : { student_answer: e.target.value })} />
              </div>
              <button type="button" className="btn-ghost c3-close" onClick={() => onRows(rows.filter((_, idx) => idx !== i))} aria-label={`Remove row ${i + 1}`}>Remove</button>
            </div>
          ))}
          <div><button type="button" className="btn secondary c3-sm" onClick={() => onRows([...rows, { student_id: '', student_answer: '' }])}>Add row</button></div>
        </div>
      )}

      {error && <Notice tone="error" title="Check the answers">{error}</Notice>}
      <div className="c3-form-actions" style={{ marginTop: 14 }}>
        <button type="button" className="btn secondary" onClick={onBack} disabled={busy}>Back to setup</button>
        <button type="button" className="btn" onClick={onValidate} disabled={busy}>{busy ? 'Checking...' : 'Check answers'}</button>
      </div>
    </section>
  );
}

// Step 3: what the checks found, then run marking.
export function ValidationSummary({ result, onBack, onRun, busy, error }) {
  return (
    <section className="panel" aria-label="Check results">
      <h2 style={{ margin: '0 0 12px' }}>Check results</h2>
      <div className="c3-stats">
        <div className="c3-stat"><b>{result.total_rows}</b><span>Rows</span></div>
        <div className="c3-stat"><b>{result.valid_count}</b><span>Ready to mark</span></div>
        <div className="c3-stat"><b>{result.invalid_count}</b><span>Need fixing</span></div>
      </div>
      {result.invalid_count > 0 && (
        <>
          <Notice tone="warn" title="These rows will be skipped">Fix them in the previous step and check again, or continue without them.</Notice>
          <div className="table-wrap">
            <table className="data-table c3-table">
              <thead><tr><th scope="col">Row</th><th scope="col">Student</th><th scope="col">Problem</th></tr></thead>
              <tbody>
                {result.invalid_items.map((it, i) => (
                  <tr key={i}><td>{it.row}</td><td>{it.student_id || '-'}</td><td>{it.reason}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {result.valid_count > 0 && (
        <details style={{ marginTop: 12 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--primary-dark)' }}>Rows that will be marked ({result.valid_count})</summary>
          <div className="table-wrap">
            <table className="data-table c3-table">
              <thead><tr><th scope="col">Row</th><th scope="col">Student</th><th scope="col">Answer</th></tr></thead>
              <tbody>
                {result.valid_items.map((it) => (
                  <tr key={it.row}>
                    <td>{it.row}</td>
                    <td>{it.student_id}</td>
                    <td><div className="c3-trunc" title={it.student_answer}>{it.is_unanswered ? <span className="muted">No option chosen (scores 0)</span> : it.student_answer}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      {error && <Notice tone="error" title="Marking failed">{error}</Notice>}
      <div className="c3-form-actions" style={{ marginTop: 14 }}>
        <button type="button" className="btn secondary" onClick={onBack} disabled={busy}>Back to answers</button>
        <button type="button" className="btn" onClick={onRun} disabled={busy || result.valid_count === 0}>
          {busy ? `Marking ${result.valid_count} answers...` : `Mark ${result.valid_count} answer${result.valid_count === 1 ? '' : 's'}`}
        </button>
        {busy && <Spinner />}
      </div>
    </section>
  );
}

// Step 4: cohort results.
export function ResultsTable({ setup, summary, stats, items, search, onSearch, status, onStatus, onRefresh, onInspect, onFinalizeAll, finalizing, finalizeMsg, onMore, onNew }) {
  const max = setup.max_marks;
  return (
    <section aria-label="Results" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {summary && (
        <Notice tone={summary.failed_count > 0 ? 'warn' : 'success'} title="Marking complete">
          {summary.successful_count} marked{summary.failed_count ? `, ${summary.failed_count} could not be marked` : ''}{summary.invalid_rows_ignored ? `, ${summary.invalid_rows_ignored} skipped after checks` : ''}.
          {summary.failed_count > 0 && (
            <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
              {(summary.results || []).filter((x) => x.status === 'failed').map((x) => (
                <li key={x.student_id}>{x.student_id}: {x.error}</li>
              ))}
            </ul>
          )}
        </Notice>
      )}
      {finalizeMsg && <Notice tone="success">{finalizeMsg}</Notice>}

      {stats && (
        <div className="c3-stats">
          <div className="c3-stat"><b>{stats.total_count}</b><span>Students</span></div>
          <div className="c3-stat"><b>{stats.pending_count}</b><span>Awaiting review</span></div>
          <div className="c3-stat"><b>{stats.reviewed_count}</b><span>Reviewed</span></div>
          <div className="c3-stat"><b>{stats.finalized_count}</b><span>Finalized</span></div>
          {stats.average_mark != null && <div className="c3-stat"><b>{stats.average_mark}</b><span>Average of {max}</span></div>}
        </div>
      )}

      <div className="panel" style={{ margin: 0 }}>
        <div className="c3-queue-filters">
          <div className="tabs" role="group" aria-label="Filter by status" style={{ margin: 0 }}>
            {[['all', 'All'], ['pending_review', 'Awaiting review'], ['reviewed', 'Reviewed'], ['finalized', 'Finalized'], ['failed', 'Failed']].map(([k, label]) => (
              <button key={k} type="button" className={status === k ? 'on' : ''} aria-pressed={status === k} onClick={() => onStatus(k)}>{label}</button>
            ))}
          </div>
          <div>
            <label htmlFor="r-search" className="c3-sr">Search by student or answer</label>
            <input id="r-search" type="search" value={search} onChange={(e) => onSearch(e.target.value)} placeholder="Search student or answer" />
          </div>
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState title="No results to show">Nothing matches the filters, or no answers have been marked yet.</EmptyState>
      ) : (
        <div className="panel flush" style={{ margin: 0 }}>
          <div className="table-wrap">
            <table className="data-table c3-table" style={{ margin: 0, minWidth: 720 }}>
              <caption className="c3-sr">Marked answers</caption>
              <thead>
                <tr>
                  <th scope="col">Student</th>
                  <th scope="col">Answer</th>
                  <th scope="col">Automatic mark</th>
                  <th scope="col">Final mark</th>
                  <th scope="col">Status</th>
                  <th scope="col"><span className="c3-sr">Action</span></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr key={it.submission_id}>
                    <td><strong>{it.student_id}</strong></td>
                    <td><div className="c3-trunc" title={it.student_answer}>{it.student_answer || '-'}</div></td>
                    <td>{it.automated_mark ?? '-'} / {max}</td>
                    <td>{it.final_mark != null ? `${it.final_mark} / ${max}` : <span className="muted">-</span>}</td>
                    <td><StatusPill status={it.status} /></td>
                    <td><button type="button" className="btn secondary c3-sm" onClick={() => onInspect(it.submission_id)}>View analysis</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="c3-form-actions">
        <button type="button" className="btn" onClick={onFinalizeAll} disabled={finalizing || items.length === 0}>{finalizing ? 'Finalizing...' : 'Finalize reviewed'}</button>
        <button type="button" className="btn secondary" onClick={onRefresh}>Refresh</button>
        <button type="button" className="btn secondary" onClick={onMore}>Add more students</button>
        <button type="button" className="btn secondary" onClick={onNew}>New batch</button>
      </div>
    </section>
  );
}

export function PastBatches({ setups, loading, error, onRetry, onOpen, onNew }) {
  if (loading) return <Spinner label="Loading past batches..." />;
  if (error) return <Notice tone="error" title="Past batches unavailable" onRetry={onRetry}>{error}</Notice>;
  if (setups.length === 0) return <EmptyState title="No batches yet" action={<button type="button" className="btn" onClick={onNew}>Start a batch</button>}>Batches you create appear here.</EmptyState>;
  return (
    <div className="panel flush" style={{ margin: 0 }}>
      <div className="table-wrap">
        <table className="data-table c3-table" style={{ margin: 0, minWidth: 720 }}>
          <caption className="c3-sr">Past batches</caption>
          <thead><tr><th scope="col">Assessment</th><th scope="col">Module</th><th scope="col">Created</th><th scope="col">Marked</th><th scope="col">Finalized</th><th scope="col"><span className="c3-sr">Action</span></th></tr></thead>
          <tbody>
            {setups.map((s) => (
              <tr key={s._id}>
                <td><strong>{s.title}</strong><div className="small muted">{s.question_id}</div></td>
                <td>{s.module_id}</td>
                <td className="small muted">{fmt(s.created_at)}</td>
                <td>{s.stats?.total ?? 0}</td>
                <td>{s.stats?.finalized ?? 0} / {s.stats?.total ?? 0}</td>
                <td><button type="button" className="btn secondary c3-sm" onClick={() => onOpen(s)}>Open</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Review one student's result without leaving the batch.
export function InspectDialog({ detail, loading, error, msg, mark, onMark, reason, onReason, markError, reasonError, busy, onAccept, onOverride, onFinalize, onClose }) {
  const r = detail?.result;
  const total = r?.total_possible_marks;
  const finalized = r?.status === 'finalized';
  return (
    <Dialog title={detail ? `Review ${detail.submission.student_id}` : 'Review'} onClose={onClose} wide>
      {loading && <Spinner label="Loading result..." />}
      {error && <Notice tone="error" title="Could not load or update this result">{error}</Notice>}
      {msg && <Notice tone="success">{msg}</Notice>}
      {detail && (
        <>
          <div className="c3-dual" style={{ marginBottom: 14 }}>
            <div>
              <div className="c3-dual-label">Automatic mark</div>
              <div className="c3-mark-big">{r.automated_mark ?? '-'}<span className="c3-mark-of"> / {total}</span></div>
            </div>
            <div>
              <div className="c3-dual-label">{finalized ? 'Final mark' : 'Your mark'}</div>
              {r.final_mark != null ? <div className="c3-mark-big">{r.final_mark}<span className="c3-mark-of"> / {total}</span></div> : <div className="muted" style={{ padding: '10px 0' }}>Not decided yet</div>}
              <div className="small muted"><StatusPill status={r.status} /></div>
            </div>
          </div>

          {!finalized && (
            <div className="c3-inline-review">
              <div className="c3-grid-2">
                <div className="c3-field">
                  <label htmlFor="i-mark">New mark (0 to {total})</label>
                  <input id="i-mark" type="number" min="0" max={total} step="0.5" value={mark} onChange={(e) => onMark(e.target.value)} aria-invalid={!!markError} />
                  {markError && <p className="c3-error" role="alert">{markError}</p>}
                </div>
                <div className="c3-field">
                  <label htmlFor="i-reason">Reason for changing the mark</label>
                  <textarea id="i-reason" style={{ minHeight: 60 }} maxLength={2000} value={reason} onChange={(e) => onReason(e.target.value)} aria-invalid={!!reasonError} />
                  {reasonError && <p className="c3-error" role="alert">{reasonError}</p>}
                </div>
              </div>
              <div className="c3-form-actions">
                <button type="button" className="btn" onClick={onAccept} disabled={busy}>Accept automatic mark</button>
                <button type="button" className="btn secondary" onClick={onOverride} disabled={busy}>Save changed mark</button>
                <button type="button" className="btn secondary" onClick={onFinalize} disabled={busy || r.status !== 'reviewed'} title={r.status === 'reviewed' ? '' : 'Accept or change the mark first'}>Finalize</button>
                <Link to={`/lecturer/c3/${detail.submission._id}`} className="small">Open full review page</Link>
              </div>
            </div>
          )}
          {finalized && <p className="muted">This result is finalized and cannot be changed.</p>}

          <div style={{ marginTop: 16 }}>
            <AssessmentResult evaluation={r.ai_evaluation} historicalResult={r} question={detail.submission.question_text} answer={detail.submission.student_answer} showMarkCard={false} showContext />
          </div>
        </>
      )}
    </Dialog>
  );
}
