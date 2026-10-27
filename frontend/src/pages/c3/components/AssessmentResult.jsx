import React from 'react';
import CriterionCard from './CriterionCard.jsx';
import ConceptDiagnosis from './ConceptDiagnosis.jsx';
import MindMapGraph from './MindMapGraph.jsx';
import { Notice, StatusPill, Unavailable } from './c3ui.jsx';
import { normaliseEvaluation } from '../analysis.js';

// The single result/analysis view used by the student page, the lecturer review page and the batch inspect dialog.
// Everything shown comes from the saved evaluation; a part that was not produced is replaced by an explicit
// "unavailable" note with the reason (never an empty panel and never placeholder analysis).
//   showMarkCard: proposed/final mark card with status (pages that have their own decision panel switch it off)
//   showContext:  the question and the student's submitted answer
export default function AssessmentResult({ evaluation, historicalResult, question, answer, submissionId, showMarkCard = true, showContext = true }) {
  const a = normaliseEvaluation(evaluation);
  const status = historicalResult?.status || 'pending_review';
  const finalized = status === 'finalized';
  const total = historicalResult?.total_possible_marks ?? evaluation?.total_possible_marks ?? evaluation?.marking?.total_possible_marks ?? 0;
  const proposed = historicalResult?.automated_mark ?? evaluation?.total_awarded_marks ?? evaluation?.marking?.total_awarded_marks ?? 0;
  const shown = finalized ? historicalResult?.final_mark ?? proposed : proposed;
  const pct = total > 0 ? Math.round((shown / total) * 1000) / 10 : 0;
  const sentenceMap = new Map(a.sentences.map((s) => [s.sentence_id, s.text]));
  const fbByCriterion = new Map((evaluation?.feedback?.criteria_feedback || []).map((f) => [f.criterion_id, f]));
  const isMcqResult = a.kind === 'mcq';

  return (
    <div className="c3-result">
      {showMarkCard && (
        <>
          <section className="c3-mark-card" aria-label="Mark">
            <div>
              <StatusPill status={status} />
              <h2>{finalized ? 'Final result' : 'Proposed mark'}</h2>
              <p className="muted">
                {finalized
                  ? `Confirmed by ${historicalResult?.reviewed_by || 'your lecturer'}.`
                  : status === 'reviewed'
                  ? 'Your lecturer has reviewed this result. It becomes official when it is finalized.'
                  : 'Marked automatically. Your lecturer reviews it before it becomes official.'}
              </p>
              {submissionId && <p className="small muted">Reference: #{String(submissionId).slice(-6)}</p>}
            </div>
            <div className="c3-mark-figure">
              <div>
                <span className="c3-mark-big">{shown}</span>
                <span className="c3-mark-of"> / {total}</span>
              </div>
              <div className="c3-mark-sub">{pct}%</div>
              <div className={`c3-bar${finalized ? ' final' : ''}`} role="img" aria-label={`${pct} percent`}>
                <span style={{ width: `${Math.min(100, pct)}%` }} />
              </div>
            </div>
          </section>

          {finalized && historicalResult?.lecturer_decision === 'overridden' && (
            <Notice tone="warn" title="Your lecturer adjusted the automatic mark">
              {historicalResult.override_reason || 'The mark was updated after review.'} Automatic mark: {proposed} / {total}. Final mark: {historicalResult.final_mark} / {total}.
            </Notice>
          )}
        </>
      )}

      {/* Advisory AI estimate: only present in the staff copy of the evaluation (the server removes it for students). */}
      {evaluation?.ai_estimate && (
        <section className="panel" aria-label="AI score estimate" style={{ margin: 0 }}>
          <h3 style={{ margin: '0 0 8px' }}>AI second opinion (advisory)</h3>
          <p style={{ margin: 0 }}>
            Estimated mark: <strong>{Math.round(evaluation.ai_estimate.estimated_marks * 10) / 10} / {total}</strong>
            {' '}({Math.round(evaluation.ai_estimate.estimated_ratio * 100)}%) &middot; Rubric mark: {proposed} / {total}
            {' '}
            <span className={`pill ${evaluation.ai_estimate.needs_review ? 'status-rejected' : 'status-approved'}`}>
              {evaluation.ai_estimate.needs_review ? 'Differs - review recommended' : 'Consistent with rubric'}
            </span>
          </p>
          <p className="small muted" style={{ margin: '8px 0 0' }}>
            {evaluation.ai_estimate.note}
          </p>
        </section>
      )}

      {a.warnings.length > 0 && (
        <Notice tone="warn" title="Notes about this result">
          <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
            {a.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Notice>
      )}

      {showContext && (
        <section className="panel" aria-label="Question and answer" style={{ margin: 0 }}>
          <h3 style={{ margin: '0 0 8px' }}>Question and answer</h3>
          {question && (
            <p className="small" style={{ marginTop: 0 }}>
              <strong>Question:</strong> {question}
            </p>
          )}
          <div className="c3-answer-box">{answer || 'No answer text was recorded.'}</div>
        </section>
      )}

      {a.kind === 'none' && (
        <Notice tone="warn" title="No analysis available">
          {a.feedback.reason} The mark shown comes from the stored result record.
        </Notice>
      )}

      {a.answerKey && (
        <section className="panel" aria-label="Answer key match" style={{ margin: 0 }}>
          <h3 style={{ margin: '0 0 8px' }}>Answer key match</h3>
          <div className="table-wrap">
            <table className="data-table c3-table" style={{ margin: 0 }}>
              <thead>
                <tr>
                  <th scope="col">Selected</th>
                  <th scope="col">Correct answer</th>
                  <th scope="col">Result</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>{a.answerKey.selected.join(', ') || 'No option chosen'}</td>
                  <td>{a.answerKey.correct.join(', ')}</td>
                  <td>
                    <span className={`pill ${a.answerKey.isCorrect ? 'status-approved' : 'status-rejected'}`}>{a.answerKey.isCorrect ? 'Correct' : a.answerKey.unanswered ? 'Unanswered' : 'Not correct'}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}

      {a.kind !== 'none' &&
        (a.feedback.available ? (
          <section className="panel c3-summary-card" aria-label="Feedback" style={{ margin: 0 }}>
            <h3>Feedback</h3>
            {a.feedback.summary && <p className="c3-summary-text">{a.feedback.summary}</p>}
            <div className="c3-summary-columns">
              {a.feedback.sections.map((sec) => (
                <div key={sec.key} className="c3-summary-col">
                  <h5>{sec.title}</h5>
                  <ul>
                    {sec.items.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            {a.feedback.note && (
              <p className="small muted" style={{ margin: '10px 0 0' }}>
                {a.feedback.note}
              </p>
            )}
          </section>
        ) : (
          <Unavailable title="Feedback" reason={a.feedback.reason} />
        ))}

      {a.criteria.length > 0 && (
        <>
          <h2 style={{ margin: '12px 0 0' }}>Marking by criterion</h2>
          {a.criteria.map((cr) => (
            <CriterionCard key={cr.criterion_id} criterionMarking={cr} criterionFeedback={fbByCriterion.get(cr.criterion_id)} sentenceMap={sentenceMap} showEvidence={!isMcqResult} />
          ))}
        </>
      )}
      {a.kind !== 'none' && a.criteria.length === 0 && <Unavailable title="Marking by criterion" reason="No criterion-level marking was saved for this submission." />}

      {a.kind !== 'none' && (a.concepts.available ? <ConceptDiagnosis analysis={a.concepts.analysis} sentenceMap={sentenceMap} /> : <Unavailable title="Concept diagnosis" reason={a.concepts.reason} />)}

      {a.kind !== 'none' &&
        (a.map.available ? (
          <>
            <h2 style={{ margin: '12px 0 0' }}>Concept map</h2>
            <MindMapGraph mindmap={a.map.mindmap} sentences={a.sentences} />
          </>
        ) : (
          <Unavailable title="Concept map" reason={a.map.reason} />
        ))}
    </div>
  );
}
