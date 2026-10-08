import { useState, useEffect } from 'react';
import { useNavigate, useParams, useOutletContext } from 'react-router-dom';
import { lecturerGetSubmission, lecturerAccept, lecturerOverride } from '../../../services/c3Api.js';
import '../../c3/C3.css';

function ConceptStatus({ status }) {
  if (status === 'demonstrated') return <span className="c3-status-demonstrated">✓ Demonstrated</span>;
  if (status === 'partial')      return <span className="c3-status-partial">◐ Partial</span>;
  return <span className="c3-status-not-demonstrated">○ Not Demonstrated</span>;
}

function CriterionPanel({ cr }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="c3-accordion">
      <div className="c3-accordion-header" onClick={() => setOpen(!open)}>
        <div className="c3-gap-3">
          <span style={{ fontWeight: 600, color: '#fff', fontSize: 15 }}>
            {cr.criterion_id}: {cr.criterion_description}
          </span>
          <span className="c3-badge c3-badge-essay" style={{ fontSize: 14 }}>
            {cr.awarded_mark} / {cr.max_marks}
          </span>
          <span className={`c3-badge ${cr.awarded_mark === cr.max_marks ? 'c3-badge-available' : cr.awarded_mark > 0 ? 'c3-badge-review' : 'c3-badge-failed'}`}>
            {cr.selected_level_label}
          </span>
        </div>
        <span style={{ color: 'var(--c3-muted)', fontSize: 18 }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className="c3-accordion-body">
          <div className="c3-bento" style={{ gap: 16, marginBottom: 0 }}>
            {/* Evidence */}
            <div className="c3-col-6">
              <div className="c3-label">Evidence Sentences</div>
              {cr.evidence_sentence_ids?.length > 0 ? (
                <div className="c3-evidence-box">
                  Evidence identified in sentences: {cr.evidence_sentence_ids.join(', ')}
                </div>
              ) : (
                <p className="c3-text-dim" style={{ margin: 0 }}>No specific evidence sentences identified.</p>
              )}
            </div>

            {/* Supporting concepts */}
            <div className="c3-col-6">
              <div className="c3-label">Supporting Concepts</div>
              {cr.supporting_concepts?.length > 0 ? (
                <div className="c3-gap-3" style={{ flexWrap: 'wrap' }}>
                  {cr.supporting_concepts.map((c, i) => (
                    <span key={i} className="c3-badge c3-badge-available">✓ {c}</span>
                  ))}
                </div>
              ) : (
                <p className="c3-text-dim" style={{ margin: 0 }}>No supporting concepts demonstrated.</p>
              )}
            </div>

            {/* Explanation */}
            <div className="c3-col-12">
              <div className="c3-label">Explanation</div>
              <p style={{ color: 'var(--c3-muted)', margin: 0, lineHeight: 1.75 }}>{cr.explanation}</p>
            </div>

            {/* Rubric descriptor */}
            {cr.rubric_descriptor && (
              <div className="c3-col-12">
                <div className="c3-label">Applied Rubric Descriptor</div>
                <p style={{ color: 'var(--c3-dim)', margin: 0, fontStyle: 'italic', fontSize: 13 }}>
                  "{cr.rubric_descriptor}"
                </p>
              </div>
            )}

            {/* Warnings */}
            {cr.warnings?.length > 0 && (
              <div className="c3-col-12">
                <div className="c3-alert c3-alert-warning" style={{ marginBottom: 0 }}>
                  <span>⚠</span>
                  <ul style={{ margin: 0, paddingLeft: 16 }}>
                    {cr.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function MindMapPanel({ mindmap }) {
  const [selected, setSelected] = useState(null);

  if (!mindmap?.nodes?.length) {
    return <p className="c3-text-dim">Mind map not available.</p>;
  }

  return (
    <div className="c3-mindmap-area">
      <div className="c3-mindmap-grid">
        {mindmap.nodes.map((node) => {
          const statusCls = (node.status || '').toLowerCase().replace(' ', '_');
          return (
            <div
              key={node.node_id}
              className={`c3-mindmap-node ${statusCls}`}
              onClick={() => setSelected(selected?.node_id === node.node_id ? null : node)}
              title={node.concept}
            >
              <div className="c3-node-label">{node.label}</div>
              <div className="c3-node-status">{node.status}</div>
            </div>
          );
        })}
      </div>

      {selected && (
        <div className="c3-card c3-mt-6" style={{ background: 'rgba(0,0,0,0.3)' }}>
          <div className="c3-between c3-mb-4">
            <strong>{selected.label}</strong>
            <button className="c3-btn c3-btn-ghost c3-btn-sm" onClick={() => setSelected(null)}>✕</button>
          </div>
          <div className="c3-gap-3 c3-mb-4">
            <span className="c3-badge c3-badge-essay">{selected.type}</span>
            <ConceptStatus status={selected.status} />
          </div>
          <div className="c3-label">Concept</div>
          <p className="c3-text-muted" style={{ margin: 0 }}>{selected.concept}</p>
          {selected.evidence_sentence_ids?.length > 0 && (
            <div className="c3-mt-4">
              <div className="c3-label">Evidence sentences</div>
              <p className="c3-text-muted" style={{ margin: 0 }}>
                Sentences {selected.evidence_sentence_ids.join(', ')}
              </p>
            </div>
          )}
        </div>
      )}

      {mindmap.summary && (
        <div className="c3-gap-4 c3-mt-4" style={{ justifyContent: 'flex-end' }}>
          <span className="c3-status-demonstrated">✓ {mindmap.summary.demonstrated_count} demonstrated</span>
          <span className="c3-status-partial">◐ {mindmap.summary.partial_count} partial</span>
          <span className="c3-status-not-demonstrated">○ {mindmap.summary.missing_count} missing</span>
        </div>
      )}
    </div>
  );
}

function PipelineStatus({ aiResult, isFailed }) {
  const steps = [
    { label: 'Answer Analysis', hasData: !!aiResult?.analysis?.student_word_count, desc: 'Processed raw text payload.' },
    { label: 'Semantic / Concept Analysis', hasData: !!aiResult?.analysis?.concept_matches?.length, desc: 'Mapped sentences to expected concepts.' },
    { label: 'Rubric Marking', hasData: !!aiResult?.marking?.criteria_results?.length, desc: 'Evaluated concepts against rubric rules.' },
    { label: 'Evidence', hasData: !!aiResult?.marking?.criteria_results?.[0]?.evidence_sentence_ids, desc: 'Linked exact sentences to criterion decisions.' },
    { label: 'Explainable Decision', hasData: !!aiResult?.marking?.overall_explanation, desc: 'Generated structured explanation.' },
    { label: 'Concept Diagnosis', hasData: !!aiResult?.analysis?.concept_matches, desc: 'Classified concepts as demonstrated/partial/missing.' },
    { label: 'Feedback', hasData: !!aiResult?.feedback?.overall_feedback, desc: 'Structured strengths & missing concepts.' },
    { label: 'Mind Map', hasData: !!aiResult?.mindmap?.nodes?.length, desc: 'Transformed concepts into graph representation.' }
  ];

  return (
    <div className="c3-card c3-mb-6">
      <div className="c3-section-title"><span className="c3-section-dot" />Pipeline Status</div>
      <div className="c3-pipeline-grid">
        {steps.map((s, i) => (
          <div key={i} className="c3-pipeline-step">
            <div className={`c3-pipeline-icon ${isFailed ? 'failed' : (s.hasData ? 'success' : 'pending')}`}>
               {isFailed ? '✗' : (s.hasData ? '✓' : '○')}
            </div>
            <div className="c3-pipeline-text">
               <div className="c3-pipeline-label">{s.label}</div>
               <div className="c3-pipeline-desc">{s.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function LecturerReview() {
  const { submissionId } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Decision state
  const [decision, setDecision] = useState(''); // '' | 'accept' | 'override'
  const [overrideMark, setOverrideMark] = useState('');
  const [overrideReason, setOverrideReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [finalized, setFinalized] = useState(null);

  useEffect(() => {
    setLoading(true);
    lecturerGetSubmission(submissionId)
      .then((res) => {
        setData(res);
        if (res.result?.status === 'finalized') setFinalized(res.result);
      })
      .catch((err) => setError(err.message || 'Failed to load submission'))
      .finally(() => setLoading(false));
  }, [submissionId]);

  const handleAccept = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await lecturerAccept(submissionId);
      const refreshed = await lecturerGetSubmission(submissionId);
      setData(refreshed);
      setFinalized(refreshed.result);
    } catch (err) {
      setSubmitError(err.message || 'Failed to finalize. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleOverrideSave = async () => {
    if (!overrideMark || isNaN(Number(overrideMark))) {
      setSubmitError('Please enter a valid revised mark.');
      return;
    }
    if (!overrideReason.trim()) {
      setSubmitError('Please provide an override reason.');
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      await lecturerOverride(submissionId, Number(overrideMark), overrideReason.trim());
      const refreshed = await lecturerGetSubmission(submissionId);
      setData(refreshed);
      setFinalized(refreshed.result);
    } catch (err) {
      setSubmitError(err.message || 'Override failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Loading
  if (loading) {
    return (
      <div className="c3-page c3-page-dark">
        <div className="c3-skeleton" style={{ height: 32, width: '40%', marginBottom: 24 }} />
        <div className="c3-bento">
          <div className="c3-col-8"><div className="c3-card"><div className="c3-skeleton" style={{ height: 200 }} /></div></div>
          <div className="c3-col-4"><div className="c3-card"><div className="c3-skeleton" style={{ height: 200 }} /></div></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="c3-page c3-page-dark">
        <div className="c3-alert c3-alert-error">{error}</div>
        <button className="c3-btn c3-btn-ghost" onClick={() => navigate('/lecturer/c3')}>← Back</button>
      </div>
    );
  }

  const { submission, result, assessment } = data;
  const ai = result?.ai_result || {};
  const marking = ai.marking || {};
  const analysis = ai.analysis || {};
  const feedback = ai.feedback || {};
  const mindmap  = ai.mindmap  || {};

  const aiMark   = marking.total_awarded_marks ?? '?';
  const maxMarks = marking.total_possible_marks ?? (assessment?.max_marks ?? 10);
  const isAlreadyFinalized = finalized || result?.status === 'finalized';
  const conceptMatches = analysis.concept_matches || [];

  if (submission.status === 'failed') {
    return (
      <div className="c3-page c3-page-dark">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
          <div>
            <button className="c3-btn c3-btn-ghost c3-btn-sm" onClick={() => navigate('/lecturer/c3')}>
              ← Submission Queue
            </button>
            <div className="c3-gap-3 c3-mt-4">
              <span className="c3-text-muted">Student:</span>
              <code style={{ color: '#93c5fd', fontWeight: 600 }}>{submission.student_id}</code>
              {assessment && (
                <>
                  <span className="c3-text-dim">|</span>
                  <span className="c3-text-muted">{assessment.title}</span>
                </>
              )}
            </div>
          </div>
          <span className="c3-badge c3-badge-failed">✗ AI Processing Failed</span>
        </div>
        <div className="c3-alert c3-alert-error">
          <h2 style={{ fontSize: 18, marginTop: 0 }}>Cannot Review Submission</h2>
          <p style={{ margin: 0 }}>The AI processing pipeline failed for this submission, therefore no results were generated.</p>
        </div>
        <div className="c3-card c3-mt-6">
          <div className="c3-section-title"><span className="c3-section-dot" />Student Answer</div>
          <div className="c3-answer-display">
            {submission.student_answer}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="c3-page c3-page-dark">
      {/* ── Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
        <div>
          <button className="c3-btn c3-btn-ghost c3-btn-sm" onClick={() => navigate('/lecturer/c3')}>
            ← Submission Queue
          </button>
          <div className="c3-gap-3 c3-mt-4">
            <span className="c3-text-muted">Student:</span>
            <code style={{ color: '#93c5fd', fontWeight: 600 }}>{submission.student_id}</code>
            {assessment && (
              <>
                <span className="c3-text-dim">|</span>
                <span className="c3-text-muted">{assessment.title}</span>
              </>
            )}
          </div>
        </div>
        <span className={`c3-badge ${isAlreadyFinalized ? 'c3-badge-finalized' : 'c3-badge-review'}`}>
          {isAlreadyFinalized ? '✓ Finalized' : '◐ Awaiting Review'}
        </span>
      </div>

      {/* ── Already finalized banner */}
      {isAlreadyFinalized && (
        <div className="c3-alert c3-alert-info c3-mb-6">
          <span>✓</span>
          <div>
            This submission has been finalized.
            Decision: <strong>{finalized?.lecturer_decision}</strong>.
            Final mark: <strong>{finalized?.final_mark} / {maxMarks}</strong>.
            {finalized?.override_reason && (
              <> Override reason: <em>{finalized.override_reason}</em></>
            )}
          </div>
        </div>
      )}

      <div className="c3-bento">
        {/* ── LEFT: Main review area */}
        <div className="c3-col-8" style={{ paddingRight: 32 }}>
          {/* Pipeline Status */}
          <div className="c3-flat-section">
            <PipelineStatus aiResult={ai} isFailed={false} />
          </div>

          <hr className="c3-divider-strong" style={{ marginTop: 0 }} />

          {/* Student Answer */}
          <div className="c3-flat-section">
            <div className="c3-section-title large"><span className="c3-section-dot" />Student Answer</div>
            <div className="c3-answer-flat">
              {submission.student_answer}
            </div>
            <div className="c3-word-count">
              {submission.student_answer?.trim().split(/\s+/).length ?? 0} words ·
              Submitted {new Date(submission.submitted_at).toLocaleString()}
            </div>
          </div>

          <hr className="c3-divider-strong" />

          {/* Criterion Evaluation */}
          {marking.criteria_results?.length > 0 && (
            <div className="c3-flat-section">
              <div className="c3-between c3-mb-4">
                <div className="c3-section-title large" style={{ margin: 0 }}>
                  <span className="c3-section-dot" />Criterion Evaluation
                </div>
                <span className="c3-text-muted">Evidence-based review</span>
              </div>
              <div className="c3-stack" style={{ gap: 16 }}>
                {marking.criteria_results.map((cr, i) => (
                  <CriterionPanel key={i} cr={cr} />
                ))}
              </div>
              {marking.overall_explanation && (
                <div className="c3-mt-6" style={{ background: 'rgba(59, 130, 246, 0.05)', padding: 20, borderRadius: 12, border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                  <div className="c3-label" style={{ color: 'var(--c3-primary)' }}>Overall Explanation</div>
                  <p style={{ color: 'var(--c3-muted)', margin: 0, lineHeight: 1.75 }}>
                    {marking.overall_explanation}
                  </p>
                </div>
              )}
            </div>
          )}

          <hr className="c3-divider-strong" />

          {/* Concept Analysis */}
          {conceptMatches.length > 0 && (
            <div className="c3-flat-section">
              <div className="c3-section-title large"><span className="c3-section-dot" />Concept Analysis</div>
              <div className="c3-concept-grid">
                {conceptMatches.map((c, i) => {
                  const statusCls = c.status === 'demonstrated' ? 'demonstrated' : c.status === 'partial' ? 'partial' : 'not_demonstrated';
                  return (
                    <div key={i} className={`c3-concept-chip ${statusCls}`}>
                      <div className="c3-concept-name">{c.concept}</div>
                      <div><ConceptStatus status={c.status} /></div>
                      {c.evidence_sentence_ids?.length > 0 && (
                        <div style={{ fontSize: 11, color: 'var(--c3-dim)', marginTop: 2 }}>
                          Evidence: sentences {c.evidence_sentence_ids.join(', ')}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <hr className="c3-divider-strong" />

          {/* Feedback */}
          {feedback.overall_feedback && (
            <div className="c3-flat-section">
              <div className="c3-section-title large"><span className="c3-section-dot" />AI-Generated Feedback</div>
              <div className="c3-bento">
                {feedback.overall_feedback.overall_strengths?.length > 0 && (
                  <div className="c3-col-6">
                    <div className="c3-label" style={{ color: 'var(--c3-success)' }}>Strengths</div>
                    <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--c3-muted)', lineHeight: 1.8 }}>
                      {feedback.overall_feedback.overall_strengths.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
                {feedback.overall_feedback.overall_missing_concepts?.length > 0 && (
                  <div className="c3-col-6">
                    <div className="c3-label" style={{ color: 'var(--c3-warning)' }}>Missing Concepts</div>
                    <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--c3-muted)', lineHeight: 1.8 }}>
                      {feedback.overall_feedback.overall_missing_concepts.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                )}
                {feedback.overall_feedback.overall_improvement_suggestions?.length > 0 && (
                  <div className="c3-col-12 c3-mt-4">
                    <div className="c3-label" style={{ color: 'var(--c3-primary)' }}>Improvement Suggestions</div>
                    <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--c3-muted)', lineHeight: 1.8 }}>
                      {feedback.overall_feedback.overall_improvement_suggestions.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <hr className="c3-divider-strong" />

          {/* Mind Map */}
          <div className="c3-flat-section">
            <div className="c3-between c3-mb-4">
              <div className="c3-section-title large" style={{ margin: 0 }}>
                <span className="c3-section-dot" />Concept Mind Map
              </div>
              {mindmap.title && <span className="c3-text-muted">{mindmap.title}</span>}
            </div>
            <MindMapPanel mindmap={mindmap} />
          </div>
        </div>

        {/* ── RIGHT: Decision panel */}
        <div className="c3-col-4">
          {/* AI mark summary */}
          <div className="c3-card-metric c3-mb-4" style={{ borderRadius: 14 }}>
            <div className="c3-label">AI Suggested Mark</div>
            <div className="c3-result-mark-big">
              {aiMark}
              <span className="c3-result-mark-denom"> / {maxMarks}</span>
            </div>
            {marking.percentage !== undefined && (
              <div className="c3-metric-sub">{Math.round(marking.percentage)}% score</div>
            )}
          </div>

          {/* Decision panel */}
          {!isAlreadyFinalized ? (
            <div className="c3-decision-panel">
              <div className="c3-section-title" style={{ marginBottom: 20 }}>
                <span className="c3-section-dot" />Lecturer Decision
              </div>

              {submitError && (
                <div className="c3-alert c3-alert-error c3-mb-4" style={{ marginTop: 0 }}>
                  <span>⚠</span> <span>{submitError}</span>
                </div>
              )}

              {/* Choice buttons */}
              {decision === '' && (
                <div className="c3-stack">
                  <button
                    className="c3-btn c3-btn-success"
                    style={{ justifyContent: 'center' }}
                    onClick={() => setDecision('accept')}
                    disabled={submitting}
                  >
                    ✓ Accept AI Mark
                  </button>
                  <button
                    className="c3-btn c3-btn-danger"
                    style={{ justifyContent: 'center' }}
                    onClick={() => setDecision('override')}
                    disabled={submitting}
                  >
                    ✎ Override AI Mark
                  </button>
                </div>
              )}

              {/* Accept confirmation */}
              {decision === 'accept' && (
                <div className="c3-stack">
                  <div className="c3-alert c3-alert-info" style={{ marginBottom: 0 }}>
                    <span>ℹ</span>
                    <span>
                      You are accepting the AI mark of <strong>{aiMark} / {maxMarks}</strong>.
                      This will be recorded as the final mark.
                    </span>
                  </div>
                  <div className="c3-gap-3 c3-mt-4">
                    <button
                      className="c3-btn c3-btn-success"
                      onClick={handleAccept}
                      disabled={submitting}
                    >
                      {submitting ? 'Finalizing…' : 'Confirm & Finalize'}
                    </button>
                    <button
                      className="c3-btn c3-btn-ghost"
                      onClick={() => setDecision('')}
                      disabled={submitting}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Override form */}
              {decision === 'override' && (
                <div className="c3-stack">
                  <div>
                    <label className="c3-label" htmlFor="override-mark">Revised Mark (0 – {maxMarks})</label>
                    <input
                      id="override-mark"
                      type="number"
                      className="c3-input"
                      value={overrideMark}
                      onChange={(e) => setOverrideMark(e.target.value)}
                      min={0}
                      max={maxMarks}
                      step={0.5}
                      placeholder={`0 – ${maxMarks}`}
                    />
                  </div>
                  <div>
                    <label className="c3-label" htmlFor="override-reason">Override Reason</label>
                    <textarea
                      id="override-reason"
                      className="c3-textarea"
                      rows={4}
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      placeholder="Explain why the AI mark was changed..."
                    />
                    <div className="c3-alert c3-alert-warning c3-mt-4" style={{ marginBottom: 0 }}>
                      <span>⚠</span>
                      <span style={{ fontSize: 12 }}>
                        The original AI mark ({aiMark}/{maxMarks}) is preserved for audit.
                        Both marks will be stored.
                      </span>
                    </div>
                  </div>
                  <div className="c3-gap-3 c3-mt-4">
                    <button
                      className="c3-btn c3-btn-danger"
                      onClick={handleOverrideSave}
                      disabled={submitting}
                    >
                      {submitting ? 'Saving…' : 'Save Override & Finalize'}
                    </button>
                    <button
                      className="c3-btn c3-btn-ghost"
                      onClick={() => { setDecision(''); setOverrideMark(''); setOverrideReason(''); setSubmitError(null); }}
                      disabled={submitting}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="c3-decision-panel">
              <div className="c3-section-title c3-mb-4">
                <span className="c3-section-dot" style={{ background: '#34d399' }} />Finalized
              </div>
              <div className="c3-stack">
                <div>
                  <div className="c3-label">Decision</div>
                  <div style={{ fontWeight: 600, color: '#fff', textTransform: 'capitalize' }}>
                    {finalized?.lecturer_decision}
                  </div>
                </div>
                <div>
                  <div className="c3-label">Final Mark</div>
                  <div style={{ fontWeight: 700, color: '#34d399', fontSize: 24 }}>
                    {finalized?.final_mark} / {maxMarks}
                  </div>
                </div>
                {finalized?.override_reason && (
                  <div>
                    <div className="c3-label">Override Reason</div>
                    <p style={{ color: 'var(--c3-muted)', margin: 0, fontStyle: 'italic', fontSize: 13 }}>
                      {finalized.override_reason}
                    </p>
                  </div>
                )}
                <div>
                  <div className="c3-label">Finalized At</div>
                  <div className="c3-text-dim">{new Date(finalized?.finalized_at).toLocaleString()}</div>
                </div>
              </div>
              <button
                className="c3-btn c3-btn-ghost c3-mt-6"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => navigate('/lecturer/c3')}
              >
                ← Back to Queue
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
