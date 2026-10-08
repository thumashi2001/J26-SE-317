import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getResult } from '../../services/c3Api.js';
import '../c3/C3.css';

function ConceptStatus({ status }) {
  if (status === 'demonstrated') return <span className="c3-status-demonstrated">✓ Demonstrated</span>;
  if (status === 'partial')      return <span className="c3-status-partial">◐ Partial</span>;
  return <span className="c3-status-not-demonstrated">○ Not Demonstrated</span>;
}

function CriterionAccordion({ cr, rubricCriteria }) {
  const [open, setOpen] = useState(false);
  const rubricC = rubricCriteria?.find(c => c.criterion_id === cr.criterion_id);
  const maxMarks = rubricC?.max_marks ?? cr.max_marks ?? '?';

  return (
    <div className="c3-accordion">
      <div className="c3-accordion-header" onClick={() => setOpen(!open)}>
        <div className="c3-gap-3">
          <span style={{ fontWeight: 600, color: '#fff' }}>{cr.criterion_id}: {cr.criterion_description}</span>
          <span className="c3-badge c3-badge-essay">{cr.awarded_mark} / {maxMarks}</span>
          <span className={`c3-badge ${cr.selected_level_label?.toLowerCase() === 'demonstrated' ? 'c3-badge-available' : 'c3-badge-review'}`}>
            {cr.selected_level_label}
          </span>
        </div>
        <span style={{ color: 'var(--c3-muted)', fontSize: 18 }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div className="c3-accordion-body">
          {cr.evidence_sentence_ids?.length > 0 && (
            <div className="c3-mb-4">
              <div className="c3-label">Evidence Sentences</div>
              <div className="c3-evidence-box">
                Evidence from sentences: {cr.evidence_sentence_ids.join(', ')}
              </div>
            </div>
          )}

          {cr.supporting_concepts?.length > 0 && (
            <div className="c3-mb-4">
              <div className="c3-label">Supporting Concepts</div>
              <div className="c3-gap-3">
                {cr.supporting_concepts.map((c, i) => (
                  <span key={i} className="c3-badge c3-badge-available">✓ {c}</span>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="c3-label">Explanation</div>
            <p className="c3-text-muted" style={{ margin: 0, lineHeight: 1.7 }}>{cr.explanation}</p>
          </div>

          {cr.rubric_descriptor && (
            <div className="c3-mt-4">
              <div className="c3-label">Rubric Descriptor</div>
              <p className="c3-text-dim" style={{ margin: 0, fontStyle: 'italic' }}>{cr.rubric_descriptor}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MindMapVisual({ mindmap }) {
  const [selectedNode, setSelectedNode] = useState(null);

  if (!mindmap?.nodes?.length) {
    return <p className="c3-text-dim">Mind map data is not available.</p>;
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
              onClick={() => setSelectedNode(selectedNode?.node_id === node.node_id ? null : node)}
              title={node.concept}
            >
              <div className="c3-node-label">{node.label}</div>
              <div className="c3-node-status">{node.status || '—'}</div>
              {node.parent_node_id && (
                <div style={{ fontSize: 10, color: 'var(--c3-dim)', marginTop: 2 }}>
                  → {node.parent_node_id}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedNode && (
        <div className="c3-card c3-mt-6" style={{ background: 'rgba(0,0,0,0.3)' }}>
          <div className="c3-between c3-mb-4">
            <div className="c3-section-title" style={{ margin: 0 }}>{selectedNode.label}</div>
            <button className="c3-btn c3-btn-ghost c3-btn-sm" onClick={() => setSelectedNode(null)}>✕</button>
          </div>
          <div className="c3-gap-3 c3-mb-4">
            <span className="c3-badge c3-badge-essay">{selectedNode.type}</span>
            <ConceptStatus status={selectedNode.status} />
          </div>
          <div className="c3-label">Concept</div>
          <p className="c3-text-muted" style={{ margin: 0 }}>{selectedNode.concept}</p>
          {selectedNode.evidence_sentence_ids?.length > 0 && (
            <div className="c3-mt-4">
              <div className="c3-label">Evidence sentences</div>
              <p className="c3-text-muted" style={{ margin: 0 }}>
                Sentences: {selectedNode.evidence_sentence_ids.join(', ')}
              </p>
            </div>
          )}
        </div>
      )}

      {mindmap.summary && (
        <div className="c3-gap-4" style={{ marginTop: 16, justifyContent: 'flex-end' }}>
          <span className="c3-text-dim">Total nodes: {mindmap.summary.total_nodes}</span>
          <span className="c3-status-demonstrated">✓ {mindmap.summary.demonstrated_count} demonstrated</span>
          <span className="c3-status-partial">◐ {mindmap.summary.partial_count} partial</span>
          <span className="c3-status-not-demonstrated">○ {mindmap.summary.missing_count} missing</span>
        </div>
      )}
    </div>
  );
}

export default function StudentResult() {
  const { id: submissionId } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    getResult(submissionId)
      .then((res) => setData(res))
      .catch((err) => setError(err.message || 'Failed to load result'))
      .finally(() => setLoading(false));
  }, [submissionId]);

  if (loading) {
    return (
      <div className="c3-page c3-page-dark">
        <div className="c3-skeleton" style={{ height: 32, width: '35%', marginBottom: 24 }} />
        <div className="c3-bento">
          {[0,1,2].map(i => (
            <div key={i} className="c3-col-4">
              <div className="c3-card-metric">
                <div className="c3-skeleton" style={{ height: 48, width: 80, marginBottom: 8 }} />
                <div className="c3-skeleton" style={{ height: 14, width: 100 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="c3-page c3-page-dark">
        <div className="c3-alert c3-alert-error">{error}</div>
        <button className="c3-btn c3-btn-ghost" onClick={() => navigate('/c3')}>← Back</button>
      </div>
    );
  }

  const { submission, result } = data || {};

  if (submission?.status === 'failed') {
    return (
      <div className="c3-page c3-page-dark">
        <div className="c3-header-row c3-mb-6">
          <div>
            <button className="c3-btn c3-btn-ghost c3-btn-sm c3-mb-4" onClick={() => navigate('/c3')}>
              ← My Assessments
            </button>
            <h1 className="c3-page-title">Assessment Result</h1>
          </div>
          <span className="c3-badge c3-badge-failed">✗ AI Processing Failed</span>
        </div>
        <div className="c3-alert c3-alert-error">
          <h2 style={{ fontSize: 18, marginTop: 0 }}>Processing Failed</h2>
          <p style={{ margin: 0 }}>The AI processing pipeline failed for this submission, therefore no results were generated. Please try submitting again later.</p>
        </div>
        <div className="c3-card c3-mt-6">
          <div className="c3-section-title"><span className="c3-section-dot" />Your Answer</div>
          <div className="c3-answer-display">
            {submission.student_answer}
          </div>
        </div>
      </div>
    );
  }

  const ai = result?.ai_result || {};
  const marking = ai.marking || {};
  const analysis = ai.analysis || {};
  const feedback = ai.feedback || {};
  const mindmap  = ai.mindmap  || {};

  const isFinalized = result?.status === 'finalized';
  const aiMark   = marking.total_awarded_marks ?? 0;
  const maxMarks = marking.total_possible_marks ?? 10;
  const finalMark = result?.final_mark;
  const pct = Math.round((aiMark / maxMarks) * 100);
  const conceptMatches = analysis.concept_matches || [];
  const demonstratedCount = conceptMatches.filter(c => c.status === 'demonstrated').length;

  return (
    <div className="c3-page c3-page-dark">
      {/* Header */}
      <div className="c3-header-row">
        <div>
          <button className="c3-btn c3-btn-ghost c3-btn-sm c3-mb-4" onClick={() => navigate('/c3')}>
            ← My Assessments
          </button>
          <h1 className="c3-page-title">Assessment Result</h1>
          <p className="c3-page-subtitle">
            {isFinalized ? 'Finalized by Lecturer' : 'AI Assessment Complete — Awaiting Lecturer Review'}
          </p>
        </div>
        <span
          className={`c3-result-status-pill ${isFinalized ? 'finalized' : 'awaiting'}`}
        >
          {isFinalized ? '✓ Finalized' : '◐ Awaiting Review'}
        </span>
      </div>

      {/* ── Summary metrics */}
      <div className="c3-bento c3-mb-6">
        <div className="c3-col-4">
          <div className="c3-card-metric">
            <div className="c3-label">
              {isFinalized && result.lecturer_decision === 'overridden' ? 'AI Suggested Mark' : 'AI Suggested Mark'}
            </div>
            <div className="c3-result-mark-big">
              {aiMark}
              <span className="c3-result-mark-denom"> / {maxMarks}</span>
            </div>
            {!isFinalized && (
              <div className="c3-metric-sub">Pending lecturer review</div>
            )}
          </div>
        </div>

        {isFinalized && (
          <div className="c3-col-4">
            <div className="c3-card-metric">
              <div className="c3-label">Final Mark</div>
              <div className="c3-result-mark-big" style={{ color: '#34d399' }}>
                {finalMark}
                <span className="c3-result-mark-denom"> / {maxMarks}</span>
              </div>
              {result.lecturer_decision === 'overridden' && result.override_reason && (
                <div className="c3-metric-sub" style={{ marginTop: 8 }}>
                  Revised by lecturer
                </div>
              )}
            </div>
          </div>
        )}

        <div className="c3-col-4">
          <div className="c3-card-metric">
            <div className="c3-label">Concept Coverage</div>
            <div className="c3-result-mark-big" style={{ color: '#c4b5fd' }}>
              {pct}%
            </div>
            <div className="c3-metric-sub">{demonstratedCount} of {conceptMatches.length} concepts</div>
          </div>
        </div>

        {!isFinalized && (
          <div className="c3-col-4">
            <div className="c3-card-metric">
              <div className="c3-label">Concepts Demonstrated</div>
              <div className="c3-result-mark-big">
                {demonstratedCount}
                <span className="c3-result-mark-denom"> / {conceptMatches.length}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Override notice */}
      {isFinalized && result.lecturer_decision === 'overridden' && (
        <div className="c3-alert c3-alert-info c3-mb-6">
          <span>ℹ</span>
          <div>
            <strong>Lecturer override applied.</strong> The lecturer adjusted the AI suggested mark.
            {result.override_reason && (
              <> Reason: <em>{result.override_reason}</em></>
            )}
          </div>
        </div>
      )}

      {/* ── Overall explanation */}
      {marking.overall_explanation && (
        <div className="c3-card c3-mb-6">
          <div className="c3-section-title"><span className="c3-section-dot" />Why did I get this mark?</div>
          <p style={{ color: 'var(--c3-muted)', lineHeight: 1.8, margin: 0 }}>
            {marking.overall_explanation}
          </p>
        </div>
      )}

      {/* ── Criterion breakdown */}
      {marking.criteria_results?.length > 0 && (
        <div className="c3-card c3-mb-6">
          <div className="c3-section-title"><span className="c3-section-dot" />Criterion Breakdown</div>
          {marking.criteria_results.map((cr, i) => (
            <CriterionAccordion key={i} cr={cr} rubricCriteria={[]} />
          ))}
        </div>
      )}

      {/* ── Concept analysis */}
      {conceptMatches.length > 0 && (
        <div className="c3-card c3-mb-6">
          <div className="c3-section-title"><span className="c3-section-dot" />Concept Analysis</div>
          <div className="c3-concept-grid">
            {conceptMatches.map((c, i) => {
              const statusCls = c.status === 'demonstrated' ? 'demonstrated' : c.status === 'partial' ? 'partial' : 'not_demonstrated';
              return (
                <div key={i} className={`c3-concept-chip ${statusCls}`}>
                  <div className="c3-concept-name">{c.concept}</div>
                  <div className="c3-concept-status-label"><ConceptStatus status={c.status} /></div>
                  {c.overlap_score !== undefined && (
                    <div style={{ fontSize: 11, color: 'var(--c3-dim)', marginTop: 2 }}>
                      Overlap: {Math.round(c.overlap_score * 100)}%
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Feedback */}
      {feedback.overall_feedback && (
        <div className="c3-bento c3-mb-6">
          {feedback.overall_feedback.overall_strengths?.length > 0 && (
            <div className="c3-col-4">
              <div className="c3-card">
                <div className="c3-section-title" style={{ color: '#34d399' }}>
                  <span className="c3-section-dot" style={{ background: '#34d399' }} /> Strengths
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--c3-muted)', lineHeight: 1.8 }}>
                  {feedback.overall_feedback.overall_strengths.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            </div>
          )}
          {feedback.overall_feedback.overall_missing_concepts?.length > 0 && (
            <div className="c3-col-4">
              <div className="c3-card">
                <div className="c3-section-title" style={{ color: '#fbbf24' }}>
                  <span className="c3-section-dot" style={{ background: '#fbbf24' }} /> Missing Concepts
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--c3-muted)', lineHeight: 1.8 }}>
                  {feedback.overall_feedback.overall_missing_concepts.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            </div>
          )}
          {feedback.overall_feedback.overall_improvement_suggestions?.length > 0 && (
            <div className="c3-col-4">
              <div className="c3-card">
                <div className="c3-section-title" style={{ color: '#a78bfa' }}>
                  <span className="c3-section-dot" style={{ background: '#a78bfa' }} /> How to Improve
                </div>
                <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--c3-muted)', lineHeight: 1.8 }}>
                  {feedback.overall_feedback.overall_improvement_suggestions.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Mind map */}
      <div className="c3-card c3-mb-6">
        <div className="c3-between c3-mb-4">
          <div className="c3-section-title" style={{ margin: 0 }}>
            <span className="c3-section-dot" /> Concept Mind Map
          </div>
          {mindmap.title && <span className="c3-text-muted">{mindmap.title}</span>}
        </div>
        <MindMapVisual mindmap={mindmap} />
      </div>

      {/* ── Audit disclaimer */}
      <div className="c3-alert c3-alert-info">
        <span>ℹ</span>
        <span>
          {isFinalized
            ? `This result was finalized by a lecturer on ${new Date(result.finalized_at).toLocaleString()}.`
            : 'This is an AI-generated assessment result. It is awaiting lecturer review. The lecturer has final academic authority over your mark.'}
        </span>
      </div>
    </div>
  );
}
