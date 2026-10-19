import React, { useMemo, useState, useEffect } from 'react';
import { getC2PredictionReadiness } from '../../../services/c2Api.js';

function displayTopicName(topicId) {
  if (!topicId) return 'Unclassified';
  return topicId
    .replace(/^provisional_/, '')
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

const READINESS_INFO = {
  insufficient_evidence: {
    label: 'Insufficient Historical Evidence',
    badgeClass: 'badge-insufficient_evidence',
    desc: 'Fewer than 3 authentic past papers or fewer than 2 distinct calendar years are currently available.',
  },
  awaiting_lecturer_verification: {
    label: 'Awaiting Lecturer Verification',
    badgeClass: 'badge-awaiting_lecturer_verification',
    desc: 'Authentic past-paper questions are ingested, but course lecturers have not yet verified topic assignments.',
  },
  historical_analysis_ready: {
    label: 'Historical Analysis Ready',
    badgeClass: 'badge-historical_analysis_ready',
    desc: 'Descriptive past-paper topic frequencies are verified and ready for historical trend analysis.',
  },
  experimental_prediction_ready: {
    label: 'Experimental Prediction Ready',
    badgeClass: 'badge-experimental_prediction_ready',
    desc: 'Sufficient independent historical sessions exist for experimental baseline evaluation.',
  },
  validated_prediction_ready: {
    label: 'Validated Prediction Ready',
    badgeClass: 'badge-validated_prediction_ready',
    desc: 'Prediction models have passed chronological walk-forward validation on independent historical exams.',
  },
};

export default function HistoricalTopicEvidenceSection({
  prediction,
  predictionLoading,
  predictionError,
  currentModuleName,
  moduleCode,
  onProceedToSetup,
  onSelectPreferredTopic,
  targetPeriod = 'next_session',
  onChangeTargetPeriod,
}) {
  const [selectedYearFilter, setSelectedYearFilter] = useState('all');
  const [selectedBaseline, setSelectedBaseline] = useState('baseline_b'); // 'baseline_a' | 'baseline_b' | 'baseline_c'
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [diagnosticsData, setDiagnosticsData] = useState(null);
  const [loadingDiagnostics, setLoadingDiagnostics] = useState(false);

  // Evidence extraction
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

  // Readiness status
  const readiness = prediction?.prediction_readiness || {};
  const readinessStatus = readiness.readiness_status || prediction?.status || 'awaiting_lecturer_verification';
  const readinessMeta = READINESS_INFO[readinessStatus] || READINESS_INFO.awaiting_lecturer_verification;

  // Prediction models
  const predictionModels = prediction?.prediction_models || {};
  const currentModelData = predictionModels[selectedBaseline];

  // Lazy load diagnostics matrix on toggle
  useEffect(() => {
    if (showDiagnostics && !diagnosticsData && !loadingDiagnostics) {
      setLoadingDiagnostics(true);
      getC2PredictionReadiness()
        .then((res) => {
          setDiagnosticsData(res?.modules || {});
        })
        .catch((err) => {
          console.warn('Failed to fetch prediction readiness diagnostics:', err);
        })
        .finally(() => {
          setLoadingDiagnostics(false);
        });
    }
  }, [showDiagnostics, diagnosticsData, loadingDiagnostics]);

  // Topic stats filter
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

  const handleTopicClick = (topicId) => {
    if (typeof onSelectPreferredTopic === 'function') {
      onSelectPreferredTopic(topicId);
    } else if (typeof onProceedToSetup === 'function') {
      onProceedToSetup();
    }
  };

  return (
    <section
      className="c2-student-bank c2-evidence-section"
      aria-label="Stage 2: Topic Evidence and Historical Analysis"
    >
      {/* Header */}
      <div className="c2-student-bank-header">
        <div>
          <span className="c2-student-panel-eyebrow">
            STAGE 2 — EXAM TOPIC PREDICTIONS & HISTORICAL EVIDENCE
          </span>
          <h2>Evidence-Aware Examination Topic Intelligence</h2>
          <p>
            Curriculum-grounded evidence from verified past examination papers
            for <strong>{currentModuleName}</strong> {moduleCode ? `(${moduleCode})` : ''}.
          </p>

          {/* Prediction Readiness Badge */}
          <div className="c2-readiness-badge-row">
            <span className={`c2-readiness-badge ${readinessMeta.badgeClass}`}>
              ● {readinessMeta.label}
            </span>
            <small style={{ color: 'var(--muted)' }}>
              {readinessMeta.desc}
            </small>
          </div>
        </div>

        <button
          type="button"
          className="btn primary"
          onClick={onProceedToSetup}
        >
          Configure Practice Mock (Stage 3) ➔
        </button>
      </div>

      {/* Target Examination Period Bar & Diagnostics Toggle */}
      <div className="c2-period-selector-bar">
        <label htmlFor="targetPeriodSelect">Target Examination Period:</label>
        <select
          id="targetPeriodSelect"
          value={targetPeriod}
          onChange={(e) => {
            if (typeof onChangeTargetPeriod === 'function') {
              onChangeTargetPeriod(e.target.value);
            }
          }}
        >
          <option value="upcoming_unconfirmed">Upcoming Examination — Date Not Confirmed (Default)</option>
          <option value="end_semester">Next Regular End-Semester Examination</option>
          <option value="historical_backtest_scenario">Historical Backtest Scenario (Research Evaluation Only)</option>
        </select>

        <button
          type="button"
          className="c2-diagnostics-toggle-btn"
          onClick={() => setShowDiagnostics((prev) => !prev)}
        >
          {showDiagnostics ? 'Hide Readiness Summary ✕' : '📊 Evidence & Readiness Summary (All Modules)'}
        </button>
      </div>

      {targetPeriod === 'historical_backtest_scenario' && (
        <div className="c2-backtest-banner" style={{ background: '#f0f9ff', border: '1px solid #bae6fd', color: '#0369a1', padding: '10px 14px', borderRadius: 8, margin: '12px 0', fontSize: '0.85rem' }}>
          <strong>🔬 Historical Evaluation Backtest Scenario:</strong> This scenario evaluates prediction models on historical past papers for research purposes. To ensure zero future-data leakage, all model features are constructed strictly using sessions prior to the target session.
        </div>
      )}

      {/* Non-Sensitive Evidence & Readiness Summary (All 8 Modules) */}
      {showDiagnostics && (
        <div className="c2-diagnostics-matrix-panel" role="region" aria-label="Evidence Readiness Summary">
          <div className="c2-diagnostics-head">
            <h4>Evidence & Prediction Readiness Summary: 8 Year 3 Modules</h4>
            <span className="pill status-neutral">Read-Only Research Audit</span>
          </div>
          <p className="c2-diagnostics-note">
            Authentic examination evidence audit across all eight SLIIT Year 3 Software Engineering modules.
            Under research guidelines, machine learning topic prediction is strictly suppressed until taxonomies and question classifications are verified by academic staff.
            This summary is non-sensitive and read-only.
          </p>

          {loadingDiagnostics ? (
            <p className="c2-student-muted">Loading module readiness reports...</p>
          ) : diagnosticsData ? (
            <div className="c2-table-wrap">
              <table className="c2-diagnostics-table">
                <thead>
                  <tr>
                    <th>Module Key</th>
                    <th>Authentic Papers</th>
                    <th>Calendar Years</th>
                    <th>Verified Questions</th>
                    <th>Readiness Status</th>
                    <th>Permitted Outputs</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(diagnosticsData).map(([key, item]) => {
                    const isCurrent = key === prediction?.module_key;
                    const meta = READINESS_INFO[item.readiness_status] || READINESS_INFO.awaiting_lecturer_verification;
                    return (
                      <tr key={key} className={isCurrent ? 'current-row' : ''}>
                        <td>
                          <strong>{displayTopicName(key)}</strong>
                          {isCurrent && <span style={{ marginLeft: 6, color: 'var(--primary)', fontWeight: 700 }}> (Current)</span>}
                        </td>
                        <td>{item.distinct_historical_papers} papers</td>
                        <td>{item.available_years?.join(', ') || 'None'}</td>
                        <td>
                          {item.verified_question_count} / {item.total_eligible_question_count} ({Math.round((item.evidence_coverage || 0) * 100)}%)
                        </td>
                        <td>
                          <span className={`c2-readiness-badge ${meta.badgeClass}`} style={{ fontSize: '0.7rem', padding: '2px 8px' }}>
                            {meta.label}
                          </span>
                        </td>
                        <td>
                          <small>{item.permitted_outputs?.join(', ') || 'None'}</small>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="c2-student-muted">Unable to load full diagnostics matrix.</p>
          )}
        </div>
      )}

      {/* Critical Academic Integrity Disclaimer Banner */}
      <div className="c2-attempt-integrity-box">
        <strong>Critical Research & Academic Integrity Standard:</strong>
        <p style={{ margin: '4px 0 0' }}>
          Future-exam predictive machine learning is evaluated on strictly chronological historical splits.
          The distributions and metrics displayed below represent{' '}
          <strong>descriptive historical frequencies</strong> derived from authentic past-paper questions.
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

          {/* PREDICTION BASELINES & MODELS STATUS */}
          <div className="c2-evidence-panel">
            <div className="c2-panel-head-row">
              <div>
                <h3>Examination Topic Prediction Baselines (M20 Framework)</h3>
                <p className="c2-panel-desc">
                  Three modular prediction baselines with chronological walk-forward evaluation gates.
                </p>
              </div>
            </div>

            <div className="c2-baseline-tabs">
              <button
                type="button"
                className={`c2-baseline-tab ${selectedBaseline === 'baseline_a' ? 'active' : ''}`}
                onClick={() => setSelectedBaseline('baseline_a')}
              >
                Baseline A: Historical Frequency
              </button>
              <button
                type="button"
                className={`c2-baseline-tab ${selectedBaseline === 'baseline_b' ? 'active' : ''}`}
                onClick={() => setSelectedBaseline('baseline_b')}
              >
                Baseline B: Recency-Weighted Frequency (λ=0.75)
              </button>
              <button
                type="button"
                className={`c2-baseline-tab ${selectedBaseline === 'baseline_c' ? 'active' : ''}`}
                onClick={() => setSelectedBaseline('baseline_c')}
              >
                Baseline C: Regularized Statistical Model
              </button>
            </div>

            {currentModelData?.status === 'model_not_trained' ? (
              <div className="c2-model-unavailability-card">
                <h5>Model Status: Not Trained (Honest Readiness Gate)</h5>
                <p>
                  {currentModelData.academic_integrity_notice ||
                    'Model training is inhibited to preserve scientific integrity. Topic prediction requires approved syllabus taxonomies and lecturer-verified examination labels.'}
                </p>
                {currentModelData.missing_requirements?.length > 0 && (
                  <div>
                    <strong>Prerequisites pending fulfillment:</strong>
                    <ul className="c2-missing-reqs-list">
                      {currentModelData.missing_requirements.map((req, i) => (
                        <li key={i}>{req}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : currentModelData?.predictions?.length > 0 ? (
              <div className="c2-topic-frequency-bars">
                {currentModelData.predictions.map((p, idx) => (
                  <div className="c2-topic-bar-item c2-topic-clickable" key={p.topic_id} onClick={() => handleTopicClick(p.topic_id)}>
                    <div className="c2-topic-bar-meta">
                      <span className="c2-topic-rank">#{idx + 1}</span>
                      <strong className="c2-topic-title">{p.topic_name || displayTopicName(p.topic_id)}</strong>
                      <span className="c2-topic-count">
                        Score: <strong>{p.score}</strong> ({p.score_type})
                      </span>
                      <button
                        type="button"
                        className="c2-select-topic-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTopicClick(p.topic_id);
                        }}
                      >
                        Practice Topic ➔
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {/* MAIN EVIDENCE CONTENT: Ranked Topics or Insufficient Evidence Banner */}
          {isRankingReady ? (
            <div className="c2-evidence-panel">
              <div className="c2-panel-head-row">
                <div>
                  <h3>Historical Topic Frequencies & Study Priorities</h3>
                  <p className="c2-panel-desc">
                    Descriptive frequencies from {verifiedQuestions} verified examination questions across {distinctPapers} authentic papers.
                    Relative bar widths represent historical occurrence counts. Click any topic to focus your practice.
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
                    <div
                      className="c2-topic-bar-item c2-topic-clickable"
                      key={topic.topic_id || index}
                      onClick={() => handleTopicClick(topic.topic_id)}
                      title="Click to practice this topic in Stage 3"
                    >
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
                        <button
                          type="button"
                          className="c2-select-topic-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTopicClick(topic.topic_id);
                          }}
                        >
                          Practice Topic ➔
                        </button>
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

          {/* Provisional AI Classification Transparency Section */}
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
