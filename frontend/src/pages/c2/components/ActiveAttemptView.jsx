import React, { useState, useEffect } from 'react';
import { submitC2MockAttempt } from '../../../services/c2Api.js';
import {
  prepareAttemptPayload,
  executeAttemptSubmission,
} from '../../../services/attemptSubmissionHelper.js';

function formatTime(totalSeconds) {
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export default function ActiveAttemptView({
  paper,
  moduleKey,
  moduleName,
  onSubmitAttempt,
  onSubmitSuccess,
  onCancel,
  submitting = false,
  error = '',
}) {
  const questions = Array.isArray(paper?.questions) ? paper.questions : [];
  const [answers, setAnswers] = useState({});
  const [secondsElapsed, setSecondsElapsed] = useState(0);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [viewMode, setViewMode] = useState('focused'); // 'focused' | 'all'
  const [localSubmitting, setLocalSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');
  const [showUnansweredConfirm, setShowUnansweredConfirm] = useState(false);

  const isSubmitting = Boolean(submitting || localSubmitting);
  const displayError = error || localError;

  // Live timer
  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsElapsed((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  function handleAnswerChange(questionId, value) {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  }

  const isQuestionAnswered = (q) => {
    const qId = q.question_id || q.questionId;
    return (answers[qId] || '').trim().length > 0;
  };

  const answeredCount = questions.filter(isQuestionAnswered).length;
  const unansweredQuestions = questions
    .map((q, idx) => ({ ...q, originalIndex: idx }))
    .filter((q) => !isQuestionAnswered(q));

  function handleCancel() {
    if (answeredCount > 0) {
      const confirmDiscard = window.confirm(
        'You have unsaved answers in this active practice attempt. Are you sure you want to cancel and discard them?'
      );
      if (!confirmDiscard) return;
    }
    if (typeof onCancel === 'function') {
      onCancel();
    }
  }

  function handleJumpToQuestion(idx) {
    if (idx >= 0 && idx < questions.length) {
      setActiveQuestionIndex(idx);
      if (viewMode === 'all') {
        const el = document.getElementById(`attempt-q-${idx}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }
  }

  function handleJumpToNextUnanswered() {
    const nextUnanswered = questions.findIndex(
      (q, idx) => idx > activeQuestionIndex && !isQuestionAnswered(q)
    );
    if (nextUnanswered !== -1) {
      handleJumpToQuestion(nextUnanswered);
      return;
    }
    const anyUnanswered = questions.findIndex((q) => !isQuestionAnswered(q));
    if (anyUnanswered !== -1) {
      handleJumpToQuestion(anyUnanswered);
    }
  }

  function handleInitiateSubmit(e) {
    if (e) e.preventDefault();

    if (answeredCount === 0) {
      const proceedEmpty = window.confirm(
        'You have not answered any questions yet. Do you still want to submit an empty practice attempt?'
      );
      if (!proceedEmpty) return;
      doSubmit();
      return;
    }

    if (unansweredQuestions.length > 0) {
      setShowUnansweredConfirm(true);
      return;
    }

    doSubmit();
  }

  async function doSubmit() {
    setShowUnansweredConfirm(false);
    setLocalError('');
    setLocalSubmitting(true);

    try {
      const payload = prepareAttemptPayload({
        paper,
        moduleKey,
        questions,
        answers,
        secondsElapsed,
      });

      await executeAttemptSubmission({
        onSubmitAttempt,
        onSubmitSuccess,
        payload,
        fallbackSubmitFn: submitC2MockAttempt,
      });
    } catch (err) {
      setLocalError(err?.message || 'Failed to submit practice attempt. Please try again.');
    } finally {
      setLocalSubmitting(false);
    }
  }

  const isSynthetic =
    paper?.source_type === 'synthetic' ||
    paper?.practice_mode === 'synthetic_experimental';

  const totalMarksDisplay =
    paper?.total_marks !== null && paper?.total_marks !== undefined
      ? `${paper.total_marks} marks`
      : 'Unassessed';

  const currentQuestion = questions[activeQuestionIndex];

  return (
    <div className="c2-active-attempt" aria-label="Active practice exam attempt">
      {/* Top Header Bar */}
      <div className="c2-attempt-topbar">
        <div>
          <span className="c2-student-panel-eyebrow">
            STAGE 4 — {isSynthetic ? 'SYNTHETIC PRACTICE ATTEMPT (EXPERIMENTAL)' : 'EXAM ATTEMPT'}
          </span>
          <h2>{moduleName} Practice Examination</h2>
          <p className="c2-student-muted" style={{ margin: 0 }}>
            Mock Paper ID: <code>{paper?.paper_id || paper?.mock_id || paper?.mockId}</code> • Total Marks: {totalMarksDisplay}
          </p>
        </div>

        <div className="c2-attempt-stats-row">
          <div className="c2-attempt-timer-pill">
            <span className="c2-timer-label">Time Elapsed</span>
            <strong className="c2-timer-val">{formatTime(secondsElapsed)}</strong>
          </div>

          <div className="c2-attempt-progress-pill">
            <span className="c2-progress-label">Progress</span>
            <strong className="c2-progress-val">
              {answeredCount} / {questions.length} Answered
            </strong>
          </div>
        </div>
      </div>

      {/* Academic Research Safeguard Notice */}
      <div className="c2-attempt-notice">
        <strong>Academic Research Safeguard:</strong> Natural-language answers entered below will be recorded securely.
        {isSynthetic && (
          <span>
            {' '}This paper uses <strong>synthetic practice questions (M16 development fixtures)</strong>. Marks are unassessed to avoid fabricating academic criteria.
          </span>
        )}
        {' '}If Component 3 automated marking is offline or pending lecturer review, the submission remains in{' '}
        <em>Pending Marking</em> state. No estimated or simulated marks are generated.
      </div>

      {/* Question Navigator Palette */}
      <div className="c2-question-navigator-card">
        <div className="c2-navigator-header">
          <div className="c2-navigator-title-row">
            <span className="c2-navigator-label">QUESTION NAVIGATOR</span>
            <span className="c2-navigator-meta">
              Click any question to jump directly • <strong>{answeredCount} answered</strong>, {questions.length - answeredCount} unanswered
            </span>
          </div>

          <div className="c2-view-mode-toggle">
            <button
              type="button"
              className={`c2-toggle-btn ${viewMode === 'focused' ? 'active' : ''}`}
              onClick={() => setViewMode('focused')}
              title="Focus on one question at a time"
            >
              🎯 Focused View
            </button>
            <button
              type="button"
              className={`c2-toggle-btn ${viewMode === 'all' ? 'active' : ''}`}
              onClick={() => setViewMode('all')}
              title="View all questions in a scrollable list"
            >
              📑 All Questions
            </button>
          </div>
        </div>

        <div className="c2-question-pills-grid" role="navigation" aria-label="Questions list">
          {questions.map((q, idx) => {
            const answered = isQuestionAnswered(q);
            const isCurrent = idx === activeQuestionIndex;

            let pillClass = 'c2-q-nav-pill';
            if (isCurrent) pillClass += ' c2-q-nav-current';
            if (answered) pillClass += ' c2-q-nav-answered';
            else pillClass += ' c2-q-nav-unanswered';

            return (
              <button
                key={q.question_id || q.questionId || idx}
                type="button"
                className={pillClass}
                onClick={() => handleJumpToQuestion(idx)}
                title={`Question ${idx + 1}: ${answered ? 'Answered' : 'Unanswered'}${isCurrent ? ' (Active)' : ''}`}
                aria-label={`Go to question ${idx + 1}, ${answered ? 'answered' : 'unanswered'}`}
              >
                <span className="c2-q-nav-num">{idx + 1}</span>
                <span className="c2-q-nav-status">{answered ? '✓' : '•'}</span>
              </button>
            );
          })}
        </div>
      </div>

      {displayError && (
        <div className="c2-student-error" role="alert" style={{ margin: '14px 0' }}>
          <strong>Submission failed</strong>
          <p>{displayError}</p>
          <button
            type="button"
            className="btn secondary small-btn"
            style={{ marginTop: 8 }}
            onClick={doSubmit}
            disabled={isSubmitting}
          >
            Retry Submission
          </button>
        </div>
      )}

      {/* Main Attempt Form */}
      <form onSubmit={handleInitiateSubmit} className="c2-attempt-form">
        {viewMode === 'focused' && currentQuestion && (
          <div className="c2-focused-question-container">
            <div className="c2-focused-nav-bar">
              <span className="c2-focused-counter">
                Question <strong>{activeQuestionIndex + 1}</strong> of {questions.length}
              </span>

              <div className="c2-focused-nav-buttons">
                <button
                  type="button"
                  className="btn secondary small-btn"
                  disabled={activeQuestionIndex === 0 || isSubmitting}
                  onClick={() => handleJumpToQuestion(activeQuestionIndex - 1)}
                >
                  ⬅ Previous
                </button>

                {unansweredQuestions.length > 0 && (
                  <button
                    type="button"
                    className="btn secondary small-btn"
                    onClick={handleJumpToNextUnanswered}
                    title="Jump to the next unanswered question"
                  >
                    Next Unanswered ⏩
                  </button>
                )}

                <button
                  type="button"
                  className="btn secondary small-btn"
                  disabled={activeQuestionIndex === questions.length - 1 || isSubmitting}
                  onClick={() => handleJumpToQuestion(activeQuestionIndex + 1)}
                >
                  Next ➡
                </button>
              </div>
            </div>

            {/* Focused Question Card */}
            {(() => {
              const q = currentQuestion;
              const qId = q.question_id || q.questionId || `Q${activeQuestionIndex + 1}`;
              const answerText = answers[qId] || '';
              const qSynthetic = q.source_type === 'synthetic' || isSynthetic;

              return (
                <article className="c2-attempt-question-card c2-focused-card">
                  <div className="c2-attempt-q-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span className="c2-attempt-q-number">Question {activeQuestionIndex + 1}</span>
                      <span className="c2-student-caption">ID: {qId}</span>
                      {qSynthetic && (
                        <span className="c2-student-pill" style={{ background: '#f59e0b', color: '#fff', fontSize: '0.72rem' }}>
                          SYNTHETIC
                        </span>
                      )}
                    </div>

                    <div className="c2-attempt-q-meta">
                      {q.topic_id && (
                        <span className="c2-attempt-topic-badge">
                          Topic: {String(q.topic_id).replaceAll('_', ' ')}
                        </span>
                      )}
                      <span className="c2-attempt-marks-badge">
                        {q.marks !== null && q.marks !== undefined ? `${q.marks} marks` : 'Unassessed'}
                      </span>
                    </div>
                  </div>

                  <div className="c2-attempt-q-body">
                    <p className="c2-attempt-prompt">{q.question_text}</p>
                  </div>

                  <div className="c2-attempt-answer-box">
                    <div className="c2-answer-label-row">
                      <label htmlFor={`answer-${qId}`}>Your Natural-Language Answer / Reasoning:</label>
                      <span className="c2-answer-length-count">
                        {answerText.length} characters
                      </span>
                    </div>

                    <textarea
                      id={`answer-${qId}`}
                      rows={8}
                      value={answerText}
                      disabled={isSubmitting}
                      placeholder="Type your technical answer, system explanation, or architectural justification here. Your answers are preserved when navigating between questions..."
                      onChange={(e) => handleAnswerChange(qId, e.target.value)}
                    />
                  </div>
                </article>
              );
            })()}
          </div>
        )}

        {viewMode === 'all' && (
          <div className="c2-attempt-questions-list">
            {questions.map((question, index) => {
              const qId = question.question_id || question.questionId || `Q${index + 1}`;
              const answerText = answers[qId] || '';
              const qSynthetic = question.source_type === 'synthetic' || isSynthetic;

              return (
                <article
                  key={qId}
                  id={`attempt-q-${index}`}
                  className={`c2-attempt-question-card ${index === activeQuestionIndex ? 'c2-active-border' : ''}`}
                >
                  <div className="c2-attempt-q-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span className="c2-attempt-q-number">Question {index + 1}</span>
                      <span className="c2-student-caption">ID: {qId}</span>
                      {qSynthetic && (
                        <span className="c2-student-pill" style={{ background: '#f59e0b', color: '#fff', fontSize: '0.72rem' }}>
                          SYNTHETIC
                        </span>
                      )}
                    </div>

                    <div className="c2-attempt-q-meta">
                      {question.topic_id && (
                        <span className="c2-attempt-topic-badge">
                          Topic: {String(question.topic_id).replaceAll('_', ' ')}
                        </span>
                      )}
                      <span className="c2-attempt-marks-badge">
                        {question.marks !== null && question.marks !== undefined
                          ? `${question.marks} marks`
                          : 'Unassessed'}
                      </span>
                    </div>
                  </div>

                  <div className="c2-attempt-q-body">
                    <p className="c2-attempt-prompt">{question.question_text}</p>
                  </div>

                  <div className="c2-attempt-answer-box">
                    <div className="c2-answer-label-row">
                      <label htmlFor={`answer-all-${qId}`}>Your Answer / Working:</label>
                      <span className="c2-answer-length-count">
                        {answerText.length} characters
                      </span>
                    </div>

                    <textarea
                      id={`answer-all-${qId}`}
                      rows={6}
                      value={answerText}
                      disabled={isSubmitting}
                      placeholder="Enter your technical explanation, architectural justification, or step-by-step reasoning here..."
                      onChange={(e) => handleAnswerChange(qId, e.target.value)}
                    />
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {/* Footer Actions */}
        <div className="c2-attempt-footer-actions">
          <button
            type="button"
            className="btn secondary"
            disabled={isSubmitting}
            onClick={handleCancel}
          >
            Cancel Attempt
          </button>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="c2-student-muted" style={{ fontSize: '0.85rem' }}>
              {answeredCount} of {questions.length} questions completed
            </span>

            <button
              type="submit"
              className="btn primary"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? 'Submitting Practice Attempt...'
                : `Submit Practice Attempt (${answeredCount}/${questions.length})`}
            </button>
          </div>
        </div>
      </form>

      {/* Unanswered Questions Confirmation Dialog */}
      {showUnansweredConfirm && (
        <div className="c2-modal-backdrop" role="dialog" aria-modal="true">
          <div className="c2-modal-card">
            <h3>⚠️ Unanswered Questions Review</h3>
            <p>
              You have answered <strong>{answeredCount}</strong> out of <strong>{questions.length}</strong> questions.
            </p>
            <p className="c2-student-muted">
              The following {unansweredQuestions.length} question(s) are currently unanswered:
            </p>
            <div className="c2-unanswered-list">
              {unansweredQuestions.map((q) => (
                <button
                  key={q.question_id || q.questionId || q.originalIndex}
                  type="button"
                  className="c2-unanswered-chip"
                  onClick={() => {
                    setShowUnansweredConfirm(false);
                    handleJumpToQuestion(q.originalIndex);
                  }}
                >
                  Q{q.originalIndex + 1} ➔ Jump
                </button>
              ))}
            </div>

            <div className="c2-modal-actions">
              <button
                type="button"
                className="btn secondary"
                onClick={() => setShowUnansweredConfirm(false)}
              >
                Keep Answering
              </button>
              <button
                type="button"
                className="btn primary"
                disabled={isSubmitting}
                onClick={doSubmit}
              >
                Submit Practice Attempt Anyway
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
