import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { assessAnswer } from '../../services/c3Api.js';
import { C3_PRESETS } from './presets.js';
import MindMapGraph from './components/MindMapGraph.jsx';
import CriterionCard from './components/CriterionCard.jsx';
import ConceptDiagnosis from './components/ConceptDiagnosis.jsx';
import './c3.css';

export default function AssessmentPage() {
  const { user } = useAuth();
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

  // Advanced rubric view toggle
  const [showRubricDetails, setShowRubricDetails] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  // Pipeline Execution State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Switch preset
  const handleSelectPreset = (preset) => {
    setSelectedPresetId(preset.id);
    setQuestionId(preset.payload.question_id);
    setQuestionText(preset.payload.question_text);
    setStudentAnswer(preset.payload.student_answer);
    setReferenceAnswer(preset.payload.reference_answer || '');
    setExpectedConceptsStr((preset.payload.expected_concepts || []).join(', '));
    setAnswerType(preset.payload.answer_type || 'short');
    setRubric(preset.payload.rubric);
    setError(null);
  };

  // Submit assessment request to backend
  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!studentAnswer.trim()) {
      setError('Please provide a student answer to assess.');
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

    // Build payload
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
      rubric,
    };

    try {
      const data = await assessAnswer(payload);
      setResult(data);
    } catch (err) {
      console.error('Assessment pipeline error:', err);
      let errMsg = err.message || 'Assessment pipeline failed';
      if (err.status === 422) {
        errMsg = `Input validation error (422): ${err.message}. Please check all required fields.`;
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

  // Build sentence text map from result for evidence cross-referencing
  const sentenceMap = new Map();
  if (result?.analysis?.sentences) {
    result.analysis.sentences.forEach((s) => sentenceMap.set(s.sentence_id, s.text));
  }

  // Quick feedback by criterion id
  const feedbackByCriterionId = new Map();
  if (result?.feedback?.criteria_feedback) {
    result.feedback.criteria_feedback.forEach((fb) => feedbackByCriterionId.set(fb.criterion_id, fb));
  }

  return (
    <div className="c3-page">
      {/* Top Header */}
      <div className="c3-header-lead">
        <div>
          <h1>AI-Powered Automated Marking & Answer Analysis</h1>
          <p className="muted" style={{ margin: '4px 0 0' }}>
            AdaptiveLearnSE Component 3 • Deterministic Lexical & Rubric-Aware Research Pipeline
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {user?.role === 'lecturer' && (
            <Link to="/c3/review" className="btn secondary" style={{ width: 'auto', padding: '6px 14px' }}>
              📋 Review Submissions Queue →
            </Link>
          )}
          <span className="c3-badge-research">Research Prototype • Component 3</span>
        </div>
      </div>

      {/* Preset Benchmarks Selector */}
      <div className="c3-presets-bar">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <strong>Evaluation Presets & Research Benchmarks:</strong>
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
              onChange={(e) => setQuestionId(e.target.value)}
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

        <div>
          <label htmlFor="studentAns">
            Student Answer <span style={{ color: '#d6453d' }}>*</span>
          </label>
          <textarea
            id="studentAns"
            className="c3-textarea"
            rows="4"
            value={studentAnswer}
            onChange={(e) => setStudentAnswer(e.target.value)}
            placeholder="Paste natural-language student response here..."
            required
          />
          <span className="hint">
            Words: {studentAnswer.trim() ? studentAnswer.trim().split(/\s+/).length : 0} • Characters:{' '}
            {studentAnswer.length}
          </span>
        </div>

        <div>
          <label htmlFor="refAns">Reference / Model Answer (Optional)</label>
          <textarea
            id="refAns"
            className="c3-textarea"
            rows="2"
            value={referenceAnswer}
            onChange={(e) => setReferenceAnswer(e.target.value)}
            placeholder="Lecturer model answer for cosine similarity comparison..."
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
            {loading ? 'Executing C3 Pipeline (F1 → F2 → F3 → F4)...' : 'Assess Student Answer'}
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
          ASSESSMENT RESULT SECTION
         ========================================================================= */}
      {result && (
        <div className="c3-result-container">
          {/* Top Score Banner */}
          <div className="c3-result-banner">
            <div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                <span className="c3-badge-research" style={{ background: 'rgba(255,255,255,0.2)' }}>
                  {result.pipeline_version} • Single Source of Truth
                </span>
                <span className="c3-badge-status pending_review" style={{ background: 'rgba(254,245,231,0.9)' }}>
                  ⏳ AI Proposed Mark • Pending Lecturer Review
                </span>
              </div>
              <h2 className="c3-banner-title">AI Proposed Assessment</h2>
              <p className="c3-banner-sub">
                Question: {result.question_id} • Analyzed via Function 1–4 sequential pipeline
              </p>
              {result.submission_id && (
                <p className="small" style={{ color: '#bcd0e2', margin: '4px 0 0' }}>
                  Recorded Submission ID: <code>{result.submission_id}</code>
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
                    stroke="#3ddbb0"
                    strokeDasharray="251.2"
                    strokeDashoffset={
                      result.percentage !== null && result.percentage !== undefined
                        ? 251.2 - (251.2 * result.percentage) / 100
                        : 251.2
                    }
                  />
                </svg>
                <div className="c3-score-circle-text">
                  <div className="c3-score-percent">{result.percentage}%</div>
                  <div className="c3-score-denom-label">AI Proposed</div>
                </div>
              </div>

              <div className="c3-score-numbers">
                <div>
                  <span className="c3-score-big">{result.total_awarded_marks}</span>
                  <span className="c3-score-total"> / {result.total_possible_marks}</span>
                </div>
                <span className="c3-score-legend">
                  AI Proposed Mark (Pending Final Lecturer Verification)
                </span>
              </div>
            </div>
          </div>

          {/* Warnings Alert Box */}
          {result.warnings && result.warnings.length > 0 && (
            <div className="c3-alert-box c3-alert-warning">
              <span style={{ fontSize: '1.2rem' }}>ℹ️</span>
              <div>
                <strong>Pipeline Warnings:</strong>
                <ul style={{ margin: '4px 0 0', paddingLeft: '18px', fontSize: '0.88rem' }}>
                  {result.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Overall Feedback Summary Card */}
          {result.feedback?.overall_feedback && (
            <div className="panel c3-summary-card">
              <h3>Overall Feedback Synthesis</h3>
              <p className="c3-summary-text">
                {result.feedback.overall_feedback.overall_summary}
              </p>

              <div className="c3-summary-columns">
                {result.feedback.overall_feedback.overall_strengths?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#065543' }}>✓ Strengths Identified</h5>
                    <ul>
                      {result.feedback.overall_feedback.overall_strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.feedback.overall_feedback.overall_missing_concepts?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#8a1f17' }}>○ Missing Concepts</h5>
                    <ul>
                      {result.feedback.overall_feedback.overall_missing_concepts.map((m, i) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.feedback.overall_feedback.overall_improvement_suggestions?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#1b4d75' }}>💡 Recommended Improvements</h5>
                    <ul>
                      {result.feedback.overall_feedback.overall_improvement_suggestions.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.feedback.overall_feedback.overall_next_level_improvements?.length > 0 && (
                  <div className="c3-summary-col">
                    <h5 style={{ color: '#5c2069' }}>🚀 Target Next Level</h5>
                    <ul>
                      {result.feedback.overall_feedback.overall_next_level_improvements.map((nl, i) => (
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
            {result.marking?.criteria_results?.map((cr) => (
              <CriterionCard
                key={cr.criterion_id}
                criterionMarking={cr}
                criterionFeedback={feedbackByCriterionId.get(cr.criterion_id)}
                sentenceMap={sentenceMap}
              />
            ))}
          </div>

          {/* Concept Diagnosis Table Section */}
          <ConceptDiagnosis analysis={result.analysis} sentenceMap={sentenceMap} />

          {/* Interactive Concept Mind Map Section */}
          <h2>Concept-Based Mind Map Visualization</h2>
          <MindMapGraph mindmap={result.mindmap} sentences={result.analysis?.sentences || []} />

          {/* Debug / Raw JSON Inspector */}
          <div style={{ marginTop: '20px', textAlign: 'right' }}>
            <button
              type="button"
              className="btn-ghost"
              style={{ width: 'auto', padding: '6px 14px' }}
              onClick={() => setShowRawJson(!showRawJson)}
            >
              {showRawJson ? 'Hide Raw API Response' : 'Inspect Raw Assessment JSON'}
            </button>
          </div>

          {showRawJson && (
            <div className="panel" style={{ marginTop: '10px' }}>
              <h4>Raw Response from POST /api/v1/c3/assess</h4>
              <pre
                style={{
                  background: '#0e2238',
                  color: '#3ddbb0',
                  padding: '16px',
                  borderRadius: '8px',
                  overflowX: 'auto',
                  fontSize: '0.82rem',
                }}
              >
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
