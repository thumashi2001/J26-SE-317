import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listSubmissions } from '../../services/c3Api.js';
import './c3.css';

export default function LecturerQueuePage() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listSubmissions(statusFilter ? { status: statusFilter } : {});
      setSubmissions(data.submissions || []);
    } catch (err) {
      console.error('Failed to load submissions queue:', err);
      setError(err.message || 'Failed to retrieve assessment submissions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [statusFilter]);

  const totalCount = submissions.length;
  const pendingCount = submissions.filter((s) => s.status === 'pending_review' || !s.status).length;
  const reviewedCount = submissions.filter((s) => s.status === 'reviewed').length;
  const finalizedCount = submissions.filter((s) => s.status === 'finalized').length;

  return (
    <div className="c3-page">
      {/* Header */}
      <div className="c3-header-lead">
        <div>
          <h1>Lecturer Assessment Review Queue</h1>
          <p className="muted" style={{ margin: '4px 0 0' }}>
            AdaptiveLearnSE Component 3 • Human-in-the-Loop Review, Override & Finalization Workflow
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span className="c3-badge-research">Lecturer Verification Gateway</span>
          <button type="button" className="btn-ghost" onClick={fetchQueue} disabled={loading}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="c3-queue-stats-grid">
        <div className="c3-queue-stat-card">
          <span className="c3-queue-stat-num">{totalCount}</span>
          <span className="c3-queue-stat-label">Total Submissions</span>
        </div>
        <div className="c3-queue-stat-card" style={{ borderLeft: '4px solid #d9901a' }}>
          <span className="c3-queue-stat-num" style={{ color: '#7a5200' }}>
            {pendingCount}
          </span>
          <span className="c3-queue-stat-label">Awaiting Lecturer Review</span>
        </div>
        <div className="c3-queue-stat-card" style={{ borderLeft: '4px solid #1b4d75' }}>
          <span className="c3-queue-stat-num" style={{ color: '#1b4d75' }}>
            {reviewedCount}
          </span>
          <span className="c3-queue-stat-label">Lecturer Reviewed</span>
        </div>
        <div className="c3-queue-stat-card" style={{ borderLeft: '4px solid #087a63' }}>
          <span className="c3-queue-stat-num" style={{ color: '#087a63' }}>
            {finalizedCount}
          </span>
          <span className="c3-queue-stat-label">Finalized Results</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="c3-concept-tabs" style={{ marginBottom: '8px' }}>
        <button
          type="button"
          className={`c3-tab-btn ${statusFilter === '' ? 'active' : ''}`}
          onClick={() => setStatusFilter('')}
        >
          All Submissions ({totalCount})
        </button>
        <button
          type="button"
          className={`c3-tab-btn ${statusFilter === 'pending_review' ? 'active' : ''}`}
          onClick={() => setStatusFilter('pending_review')}
        >
          Pending Review ({pendingCount})
        </button>
        <button
          type="button"
          className={`c3-tab-btn ${statusFilter === 'reviewed' ? 'active' : ''}`}
          onClick={() => setStatusFilter('reviewed')}
        >
          Reviewed ({reviewedCount})
        </button>
        <button
          type="button"
          className={`c3-tab-btn ${statusFilter === 'finalized' ? 'active' : ''}`}
          onClick={() => setStatusFilter('finalized')}
        >
          Finalized ({finalizedCount})
        </button>
      </div>

      {/* Error alert */}
      {error && (
        <div className="c3-alert-box c3-alert-error">
          <span>⚠️</span>
          <div>
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Submissions Table */}
      {loading ? (
        <div className="panel" style={{ textAlign: 'center', padding: '40px' }}>
          <div className="c3-spinner" style={{ width: '24px', height: '24px', borderColor: 'var(--primary)' }} />
          <p className="muted" style={{ marginTop: '12px' }}>
            Loading student submissions...
          </p>
        </div>
      ) : submissions.length === 0 ? (
        <div className="panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <h3 style={{ margin: '0 0 8px' }}>No Submissions Found</h3>
          <p className="muted" style={{ margin: 0 }}>
            {statusFilter
              ? `There are currently no submissions matching status "${statusFilter}".`
              : 'No student submissions have been submitted for evaluation yet.'}
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="c3-queue-table">
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Question ID / Task</th>
                <th>Submitted</th>
                <th>AI Proposed Mark</th>
                <th>Status</th>
                <th>Lecturer Decision</th>
                <th>Final Mark</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((s) => {
                const subDate = s.submitted_at
                  ? new Date(s.submitted_at).toLocaleString(undefined, {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })
                  : '—';
                const status = s.status || 'pending_review';
                return (
                  <tr key={s._id}>
                    <td>
                      <strong>{s.student_id}</strong>
                    </td>
                    <td>
                      <div>
                        <strong>{s.question_id || 'SE-DB-001'}</strong>
                      </div>
                      {s.question_text && (
                        <div className="small muted" style={{ maxWidth: '240px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {s.question_text}
                        </div>
                      )}
                    </td>
                    <td className="small muted">{subDate}</td>
                    <td>
                      {s.automated_mark !== null && s.automated_mark !== undefined ? (
                        <div>
                          <strong>
                            {s.automated_mark} / {s.total_possible_marks}
                          </strong>
                          {s.percentage !== null && (
                            <span className="small muted" style={{ marginLeft: '6px' }}>
                              ({s.percentage}%)
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      <span className={`c3-badge-status ${status}`}>
                        {status === 'pending_review'
                          ? '⏳ AI Proposed'
                          : status === 'reviewed'
                          ? '🔍 Lecturer Reviewed'
                          : status === 'finalized'
                          ? '✓ Finalized'
                          : status}
                      </span>
                    </td>
                    <td>
                      {s.lecturer_decision ? (
                        <span className={`c3-badge-decision ${s.lecturer_decision}`}>
                          {s.lecturer_decision === 'accepted' ? 'Accepted' : 'Overridden'}
                        </span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {s.final_mark !== null && s.final_mark !== undefined ? (
                        <strong style={{ color: '#087a63' }}>
                          {s.final_mark} / {s.total_possible_marks}
                        </strong>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      <Link
                        to={`/c3/review/${s._id}`}
                        className="btn secondary"
                        style={{ padding: '6px 14px', fontSize: '0.85rem', width: 'auto' }}
                      >
                        {status === 'finalized' ? 'View Final Result' : 'Review & Verify →'}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
