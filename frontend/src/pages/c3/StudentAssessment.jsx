import { useState, useEffect } from 'react';
import { useNavigate, useParams, useOutletContext } from 'react-router-dom';
import { getAssessment, submitAnswer } from '../../services/c3Api.js';
import '../c3/C3.css';

const STEPS = [
  { key: 'analyzing',  label: 'Processing answer text' },
  { key: 'marking',    label: 'Evaluating against rubric criteria' },
  { key: 'feedback',   label: 'Generating personalised feedback' },
  { key: 'mindmap',    label: 'Building concept mind map' },
];

function wordCount(text) {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

export default function StudentAssessment() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [loadingAssessment, setLoadingAssessment] = useState(true);

  const [answer, setAnswer] = useState('');
  const [submitError, setSubmitError] = useState(null);
  const [stage, setStage] = useState('idle'); // idle | submitting | done
  const [currentStep, setCurrentStep] = useState(-1);
  const { setPageTitle } = useOutletContext();

  useEffect(() => {
    if (stage === 'idle') setPageTitle(assessment?.title || 'C3 Assessment');
    else setPageTitle('AI Assessment in Progress');
  }, [stage, assessment, setPageTitle]);

  useEffect(() => {
    setLoadingAssessment(true);
    getAssessment(id)
      .then((res) => setAssessment(res.assessment))
      .catch((err) => setLoadError(err.message || 'Failed to load assessment'))
      .finally(() => setLoadingAssessment(false));
  }, [id]);

  const handleSubmit = async () => {
    if (!answer.trim()) {
      setSubmitError('Please type your answer before submitting.');
      return;
    }
    if (wordCount(answer) < 10) {
      setSubmitError('Your answer is too short. Please provide a complete response.');
      return;
    }

    setSubmitError(null);
    setStage('submitting');

    // Animate through processing steps while real call happens
    let stepIdx = 0;
    const stepInterval = setInterval(() => {
      setCurrentStep(stepIdx);
      stepIdx++;
      if (stepIdx >= STEPS.length) clearInterval(stepInterval);
    }, 900);

    try {
      const res = await submitAnswer(String(assessment._id), answer);
      clearInterval(stepInterval);
      setCurrentStep(STEPS.length); // all done
      setStage('done');
      setTimeout(() => navigate(`/c3/result/${res.submission_id}`), 500);
    } catch (err) {
      clearInterval(stepInterval);
      setStage('idle');
      setCurrentStep(-1);
      setSubmitError(err.message || 'Assessment could not be processed. Please try again.');
    }
  };

  // ── Loading skeleton
  if (loadingAssessment) {
    return (
      <div className="c3-page c3-page-dark">
        <div className="c3-skeleton" style={{ height: 32, width: '30%', marginBottom: 24 }} />
        <div className="c3-bento">
          <div className="c3-col-8">
            <div className="c3-card">
              <div className="c3-skeleton" style={{ height: 20, width: '80%', marginBottom: 12 }} />
              <div className="c3-skeleton" style={{ height: 200 }} />
            </div>
          </div>
          <div className="c3-col-4">
            <div className="c3-card">
              <div className="c3-skeleton" style={{ height: 14, width: '60%', marginBottom: 10 }} />
              <div className="c3-skeleton" style={{ height: 14, width: '80%', marginBottom: 10 }} />
              <div className="c3-skeleton" style={{ height: 14, width: '50%' }} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="c3-page c3-page-dark">
        <div className="c3-alert c3-alert-error">
          <span>⚠</span> <span>{loadError}</span>
        </div>
        <button className="c3-btn c3-btn-ghost" onClick={() => navigate('/c3')}>← Back</button>
      </div>
    );
  }

  const maxMarks = assessment?.max_marks || 10;
  const wc = wordCount(answer);

  // ── AI Processing screen
  if (stage === 'submitting' || stage === 'done') {
    return (
      <div className="c3-page c3-page-dark">
        {/* Header managed by Top Nav */}

        <div className="c3-bento">
          <div className="c3-col-6">
            <div className="c3-card-glass">
              <div className="c3-section-title" style={{ marginBottom: 24 }}>
                <span className="c3-section-dot" />
                C3 AI Pipeline
              </div>
              <div className="c3-pipeline">
                {STEPS.map((step, i) => {
                  const isDone   = currentStep > i;
                  const isActive = currentStep === i;
                  return (
                    <div
                      key={step.key}
                      className={`c3-pipeline-step ${isDone ? 'done' : isActive ? 'active' : ''}`}
                    >
                      <div className={`c3-step-icon ${isDone ? 'done' : isActive ? 'active' : 'idle'}`}>
                        {isDone ? '✓' : isActive ? <span className="c3-spinner" /> : '○'}
                      </div>
                      <span>{step.label}</span>
                    </div>
                  );
                })}
                {stage === 'done' && (
                  <div className="c3-pipeline-step done" style={{ marginTop: 8 }}>
                    <div className="c3-step-icon done">✓</div>
                    <span>Complete — loading your result…</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="c3-col-6">
            <div className="c3-card">
              <div className="c3-section-title"><span className="c3-section-dot" />Your Answer</div>
              <div className="c3-answer-display" style={{ maxHeight: 260, overflowY: 'auto' }}>
                {answer}
              </div>
              <div className="c3-word-count">{wc} words</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Idle: show question + textarea
  return (
    <div className="c3-page c3-page-dark">
      {/* Back button above content since header is top nav */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <button
            className="c3-btn c3-btn-ghost c3-btn-sm"
            onClick={() => navigate('/c3')}
          >
            ← Back
          </button>
          <p className="c3-page-subtitle" style={{ marginTop: '8px' }}>{assessment.is_dev_seed ? 'PP1 Demonstration Assessment' : 'Assessment'}</p>
        </div>
        <span className="c3-badge c3-badge-available">● Available</span>
      </div>

      <div className="c3-bento">
        {/* ── Left: question + answer area */}
        <div className="c3-col-8">
          {/* Question */}
          <div className="c3-card c3-mb-4">
            <div className="c3-section-title">
              <span className="c3-section-dot" />
              Question
            </div>
            <p className="c3-question-text">{assessment.question_text}</p>
            <div className="c3-gap-3 c3-mt-4">
              <span className="c3-badge c3-badge-essay">✏️ Written Answer</span>
              <span className="c3-text-dim">{maxMarks} marks</span>
            </div>
          </div>

          {/* Answer */}
          <div className="c3-card">
            <div className="c3-section-title">
              <span className="c3-section-dot" />
              Your Answer
            </div>

            {submitError && (
              <div className="c3-alert c3-alert-error c3-mb-4">
                <span>⚠</span> <span>{submitError}</span>
              </div>
            )}

            <label className="c3-label" htmlFor="c3-answer">
              Type your answer below
            </label>
            <textarea
              id="c3-answer"
              className="c3-textarea"
              placeholder="Write your complete answer here..."
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={14}
            />
            <div className="c3-between c3-mt-4">
              <span className="c3-word-count">{wc} words</span>
              <div className="c3-gap-3">
                <button
                  className="c3-btn c3-btn-ghost"
                  onClick={() => setAnswer('')}
                  disabled={!answer}
                >
                  Clear
                </button>
                <button
                  className="c3-btn c3-btn-primary c3-btn-large"
                  onClick={handleSubmit}
                  disabled={!answer.trim()}
                >
                  Submit Answer →
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right: assessment info */}
        <div className="c3-col-4">
          <div className="c3-card">
            <div className="c3-section-title">
              <span className="c3-section-dot" />
              Assessment Info
            </div>
            <div className="c3-stack">
              <div>
                <div className="c3-label">Answer Type</div>
                <div className="c3-text-white" style={{ textTransform: 'capitalize' }}>
                  {assessment.answer_type || 'Written Answer'}
                </div>
              </div>
              <hr className="c3-divider" />
              <div>
                <div className="c3-label">Maximum Marks</div>
                <div className="c3-text-white">{maxMarks}</div>
              </div>
              <hr className="c3-divider" />
              <div>
                <div className="c3-label">Status</div>
                <span className="c3-badge c3-badge-available">● Not Submitted</span>
              </div>
              <hr className="c3-divider" />
              <div className="c3-alert c3-alert-info" style={{ marginBottom: 0 }}>
                <span style={{ flexShrink: 0 }}>ℹ</span>
                <span style={{ fontSize: 12 }}>
                  Your answer will be assessed by the C3 AI pipeline and then reviewed by your lecturer.
                  The lecturer holds final academic authority.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
