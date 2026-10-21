import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { assessAnswer, listSubmissions, getSubmission } from '../../services/c3Api.js';
import { C3_PRESETS } from './presets.js';
import MindMapGraph from './components/MindMapGraph.jsx';
import CriterionCard from './components/CriterionCard.jsx';
import ConceptDiagnosis from './components/ConceptDiagnosis.jsx';
import './c3.css';

export default function AssessmentPage() {
  const { user } = useAuth();

  // Mode: 'new_assessment' | 'history'
  const [activeTab, setActiveTab] = useState('new_assessment');

  // Active preset (default to full credit architecture preset)
  const [selectedPresetId, setSelectedPresetId] = useState('arch-full');

  // Form State
  const initialPreset = C3_PRESETS[0];
  const [questionId, setQuestionId] = useState(initialPreset.payload.question_id);
  const [questionText, setQuestionText] = useState(initialPreset.payload.question_text);
  const [studentAnswer, setStudentAnswer] = useState(initialPreset.payload.student_answer);
  const [referenceAnswer, setReferenceAnswer] = useState(initialPreset.payload.reference_answer || '');
  const [expectedConceptsStr, setExpectedConceptsStr] = useState(
    initialPreset.payload.expected_concepts.join(', ')
  );
  const [answerType, setAnswerType] = useState(initialPreset.payload.answer_type || 'short');
  const [rubric, setRubric] = useState(initialPreset.payload.rubric);
  const [options, setOptions] = useState(initialPreset.payload.options || null);
  const [selectedOptionId, setSelectedOptionId] = useState(initialPreset.payload.selected_option_id || null);
  const [correctAnswer, setCorrectAnswer] = useState(initialPreset.payload.correct_answer || null);
  const [maxMarks, setMaxMarks] = useState(initialPreset.payload.max_marks || null);

  // Rubric view toggles
  const [showRubricDetails, setShowRubricDetails] = useState(false);

  // Pipeline Execution State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Submissions History State
  const [historySubmissions, setHistorySubmissions] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [viewingHistoricalSubmission, setViewingHistoricalSubmission] = useState(null);
  const [loadingHistoricalDetail, setLoadingHistoricalDetail] = useState(false);

  // Fetch student's own submissions
  const fetchStudentHistory = async () => {
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const data = await listSubmissions();
      setHistorySubmissions(data.submissions || []);
    } catch (err) {
      console.error('Failed to load submissions history:', err);
      setHistoryError(err.message || 'Could not load your submissions history.');
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchStudentHistory();
  }, []);

  // Switch preset
  const handleSelectPreset = (preset) => {
    setSelectedPresetId(preset.id);
    setQuestionId(preset.payload.question_id);
    setQuestionText(preset.payload.question_text);
    setStudentAnswer(preset.payload.student_answer);
    setReferenceAnswer(preset.payload.reference_answer || '');
    setExpectedConceptsStr((preset.payload.expected_concepts || []).join(', '));
    setAnswerType(preset.payload.answer_type || 'short');
    setRubric(preset.payload.rubric || null);
    setOptions(preset.payload.options || null);
    setSelectedOptionId(preset.payload.selected_option_id || null);
    setCorrectAnswer(preset.payload.correct_answer || null);
    setMaxMarks(preset.payload.max_marks || null);
    setError(null);
  };

  // Submit assessment request to backend
  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!studentAnswer.trim() && !selectedOptionId) {
      setError('Please provide a student answer or select an option to assess.');
      return;
    }
    if (!questionId.trim()) {
      setError('Please specify a Question ID.');
      return;
    }
    if (!questionText.trim()) {
      setError('Please specify Question Text.');
      return;
    }

    setLoading(true);
    setError(null);

    const conceptsList = expectedConceptsStr
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean);

    const payload = {
      question_id: questionId.trim(),
      question_text: questionText.trim(),
      student_answer: studentAnswer.trim(),
      reference_answer: referenceAnswer.trim() || null,
      expected_concepts: conceptsList.length > 0 ? conceptsList : null,
      answer_type: answerType,
      options: options || null,
      selected_option_id: selectedOptionId || null,
      correct_answer: correctAnswer || null,
      max_marks: maxMarks || undefined,
      rubric: rubric || null,
      is_demo: selectedPresetId !== 'custom',
    };

    try {
      const data = await assessAnswer(payload);
      setResult(data);
      setViewingHistoricalSubmission(null);
      // Refresh history silently
      fetchStudentHistory();
    } catch (err) {
      console.error('Assessment pipeline error:', err);
      let errMsg = err.message || 'Assessment pipeline failed';
      if (err.status === 422) {
        errMsg = `Input validation error (422): ${err.message}. Please check all required rubric and question fields.`;
      } else if (err.status === 502) {
        errMsg = `Backend error (502): ${err.message}. Ensure the C3 Python AI service is running on port 8003.`;
      } else if (err.status === 401) {
        errMsg = 'Session expired or unauthorized. Please log in again.';
      }
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  // View a past submission from history
  const handleOpenHistoricalSubmission = async (subId) => {
    setLoadingHistoricalDetail(true);
    setError(null);
    try {
      const detail = await getSubmission(subId);
      setViewingHistoricalSubmission(detail);
      setResult(null);
    } catch (err) {
      console.error('Failed to load past submission detail:', err);
      setError(err.message || 'Failed to open submission detail.');
    } finally {
      setLoadingHistoricalDetail(false);
    }
  };

  // Determine active evaluation to render
  const activeEvaluation = viewingHistoricalSubmission
    ? viewingHistoricalSubmission.result?.ai_evaluation || viewingHistoricalSubmission.result
    : result;

  const activeSubmissionContext = viewingHistoricalSubmission
    ? viewingHistoricalSubmission.submission
    : result
    ? {
        question_id: result.question_id,
        question_text: questionText,
        student_answer: studentAnswer,
        reference_answer: referenceAnswer,
        status: result.status || 'pending_review',
        submission_id: result.submission_id,
      }
    : null;

  const historicalResult = viewingHistoricalSubmission?.result;
  const isFinalized = historicalResult?.status === 'finalized';

  // Build sentence text map from active evaluation
  const sentenceMap = new Map();
  if (activeEvaluation?.analysis?.sentences) {
    activeEvaluation.analysis.sentences.forEach((s) => sentenceMap.set(s.sentence_id, s.text));
  }

  // Quick feedback by criterion id
  const feedbackByCriterionId = new Map();
  if (activeEvaluation?.feedback?.criteria_feedback) {
    activeEvaluation.feedback.criteria_feedback.forEach((fb) => feedbackByCriterionId.set(fb.criterion_id, fb));
  }

  const totalPossible =
    historicalResult?.total_possible_marks ??
    activeEvaluation?.total_possible_marks ??
    activeEvaluation?.marking?.total_possible_marks ??
    0;

  const automatedMark =
    historicalResult?.automated_mark ??
    activeEvaluation?.total_awarded_marks ??
    activeEvaluation?.marking?.total_awarded_marks ??
    0;

  const scorePercentage =
    historicalResult?.percentage ??
    activeEvaluation?.percentage ??
    (totalPossible > 0 ? Math.round((automatedMark / totalPossible) * 1000) / 10 : 0);

  return (
    <div className="c3-page">
      {/* Top Header */}
      <div className="c3-header-lead">
        <div>
          <h1>Automated Marking & Answer Analysis</h1>
          <p className="muted" style={{ margin: '4px 0 0' }}>
            AdaptiveLearnSE Component 3 • Rubric-Aware Semantic Evaluation & Concept Diagnosis
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {user?.role === 'lecturer' && (
            <Link to="/lecturer/c3" className="btn secondary" style={{ width: 'auto', padding: '6px 14px' }}>
              📋 Review Submissions Queue →
            </Link>
          )}
          <span className="c3-badge-research">AdaptiveLearnSE • Component 3</span>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="c3-mode-tabs">
        <button
          type="button"
          className={`c3-mode-tab ${activeTab === 'new_assessment' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('new_assessment');
            setViewingHistoricalSubmission(null);
          }}
        >
          ✍️ New Assessment & Benchmarks
        </button>
        <button
          type="button"
          className={`c3-mode-tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('history');
            fetchStudentHistory();
          }}
        >
          📋 My Submissions History ({historySubmissions.length})
        </button>
      </div>

      {/* =========================================================================
          MODE 1: SUBMISSIONS HISTORY TAB
         ========================================================================= */}
      {activeTab === 'history' && !viewingHistoricalSubmission && (
        <div className="panel" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0 }}>Your Assessment History</h3>
              <p className="small muted" style={{ margin: '4px 0 0' }}>
                Track your submitted answers, AI proposed evaluations, and lecturer-finalized marks.
              </p>
            </div>
            <button
              type="button"
              className="btn-ghost"
              style={{ width: 'auto', padding: '6px 12px' }}
              onClick={fetchStudentHistory}
              disabled={loadingHistory}
            >
              🔄 Refresh History
            </button>
          </div>

          {loadingHistory ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div className="c3-spinner" style={{ width: '24px', height: '24px', borderColor: 'var(--primary)' }} />
              <p className="muted" style={{ marginTop: '12px' }}>Loading past submissions...</p>
            </div>
          ) : historyError ? (
            <div className="c3-alert-box c3-alert-error">
              <span>⚠️</span>
              <div>{historyError}</div>
            </div>
          ) : historySubmissions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 16px' }}>
              <h4>No Submissions Yet</h4>
              <p className="muted" style={{ margin: '6px 0 16px' }}>
                You have not submitted any answers for automated marking yet.
              </p>
              <button
                type="button"
                className="btn"
                style={{ width: 'auto', margin: '0 auto' }}
                onClick={() => setActiveTab('new_assessment')}
              >
                Start an Assessment Now →
              </button>
            </div>
          ) : (
            <div className="c3-table-responsive">
              <table className="c3-queue-table">
                <thead>
                  <tr>
                    <th>Question / Task</th>
                    <th>Submitted At</th>
                    <th>AI Proposed Mark</th>
                    <th>Status</th>
                    <th>Final Approved Mark</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {historySubmissions.map((s) => {
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
                          <div>
                            <strong>{s.question_id || 'SE-DB-001'}</strong>
                          </div>
                          {s.question_text && (
                            <div
                              className="small muted"
                              style={{
                                maxWidth: '280px',
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
                              ? '⏳ AI Proposed (Pending)'
                              : status === 'reviewed'
                              ? '🔍 Under Review'
                              : status === 'finalized'
                              ? '✓ Finalized'
                              : status}
                          </span>
                        </td>
                        <td>
                          {s.final_mark !== null && s.final_mark !== undefined ? (
                            <strong style={{ color: '#087a63', fontSize: '1rem' }}>
                              {s.final_mark} / {s.total_possible_marks}
                            </strong>
                          ) : (
                            <span className="small muted">Awaiting finalization</span>
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn secondary"
                            style={{ padding: '6px 12px', fontSize: '0.85rem', width: 'auto', whiteSpace: 'nowrap' }}
                            onClick={() => handleOpenHistoricalSubmission(s._id)}
                          >
                            View Evaluation & Mind Map →
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
      )}

      {/* =========================================================================
          MODE 2: NEW ASSESSMENT INPUT FORM
         ========================================================================= */}
      {activeTab === 'new_assessment' && !activeEvaluation && (
        <>
          {/* Preset Benchmarks Selector */}
          <div className="c3-presets-bar">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>🎯 Controlled PP1 Demonstration Scenarios:</strong>
              <span className="small muted">Click to auto-populate validated test scenarios</span>
            </div>
            <div className="c3-presets-list">
              {C3_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`c3-preset-btn ${selectedPresetId === p.id ? 'active' : ''}`}
                  onClick={() => handleSelectPreset(p)}
                >
                  {p.title}
                </button>
              ))}
            </div>
          </div>

          {/* Assessment Form */}
          <form className="panel form-block" onSubmit={handleSubmit}>
            <h3>Assessment Configuration & Input</h3>

            <div className="c3-form-grid">
              <div>
                <label htmlFor="qId">Question ID</label>
                <input
                  id="qId"
                  type="text"
                  value={questionId}
                  onChange={(e) => {
                    setQuestionId(e.target.value);
                    setSelectedPresetId('custom');
                  }}
                  placeholder="e.g. SE3010-Q01"
                  required
                />
              </div>
              <div>
                <label htmlFor="ansType">Answer Type</label>
                <select
                  id="ansType"
                  value={answerType}
                  onChange={(e) => setAnswerType(e.target.value)}
                >
                  <option value="short">Short Answer</option>
                  <option value="structured">Structured Short Answer</option>
                  <option value="essay">Descriptive / Essay</option>
                  <option value="mcq">Multiple-Choice Question (MCQ)</option>
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="qText">Question Text</label>
              <input
                id="qText"
                type="text"
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                placeholder="Enter the examination question text..."
                required
              />
            </div>

            {/* Interactive MCQ Options when answerType is mcq or options provided */}
            {options && options.length > 0 ? (
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontWeight: 600, marginBottom: '8px' }}>
                  Multiple-Choice Options (Select your answer):
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {options.map((opt) => {
                    const isSelected = selectedOptionId === opt.option_id || selectedOptionId === opt.label;
                    return (
                      <label
                        key={opt.option_id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          padding: '10px 14px',
                          border: isSelected ? '2px solid var(--primary)' : '1px solid var(--line)',
                          borderRadius: '8px',
                          background: isSelected ? 'rgba(8, 122, 99, 0.05)' : '#fff',
                          cursor: 'pointer',
                        }}
                      >
                        <input
                          type="radio"
                          name="c3-mcq-choice"
                          checked={isSelected}
                          onChange={() => {
                            setSelectedOptionId(opt.option_id);
                            setStudentAnswer(`Option ${opt.label}: ${opt.text}`);
                          }}
                        />
                        <span style={{ fontWeight: 700, minWidth: '24px' }}>[{opt.label}]</span>
                        <span>{opt.text}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div>
                <label htmlFor="studentAns">
                  Student Answer <span style={{ color: '#d6453d' }}>*</span>
                </label>
                <textarea
                  id="studentAns"
                  className="c3-textarea"
                  rows="4"
                  value={studentAnswer}
                  onChange={(e) => {
                    setStudentAnswer(e.target.value);
                    setSelectedPresetId('custom');
                  }}
                  placeholder="Type or paste natural-language student response here..."
                  required
                />
                <span className="hint">
                  Words: {studentAnswer.trim() ? studentAnswer.trim().split(/\s+/).length : 0} • Characters:{' '}
                  {studentAnswer.length}
                </span>
              </div>
            )}

            <div>
              <label htmlFor="refAns">Reference / Model Answer (Optional)</label>
              <textarea
                id="refAns"
                className="c3-textarea"
                rows="2"
                value={referenceAnswer}
                onChange={(e) => setReferenceAnswer(e.target.value)}
                placeholder="Lecturer model answer for semantic alignment comparison..."
              />
            </div>

            <div>
              <label htmlFor="expConcepts">Expected Domain Concepts (comma-separated)</label>
              <input
                id="expConcepts"
                type="text"
                value={expectedConceptsStr}
                onChange={(e) => setExpectedConceptsStr(e.target.value)}
                placeholder="e.g. high-level structure, components, relationships"
              />
            </div>

            {/* Rubric Overview Bar */}
            <div style={{ marginTop: '10px' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: '#f7fafc',
                  border: '1px solid var(--line)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                }}
              >
                <div>
                  <strong>Active Rubric:</strong> {rubric?.title} (ID: {rubric?.rubric_id}) •{' '}
                  {rubric?.criteria?.length || 0} Criterion/Criteria
                </div>
                <button
                  type="button"
                  className="btn-ghost"
                  style={{ width: 'auto', padding: '4px 10px' }}
                  onClick={() => setShowRubricDetails(!showRubricDetails)}
                >
                  {showRubricDetails ? 'Hide Rubric Structure' : 'Inspect Rubric Structure'}
                </button>
              </div>

              {showRubricDetails && (
                <div style={{ background: '#f3f6f8', padding: '12px', borderRadius: '8px', marginTop: '6px' }}>
                  {rubric?.criteria?.map((c, i) => (
                    <div key={i} style={{ marginBottom: '10px', fontSize: '0.88rem' }}>
                      <strong>
                        Criterion {c.criterion_id}: {c.description} (Max: {c.max_marks} marks)
                      </strong>
                      <div style={{ marginLeft: '12px', marginTop: '4px' }}>
                        {c.scoring_levels?.map((lvl, j) => (
                          <div key={j} className="small muted">
                            • Level {lvl.level_id} ({lvl.mark} marks): {lvl.descriptor}
                            {lvl.required_concepts?.length > 0 &&
                              ` [Requires: ${lvl.required_concepts.join(', ')}]`}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="c3-form-actions">
              <button type="submit" className="btn" disabled={loading}>
                {loading && <span className="c3-spinner" />}
                {loading ? 'Evaluating via C3 Pipeline (F1 → F2 → F3 → F4)...' : 'Assess Student Answer'}
              </button>
              <button
                type="button"
                className="btn secondary"
                onClick={() => {
                  setStudentAnswer('');
                  setResult(null);
                  setError(null);
                }}
              >
                Clear
              </button>
            </div>
          </form>
        </>
      )}

      {/* Loading state for Historical Detail */}
      {loadingHistoricalDetail && (
        <div className="panel" style={{ textAlign: 'center', padding: '50px' }}>
          <div className="c3-spinner" style={{ width: '28px', height: '28px', borderColor: 'var(--primary)' }} />
          <p className="muted" style={{ marginTop: '12px' }}>Loading complete assessment evaluation...</p>
        </div>
      )}

      {/* Error Message Box */}
      {error && (
        <div className="c3-alert-box c3-alert-error">
          <span style={{ fontSize: '1.2rem' }}>⚠️</span>
          <div>
            <strong>Evaluation Error:</strong>
            <p style={{ margin: '2px 0 0', fontSize: '0.9rem' }}>{error}</p>
          </div>
        </div>
      )}

      {/* =========================================================================
          ASSESSMENT RESULT SECTION (Active Submission OR Historical View)
         ========================================================================= */}
      {activeEvaluation && !loadingHistoricalDetail && (
        <div className="c3-result-container">
          {/* Top Back Navigation if viewing past submission */}
          {viewingHistoricalSubmission && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <button
                type="button"
                className="btn-ghost"
                style={{ width: 'auto', padding: '6px 14px' }}
                onClick={() => setViewingHistoricalSubmission(null)}
              >
                ← Back to Submissions History
              </button>
              <button
                type="button"
                className="btn secondary"
                style={{ width: 'auto', padding: '6px 14px' }}
                onClick={() => {
                  setActiveTab('new_assessment');
                  setViewingHistoricalSubmission(null);
                  setResult(null);
                }}
              >
                ✍️ Start New Assessment
              </button>
            </div>
          )}

          {/* Top Score Banner */}
          <div className="c3-result-banner">
            <div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                <span className="c3-badge-research" style={{ background: 'rgba(255,255,255,0.2)' }}>
                  {activeEvaluation.pipeline_version || 'f2-rubric-v1'} • Component 3
                </span>
                {isFinalized ? (
                  <span className="c3-badge-status finalized" style={{ background: '#e6f7f2', color: '#065543' }}>
                    ✓ Official Result Finalized by Lecturer
                  </span>
                ) : (
                  <span className="c3-badge-status pending_review" style={{ background: 'rgba(254,245,231,0.95)' }}>
                    ⏳ AI Proposed Mark • Pending Final Lecturer Review
                  </span>
                )}
              </div>
              <h2 className="c3-banner-title">
                {isFinalized ? 'Finalized Assessment Result' : 'AI Proposed Evaluation'}
              </h2>
              <p className="c3-banner-sub">
                Question: {activeSubmissionContext?.question_id} • Evaluated via F1–F4 sequential pipeline
              </p>
              {activeSubmissionContext?.submission_id && (
                <p className="small" style={{ color: '#bcd0e2', margin: '4px 0 0' }}>
                  Submission Reference: <code>#{String(activeSubmissionContext.submission_id).slice(-6)}</code>
                </p>
              )}
            </div>

            <div className="c3-score-display">
              <div className="c3-score-ring-wrap">
                <svg viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)' }}>
                  <circle cx="50" cy="50" r="40" className="ring-track" stroke="rgba(255,255,255,0.2)" />
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    className="ring-fill"
                    stroke={isFinalized ? '#3ddbb0' : '#ffd166'}
                    strokeDasharray="251.2"
                    strokeDashoffset={
                      scorePercentage !== null && scorePercentage !== undefined
                        ? 251.2 - (251.2 * scorePercentage) / 100
                        : 251.2
                    }
                  />
                </svg>
                <div className="c3-score-circle-text">
                  <div className="c3-score-percent">{scorePercentage}%</div>
                  <div className="c3-score-denom-label">{isFinalized ? 'Final' : 'AI Mark'}</div>
                </div>
              </div>

              <div className="c3-score-numbers">
                <div>
                  <span className="c3-score-big">
                    {isFinalized ? historicalResult?.final_mark : automatedMark}
                  </span>
                  <span className="c3-score-total"> / {totalPossible}</span>
                </div>
                <span className="c3-score-legend">
                  {isFinalized
                    ? `Authoritative Score (Verified by ${historicalResult?.reviewed_by || 'Lecturer'})`
                    : 'AI Proposed Mark (Pending Final Lecturer Verification)'}
                </span>
              </div>
            </div>
          </div>

          {/* Finalized Lecturer Decision Notice */}
          {isFinalized && historicalResult?.lecturer_decision === 'overridden' && (
            <div className="panel" style={{ borderLeft: '5px solid #c05621', background: '#fdfaf8' }}>
              <h4 style={{ margin: '0 0 6px', color: '#9c4215' }}>Lecturer Review Notes & Override Reason</h4>
              <p style={{ margin: 0, fontStyle: 'italic', fontSize: '0.95rem' }}>
                "{historicalResult?.override_reason || 'Verified and updated by lecturer.'}"
              </p>
              <div className="small muted" style={{ marginTop: '8px' }}>
                Original AI Proposed Mark: {automatedMark} / {totalPossible} • Final Score: {historicalResult?.final_mark} / {totalPossible}
              </div>
            </div>
          )}

          {/* Warnings Alert Box */}
          {activeEvaluation.warnings && activeEvaluation.warnings.length > 0 && (
            <div className="c3-alert-box c3-alert-warning">
              <span style={{ fontSize: '1.2rem' }}>ℹ️</span>
              <div>
                <strong>Pipeline Warnings:</strong>
                <ul style={{ margin: '4px 0 0', paddingLeft: '18px', fontSize: '0.88rem' }}>
                  {activeEvaluation.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Question and Student Answer Context */}
          <div className="panel">
            <h4 style={{ margin: '0 0 8px' }}>Assessment Context & Evaluated Answer</h4>
            <div className="small muted" style={{ marginBottom: '8px' }}>
              <strong>Question:</strong> {activeSubmissionContext?.question_text}
            </div>
            <div
              style={{
                background: '#f8fafc',
                border: '1px solid var(--line)',
                borderRadius: '8px',
                padding: '12px 16px',
                whiteSpace: 'pre-wrap',
                fontSize: '0.92rem',
                lineHeight: 1.5,
              }}
            >
              {activeSubmissionContext?.student_answer}
            </div>
          </div>

          {/* Overall Feedback Summary Card */}
          {activeEvaluation.feedback?.overall_feedback && (
            <div className="panel c3-summary-card">
              <h3>Overall Feedback Synthesis</h3>
              <p className="c3-summary-text">
                {activeEvaluation.feedback.overall_feedback.overall_summary}
              </p>

              <div className="c3-summary-columns">
                {activeEvaluation.feedback.overall_feedback.overall_strengths?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#065543' }}>✓ Strengths Identified</h5>
                    <ul>
                      {activeEvaluation.feedback.overall_feedback.overall_strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {activeEvaluation.feedback.overall_feedback.overall_missing_concepts?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#8a1f17' }}>○ Missing Concepts</h5>
                    <ul>
                      {activeEvaluation.feedback.overall_feedback.overall_missing_concepts.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {activeEvaluation.feedback.overall_feedback.overall_improvement_suggestions?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#1b4d75' }}>💡 Recommended Improvements</h5>
                    <ul>
                      {activeEvaluation.feedback.overall_feedback.overall_improvement_suggestions.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {activeEvaluation.feedback.overall_feedback.overall_next_level_improvements?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#5c2069' }}>🚀 Target Next Level</h5>
                    <ul>
                      {activeEvaluation.feedback.overall_feedback.overall_next_level_improvements.map((nl, i) => (
                        <li key={i}>{nl}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Criteria Evaluation Results Section */}
          <div style={{ marginTop: '24px' }}>
            <h2>Criterion-Level Evaluation & Grounded Evidence</h2>
            {activeEvaluation.marking?.criteria_results?.map((cr) => (
              <CriterionCard
                key={cr.criterion_id}
                criterionMarking={cr}
                criterionFeedback={feedbackByCriterionId.get(cr.criterion_id)}
                sentenceMap={sentenceMap}
              />
            ))}
          </div>

          {/* Concept Diagnosis Table Section */}
          <ConceptDiagnosis analysis={activeEvaluation.analysis} sentenceMap={sentenceMap} />

          {/* Interactive Concept Mind Map Section */}
          <h2>Concept-Based Mind Map Visualization</h2>
          <MindMapGraph mindmap={activeEvaluation.mindmap} sentences={activeEvaluation.analysis?.sentences || []} />

          {/* Bottom Actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px' }}>
            <button
              type="button"
              className="btn secondary"
              style={{ width: 'auto' }}
              onClick={() => {
                setResult(null);
                setViewingHistoricalSubmission(null);
                setActiveTab('history');
                fetchStudentHistory();
              }}
            >
              📋 View in Submissions History
            </button>
            <button
              type="button"
              className="btn"
              style={{ width: 'auto' }}
              onClick={() => {
                setResult(null);
                setViewingHistoricalSubmission(null);
                setActiveTab('new_assessment');
              }}
            >
              ✍️ Assess Another Answer
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
