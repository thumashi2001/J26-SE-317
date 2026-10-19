import { useState } from 'react';

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export default function AttemptHistoryView({
  attempts = [],
  loading,
  onRefresh,
  onSelectAttempt,
}) {
  const [expandedId, setExpandedId] = useState(null);

  function toggleExpand(attemptId) {
    setExpandedId((prev) => (prev === attemptId ? null : attemptId));
  }

  return (
    <div className="c2-attempt-history-section">
      <div className="c2-attempt-history-header">
        <div>
          <h3>My Practice Attempts</h3>
          <p className="c2-student-muted" style={{ margin: 0 }}>
            Audit log of completed mock exam attempts and academic evaluation status.
          </p>
        </div>

        <button
          type="button"
          className="btn secondary small-btn"
          disabled={loading}
          onClick={onRefresh}
        >
          {loading ? 'Refreshing...' : 'Refresh Attempts'}
        </button>
      </div>

      {loading && attempts.length === 0 && (
        <div className="c2-student-loading">Loading practice attempts...</div>
      )}

      {!loading && attempts.length === 0 && (
        <div className="c2-student-empty" style={{ padding: '24px', margin: '14px 0' }}>
          <h4>No practice attempts recorded yet</h4>
          <p className="c2-student-muted" style={{ margin: '6px 0 0' }}>
            Generate a practice mock exam above and click &quot;Start Practice Attempt&quot; to test your knowledge.
          </p>
        </div>
      )}

      {attempts.length > 0 && (
        <div className="c2-attempt-cards-list">
          {attempts.map((attempt) => {
            const isExpanded = expandedId === attempt.attemptId;
            const submittedDate = attempt.submittedAt
              ? new Date(attempt.submittedAt).toLocaleString()
              : 'Unknown date';

            return (
              <div key={attempt.attemptId} className="c2-attempt-history-card">
                <div className="c2-attempt-card-main">
                  <div className="c2-attempt-card-meta">
                    <span className="c2-attempt-id-chip">{attempt.attemptId}</span>
                    <span className="c2-attempt-timestamp">{submittedDate}</span>
                    <span className="c2-attempt-duration">
                      Duration: {formatDuration(attempt.timeSpentSeconds)}
                    </span>
                  </div>

                  <div className="c2-attempt-card-stats">
                    <span className="c2-attempt-stat-item">
                      Questions: <strong>{attempt.answeredCount} / {attempt.questionCount}</strong> answered
                    </span>
                    <span className="c2-attempt-stat-item">
                      Marks: <strong>{attempt.totalMarks !== null && attempt.totalMarks !== undefined ? `${attempt.totalMarks} total` : 'Unassessed'}</strong>
                    </span>
                    <span className="pill status-pending" title="Evaluation status">
                      {attempt.status === 'pending_marking' ? 'Pending Marking' : attempt.status}
                    </span>
                  </div>

                  <div className="c2-attempt-card-action" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    {typeof onSelectAttempt === 'function' && (
                      <button
                        type="button"
                        className="btn primary small-btn"
                        onClick={() => onSelectAttempt(attempt)}
                        title="Open this attempt in Stage 5 Results & Feedback view"
                      >
                        Open Full Result ➔
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn secondary small-btn"
                      onClick={() => toggleExpand(attempt.attemptId)}
                    >
                      {isExpanded ? 'Hide Submitted Answers ▲' : 'View Submitted Answers ▼'}
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div className="c2-attempt-expanded-details">
                    <div className="c2-attempt-integrity-box">
                      <strong>Evaluation Notice:</strong> {attempt.academicIntegrityNotice ||
                        'Component 3 automated marking is pending. No estimated or simulated grades are shown until verified.'}
                    </div>

                    <div className="c2-attempt-questions-review">
                      {(attempt.questions || []).map((q, qIndex) => (
                        <div key={q.questionId || qIndex} className="c2-attempt-q-review-item">
                          <div className="c2-review-q-head">
                            <div>
                              <strong>
                                Question {qIndex + 1} ({q.marks !== null && q.marks !== undefined ? `${q.marks} marks` : 'Unassessed marks'})
                              </strong>
                              {q.sourceType === 'synthetic' && (
                                <span className="c2-student-pill" style={{ marginLeft: 8, fontSize: '0.72rem', background: '#f59e0b', color: '#fff' }}>
                                  SYNTHETIC
                                </span>
                              )}
                            </div>
                            <span className="pill status-pending" style={{ fontSize: '0.75rem' }}>
                              {q.markingStatus === 'pending_marking' ? 'Pending Marking' : q.markingStatus}
                            </span>
                          </div>


                          <p className="c2-review-q-text">{q.questionText}</p>

                          <div className="c2-review-answer-box">
                            <span className="c2-review-answer-label">Your Submitted Answer:</span>
                            {q.studentAnswer ? (
                              <blockquote className="c2-review-student-answer">
                                {q.studentAnswer}
                              </blockquote>
                            ) : (
                              <p className="c2-student-muted" style={{ fontStyle: 'italic', margin: '4px 0' }}>
                                (Left unanswered)
                              </p>
                            )}
                          </div>

                          <div className="c2-review-marks-result">
                            <span className="c2-student-muted small">
                              Score: <strong>Pending Evaluation</strong> (Marks not fabricated)
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
