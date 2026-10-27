import React from 'react';

// Feedback lists shown under a criterion: [key in the feedback object, heading, CSS class]. Empty lists are hidden.
const LIST_BLOCKS = [
  ['strengths', 'Strengths', 'strengths'],
  ['missing_or_partial_areas', 'Needs attention', 'gaps'],
  ['improvement_suggestions', 'How to improve', 'suggestions'],
  ['next_level_improvements', 'To reach the next level', 'next-level'],
];

// One rubric criterion: mark, the level that was selected, the answer sentences used as evidence, and feedback.
export default function CriterionCard({ criterionMarking, criterionFeedback, sentenceMap, showEvidence = true }) {
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
    explanation,
    warnings,
  } = criterionMarking;
  const fb = criterionFeedback || {};
  // Percentage of this criterion's marks earned, and the colour of the pill: full marks green, zero red, otherwise amber.
  const pct = max_marks > 0 ? Math.round((awarded_mark / max_marks) * 100) : 0;
  const tone = awarded_mark === max_marks ? 'status-approved' : awarded_mark === 0 ? 'status-rejected' : 'status-pending';
  // One list of concept chips (demonstrated / partial / missing) built from the feedback for this criterion.
  const concepts = [
    ...(fb.demonstrated_concepts || []).map((c) => ({ c, kind: 'demonstrated', label: 'Demonstrated' })),
    ...(fb.partial_concepts || []).map((c) => ({ c, kind: 'partial', label: 'Partial' })),
    ...(fb.missing_concepts || []).map((c) => ({ c, kind: 'missing', label: 'Missing' })),
  ];

  return (
    <section className="panel c3-criterion-card" aria-label={`Criterion ${criterion_id}`}>
      <div className="c3-criterion-head">
        <div>
          <div className="c3-criterion-tag">
            <span>{criterion_id}</span>
            <span className="muted">out of {max_marks} marks</span>
          </div>
          <h3 className="c3-criterion-title">{criterion_description}</h3>
        </div>
        <div className="c3-score-box">
          <div className="c3-score-value">
            <span className="c3-mark-num">{awarded_mark}</span>
            <span className="c3-mark-denom">/{max_marks}</span>
          </div>
          <span className={`pill ${tone}`}>
            {pct}% · {selected_level_label || selected_level_id}
          </span>
        </div>
      </div>

      {/* The rubric level that was selected, quoted from the rubric itself */}
      {rubric_descriptor && (
        <div className="c3-level-descriptor">
          <span className="c3-descriptor-label">Rubric level reached ({selected_level_id})</span>
          <p className="c3-descriptor-text">{rubric_descriptor}</p>
        </div>
      )}

      {/* Answer sentences used as evidence (hidden for multiple choice, which has no written evidence) */}
      {showEvidence && (
      <div className="c3-evidence-section">
        <strong>Evidence in the answer</strong>
        {evidence_sentence_ids && evidence_sentence_ids.length > 0 ? (
          <div className="c3-evidence-list">
            {evidence_sentence_ids.map((sid) => (
              <div key={sid} className="c3-evidence-item">
                <span className="c3-sentence-tag">Sentence {sid}</span>
                <span className="c3-sentence-quote">&ldquo;{sentenceMap?.get(sid) || ''}&rdquo;</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="small muted" style={{ margin: '4px 0 0' }}>
            No sentence in the answer matched this criterion.
          </p>
        )}
      </div>
      )}

      {concepts.length > 0 && (
        <ul className="c3-concept-pills-row" aria-label="Concepts for this criterion">
          {concepts.map(({ c, kind, label }) => (
            <li key={`${kind}-${c}`} className={`c3-concept-pill ${kind}`}>
              <span className="c3-sr">{label}: </span>
              {c}
            </li>
          ))}
        </ul>
      )}

      {/* Plain-English reason for the mark */}
      {explanation && (
        <div className="c3-explanation-box">
          <strong>Why this mark</strong>
          <p>{explanation}</p>
        </div>
      )}

      <div className="c3-feedback-grid">
        {LIST_BLOCKS.map(([key, title, cls]) =>
          (fb[key] || []).length > 0 ? (
            <div key={key} className={`c3-feedback-col ${cls}`}>
              <h5>{title}</h5>
              <ul>
                {fb[key].map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null
        )}
      </div>

      {warnings && warnings.length > 0 && (
        <div className="c3-criterion-warnings">
          {warnings.map((w, i) => (
            <div key={i} className="small muted">
              Note: {w}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
