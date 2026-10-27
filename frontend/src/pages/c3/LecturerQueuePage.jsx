// LECTURER QUEUE: list of saved submissions waiting for review (filter by status, source and search text).
// Each row links to the review page. Counts at the top are computed from the loaded list.

import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { listSubmissions } from '../../services/c3Api.js';
import { EmptyState, Notice, PageHeader, SourceBadge, Spinner, StatusPill, friendlyError, sourceKind } from './components/c3ui.jsx';
import './c3.css';


export default function LecturerQueuePage() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('');
  const [source, setSource] = useState('all');
  const [search, setSearch] = useState('');

  // Load submissions from the server; reloads when the status filter changes.
  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listSubmissions(status ? { status } : {});
      setSubmissions(data.submissions || []);
    } catch (err) {
      setError(friendlyError(err, 'The marking queue could not be loaded.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  // Totals per status and per source (student / sample / test data).
  const counts = useMemo(() => {
    const c = { total: submissions.length, pending: 0, reviewed: 0, finalized: 0, student: 0, sample: 0, test: 0 };
    submissions.forEach((s) => {
      const st = s.status || 'pending_review';
      if (st === 'pending_review') c.pending += 1;
      if (st === 'reviewed') c.reviewed += 1;
      if (st === 'finalized') c.finalized += 1;
      c[sourceKind(s)] += 1;
    });
    return c;
  }, [submissions]);

  // Rows shown: the source tab and the search box are applied here (the status filter is applied by the server).
  const rows = submissions.filter((s) => {
    if (source !== 'all' && sourceKind(s) !== source) return false;
    const t = search.trim().toLowerCase();
    return !t || [s.question_id, s.student_id, s.question_text].some((v) => (v || '').toLowerCase().includes(t));
  });
  // True when any filter is active (changes the empty-state wording and offers 'Clear filters').
  const filtered = status || source !== 'all' || search.trim();

  // Source tabs; 'Test data' appears only when such submissions exist.
  const sources = [['all', 'All', counts.total], ['student', 'Student submissions', counts.student], ['sample', 'Sample assessments', counts.sample]];
  if (counts.test > 0) sources.push(['test', 'Test data', counts.test]);

  return (
    <div className="c3-page">
      <PageHeader
        title="Marking Review"
        subtitle="Check the automatic marks, adjust them where needed and finalize results."
        actions={
          <>
            <Link to="/lecturer/c3/batch" className="btn">Batch marking</Link>
            <button type="button" className="btn secondary" onClick={load} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
          </>
        }
      />

      <div className="c3-stats">
        <div className="c3-stat"><b>{counts.total}</b><span>Submissions</span></div>
        <div className="c3-stat"><b>{counts.pending}</b><span>Awaiting review</span></div>
        <div className="c3-stat"><b>{counts.reviewed}</b><span>Reviewed</span></div>
        <div className="c3-stat"><b>{counts.finalized}</b><span>Finalized</span></div>
      </div>

      <div className="panel" style={{ margin: 0 }}>
        <div className="c3-queue-filters">
          <div className="tabs" role="group" aria-label="Filter by source" style={{ margin: 0 }}>
            {sources.map(([key, label, n]) => (
              <button key={key} type="button" className={source === key ? 'on' : ''} aria-pressed={source === key} onClick={() => setSource(key)}>
                {label} <span className="tab-count">{n}</span>
              </button>
            ))}
          </div>
          <div>
            <label htmlFor="q-search" className="c3-sr">Search by student, question or text</label>
            <input id="q-search" type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search student or question" />
          </div>
        </div>
        <div className="tabs" role="group" aria-label="Filter by status" style={{ margin: '12px 0 0' }}>
          {[['', 'Any status'], ['pending_review', 'Awaiting review'], ['reviewed', 'Reviewed'], ['finalized', 'Finalized']].map(([key, label]) => (
            <button key={key || 'any'} type="button" className={status === key ? 'on' : ''} aria-pressed={status === key} onClick={() => setStatus(key)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && <Notice tone="error" title="Queue unavailable" onRetry={load}>{error}</Notice>}

      {loading && submissions.length === 0 ? (
        <Spinner label="Loading submissions..." />
      ) : rows.length === 0 && !error ? (
        <EmptyState
          title="No submissions found"
          action={filtered ? <button type="button" className="btn secondary" onClick={() => { setStatus(''); setSource('all'); setSearch(''); }}>Clear filters</button> : null}
        >
          {filtered ? 'Nothing matches the current filters.' : 'No answers have been submitted yet.'}
        </EmptyState>
      ) : (
        rows.length > 0 && (
          <div className="panel flush" style={{ margin: 0 }}>
            <div className="table-wrap">
              <table className="data-table c3-table" style={{ margin: 0, minWidth: 700 }}>
                <caption className="c3-sr">Submissions to review</caption>
                <thead>
                  <tr>
                    <th scope="col">Student</th>
                    <th scope="col">Question</th>
                    <th scope="col">Submitted</th>
                    <th scope="col">Automatic mark</th>
                    <th scope="col">Status</th>
                    <th scope="col">Final mark</th>
                    <th scope="col"><span className="c3-sr">Action</span></th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((s) => {
                    const st = s.status || 'pending_review';
                    const kind = sourceKind(s);
                    return (
                      <tr key={s._id}>
                        <td>
                          <strong>{s.student_id}</strong>
                          {kind !== 'student' && <div><SourceBadge submission={s} /></div>}
                        </td>
                        <td>
                          <strong>{s.question_id}</strong>
                          {s.question_text && <div className="small muted c3-trunc" title={s.question_text}>{s.question_text}</div>}
                        </td>
                        <td className="small muted">{s.submitted_at ? new Date(s.submitted_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '-'}</td>
                        <td>{s.automated_mark != null ? <><strong>{s.automated_mark} / {s.total_possible_marks}</strong>{s.percentage != null && <span className="small muted"> ({s.percentage}%)</span>}</> : <span className="muted">-</span>}</td>
                        <td><StatusPill status={st} /></td>
                        <td>{s.final_mark != null ? <><strong>{s.final_mark} / {s.total_possible_marks}</strong>{s.lecturer_decision && <div className="small muted">{s.lecturer_decision === 'accepted' ? 'Accepted' : 'Adjusted'}</div>}</> : <span className="muted">-</span>}</td>
                        <td>
                          <Link to={`/lecturer/c3/${s._id}`} className={`btn c3-sm${st === 'pending_review' ? '' : ' secondary'}`}>
                            {st === 'pending_review' ? 'Review' : st === 'reviewed' ? 'Finalize' : 'View'}
                          </Link>
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
    </div>
  );
}
