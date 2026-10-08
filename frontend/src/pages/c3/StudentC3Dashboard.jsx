import { useState, useEffect } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { listAssessments, listMySubmissions } from '../../services/c3Api.js';
import '../c3/C3.css';

export default function StudentC3Dashboard() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { setPageTitle } = useOutletContext();

  useEffect(() => {
    setPageTitle('C3 My Assessments');
    setLoading(true);
    Promise.all([listAssessments(), listMySubmissions()])
      .then(([aRes, sRes]) => {
        setAssessments(aRes.assessments || []);
        setSubmissions(sRes.submissions || []);
      })
      .catch((err) => setError(err.message || 'Failed to load assessments'))
      .finally(() => setLoading(false));
  }, []);

  // Compute summary counts
  const mySubmissionMap = {};
  for (const s of submissions) mySubmissionMap[s.assessment_id] = s;

  const available = assessments.filter(a => !mySubmissionMap[String(a._id)]).length;
  const inProgress = submissions.filter(s => s.status === 'awaiting_review').length;
  const finalized  = submissions.filter(s => s.status === 'finalized').length;

  const statusBadge = (assessment) => {
    const sub = mySubmissionMap[String(assessment._id)];
    if (!sub) return { label: 'Available', cls: 'c3-badge-available', dot: '●' };
    if (sub.status === 'finalized') return { label: 'Finalized', cls: 'c3-badge-finalized', dot: '✓' };
    return { label: 'Awaiting Review', cls: 'c3-badge-review', dot: '◐' };
  };

  return (
    <div className="c3-page c3-page-dark">
      {/* Page title managed by Top Nav */}

      {/* ── Summary metrics ─────────────────────────────────── */}
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
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: 'var(--c3-success)' }}>{String(available).padStart(2, '0')}</div>
              <div className="c3-metric-label">Available</div>
              <div className="c3-metric-sub">Ready to attempt</div>
            </div>
          </div>
          <div className="c3-col-4">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: 'var(--c3-warning)' }}>{String(inProgress).padStart(2, '0')}</div>
              <div className="c3-metric-label">Awaiting Review</div>
              <div className="c3-metric-sub">AI assessment complete</div>
            </div>
          </div>
          <div className="c3-col-4">
            <div className="c3-card-metric">
              <div className="c3-metric-value" style={{ color: 'var(--c3-primary)' }}>{String(finalized).padStart(2, '0')}</div>
              <div className="c3-metric-label">Finalized</div>
              <div className="c3-metric-sub">Lecturer reviewed</div>
            </div>
          </div>
        </div>
      )}

      {/* ── Error state ─────────────────────────────────────── */}
      {error && (
        <div className="c3-alert c3-alert-error c3-mb-4">
          <span>⚠</span>
          <span>{error}. <button className="c3-btn c3-btn-ghost c3-btn-sm" onClick={() => window.location.reload()}>Retry</button></span>
        </div>
      )}

      {/* ── Assessment list ──────────────────────────────────── */}
      <div className="c3-card">
        <div className="c3-section-title">
          <span className="c3-section-dot" />
          Assessments
        </div>

        {loading ? (
          <div className="c3-stack">
            {[0,1].map(i => (
              <div key={i} className="c3-assessment-card" style={{ cursor: 'default' }}>
                <div className="c3-skeleton" style={{ height: 20, width: '40%', marginBottom: 10 }} />
                <div className="c3-skeleton" style={{ height: 14, width: '80%', marginBottom: 6 }} />
                <div className="c3-skeleton" style={{ height: 14, width: '60%' }} />
              </div>
            ))}
          </div>
        ) : assessments.length === 0 ? (
          <div className="c3-empty">
            <div className="c3-empty-icon">📋</div>
            <div className="c3-empty-title">No assessments assigned yet</div>
            <div className="c3-empty-sub">Assessments will appear here once your lecturer publishes them.</div>
          </div>
        ) : (
          <div>
            {assessments.map((assessment) => {
              const sub = mySubmissionMap[String(assessment._id)];
              const badge = statusBadge(assessment);
              const maxMarks = assessment.max_marks || 10;

              return (
                <div key={String(assessment._id)} className="c3-assessment-card">
                  <div className="c3-assessment-card-inner">
                    <div>
                      <div className="c3-gap-3 c3-mb-4">
                        <span className={`c3-badge ${badge.cls}`}>{badge.dot} {badge.label}</span>
                        {assessment.is_dev_seed && (
                          <span className="c3-badge c3-badge-dev">🔬 PP1 Demo</span>
                        )}
                        <span className="c3-badge c3-badge-essay">{assessment.answer_type || 'essay'}</span>
                      </div>

                      <h2 className="c3-assessment-title">{assessment.title}</h2>
                      <p className="c3-assessment-course">{assessment.course}</p>

                      <p className="c3-assessment-question-preview">
                        <strong>Q:</strong> {assessment.question_text}
                      </p>

                      <div className="c3-assessment-meta">
                        <span className="c3-text-dim">✏️ Written Answer</span>
                        <span className="c3-text-dim">·</span>
                        <span className="c3-text-dim">{maxMarks} Marks</span>
                      </div>
                    </div>

                    <div className="c3-assessment-actions">
                      {!sub ? (
                        <button
                          className="c3-btn c3-btn-primary"
                          onClick={() => navigate(`/c3/assessment/${String(assessment._id)}`)}
                        >
                          Start Assessment →
                        </button>
                      ) : sub.status === 'finalized' ? (
                        <button
                          className="c3-btn c3-btn-ghost"
                          onClick={() => navigate(`/c3/result/${String(sub._id)}`)}
                        >
                          View Final Result
                        </button>
                      ) : (
                        <button
                          className="c3-btn c3-btn-ghost"
                          onClick={() => navigate(`/c3/result/${String(sub._id)}`)}
                        >
                          View AI Result
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
