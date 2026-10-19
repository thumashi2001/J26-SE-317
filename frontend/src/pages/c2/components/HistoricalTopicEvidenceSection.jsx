import React, { useMemo, useState } from 'react';

function displayTopicName(topicId) {
  if (!topicId) return 'Unclassified';
  return topicId
    .replace(/^provisional_/, '')
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default function HistoricalTopicEvidenceSection({
  prediction,
  predictionLoading,
  predictionError,
  currentModuleName,
  moduleCode,
  onProceedToSetup,
}) {
  const [selectedYearFilter, setSelectedYearFilter] = useState('all');

  const evidence = prediction?.historical_evidence;
  const verifiedQuestions = evidence?.verified_topic_questions ?? 0;
  const totalQuestions = evidence?.authentic_questions ?? 0;
  const distinctPapers = evidence?.distinct_papers ?? 0;
  const distinctYears = evidence?.distinct_years ?? [];
  const unavailableYears = evidence?.unavailable_years ?? [];
  const provisionalQuestions = evidence?.provisional_topic_questions ?? 0;
  const unclassifiedQuestions = evidence?.unverified_topic_questions ?? 0;
  const verifiedCoverage = evidence?.verified_topic_coverage ?? 0;
  const confirmedMarks = evidence?.sum_of_extracted_question_marks ?? 0;
  const ambiguousMarksCount = evidence?.ambiguous_marks_questions ?? 0;
  const papersInventory = evidence?.papers_inventory ?? [];

  const verifiedCoveragePercent = `${Math.round(verifiedCoverage * 100)}%`;
  const isRankingReady = prediction?.prediction_ready === true;

  // Filter topics or year occurrences if user picks a specific year
  const topicStats = useMemo(() => {
    const stats = prediction?.topic_statistics || [];
    if (selectedYearFilter === 'all') return stats;
    return stats
      .map((t) => ({
        ...t,
        filterCount: t.yearly_occurrences?.[selectedYearFilter] ?? 0,
      }))
      .filter((t) => t.filterCount > 0)
      .sort((a, b) => b.filterCount - a.filterCount);
  }, [prediction, selectedYearFilter]);

  const maxQuestionCount = useMemo(() => {
    if (!topicStats.length) return 1;
    return Math.max(
      ...topicStats.map((t) =>
        selectedYearFilter === 'all'
          ? t.question_count || 1
          : t.filterCount || 1
      )
    );
  }, [topicStats, selectedYearFilter]);

  return (
    <section
      className="c2-student-bank c2-evidence-section"
      aria-label="Stage 2: Topic Evidence and Historical Analysis"
    >
      {/* Header */}
      <div className="c2-student-bank-header">
        <div>
          <span className="c2-student-panel-eyebrow">
            STAGE 2 — AUTHENTIC HISTORICAL EVIDENCE
          </span>
          <h2>Historical Examination Topic Evidence</h2>
          <p>
            Curriculum-grounded evidence from verified past examination papers
            for <strong>{currentModuleName}</strong> {moduleCode ? `(${moduleCode})` : ''}.
          </p>
        </div>

        <button
          type="button"
          className="btn primary"
          onClick={onProceedToSetup}
        >
          Configure Practice Mock (Stage 3) ➔
        </button>
      </div>

      {/* Critical Academic Integrity Disclaimer Banner */}
      <div className="c2-attempt-integrity-box">
        <strong>Critical Research & Academic Integrity Standard:</strong>
        <p style={{ margin: '4px 0 0' }}>
          Future-exam predictive machine learning (M20) is under active research.
          The distributions and metrics displayed below represent{' '}
          <strong>descriptive historical frequencies</strong> derived from SLIIT authentic past-paper questions.
          They do <strong>NOT</strong> represent probability percentages of appearing on upcoming examinations.
        </p>
      </div>

      {predictionLoading && (
        <div className="c2-student-loading" role="status">
          Loading authentic historical topic evidence...
        </div>
      )}

      {predictionError && (
        <div className="c2-student-error" role="alert">
          <strong>Unable to load historical topic evidence</strong>
          <p>{predictionError}</p>
        </div>
      )}

      {!predictionLoading && prediction && (
        <>
          {/* Historical Evidence Overview Metrics */}
          <div className="c2-evidence-metrics-grid">
            <div className="c2-evidence-metric-card tone-blue">
              <span className="c2-metric-label">Authentic Questions</span>
              <span className="c2-metric-value">{totalQuestions}</span>
              <span className="c2-metric-note">Leaf questions extracted from past papers</span>
            </div>

            <div className="c2-evidence-metric-card tone-teal">
              <span className="c2-metric-label">Past Examination Papers</span>
              <span className="c2-metric-value">{distinctPapers}</span>
              <span className="c2-metric-note">
                {distinctYears.length > 0
                  ? `Years: ${distinctYears.join(', ')}`
                  : 'Historical papers'}
              </span>
            </div>

            <div className="c2-evidence-metric-card tone-indigo">
              <span className="c2-metric-label">Verified Topic Labels</span>
              <span className="c2-metric-value">
                {verifiedQuestions}{' '}
                <span className="c2-metric-sub">/ {totalQuestions}</span>
              </span>
              <span className="c2-metric-note">
                Academically verified by lecturers ({verifiedCoveragePercent})
              </span>
            </div>

            <div className="c2-evidence-metric-card tone-amber">
              <span className="c2-metric-label">Provisional AI Suggestions</span>
              <span className="c2-metric-value">{provisionalQuestions}</span>
              <span className="c2-metric-note">
                Synthetic M17 predictions (pending review)
              </span>
            </div>

            <div className="c2-evidence-metric-card tone-sky">
              <span className="c2-metric-label">Confirmed Extracted Marks</span>
              <span className="c2-metric-value">{confirmedMarks}</span>
              <span className="c2-metric-note">
                {ambiguousMarksCount > 0
                  ? `${ambiguousMarksCount} ambiguous marks excluded`
                  : 'Reliable marks'}
              </span>
            </div>
          </div>

          {/* Past Papers & Examination Years Inventory Table */}
          <div className="c2-evidence-panel">
            <div className="c2-panel-head-row">
              <h3>Authentic Past-Paper Inventory</h3>
              <span className="c2-paper-badge">
                {distinctPapers} Authentic Examination Papers Available
              </span>
            </div>
            <p className="c2-panel-desc">
              Provenance of ingested historical past-paper documents used to synthesize topic evidence.
            </p>

            {papersInventory.length > 0 ? (
              <div className="c2-table-wrap">
                <table className="c2-table">
                  <thead>
                    <tr>
                      <th>Academic Year</th>
                      <th>Paper ID</th>
                      <th>Source Document</th>
                      <th>Extracted Questions</th>
                      <th>Confirmed Marks</th>
                    </tr>
                  </thead>
                  <tbody>
                    {papersInventory.map((paper) => (
                      <tr key={paper.paper_id}>
                        <td>
                          <span className="c2-year-tag">
                            {paper.calendar_year || 'Unknown Year'}
                          </span>
                        </td>
                        <td>
                          <code>{paper.paper_id}</code>
                        </td>
                        <td>{paper.source_filename || 'PDF Document'}</td>
                        <td>
                          <strong>{paper.question_count}</strong> questions
                        </td>
                        <td>
                          {paper.extracted_marks_sum > 0
                            ? `${paper.extracted_marks_sum} marks`
                            : 'Unextracted / Ambiguous'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="c2-student-muted">
                No individual paper records registered for this module.
              </p>
            )}

            {unavailableYears.length > 0 && (
              <div className="c2-unavailable-years-box">
                <strong>Non-Administered / Unavailable Examination Years:</strong>
                <p>
                  Years <code>{unavailableYears.join(', ')}</code> are not present in the authentic past-paper archive
                  (e.g., due to COVID-19 institutional schedule disruptions or non-written assessment).
                  Historical trend analyses explicitly treat these as <em>unavailable data</em> rather than zero occurrences.
                </p>
              </div>
            )}
          </div>

          {/* MAIN EVIDENCE CONTENT: Ranked Topics or Insufficient Evidence Banner */}
          {isRankingReady ? (
            <div className="c2-evidence-panel">
              <div className="c2-panel-head-row">
                <div>
                  <h3>Historical Topic Frequencies & Study Priorities</h3>
                  <p className="c2-panel-desc">
                    Descriptive frequencies from {verifiedQuestions} verified examination questions across {distinctPapers} authentic papers.
                    Relative bar widths represent historical occurrence counts.
                  </p>
                </div>

                {distinctYears.length > 1 && (
                  <div className="c2-year-filter-ctrl">
                    <label htmlFor="yearFilterSelect">Academic Year:</label>
                    <select
                      id="yearFilterSelect"
                      value={selectedYearFilter}
                      onChange={(e) => setSelectedYearFilter(e.target.value)}
                    >
                      <option value="all">All Years Combined ({distinctYears.join(', ')})</option>
                      {distinctYears.map((yr) => (
                        <option key={yr} value={yr}>
                          {yr} Paper
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Horizontal Topic Frequency Bars */}
              <div className="c2-topic-frequency-bars" role="region" aria-label="Horizontal topic frequency bars">
                {topicStats.map((topic, index) => {
                  const count =
                    selectedYearFilter === 'all'
                      ? topic.question_count || 0
                      : topic.filterCount || 0;
                  const percent = Math.min(
                    100,
                    Math.round((count / maxQuestionCount) * 100)
                  );
                  const shareOfVerified = topic.share_of_verified_questions
                    ? `${Math.round(topic.share_of_verified_questions * 100)}%`
                    : null;
                  const paperCoverage = topic.paper_coverage
                    ? `${Math.round(topic.paper_coverage * 100)}%`
                    : null;

                  return (
                    <div className="c2-topic-bar-item" key={topic.topic_id || index}>
                      <div className="c2-topic-bar-meta">
                        <span className="c2-topic-rank">
                          #{topic.rank ?? index + 1}
                        </span>
                        <strong className="c2-topic-title">
                          {displayTopicName(topic.topic_id)}
                        </strong>
                        <span className="c2-topic-count">
                          <strong>{count}</strong> {count === 1 ? 'question' : 'questions'}
                          {shareOfVerified && ` (${shareOfVerified} of verified)`}
                        </span>
                      </div>

                      <div className="c2-topic-bar-track">
                        <div
                          className="c2-topic-bar-fill"
                          style={{ width: `${percent}%` }}
                          aria-valuenow={count}
                          aria-valuemin="0"
                          aria-valuemax={maxQuestionCount}
                          role="progressbar"
                        />
                      </div>

                      <div className="c2-topic-bar-subinfo">
                        {paperCoverage && (
                          <span>
                            Paper Coverage: <strong>{paperCoverage}</strong> ({topic.papers_count || 0} of {distinctPapers} papers)
                          </span>
                        )}
                        {topic.extracted_marks > 0 && (
                          <span>
                            Confirmed Marks: <strong>{topic.extracted_marks}</strong>
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Year-by-Year Occurrence Trend Matrix */}
              {distinctYears.length > 1 && (
                <div style={{ marginTop: 28 }}>
                  <h4>Year-over-Year Topic Occurrence Trends</h4>
                  <p className="c2-panel-desc">
                    Cross-examination comparison showing verified question counts across each administered year.
                  </p>
                  <div className="c2-table-wrap">
                    <table className="c2-table">
                      <thead>
                        <tr>
                          <th>Topic</th>
                          {distinctYears.map((yr) => (
                            <th key={yr} style={{ textAlign: 'center' }}>
                              {yr}
                            </th>
                          ))}
                          <th style={{ textAlign: 'right' }}>Total Questions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topicStats.map((topic) => (
                          <tr key={topic.topic_id}>
                            <td>
                              <strong>{displayTopicName(topic.topic_id)}</strong>
                            </td>
                            {distinctYears.map((yr) => {
                              const occ = topic.yearly_occurrences?.[yr] ?? 0;
                              return (
                                <td
                                  key={yr}
                                  style={{
                                    textAlign: 'center',
                                    color: occ > 0 ? 'var(--primary)' : 'var(--muted)',
                                    fontWeight: occ > 0 ? 700 : 400,
                                  }}
                                >
                                  {occ}
                                </td>
                              );
                            })}
                            <td style={{ textAlign: 'right', fontWeight: 700 }}>
                              {topic.question_count}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Insufficient Verified Topic Evidence State */
            <div className="c2-evidence-insufficient-card">
              <div className="c2-insufficient-header">
                <div className="c2-insufficient-badge">INSUFFICIENT VERIFIED TOPIC EVIDENCE</div>
                <h3>Topic Ranking Currently Unavailable</h3>
                <p>
                  While <strong>{distinctPapers} authentic past examination papers</strong> ({totalQuestions} questions)
                  have been parsed and ingested for <strong>{currentModuleName}</strong>, course lecturers have not yet
                  completed syllabus alignment and topic classification verification for this module.
                </p>
              </div>

              <div className="c2-insufficient-stats">
                <div className="c2-insufficient-stat-item">
                  <span className="c2-stat-num">{totalQuestions}</span>
                  <span className="c2-stat-desc">Authentic Questions Available</span>
                </div>
                <div className="c2-insufficient-stat-item">
                  <span className="c2-stat-num c2-stat-warn">0</span>
                  <span className="c2-stat-desc">Lecturer-Verified Classifications</span>
                </div>
                <div className="c2-insufficient-stat-item">
                  <span className="c2-stat-num c2-stat-info">{provisionalQuestions}</span>
                  <span className="c2-stat-desc">Provisional AI Topic Candidates</span>
                </div>
                <div className="c2-insufficient-stat-item">
                  <span className="c2-stat-num c2-stat-muted">{unclassifiedQuestions}</span>
                  <span className="c2-stat-desc">Unclassified / Abstained</span>
                </div>
              </div>

              <div className="c2-insufficient-explanation">
                <h4>Why is topic ranking blocked?</h4>
                <p>
                  In accordance with the project's research integrity guidelines, automated ML topic predictions
                  must be reviewed and approved by course lecturers before historical topic rankings and study priorities
                  can be published. This ensures students receive 100% trustworthy revision guidance rather than unverified machine guesses.
                </p>
                <p>
                  <strong>What you can do right now:</strong> You can proceed to Stage 3 to practice with authentic
                  questions or synthetic development fixtures for this module.
                </p>
              </div>

              <div className="c2-insufficient-actions">
                <button
                  type="button"
                  className="btn primary"
                  onClick={onProceedToSetup}
                >
                  Proceed to Practice Setup (Stage 3) ➔
                </button>
              </div>
            </div>
          )}

          {/* Provisional AI Classification Transparency Section (if any provisional topics exist) */}
          {Array.isArray(prediction?.provisional_topic_summary) &&
            prediction.provisional_topic_summary.length > 0 && (
              <div className="c2-provisional-panel">
                <div className="c2-panel-head-row">
                  <div>
                    <h4>Provisional AI Topic Suggestions (Unverified Research Output)</h4>
                    <p className="c2-panel-desc">
                      Generated by experimental M17 machine learning models trained on synthetic development data.
                      These suggestions are strictly unverified and are withheld from historical ranking calculations.
                    </p>
                  </div>
                  <span className="c2-pill-provisional">
                    {prediction.provisional_topic_summary.length} Provisional Candidates
                  </span>
                </div>

                <div className="c2-provisional-grid">
                  {prediction.provisional_topic_summary.map((cand, idx) => (
                    <div className="c2-provisional-item" key={cand.topic_id || idx}>
                      <div className="c2-provisional-item-head">
                        <strong>{cand.candidate_name || displayTopicName(cand.topic_id)}</strong>
                        <span className="pill status-pending">Pending Lecturer Review</span>
                      </div>
                      <div className="c2-provisional-item-body">
                        <span>
                          {cand.question_count} {cand.question_count === 1 ? 'question' : 'questions'}
                        </span>
                        {cand.average_confidence && (
                          <span>
                            Confidence: {Math.round(cand.average_confidence * 100)}%
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          {/* Limitations and Data Provenance */}
          {Array.isArray(prediction.limitations) && prediction.limitations.length > 0 && (
            <div className="c2-evidence-limitations">
              <h3>Evidence Limitations & Research Scope</h3>
              <ul>
                {prediction.limitations.map((lim, idx) => (
                  <li key={idx}>
                    {typeof lim === 'string' ? lim : JSON.stringify(lim)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Footer Action */}
          <div className="c2-evidence-footer-nav">
            <button
              type="button"
              className="btn primary"
              onClick={onProceedToSetup}
            >
              Proceed to Practice Setup (Stage 3) ➔
            </button>
          </div>
        </>
      )}
    </section>
  );
}
