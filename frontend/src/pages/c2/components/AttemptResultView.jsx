import React, { useState } from 'react';
import AttemptHistoryView from './AttemptHistoryView.jsx';

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

export default function AttemptResultView({
  attempt,
  moduleName,
  moduleKey,
  onStartAnother,
  onReturnOverview,
  allAttempts = [],
  loadingAttempts = false,
  onRefreshAttempts,
  onSelectAttempt,
}) {
  const [showHistory, setShowHistory] = useState(false);

  if (!attempt) {
    return (
      <section className="c2-student-bank">
        <div className="c2-student-empty" style={{ padding: '36px 20px' }}>
          <div className="c2-student-empty-icon" aria-hidden="true">
            📝
          </div>
          <h3>No attempt selected</h3>
          <p className="c2-student-muted">
            Complete a practice examination or select an attempt from your history to view results and evaluation status.
          </p>
          <div style={{ marginTop: 20, display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button
              type="button"
              className="btn primary"
              onClick={onStartAnother}
            >
              Configure Practice Mock
            </button>
            <button
              type="button"
              className="btn secondary"
              onClick={onReturnOverview}
            >
              Return to Overview
            </button>
          </div>
        </div>

        {allAttempts.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <AttemptHistoryView
              attempts={allAttempts}
              loading={loadingAttempts}
              onRefresh={onRefreshAttempts}
              onSelectAttempt={onSelectAttempt}
            />
          </div>
        )}
      </section>
    );
  }

  const attemptId = attempt.attemptId || attempt.attempt_id || 'UNKNOWN-ID';
  const submittedDate = attempt.submittedAt || attempt.submitted_at
    ? new Date(attempt.submittedAt || attempt.submitted_at).toLocaleString()
    : 'Just now';
  const duration = formatDuration(attempt.timeSpentSeconds || attempt.time_spent_seconds || 0);

  const questions = Array.isArray(attempt.questions) ? attempt.questions : [];
  const questionCount = attempt.questionCount || attempt.question_count || questions.length;
  const answeredCount =
    typeof attempt.answeredCount === 'number'
      ? attempt.answeredCount
      : questions.filter((q) => (q.studentAnswer || '').trim().length > 0).length;
  const unansweredCount = Math.max(0, questionCount - answeredCount);

  const isSynthetic =
    attempt.sourceType === 'synthetic' ||
    attempt.source_type === 'synthetic' ||
    questions.some((q) => q.sourceType === 'synthetic' || q.source_type === 'synthetic');

  const totalMarksDisplay =
    attempt.totalMarks !== null && attempt.totalMarks !== undefined
      ? `${attempt.totalMarks} marks`
      : isSynthetic
        ? 'Unassessed'
        : 'Not recorded';

  const status = attempt.status || 'pending_marking';

  return (
    <div className="c2-results-stage" aria-label="Examination Results and Feedback">
      {/* Top Banner */}
      <div className="c2-results-header-card">
        <div className="c2-results-header-main">
          <div>
            <span className="c2-student-panel-eyebrow">
              STAGE 5 — RESULTS & FEEDBACK
            </span>
            <h2>{moduleName} Practice Result</h2>
            <div className="c2-results-meta-chips">
              <span className="c2-attempt-id-chip">Attempt: {attemptId}</span>
              <span className="c2-results-mode-chip">
                {isSynthetic ? '🧪 Synthetic Practice (Experimental)' : '📜 Authentic Past-Paper Practice'}
              </span>
              <span className="c2-results-time-chip">Submitted: {submittedDate}</span>
            </div>
          </div>

          <div className="c2-results-status-box">
            <span className="c2-status-pill status-pending">
              {status === 'pending_marking' ? 'Pending Marking' : status}
            </span>
            <span className="c2-status-subtext">
              Marks Awarded: <strong>Pending Evaluation</strong>
            </span>
          </div>
        </div>

        {/* 4 Quick Stat Pills */}
        <div className="c2-results-summary-grid">
          <div className="c2-result-stat-card">
            <span className="c2-stat-label">Questions Answered</span>
            <strong className="c2-stat-val">
              {answeredCount} / {questionCount}
            </strong>
            <span className="c2-stat-sub">
              {unansweredCount > 0 ? `${unansweredCount} unanswered` : 'All answered'}
            </span>
          </div>

          <div className="c2-result-stat-card">
            <span className="c2-stat-label">Time Spent</span>
            <strong className="c2-stat-val">{duration}</strong>
            <span className="c2-stat-sub">Recorded duration</span>
          </div>

          <div className="c2-result-stat-card">
            <span className="c2-stat-label">Total Available Marks</span>
            <strong className="c2-stat-val">{totalMarksDisplay}</strong>
            <span className="c2-stat-sub">
              {isSynthetic ? 'Synthetic fixtures' : 'Authentic syllabus'}
            </span>
          </div>

          <div className="c2-result-stat-card">
            <span className="c2-stat-label">Evaluation Status</span>
            <strong className="c2-stat-val" style={{ color: '#d97706' }}>
              Pending
            </strong>
            <span className="c2-stat-sub">Awaiting C3 Marking</span>
          </div>
        </div>

        {/* Academic Integrity Notice */}
        <div className="c2-attempt-integrity-box">
          <strong>Academic Research Notice:</strong> {attempt.academicIntegrityNotice ||
            'Component 3 automated marking is currently pending. Marks have not been estimated, simulated, or fabricated. In accordance with SLIIT academic integrity standards, official marks will only be visible once verified.'}
        </div>

        {/* Top Actions */}
        <div className="c2-results-actions-bar">
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn primary"
              onClick={onStartAnother}
            >
              ✍️ Take Another Practice Exam
            </button>
            <button
              type="button"
              className="btn secondary"
              onClick={onReturnOverview}
            >
              🏠 Return to Overview
            </button>
          </div>

          <button
            type="button"
            className="btn secondary"
            onClick={() => setShowHistory((prev) => !prev)}
          >
            {showHistory ? 'Hide Previous Attempts ▲' : `View All Previous Attempts (${allAttempts.length}) ▼`}
          </button>
        </div>
      </div>

      {/* Submitted Questions Review */}
      <section className="c2-student-bank" style={{ marginTop: 24 }}>
        <div className="c2-student-bank-header">
          <div>
            <span className="c2-student-panel-eyebrow">
              SUBMITTED WORK AUDIT
            </span>
            <h3>Question-by-Question Submission Review</h3>
            <p className="c2-student-muted">
              Inspect your submitted responses and verify question details.
            </p>
          </div>

          <span className="c2-student-count-chip">
            {questions.length} questions
          </span>
        </div>

        <div className="c2-attempt-questions-review">
          {questions.map((q, idx) => {
            const qId = q.questionId || q.question_id || `Q${idx + 1}`;
            const qText = q.questionText || q.question_text || 'Question text not available';
            const studentAns = q.studentAnswer || q.student_answer;
            const qMarks = q.marks !== null && q.marks !== undefined ? `${q.marks} marks` : 'Unassessed';
            const qSynthetic = q.sourceType === 'synthetic' || q.source_type === 'synthetic' || isSynthetic;

            return (
              <article key={qId} className="c2-attempt-q-review-item">
                <div className="c2-review-q-head">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <strong>Question {idx + 1}</strong>
                    <span className="c2-student-caption">ID: {qId}</span>
                    {qSynthetic && (
                      <span className="c2-student-pill" style={{ background: '#f59e0b', color: '#fff', fontSize: '0.72rem' }}>
                        SYNTHETIC
                      </span>
                    )}
                    <span className="c2-attempt-marks-badge">{qMarks}</span>
                  </div>

                  <span className="pill status-pending" style={{ fontSize: '0.76rem' }}>
                    Pending Marking
                  </span>
                </div>

                <p className="c2-review-q-text">{qText}</p>

                <div className="c2-review-answer-box">
                  <span className="c2-review-answer-label">Your Submitted Answer:</span>
                  {studentAns ? (
                    <blockquote className="c2-review-student-answer">
                      {studentAns}
                    </blockquote>
                  ) : (
                    <p className="c2-student-muted" style={{ fontStyle: 'italic', margin: '4px 0' }}>
                      (Left unanswered)
                    </p>
                  )}
                </div>

                <div className="c2-review-marks-result">
                  <span className="c2-student-muted small">
                    Evaluation: <strong>Pending Component 3 Automated Marking</strong> (Marks awarded: <code>null</code>)
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      {/* Historical Attempts Accordion / Section */}
      {showHistory && (
        <section className="c2-student-bank" style={{ marginTop: 24 }}>
          <AttemptHistoryView
            attempts={allAttempts}
            loading={loadingAttempts}
            onRefresh={onRefreshAttempts}
            onSelectAttempt={(selected) => {
              if (typeof onSelectAttempt === 'function') {
                onSelectAttempt(selected);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }
            }}
          />
        </section>
      )}
    </div>
  );
}
