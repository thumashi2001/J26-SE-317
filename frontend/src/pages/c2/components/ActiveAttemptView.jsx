import { useState, useEffect } from 'react';
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
  const [localSubmitting, setLocalSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

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

  const answeredCount = questions.filter(
    (q) => (answers[q.question_id || q.questionId] || '').trim().length > 0
  ).length;

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

  async function handleSubmit(e) {
    e.preventDefault();

    if (answeredCount === 0) {
      const proceedEmpty = window.confirm(
        'You have not answered any questions yet. Do you still want to submit an empty practice attempt?'
      );
      if (!proceedEmpty) return;
    }

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

  const isSynthetic = paper?.source_type === 'synthetic' || paper?.practice_mode === 'synthetic_experimental';
  const totalMarksDisplay =
    paper?.total_marks !== null && paper?.total_marks !== undefined
      ? `${paper.total_marks} marks`
      : 'Unassessed';

  return (
    <div className="c2-active-attempt" aria-label="Active practice exam attempt">
      <div className="c2-attempt-topbar">
        <div>
          <span className="c2-student-panel-eyebrow">
            {isSynthetic ? 'SYNTHETIC PRACTICE ATTEMPT (EXPERIMENTAL)' : 'ACTIVE PRACTICE ATTEMPT'}
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

      {displayError && (
        <div className="c2-student-error" role="alert" style={{ margin: '14px 0' }}>
          <strong>Submission failed</strong>
          <p>{displayError}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="c2-attempt-form">
        <div className="c2-attempt-questions-list">
          {questions.map((question, index) => {
            const qId = question.question_id || question.questionId || `Q${index + 1}`;
            const answerText = answers[qId] || '';
            const qSynthetic = question.source_type === 'synthetic' || isSynthetic;

            return (
              <article key={qId} className="c2-attempt-question-card">
                <div className="c2-attempt-q-header">
                  <div>
                    <span className="c2-attempt-q-number">Question {index + 1}</span>
                    <span className="c2-student-caption" style={{ marginLeft: 8 }}>
                      ID: {qId}
                    </span>
                    {qSynthetic && (
                      <span className="c2-student-pill" style={{ marginLeft: 8, background: '#f59e0b', color: '#fff', fontSize: '0.72rem' }}>
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
                    <label htmlFor={`answer-${qId}`}>Your Answer / Working:</label>
                    <span className="c2-answer-length-count">
                      {answerText.length} characters
                    </span>
                  </div>

                  <textarea
                    id={`answer-${qId}`}
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

        <div className="c2-attempt-footer-actions">
          <button
            type="button"
            className="btn secondary"
            disabled={isSubmitting}
            onClick={handleCancel}
          >
            Cancel Attempt
          </button>

          <button
            type="submit"
            className="btn primary"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? 'Submitting Practice Attempt...'
              : `Submit Practice Attempt (${answeredCount}/${questions.length} Answered)`}
          </button>
        </div>
      </form>
    </div>
  );
}
