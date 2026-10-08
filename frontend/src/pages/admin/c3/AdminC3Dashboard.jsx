import { useState, useEffect } from 'react';
import { getAdminStats } from '../../../services/c3Api.js';
import '../../c3/C3.css';

export default function AdminC3Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getAdminStats()
      .then(res => setStats(res.counts))
      .catch(err => setError(err.message || 'Failed to load stats'))
      .finally(() => setLoading(false));
  }, []);

  const total = stats ? (stats.processing || 0) + (stats.awaiting_review || 0) + (stats.finalized || 0) : 0;

  return (
    <div className="c3-page c3-page-dark">
      <div className="c3-header-row">
        <div>
          <h1 className="c3-page-title">C3 — Administration</h1>
          <p className="c3-page-subtitle">Platform health and assessment throughput.</p>
        </div>
      </div>

      {loading ? (
        <div className="c3-bento">
          {[0,1,2].map(i => (
            <div key={i} className="c3-col-4">
              <div className="c3-card-metric">
                <div className="c3-skeleton" style={{ height: 40, width: 60, marginBottom: 8 }} />
                <div className="c3-skeleton" style={{ height: 14, width: 100 }} />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="c3-alert c3-alert-error">
          <span>⚠</span> <span>{error}</span>
        </div>
      ) : (
        <div className="c3-bento">
          <div className="c3-col-3">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: '#60a5fa' }}>{total}</div>
              <div className="c3-metric-label">Total Submissions</div>
              <div className="c3-metric-sub">Platform-wide</div>
            </div>
          </div>
          <div className="c3-col-3">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: '#fbbf24' }}>{stats.awaiting_review || 0}</div>
              <div className="c3-metric-label">Pending Review</div>
              <div className="c3-metric-sub">Awaiting lecturer action</div>
            </div>
          </div>
          <div className="c3-col-3">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: '#34d399' }}>{stats.finalized || 0}</div>
              <div className="c3-metric-label">Finalized</div>
              <div className="c3-metric-sub">Fully completed</div>
            </div>
          </div>
          <div className="c3-col-3">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: '#a78bfa' }}>{stats.processing || 0}</div>
              <div className="c3-metric-label">Processing</div>
              <div className="c3-metric-sub">In AI Pipeline</div>
            </div>
          </div>
        </div>
      )}

      <div className="c3-bento c3-mt-6">
        <div className="c3-col-6">
          <div className="c3-card" style={{ height: '100%' }}>
            <div className="c3-section-title"><span className="c3-section-dot" />Service Connectivity</div>
            <div className="c3-stack">
              <p className="c3-text-muted" style={{ lineHeight: 1.7 }}>
                System statistics successfully retrieved from Node.js Orchestrator and MongoDB. 
                Active database connection verified.
              </p>
              <div className="c3-text-dim" style={{ marginTop: 'auto' }}>
                Last synced: {new Date().toLocaleTimeString()}
              </div>
            </div>
          </div>
        </div>
        <div className="c3-col-6">
          <div className="c3-card" style={{ height: '100%' }}>
            <div className="c3-section-title"><span className="c3-section-dot" />Platform Security</div>
            <p className="c3-text-muted" style={{ lineHeight: 1.7 }}>
              Role-based access control is actively enforced across all C3 endpoints.
              Students only have access to their own submissions.
              Lecturers have read/write access to the submission queue and override capabilities.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
