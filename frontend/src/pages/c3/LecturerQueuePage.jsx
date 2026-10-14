import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listSubmissions } from '../../services/c3Api.js';
import './c3.css';

export default function LecturerQueuePage() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [provenanceFilter, setProvenanceFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

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

  // Provenance counts
  const pp1DemoCount = submissions.filter(
    (s) => s.provenance === 'pp1_demo' || s.is_demo
  ).length;
  const studentCount = submissions.filter(
    (s) => (s.provenance === 'student' || !s.provenance) && !s.is_demo && s.status !== 'failed'
  ).length;
  const testCount = submissions.filter(
    (s) => s.provenance === 'test_fixture' || s.status === 'failed'
  ).length;

  // Filtered by Provenance and Search
  const filteredSubmissions = submissions.filter((s) => {
    // Provenance filter
    if (provenanceFilter === 'pp1_demo') {
      if (!s.is_demo && s.provenance !== 'pp1_demo') return false;
    } else if (provenanceFilter === 'student') {
      if (s.is_demo || s.provenance === 'pp1_demo' || s.provenance === 'test_fixture' || s.status === 'failed') return false;
    } else if (provenanceFilter === 'test_fixture') {
      if (s.provenance !== 'test_fixture' && s.status !== 'failed') return false;
    }

    // Search filter
    if (searchTerm.trim()) {
      const term = searchTerm.trim().toLowerCase();
      const matchQId = (s.question_id || '').toLowerCase().includes(term);
      const matchSId = (s.student_id || '').toLowerCase().includes(term);
      const matchText = (s.question_text || '').toLowerCase().includes(term);
      if (!matchQId && !matchSId && !matchText) return false;
    }

    return true;
  });

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
          <Link to="/c3" className="btn-ghost" style={{ width: 'auto', padding: '6px 14px' }}>
            ✍️ Open Student Assessment Sandbox →
          </Link>
          <button type="button" className="btn secondary" style={{ width: 'auto', padding: '6px 14px' }} onClick={fetchQueue} disabled={loading}>
            🔄 Refresh Queue
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

      {/* Controls Bar: Source Separation & Status Filters */}
      <div className="panel" style={{ padding: '16px 20px', background: '#ffffff' }}>
        <div className="c3-filter-row">
          <div>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--muted)', marginRight: '10px', textTransform: 'uppercase' }}>
              Dataset Provenance:
            </span>
            <div className="c3-concept-tabs" style={{ display: 'inline-flex', gap: '6px', margin: 0 }}>
              <button
                type="button"
                className={`c3-tab-btn ${provenanceFilter === 'all' ? 'active' : ''}`}
                onClick={() => setProvenanceFilter('all')}
              >
                All Sources ({totalCount})
              </button>
              <button
                type="button"
                className={`c3-tab-btn ${provenanceFilter === 'pp1_demo' ? 'active' : ''}`}
                onClick={() => setProvenanceFilter('pp1_demo')}
                style={provenanceFilter === 'pp1_demo' ? { background: '#6b21a8', borderColor: '#6b21a8', color: '#fff' } : {}}
              >
                🎯 PP1 Demo Benchmarks ({pp1DemoCount})
              </button>
              <button
                type="button"
                className={`c3-tab-btn ${provenanceFilter === 'student' ? 'active' : ''}`}
                onClick={() => setProvenanceFilter('student')}
              >
                👤 Student Submissions ({studentCount})
              </button>
              <button
                type="button"
                className={`c3-tab-btn ${provenanceFilter === 'test_fixture' ? 'active' : ''}`}
                onClick={() => setProvenanceFilter('test_fixture')}
              >
                🧪 Automated Test Fixtures ({testCount})
              </button>
            </div>
          </div>

          {/* Quick Search */}
          <div style={{ minWidth: '240px' }}>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="🔍 Search question, student ID..."
              style={{ padding: '7px 12px', fontSize: '0.88rem' }}
            />
          </div>
        </div>

        {/* Status Lifecycle Tabs */}
        <div className="c3-concept-tabs" style={{ marginTop: '12px', borderTop: '1px solid var(--line)', paddingTop: '12px' }}>
          <button
            type="button"
            className={`c3-tab-btn ${statusFilter === '' ? 'active' : ''}`}
            onClick={() => setStatusFilter('')}
          >
            All Lifecycle Stages
          </button>
          <button
            type="button"
            className={`c3-tab-btn ${statusFilter === 'pending_review' ? 'active' : ''}`}
            onClick={() => setStatusFilter('pending_review')}
          >
            ⏳ Pending Review ({pendingCount})
          </button>
          <button
            type="button"
            className={`c3-tab-btn ${statusFilter === 'reviewed' ? 'active' : ''}`}
            onClick={() => setStatusFilter('reviewed')}
          >
            🔍 Reviewed ({reviewedCount})
          </button>
          <button
            type="button"
            className={`c3-tab-btn ${statusFilter === 'finalized' ? 'active' : ''}`}
            onClick={() => setStatusFilter('finalized')}
          >
            ✓ Finalized ({finalizedCount})
          </button>
        </div>
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
      ) : filteredSubmissions.length === 0 ? (
        <div className="panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <h3 style={{ margin: '0 0 8px' }}>No Submissions Found</h3>
          <p className="muted" style={{ margin: '0 0 16px' }}>
            {statusFilter || provenanceFilter !== 'all' || searchTerm
              ? 'No submissions match the selected criteria or search term.'
              : 'No student submissions have been recorded yet.'}
          </p>
          {(statusFilter || provenanceFilter !== 'all' || searchTerm) && (
            <button
              type="button"
              className="btn secondary"
              style={{ width: 'auto', margin: '0 auto' }}
              onClick={() => {
                setStatusFilter('');
                setProvenanceFilter('all');
                setSearchTerm('');
              }}
            >
              Reset Filters
            </button>
          )}
        </div>
      ) : (
        <div className="c3-table-responsive">
          <table className="c3-queue-table">
            <thead>
              <tr>
                <th>Provenance</th>
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
              {filteredSubmissions.map((s) => {
                const subDate = s.submitted_at
                  ? new Date(s.submitted_at).toLocaleString(undefined, {
                      dateStyle: 'short',
                      timeStyle: 'short',
                    })
                  : '—';
                const status = s.status || 'pending_review';
                const isDemo = s.is_demo || s.provenance === 'pp1_demo';
                const isTest = s.provenance === 'test_fixture' || s.status === 'failed';

                return (
                  <tr key={s._id}>
                    <td>
                      {isDemo ? (
                        <span className="c3-badge-provenance pp1_demo">🎯 PP1 Demo</span>
                      ) : isTest ? (
                        <span className="c3-badge-provenance test_fixture">🧪 Test Run</span>
                      ) : (
                        <span className="c3-badge-provenance student">👤 Student</span>
                      )}
                    </td>
                    <td>
                      <strong>{s.student_id}</strong>
                    </td>
                    <td>
                      <div>
                        <strong>{s.question_id || 'SE-DB-001'}</strong>
                      </div>
                      {s.question_text && (
                        <div
                          className="small muted"
                          style={{
                            maxWidth: '260px',
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                          title={s.question_text}
                        >
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
                          : status === 'failed'
                          ? '⚠️ Incomplete'
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
                        to={`/lecturer/c3/${s._id}`}
                        className={`btn ${status === 'pending_review' ? '' : 'secondary'}`}
                        style={{ padding: '6px 14px', fontSize: '0.85rem', width: 'auto', whiteSpace: 'nowrap' }}
                      >
                        {status === 'pending_review'
                          ? 'Review & Verify →'
                          : status === 'reviewed'
                          ? 'Finalize Mark →'
                          : 'View Archive'}
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
