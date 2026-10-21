import React from 'react';

/**
 * Criterion Evaluation Card
 * Displays criterion marks, selected scoring level, explanation, evidence, and actionable feedback.
 */
export default function CriterionCard({ criterionMarking, criterionFeedback, sentenceMap }) {
  if (!criterionMarking) return null;

  const {
    criterion_id,
    criterion_description,
    selected_level_id,
    selected_level_label,
    rubric_descriptor,
    awarded_mark,
    max_marks,
    evidence_sentence_ids,
    supporting_concepts,
    explanation,
    warnings,
  } = criterionMarking;

  const feedback = criterionFeedback || {};
  const {
    demonstrated_concepts = [],
    partial_concepts = [],
    missing_concepts = [],
    strengths = [],
    missing_or_partial_areas = [],
    improvement_suggestions = [],
    next_level_improvements = [],
  } = feedback;

  const scorePercentage = Math.round((awarded_mark / max_marks) * 100);
  const isFullCredit = awarded_mark === max_marks;
  const isZeroCredit = awarded_mark === 0;

  return (
    <div className="panel c3-criterion-card">
      {/* Header */}
      <div className="c3-criterion-head">
        <div>
          <div className="c3-criterion-tag">
            <span>{criterion_id}</span>
            <span className="muted">•</span>
            <span>Max: {max_marks} marks</span>
          </div>
          <h3 className="c3-criterion-title">{criterion_description}</h3>
        </div>

        {/* Score & Level Badges */}
        <div className="c3-score-box">
          <div className="c3-score-value">
            <span className="c3-mark-num">{awarded_mark}</span>
            <span className="c3-mark-denom">/{max_marks}</span>
          </div>
          <span
            className={`badge ${
              isFullCredit ? 'risk-low' : isZeroCredit ? 'risk-high' : 'risk-medium'
            }`}
          >
            {scorePercentage}% • {selected_level_label || selected_level_id}
          </span>
        </div>
      </div>

      {/* Selected Level Descriptor */}
      <div className="c3-level-descriptor">
        <span className="c3-descriptor-label">Selected Level ({selected_level_id}):</span>
        <p className="c3-descriptor-text">{rubric_descriptor}</p>
      </div>

      {/* Grounded Evidence Section */}
      <div className="c3-evidence-section">
        <strong>Sentence Evidence:</strong>
        {evidence_sentence_ids && evidence_sentence_ids.length > 0 ? (
          <div className="c3-evidence-list">
            {evidence_sentence_ids.map((sid) => (
              <div key={sid} className="c3-evidence-item">
                <span className="c3-sentence-tag">Sentence {sid}</span>
                <span className="c3-sentence-quote">
                  &ldquo;{sentenceMap?.get(sid) || `Sentence ${sid} text`}&rdquo;
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            No sentence-level evidence detected in student answer for this criterion.
          </p>
        )}
      </div>

      {/* Concept Breakdown */}
      <div className="c3-concept-pills-row">
        {demonstrated_concepts.map((c) => (
          <span key={c} className="c3-concept-pill demonstrated">
            ✓ {c}
          </span>
        ))}
        {partial_concepts.map((c) => (
          <span key={c} className="c3-concept-pill partial">
            △ {c}
          </span>
        ))}
        {missing_concepts.map((c) => (
          <span key={c} className="c3-concept-pill missing">
            ○ {c}
          </span>
        ))}
      </div>

      {/* Explanation */}
      {explanation && (
        <div className="c3-explanation-box">
          <strong>Marking Explanation:</strong>
          <p>{explanation}</p>
        </div>
      )}

      {/* Strengths & Actionable Suggestions Grid */}
      <div className="c3-feedback-grid">
        {strengths.length > 0 && (
          <div className="c3-feedback-col strengths">
            <h5>Key Strengths</h5>
            <ul>
              {strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        )}

        {missing_or_partial_areas.length > 0 && (
          <div className="c3-feedback-col gaps">
            <h5>Areas Needing Attention</h5>
            <ul>
              {missing_or_partial_areas.map((area, i) => (
                <li key={i}>{area}</li>
              ))}
            </ul>
          </div>
        )}

        {improvement_suggestions.length > 0 && (
          <div className="c3-feedback-col suggestions">
            <h5>Improvement Suggestions</h5>
            <ul>
              {improvement_suggestions.map((sug, i) => (
                <li key={i}>{sug}</li>
              ))}
            </ul>
          </div>
        )}

        {next_level_improvements.length > 0 && (
          <div className="c3-feedback-col next-level">
            <h5>Next-Level Criteria to Target</h5>
            <ul>
              {next_level_improvements.map((nl, i) => (
                <li key={i}>{nl}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="c3-criterion-warnings">
          {warnings.map((w, idx) => (
            <div key={idx} className="small muted">
              ⚠️ {w}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
