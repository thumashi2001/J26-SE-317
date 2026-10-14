import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getSubmission, reviewSubmission, finalizeSubmission } from '../../services/c3Api.js';
import MindMapGraph from './components/MindMapGraph.jsx';
import CriterionCard from './components/CriterionCard.jsx';
import ConceptDiagnosis from './components/ConceptDiagnosis.jsx';
import './c3.css';

export default function LecturerReviewPage() {
  const { submissionId } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Override Modal state
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [newMark, setNewMark] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideError, setOverrideError] = useState(null);

  const fetchDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getSubmission(submissionId);
      setData(resp);
      if (resp.result?.final_mark !== null && resp.result?.final_mark !== undefined) {
        setNewMark(String(resp.result.final_mark));
      } else if (resp.result?.automated_mark !== null && resp.result?.automated_mark !== undefined) {
        setNewMark(String(resp.result.automated_mark));
      }
      if (resp.result?.override_reason) {
        setOverrideReason(resp.result.override_reason);
      }
    } catch (err) {
      console.error('Failed to load submission detail:', err);
      setError(err.message || 'Failed to retrieve submission details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [submissionId]);

  if (loading) {
    return (
      <div className="c3-page">
        <div className="panel" style={{ textAlign: 'center', padding: '60px' }}>
          <div className="c3-spinner" style={{ width: '28px', height: '28px', borderColor: 'var(--primary)' }} />
          <p className="muted" style={{ marginTop: '16px' }}>
            Loading submission and evaluation evidence...
          </p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="c3-page">
        <div className="c3-alert-box c3-alert-error">
          <span>⚠️</span>
          <div>
            <strong>Error:</strong> {error || 'Submission not found'}
          </div>
        </div>
        <Link to="/c3/review" className="btn secondary" style={{ width: 'auto' }}>
          ← Back to Submissions Queue
        </Link>
      </div>
    );
  }

  const { submission, result } = data;
  const aiEvaluation = result?.ai_evaluation || {};
  const analysis = aiEvaluation.analysis || {};
  const marking = aiEvaluation.marking || {};
  const feedback = aiEvaluation.feedback || {};
  const mindmap = aiEvaluation.mindmap || {};

  const totalPossible = result?.total_possible_marks ?? marking.total_possible_marks ?? 0;
  const automatedMark = result?.automated_mark ?? marking.total_awarded_marks ?? 0;
  const percentage =
    result?.percentage ??
    aiEvaluation.percentage ??
    (totalPossible > 0 ? Math.round((automatedMark / totalPossible) * 1000) / 10 : 0);

  const status = result?.status || submission?.status || 'pending_review';
  const decision = result?.lecturer_decision;
  const isFinalized = status === 'finalized';

  // Build sentence text map for evidence linking
  const sentenceMap = new Map();
  if (analysis?.sentences) {
    analysis.sentences.forEach((s) => sentenceMap.set(s.sentence_id, s.text));
  }

  // Feedback by criterion id
  const feedbackByCriterionId = new Map();
  if (feedback?.criteria_feedback) {
    feedback.criteria_feedback.forEach((fb) => feedbackByCriterionId.set(fb.criterion_id, fb));
  }

  // Action: Accept AI Mark
  const handleAcceptAiMark = async () => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await reviewSubmission(submission._id, { decision: 'accepted' });
      setData((prev) => ({
        ...prev,
        submission: { ...prev.submission, status: 'reviewed' },
        result: {
          ...prev.result,
          ...resp.result,
          status: 'reviewed',
          lecturer_decision: 'accepted',
          final_mark: automatedMark,
        },
      }));
      setSuccessMsg('✓ AI proposed mark accepted by lecturer. Ready for finalization.');
    } catch (err) {
      setError(err.message || 'Failed to accept AI mark.');
    } finally {
      setActionLoading(false);
    }
  };

  // Action: Open Override Modal
  const handleOpenOverride = () => {
    setOverrideError(null);
    setShowOverrideModal(true);
  };

  // Action: Submit Override
  const handleSubmitOverride = async (e) => {
    e.preventDefault();
    if (newMark === '' || isNaN(Number(newMark))) {
      setOverrideError('Please enter a valid numeric mark.');
      return;
    }
    const num = Number(newMark);
    if (num < 0 || num > totalPossible) {
      setOverrideError(`Mark must be between 0 and maximum possible marks (${totalPossible}).`);
      return;
    }
    if (!overrideReason.trim()) {
      setOverrideError('An override reason is required. Please provide academic justification.');
      return;
    }

    setActionLoading(true);
    setOverrideError(null);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await reviewSubmission(submission._id, {
        decision: 'overridden',
        new_mark: num,
        override_reason: overrideReason.trim(),
      });
      setData((prev) => ({
        ...prev,
        submission: { ...prev.submission, status: 'reviewed' },
        result: {
          ...prev.result,
          ...resp.result,
          status: 'reviewed',
          lecturer_decision: 'overridden',
          final_mark: num,
          override_reason: overrideReason.trim(),
        },
      }));
      setShowOverrideModal(false);
      setSuccessMsg(`✓ Mark successfully overridden to ${num} / ${totalPossible} with recorded reason.`);
    } catch (err) {
      setOverrideError(err.message || 'Failed to save mark override.');
    } finally {
      setActionLoading(false);
    }
  };

  // Action: Finalize Assessment
  const handleFinalize = async () => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const resp = await finalizeSubmission(submission._id);
      setData((prev) => ({
        ...prev,
        submission: { ...prev.submission, status: 'finalized' },
        result: {
          ...prev.result,
          ...resp.result,
          status: 'finalized',
        },
      }));
      setSuccessMsg('✓ Assessment successfully finalized! Official result is now archived.');
    } catch (err) {
      setError(err.message || 'Failed to finalize assessment.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="c3-page">
      {/* Navigation Breadcrumb */}
      <div>
        <Link to="/c3/review" className="btn-ghost" style={{ width: 'auto', padding: '4px 10px' }}>
          ← Back to Submissions Queue
        </Link>
      </div>

      {/* Top Header Lead */}
      <div className="c3-header-lead">
        <div>
          <h1>Assessment Review & Human-In-The-Loop Verification</h1>
          <p className="muted" style={{ margin: '4px 0 0' }}>
            Submission ID: {submission._id} • Student: {submission.student_id}
          </p>
        </div>
        <div>
          <span className={`c3-badge-status ${status}`} style={{ fontSize: '0.9rem', padding: '6px 16px' }}>
            {status === 'pending_review'
              ? '⏳ Status: AI Proposed (Pending Lecturer Review)'
              : status === 'reviewed'
              ? `🔍 Status: Lecturer Reviewed (${decision === 'accepted' ? 'Accepted' : 'Overridden'})`
              : '✓ Status: Finalized Assessment Result'}
          </span>
        </div>
      </div>

      {/* Status Messages */}
      {successMsg && (
        <div className="c3-alert-box" style={{ background: '#e6f7f2', border: '1px solid #82dec5', color: '#065543' }}>
          <span>✓</span>
          <div>{successMsg}</div>
        </div>
      )}
      {error && (
        <div className="c3-alert-box c3-alert-error">
          <span>⚠️</span>
          <div>
            <strong>Error:</strong> {error}
          </div>
        </div>
      )}

      {/* Lecturer Action Bar (Accept, Override, Finalize) */}
      <div className="c3-review-actions-bar">
        <div>
          <h4 style={{ margin: '0 0 4px' }}>Lecturer Assessment Controls</h4>
          <span className="small muted">
            {isFinalized
              ? 'This assessment has been finalized and archived.'
              : status === 'reviewed'
              ? 'Review decision recorded. You can finalize the official assessment result or adjust the override.'
              : 'Review the AI proposed mark and grounded evidence below, then Accept or Override.'}
          </span>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          {!isFinalized ? (
            <>
              <button
                type="button"
                className="c3-btn-accept"
                onClick={handleAcceptAiMark}
                disabled={actionLoading}
              >
                ✓ Accept AI Mark
              </button>
              <button
                type="button"
                className="c3-btn-override"
                onClick={handleOpenOverride}
                disabled={actionLoading}
              >
                ✏️ Override Mark
              </button>
              <button
                type="button"
                className="c3-btn-finalize"
                onClick={handleFinalize}
                disabled={actionLoading || (!decision && status !== 'reviewed')}
                title={!decision && status !== 'reviewed' ? 'Please Accept or Override before finalization' : ''}
              >
                🎓 Finalize Assessment Result
              </button>
            </>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="c3-badge-status finalized">✓ Official Result Finalized</span>
              <span className="small muted">
                (By {result?.reviewed_by || 'Lecturer'} on{' '}
                {result?.finalized_at ? new Date(result.finalized_at).toLocaleDateString() : '—'})
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Dual Marks Display: AI Proposed Mark vs Lecturer Final Mark */}
      <div className="c3-dual-marks-banner">
        {/* Tile 1: AI Proposed Mark */}
        <div className="c3-mark-tile ai-proposed">
          <div className="c3-mark-tile-title">AI Proposed Mark (Function 2)</div>
          <div className="c3-mark-tile-score" style={{ color: '#2b6cb0' }}>
            {automatedMark} <span style={{ fontSize: '1.2rem', color: 'var(--muted)' }}>/ {totalPossible}</span>
          </div>
          <div className="small muted">
            Calculated score: {percentage}% • Proposed from automated rubric evaluation
          </div>
        </div>

        {/* Tile 2: Lecturer Final Mark */}
        <div className="c3-mark-tile lecturer-final">
          <div className="c3-mark-tile-title">
            {isFinalized ? 'Final Assessment Result' : 'Lecturer Review Mark'}
          </div>
          <div className="c3-mark-tile-score" style={{ color: '#087a63' }}>
            {result?.final_mark !== null && result?.final_mark !== undefined ? (
              <>
                {result.final_mark}{' '}
                <span style={{ fontSize: '1.2rem', color: 'var(--muted)' }}>/ {totalPossible}</span>
              </>
            ) : (
              <span style={{ fontSize: '1.5rem', color: 'var(--muted)', fontWeight: 400 }}>
                Awaiting Lecturer Decision
              </span>
            )}
          </div>
          <div className="small muted">
            {decision ? (
              <span>
                Decision:{' '}
                <strong>{decision === 'accepted' ? 'Accepted AI Proposed Mark' : 'Overridden by Lecturer'}</strong>
                {result?.reviewed_by && ` by ${result.reviewed_by}`}
              </span>
            ) : (
              'Action required: Accept proposed mark or enter override with academic reason'
            )}
          </div>
        </div>
      </div>

      {/* Recorded Override Reason Notice if Overridden */}
      {decision === 'overridden' && (
        <div className="panel" style={{ borderLeft: '5px solid #c05621', background: '#fdfaf8' }}>
          <h4 style={{ margin: '0 0 6px', color: '#9c4215' }}>Recorded Override Reason (Mandatory Audit Trail)</h4>
          <p style={{ margin: 0, fontStyle: 'italic', fontSize: '0.95rem' }}>
            "{result?.override_reason || 'No reason specified'}"
          </p>
          <div className="small muted" style={{ marginTop: '8px' }}>
            Reviewed by: {result?.reviewed_by || 'Lecturer'} • Timestamp:{' '}
            {result?.reviewed_at ? new Date(result.reviewed_at).toLocaleString() : '—'}
          </div>
        </div>
      )}

      {/* =========================================================================
          SECTION 1: ASSESSMENT & QUESTION CONTEXT
         ========================================================================= */}
      <div className="panel">
        <h3>Assessment & Question Context</h3>
        <div className="c3-form-grid" style={{ marginTop: '12px' }}>
          <div>
            <strong>Question ID:</strong> {submission.question_id || 'SE-DB-001'}
          </div>
          <div>
            <strong>Answer Type:</strong> {submission.answer_type || 'Essay / Descriptive'}
          </div>
        </div>
        <div style={{ marginTop: '10px' }}>
          <strong>Question Text:</strong>
          <p style={{ margin: '4px 0 0', fontSize: '0.95rem', color: 'var(--text)' }}>
            {submission.question_text || 'Explain database normalization and describe 1NF, 2NF, and 3NF.'}
          </p>
        </div>
        {submission.reference_answer && (
          <div style={{ marginTop: '10px' }}>
            <strong>Model / Reference Answer:</strong>
            <p className="small muted" style={{ margin: '4px 0 0' }}>
              {submission.reference_answer}
            </p>
          </div>
        )}
      </div>

      {/* =========================================================================
          SECTION 2: ACTUAL STUDENT SUBMITTED ANSWER
         ========================================================================= */}
      <div className="panel" style={{ borderLeft: '5px solid var(--ink)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>Actual Student Submitted Answer</h3>
          <span className="small muted">
            Submitted:{' '}
            {submission.submitted_at ? new Date(submission.submitted_at).toLocaleString() : '—'}
          </span>
        </div>
        <div
          style={{
            background: '#f9fbfd',
            border: '1px solid var(--line)',
            borderRadius: '8px',
            padding: '16px',
            marginTop: '12px',
            whiteSpace: 'pre-wrap',
            fontFamily: 'inherit',
            lineHeight: 1.6,
            fontSize: '0.95rem',
          }}
        >
          {submission.student_answer || 'No answer text recorded.'}
        </div>
        <div className="small muted" style={{ marginTop: '8px' }}>
          Total sentences parsed by F1: {analysis?.sentences?.length || 0} • Word count:{' '}
          {submission.student_answer?.trim() ? submission.student_answer.trim().split(/\s+/).length : 0}
        </div>
      </div>

      {/* =========================================================================
          SECTION 3: CRITERION BREAKDOWN & GROUNDED EVIDENCE
         ========================================================================= */}
      <div>
        <h2>Criterion Breakdown & Grounded Sentence Evidence</h2>
        <p className="muted" style={{ margin: '0 0 16px' }}>
          Inspect the deterministic evidence and scoring descriptors assigned to each rubric criterion.
        </p>
        {marking?.criteria_results?.map((cr) => (
          <CriterionCard
            key={cr.criterion_id}
            criterionMarking={cr}
            criterionFeedback={feedbackByCriterionId.get(cr.criterion_id)}
            sentenceMap={sentenceMap}
          />
        ))}
      </div>

      {/* =========================================================================
          SECTION 4: CONCEPT ANALYSIS
         ========================================================================= */}
      <div>
        <h2>Concept Analysis & Knowledge Diagnosis</h2>
        <ConceptDiagnosis analysis={analysis} sentenceMap={sentenceMap} />
      </div>

      {/* =========================================================================
          SECTION 5: OVERALL FEEDBACK SYNTHESIS
         ========================================================================= */}
      {feedback?.overall_feedback && (
        <div className="panel c3-summary-card">
          <h3>Evidence-Grounded Feedback Synthesis</h3>
          <p className="c3-summary-text">{feedback.overall_feedback.overall_summary}</p>

          <div className="c3-summary-columns">
            {feedback.overall_feedback.overall_strengths?.length > 0 && (
              <div className="c3-summary-col">
                <h5 style={{ color: '#065543' }}>✓ Strengths Identified</h5>
                <ul>
                  {feedback.overall_feedback.overall_strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {feedback.overall_feedback.overall_missing_concepts?.length > 0 && (
              <div className="c3-summary-col">
                <h5 style={{ color: '#8a1f17' }}>○ Missing Concepts</h5>
                <ul>
                  {feedback.overall_feedback.overall_missing_concepts.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </div>
            )}

            {feedback.overall_feedback.overall_improvement_suggestions?.length > 0 && (
              <div className="c3-summary-col">
                <h5 style={{ color: '#1b4d75' }}>💡 Recommended Improvements</h5>
                <ul>
                  {feedback.overall_feedback.overall_improvement_suggestions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {feedback.overall_feedback.overall_next_level_improvements?.length > 0 && (
              <div className="c3-summary-col">
                <h5 style={{ color: '#5c2069' }}>🚀 Next-Level Goals</h5>
                <ul>
                  {feedback.overall_feedback.overall_next_level_improvements.map((nl, i) => (
                    <li key={i}>{nl}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================================================
          SECTION 6: CONCEPT-BASED MIND MAP
         ========================================================================= */}
      <div>
        <h2>Concept-Based Mind Map Representation (Function 4)</h2>
        <p className="muted" style={{ margin: '0 0 12px' }}>
          Inspect the structural relationships extracted by the automated pipeline before approving the mark.
        </p>
        <MindMapGraph mindmap={mindmap} sentences={analysis?.sentences || []} />
      </div>

      {/* =========================================================================
          OVERRIDE MODAL DIALOG
         ========================================================================= */}
      {showOverrideModal && (
        <div className="c3-modal-overlay">
          <div className="c3-modal-content">
            <div className="c3-modal-header">
              <h3>Override AI Proposed Mark</h3>
              <button
                type="button"
                className="btn-ghost"
                style={{ width: 'auto', padding: '4px 8px', fontSize: '1.2rem' }}
                onClick={() => setShowOverrideModal(false)}
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleSubmitOverride}>
              <div className="c3-modal-body">
                <div style={{ background: '#f7fafc', padding: '12px 16px', borderRadius: '8px' }}>
                  <strong>Original AI Proposed Mark:</strong> {automatedMark} / {totalPossible} ({percentage}%)
                </div>

                <div>
                  <label htmlFor="newM">
                    New Lecturer Mark <span style={{ color: '#d6453d' }}>*</span> (0 to {totalPossible})
                  </label>
                  <input
                    id="newM"
                    type="number"
                    step="0.5"
                    min="0"
                    max={totalPossible}
                    value={newMark}
                    onChange={(e) => setNewMark(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="ovReason">
                    Academic Override Reason <span style={{ color: '#d6453d' }}>*</span> (Required)
                  </label>
                  <textarea
                    id="ovReason"
                    className="c3-textarea"
                    rows="4"
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Provide clear pedagogical reasoning (e.g. 'The answer demonstrates understanding of 2NF full functional dependency, but phrasing differed from the lexical pattern.')..."
                    required
                  />
                  <span className="hint">
                    A non-empty reason is strictly required to preserve grading auditability.
                  </span>
                </div>

                {overrideError && (
                  <div className="c3-alert-box c3-alert-error" style={{ margin: 0 }}>
                    <span>⚠️</span>
                    <div>{overrideError}</div>
                  </div>
                )}
              </div>

              <div className="c3-modal-footer">
                <button
                  type="button"
                  className="btn secondary"
                  style={{ width: 'auto' }}
                  onClick={() => setShowOverrideModal(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="c3-btn-override" disabled={actionLoading}>
                  {actionLoading ? 'Saving...' : 'Save Override'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
