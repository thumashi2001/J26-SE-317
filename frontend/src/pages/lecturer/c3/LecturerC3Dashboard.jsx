import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { lecturerListSubmissions } from '../../../services/c3Api.js';
import '../../c3/C3.css';

const STATUS_LABELS = {
  awaiting_review: { label: 'Awaiting Review', cls: 'c3-badge-review',    dot: '◐' },
  finalized:       { label: 'Finalized',        cls: 'c3-badge-finalized', dot: '✓' },
  processing:      { label: 'Processing',       cls: 'c3-badge-essay',     dot: '…' },
  failed:          { label: 'Failed',           cls: 'c3-badge-failed',    dot: '✗' },
};

export default function LecturerC3Dashboard() {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState([]);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('');

  const load = () => {
    setLoading(true);
    const params = {};
    if (filter) params.status = filter;
    lecturerListSubmissions(params)
      .then(({ submissions: s, counts: c }) => {
        setSubmissions(s || []);
        setCounts(c || {});
      })
      .catch((err) => setError(err.message || 'Failed to load submissions'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  const pendingCount  = counts.awaiting_review || 0;
  const reviewedCount = (counts.ai_assessed || 0);
  const finalizedCount = counts.finalized || 0;

  return (
    <div className="c3-page c3-page-dark">
      {/* ── Header */}
      <div className="c3-header-row">
        <div>
          <h1 className="c3-page-title">C3 — Assessment Review</h1>
          <p className="c3-page-subtitle">
            Review AI-generated assessment results and retain final academic control.
          </p>
        </div>
        <button className="c3-btn c3-btn-ghost" onClick={load}>↻ Refresh</button>
      </div>

      {/* ── Summary counts */}
      {loading ? (
        <div className="c3-bento c3-mb-6">
          {[0,1,2].map(i => (
            <div key={i} className="c3-col-4">
              <div className="c3-card-metric">
                <div className="c3-skeleton" style={{ height: 40, width: 60, marginBottom: 8 }} />
                <div className="c3-skeleton" style={{ height: 14, width: 100 }} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="c3-bento c3-mb-6">
          <div className="c3-col-4">
            <div className="c3-card-metric" style={{ cursor: 'pointer' }} onClick={() => setFilter('awaiting_review')}>
              <div className="c3-metric-value" style={{ color: '#fbbf24' }}>
                {String(pendingCount).padStart(2, '0')}
              </div>
              <div className="c3-metric-label">Pending Review</div>
              <div className="c3-metric-sub">Awaiting your decision</div>
            </div>
          </div>
          <div className="c3-col-4">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: '#60a5fa' }}>
                {String(finalizedCount).padStart(2, '0')}
              </div>
              <div className="c3-metric-label">Finalized</div>
              <div className="c3-metric-sub">Academic decision recorded</div>
            </div>
          </div>
          <div className="c3-col-4">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: '#34d399' }}>
                {String(pendingCount + finalizedCount).padStart(2, '0')}
              </div>
              <div className="c3-metric-label">Total Submissions</div>
              <div className="c3-metric-sub">All time</div>
            </div>
          </div>
        </div>
      )}

      {/* ── Filter bar */}
      <div className="c3-card c3-mb-4">
        <div className="c3-between">
          <div className="c3-gap-3">
            <span className="c3-text-muted">Filter:</span>
            {['', 'awaiting_review', 'finalized'].map(s => (
              <button
                key={s}
                className={`c3-btn c3-btn-sm ${filter === s ? 'c3-btn-primary' : 'c3-btn-ghost'}`}
                onClick={() => setFilter(s)}
              >
                {s === '' ? 'All' : s === 'awaiting_review' ? 'Pending Review' : 'Finalized'}
              </button>
            ))}
          </div>
          <span className="c3-text-dim">{submissions.length} submission{submissions.length !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* ── Submission list */}
      {error && (
        <div className="c3-alert c3-alert-error c3-mb-4">
          <span>⚠</span> <span>{error} <button className="c3-btn c3-btn-ghost c3-btn-sm" onClick={load}>Retry</button></span>
        </div>
      )}

      <div className="c3-card">
        <div className="c3-section-title">
          <span className="c3-section-dot" />
          Submission Queue
        </div>

        {loading ? (
          <div className="c3-stack">
            {[0,1,2].map(i => (
              <div key={i} style={{ padding: '14px 0', borderBottom: '1px solid var(--c3-border-m)' }}>
                <div className="c3-skeleton" style={{ height: 16, width: '50%', marginBottom: 8 }} />
                <div className="c3-skeleton" style={{ height: 12, width: '70%' }} />
              </div>
            ))}
          </div>
        ) : submissions.length === 0 ? (
          <div className="c3-empty">
            <div className="c3-empty-icon">📭</div>
            <div className="c3-empty-title">No submissions found</div>
            <div className="c3-empty-sub">
              {filter
                ? `No submissions with status "${filter}". Try clearing the filter.`
                : 'Student submissions will appear here once they complete an assessment.'}
            </div>
            {filter && (
              <button className="c3-btn c3-btn-ghost c3-btn-sm" onClick={() => setFilter('')}>
                Clear Filter
              </button>
            )}
          </div>
        ) : (
          <div className="c3-table-wrap">
            <table className="c3-table">
              <thead>
                <tr>
                  <th>Student ID</th>
                  <th>Assessment</th>
                  <th>Submitted</th>
                  <th>AI Mark</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((sub) => {
                  const badge = STATUS_LABELS[sub.status] || { label: sub.status, cls: 'c3-badge-essay', dot: '?' };
                  const date = new Date(sub.submitted_at).toLocaleDateString();
                  return (
                    <tr key={String(sub._id)}>
                      <td style={{ fontFamily: 'monospace', fontWeight: 600, color: '#fff' }}>
                        {sub.student_id}
                      </td>
                      <td className="c3-text-muted" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={sub.assessment_title || sub.assessment_id}>
                        {sub.assessment_title || sub.assessment_id}
                      </td>
                      <td className="c3-text-dim">{date}</td>
                      <td>
                        {sub.ai_mark !== null && sub.ai_mark !== undefined ? (
                          <span style={{ fontWeight: 600, color: '#fff' }}>{sub.ai_mark}</span>
                        ) : (
                          <span style={{ fontWeight: 600, color: '#94a3b8' }}>—</span>
                        )}
                      </td>
                      <td>
                        <span className={`c3-badge ${badge.cls}`}>{badge.dot} {badge.label}</span>
                      </td>
                      <td>
                        <button
                          className="c3-btn c3-btn-primary c3-btn-sm"
                          onClick={() => navigate(`/lecturer/c3/review/${String(sub._id)}`)}
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
