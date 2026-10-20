import React, { useMemo, useState, useEffect } from 'react';
import {
  getC2PredictionReadiness,
  getC2ExperimentalTopicPredictions,
} from '../../../services/c2Api.js';

function displayTopicName(topicId) {
  if (!topicId) return 'Unclassified';
  return topicId
    .replace(/^provisional_/, '')
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function resolveTopicTitle(topic) {
  if (!topic) return 'Unclassified';
  if (topic.topic_name && topic.topic_name !== topic.topic_id) {
    return topic.topic_name;
  }
  return displayTopicName(topic.topic_id || topic.topic_name);
}

function formatScore(val, fallback = '0.0000') {
  if (val === null || val === undefined || isNaN(Number(val))) return fallback;
  return Number(val).toFixed(4);
}

function formatPercent(val, fallback = '—') {
  if (val === null || val === undefined || isNaN(Number(val))) return fallback;
  return `${Math.round(Number(val) * 100)}%`;
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
  moduleKey,
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

  // M22.3 Synthetic Experimental Demonstration State
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoData, setDemoData] = useState(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoError, setDemoError] = useState(null);
  const [selectedDemoBaseline, setSelectedDemoBaseline] = useState('baseline_b'); // 'baseline_a' | 'baseline_b' | 'baseline_c'

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

  // Prediction models (Authentic)
  const predictionModels = prediction?.prediction_models || {};
  const currentModelData = predictionModels[selectedBaseline];

  // Active module key resolution
  const activeModuleKey = moduleKey || prediction?.module_key;

  // Fetch Synthetic Demo Predictions when Demo Mode is Enabled or Parameters Change
  useEffect(() => {
    let active = true;
    if (isDemoMode && activeModuleKey) {
      setDemoLoading(true);
      setDemoError(null);
      getC2ExperimentalTopicPredictions(activeModuleKey, targetPeriod)
        .then((res) => {
          if (active) {
            setDemoData(res);
          }
        })
        .catch((err) => {
          if (active) {
            console.error('Failed to load experimental topic predictions:', err);
            setDemoError(
              err?.message || 'Failed to load experimental prediction demo data.'
            );
          }
        })
        .finally(() => {
          if (active) {
            setDemoLoading(false);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [isDemoMode, activeModuleKey, targetPeriod]);

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

  // Topic stats filter (Authentic)
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
            {isDemoMode
              ? 'STAGE 2 — EXPERIMENTAL TOPIC PREDICTION DEMONSTRATION'
              : 'STAGE 2 — EXAM TOPIC PREDICTIONS & HISTORICAL EVIDENCE'}
          </span>
          <h2>
            {isDemoMode
              ? 'Evidence-Aware Examination Topic Intelligence (Synthetic Demo)'
              : 'Evidence-Aware Examination Topic Intelligence'}
          </h2>
          <p>
            {isDemoMode
              ? `Synthetic multi-session experimental demonstration of M20 prediction models for `
              : `Curriculum-grounded evidence from verified past examination papers for `}
            <strong>{currentModuleName}</strong> {moduleCode ? `(${moduleCode})` : ''}.
          </p>

          {/* Prediction Readiness Badge */}
          <div className="c2-readiness-badge-row">
            {isDemoMode ? (
              <>
                <span className="c2-readiness-badge badge-experimental_prediction_ready">
                  ● Synthetic Experimental Demonstration
                </span>
                <small style={{ color: 'var(--muted)' }}>
                  Evaluated on 5 deterministic synthetic sessions across 3 chronological walk-forward folds.
                </small>
              </>
            ) : (
              <>
                <span className={`c2-readiness-badge ${readinessMeta.badgeClass}`}>
                  ● {readinessMeta.label}
                </span>
                <small style={{ color: 'var(--muted)' }}>
                  {readinessMeta.desc}
                </small>
              </>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          {isDemoMode ? (
            <button
              type="button"
              className="btn secondary"
              onClick={() => setIsDemoMode(false)}
              title="Return to authentic past-paper evidence"
            >
              ← Return to Authentic Evidence
            </button>
          ) : (
            <button
              type="button"
              className="c2-demo-toggle-btn"
              onClick={() => setIsDemoMode(true)}
              title="Explore machine learning prediction baselines on synthetic multi-session data"
            >
              🔬 Explore Prediction Models — Synthetic Demo
            </button>
          )}

          <button
            type="button"
            className="btn primary"
            onClick={onProceedToSetup}
          >
            Configure Practice Mock (Stage 3) ➔
          </button>
        </div>
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

        {isDemoMode ? (
          <button
            type="button"
            className="btn secondary"
            style={{ fontSize: '0.82rem', padding: '6px 12px' }}
            onClick={() => setIsDemoMode(false)}
          >
            ← Return to Authentic Evidence
          </button>
        ) : (
          <button
            type="button"
            className="c2-demo-toggle-btn"
            onClick={() => setIsDemoMode(true)}
          >
            🔬 Explore Prediction Models — Synthetic Demo
          </button>
        )}

        <button
          type="button"
          className="c2-diagnostics-toggle-btn"
          onClick={() => setShowDiagnostics((prev) => !prev)}
        >
          {showDiagnostics ? 'Hide Readiness Summary ✕' : '📊 Evidence & Readiness Summary (All Modules)'}
        </button>
      </div>

      {targetPeriod === 'historical_backtest_scenario' && !isDemoMode && (
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
                    const isCurrent = key === activeModuleKey;
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

      {/* ======================================================== */}
      {/* M22.3 SYNTHETIC EXPERIMENTAL DEMO VIEW                   */}
      {/* ======================================================== */}
      {isDemoMode ? (
        <div className="c2-demo-container" role="region" aria-label="Synthetic Prediction Demonstration View">
          {/* Prominent Notice Banner */}
          <div className="c2-demo-banner">
            <div className="c2-demo-banner-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span className="c2-demo-pill">🔬 VIVA RESEARCH DEMONSTRATION</span>
                <span className="pill status-warning" style={{ fontSize: '0.74rem' }}>
                  SYNTHETIC FIXTURE — NOT REAL EXAM PREDICTIONS
                </span>
              </div>
              <button
                type="button"
                className="btn secondary"
                style={{ fontSize: '0.82rem', padding: '6px 14px' }}
                onClick={() => setIsDemoMode(false)}
              >
                ← Return to Authentic Evidence
              </button>
            </div>

            <h3 style={{ margin: '4px 0 0', color: '#312e81' }}>
              Synthetic Experimental Topic Prediction Demonstration
            </h3>

            <p className="c2-demo-alert-text">
              <strong>Notice:</strong> This interactive viva demonstration runs the complete M20 prediction engine and walk-forward chronological evaluation on a <strong>statistically representative synthetic 5-session curriculum exam history</strong> ({demoData?.synthetic_session_count ?? 5} synthetic sessions, {demoData?.chronological_evaluation?.eligible_evaluation_splits ?? 3} evaluation folds).
            </p>

            <div className="c2-demo-integrity-box">
              ⚠️ <strong>Academic Integrity & Research Safeguard:</strong> These scores and rankings are generated for algorithmic evaluation and viva demonstration purposes only. They <strong>DO NOT predict the next real SLIIT examination</strong> and must not be used as an assurance of what will appear on actual upcoming exam papers. Authentic past papers remain gated until lecturer verification.
            </div>
          </div>

          {demoLoading && (
            <div className="c2-student-loading" role="status">
              Loading synthetic experimental prediction models for {currentModuleName}...
            </div>
          )}

          {demoError && (
            <div className="c2-student-error" role="alert">
              <strong>Unable to load experimental prediction demo</strong>
              <p>{demoError}</p>
              <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => {
                    setDemoLoading(true);
                    setDemoError(null);
                    getC2ExperimentalTopicPredictions(activeModuleKey, targetPeriod)
                      .then((res) => setDemoData(res))
                      .catch((err) => setDemoError(err?.message || 'Failed to reload demo'))
                      .finally(() => setDemoLoading(false));
                  }}
                >
                  Retry Demo Request
                </button>
                <button
                  type="button"
                  className="btn primary"
                  onClick={() => setIsDemoMode(false)}
                >
                  ← Return to Authentic Evidence
                </button>
              </div>
            </div>
          )}

          {!demoLoading && demoData && (
            <>
              {/* Experimental Overview Metrics */}
              <div className="c2-evidence-metrics-grid">
                <div className="c2-evidence-metric-card tone-indigo">
                  <span className="c2-metric-label">Synthetic Sessions</span>
                  <span className="c2-metric-value">{demoData.synthetic_session_count ?? 5}</span>
                  <span className="c2-metric-note">Deterministic exam sequence</span>
                </div>

                <div className="c2-evidence-metric-card tone-teal">
                  <span className="c2-metric-label">Evaluation Folds</span>
                  <span className="c2-metric-value">
                    {demoData.chronological_evaluation?.eligible_evaluation_splits ?? 3}
                  </span>
                  <span className="c2-metric-note">Walk-forward chronological splits</span>
                </div>

                <div className="c2-evidence-metric-card tone-blue">
                  <span className="c2-metric-label">Prediction Algorithms</span>
                  <span className="c2-metric-value">3</span>
                  <span className="c2-metric-note">Frequency, Recency, Regularized</span>
                </div>

                <div className="c2-evidence-metric-card tone-sky">
                  <span className="c2-metric-label">Temporal Leakage</span>
                  <span className="c2-metric-value">0%</span>
                  <span className="c2-metric-note">Strictly prior history features</span>
                </div>

                <div className="c2-evidence-metric-card tone-amber">
                  <span className="c2-metric-label">Evaluation Metrics</span>
                  <span className="c2-metric-value">P@3 / R@3</span>
                  <span className="c2-metric-note">Top-3 topic coverage & Brier score</span>
                </div>
              </div>

              {/* THREE RANKED TOPIC LISTS & METHOD SELECTION */}
              <div className="c2-evidence-panel">
                <div className="c2-panel-head-row">
                  <div>
                    <h3>Ranked Topic Priorities by Prediction Method</h3>
                    <p className="c2-panel-desc">
                      Select a baseline to inspect its topic priority ranking. Ranking scores are normalized relative metrics (0.0000 - 1.0000) ordering study importance; they are <strong>NOT</strong> appearance probabilities.
                    </p>
                  </div>
                  <span className="c2-paper-badge">
                    Target: {demoData.target_period || targetPeriod}
                  </span>
                </div>

                <div className="c2-baseline-tabs">
                  <button
                    type="button"
                    className={`c2-baseline-tab ${selectedDemoBaseline === 'baseline_a' ? 'active' : ''}`}
                    onClick={() => setSelectedDemoBaseline('baseline_a')}
                  >
                    Baseline A: Historical Frequency
                  </button>
                  <button
                    type="button"
                    className={`c2-baseline-tab ${selectedDemoBaseline === 'baseline_b' ? 'active' : ''}`}
                    onClick={() => setSelectedDemoBaseline('baseline_b')}
                  >
                    Baseline B: Recency-Weighted Frequency (λ=0.75)
                  </button>
                  <button
                    type="button"
                    className={`c2-baseline-tab ${selectedDemoBaseline === 'baseline_c' ? 'active' : ''}`}
                    onClick={() => setSelectedDemoBaseline('baseline_c')}
                  >
                    Baseline C: Regularized Statistical Model
                  </button>
                </div>

                {/* Active Baseline Explanation */}
                <div className="c2-model-unavailability-card" style={{ borderColor: 'rgba(99, 102, 241, 0.4)', background: 'rgba(99, 102, 241, 0.04)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                    <h5 style={{ color: '#4338ca', margin: 0 }}>
                      {demoData.methods?.[selectedDemoBaseline]?.method_name || 'Method Overview'}
                    </h5>
                    <span className="c2-badge-score-pill">
                      Metric: {demoData.methods?.[selectedDemoBaseline]?.predictions?.[0]?.score_type || 'Ranking Score'}
                    </span>
                  </div>
                  <p style={{ margin: '8px 0 0', color: 'var(--text-2)' }}>
                    {demoData.methods?.[selectedDemoBaseline]?.description ||
                      'Evaluates historical appearance patterns to prioritize syllabus topics for student revision.'}
                  </p>
                </div>

                {/* Ranked Topic Bars for Active Baseline */}
                <div className="c2-topic-frequency-bars" role="region" aria-label="Experimental topic ranking list">
                  {(demoData.methods?.[selectedDemoBaseline]?.predictions || []).map((topic, index) => {
                    const score = Number(topic.score) || 0;
                    const percentWidth = Math.min(100, Math.max(5, Math.round(score * 100)));
                    const topicTitle = resolveTopicTitle(topic);

                    return (
                      <div
                        className="c2-topic-bar-item c2-topic-clickable"
                        key={topic.topic_id || index}
                        onClick={() => handleTopicClick(topic.topic_id)}
                        title="Click to focus your practice on this topic in Stage 3"
                      >
                        <div className="c2-topic-bar-meta">
                          <span className="c2-topic-rank">
                            #{topic.rank ?? index + 1}
                          </span>
                          <strong className="c2-topic-title">
                            {topicTitle}
                          </strong>
                          <code>{topic.topic_id}</code>

                          <span className="c2-topic-count">
                            Ranking Score: <strong>{formatScore(topic.score)}</strong>
                            <small style={{ color: 'var(--muted)', marginLeft: 6 }}>
                              (Ranking Metric — Not Probability)
                            </small>
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
                            style={{
                              width: `${percentWidth}%`,
                              background:
                                selectedDemoBaseline === 'baseline_b'
                                  ? 'linear-gradient(90deg, #6366f1, #3b82f6)'
                                  : selectedDemoBaseline === 'baseline_c'
                                  ? 'linear-gradient(90deg, #0ea5e9, #10b981)'
                                  : 'linear-gradient(90deg, #64748b, #6366f1)',
                            }}
                            aria-valuenow={score}
                            aria-valuemin="0"
                            aria-valuemax="1"
                            role="progressbar"
                          />
                        </div>

                        <div className="c2-topic-bar-subinfo">
                          <span>
                            Predicted Rank: <strong>#{topic.rank ?? index + 1}</strong> of {(demoData.methods?.[selectedDemoBaseline]?.predictions || []).length} topics
                          </span>
                          <span>
                            Score Type: <strong>{topic.score_type || 'Ranking Score'}</strong>
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* COMPARATIVE WALK-FORWARD EVALUATION RESULTS */}
              <div className="c2-evidence-panel">
                <div className="c2-panel-head-row">
                  <div>
                    <h3>Comparative Chronological Walk-Forward Evaluation</h3>
                    <p className="c2-panel-desc">
                      Rigorous chronological cross-validation across 3 independent walk-forward evaluation folds. Models are trained strictly on sessions prior to the test exam, preventing lookahead bias.
                    </p>
                  </div>
                  <span className="c2-paper-badge">
                    {demoData.chronological_evaluation?.eligible_evaluation_splits ?? 3} Evaluation Folds
                  </span>
                </div>

                <div className="c2-table-wrap">
                  <table className="c2-table">
                    <thead>
                      <tr>
                        <th>Prediction Model</th>
                        <th style={{ textAlign: 'center' }}>Walk-Forward Precision@3</th>
                        <th style={{ textAlign: 'center' }}>Walk-Forward Recall@3</th>
                        <th style={{ textAlign: 'center' }}>Mean Reciprocal Rank (MRR)</th>
                        <th style={{ textAlign: 'center' }}>Brier Score</th>
                        <th>Algorithmic Mechanism</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Method A */}
                      <tr>
                        <td>
                          <strong>Baseline A: Historical Frequency</strong>
                          <br />
                          <small style={{ color: 'var(--muted)' }}>Unweighted cumulative empirical ratio</small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatPercent(
                            demoData.chronological_evaluation?.comparative_metrics?.historical_frequency?.['mean_precision@3']
                          )}{' '}
                          <small style={{ color: 'var(--muted)', fontWeight: 400 }}>
                            ({formatScore(demoData.chronological_evaluation?.comparative_metrics?.historical_frequency?.['mean_precision@3'])})
                          </small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatPercent(
                            demoData.chronological_evaluation?.comparative_metrics?.historical_frequency?.['mean_recall@3']
                          )}{' '}
                          <small style={{ color: 'var(--muted)', fontWeight: 400 }}>
                            ({formatScore(demoData.chronological_evaluation?.comparative_metrics?.historical_frequency?.['mean_recall@3'])})
                          </small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatScore(
                            demoData.chronological_evaluation?.comparative_metrics?.historical_frequency?.mean_reciprocal_rank
                          )}
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatScore(
                            demoData.chronological_evaluation?.comparative_metrics?.historical_frequency?.mean_brier_score
                          )}
                        </td>
                        <td>
                          <small>Equally weights all prior exam appearances. Robust against sudden single-session anomalies.</small>
                        </td>
                      </tr>

                      {/* Method B */}
                      <tr style={{ background: 'rgba(99, 102, 241, 0.04)' }}>
                        <td>
                          <strong style={{ color: '#4338ca' }}>Baseline B: Recency-Weighted Frequency</strong>
                          <br />
                          <small style={{ color: 'var(--muted)' }}>Exponential decay (λ=0.75)</small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700, color: '#4338ca' }}>
                          {formatPercent(
                            demoData.chronological_evaluation?.comparative_metrics?.recency_weighted_frequency?.['mean_precision@3']
                          )}{' '}
                          <small style={{ color: 'var(--muted)', fontWeight: 400 }}>
                            ({formatScore(demoData.chronological_evaluation?.comparative_metrics?.recency_weighted_frequency?.['mean_precision@3'])})
                          </small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700, color: '#4338ca' }}>
                          {formatPercent(
                            demoData.chronological_evaluation?.comparative_metrics?.recency_weighted_frequency?.['mean_recall@3']
                          )}{' '}
                          <small style={{ color: 'var(--muted)', fontWeight: 400 }}>
                            ({formatScore(demoData.chronological_evaluation?.comparative_metrics?.recency_weighted_frequency?.['mean_recall@3'])})
                          </small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700, color: '#4338ca' }}>
                          {formatScore(
                            demoData.chronological_evaluation?.comparative_metrics?.recency_weighted_frequency?.mean_reciprocal_rank
                          )}
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700, color: '#4338ca' }}>
                          {formatScore(
                            demoData.chronological_evaluation?.comparative_metrics?.recency_weighted_frequency?.mean_brier_score
                          )}
                        </td>
                        <td>
                          <small>Weights recent exam papers more heavily to reflect curriculum shifts and modern lecturer focus.</small>
                        </td>
                      </tr>

                      {/* Method C */}
                      <tr>
                        <td>
                          <strong>Baseline C: Regularized Statistical Model</strong>
                          <br />
                          <small style={{ color: 'var(--muted)' }}>L2 Ridge linear trend regression</small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatPercent(
                            demoData.chronological_evaluation?.comparative_metrics?.regularized_statistical_model?.['mean_precision@3']
                          )}{' '}
                          <small style={{ color: 'var(--muted)', fontWeight: 400 }}>
                            ({formatScore(demoData.chronological_evaluation?.comparative_metrics?.regularized_statistical_model?.['mean_precision@3'])})
                          </small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatPercent(
                            demoData.chronological_evaluation?.comparative_metrics?.regularized_statistical_model?.['mean_recall@3']
                          )}{' '}
                          <small style={{ color: 'var(--muted)', fontWeight: 400 }}>
                            ({formatScore(demoData.chronological_evaluation?.comparative_metrics?.regularized_statistical_model?.['mean_recall@3'])})
                          </small>
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatScore(
                            demoData.chronological_evaluation?.comparative_metrics?.regularized_statistical_model?.mean_reciprocal_rank
                          )}
                        </td>
                        <td style={{ textAlign: 'center', fontWeight: 700 }}>
                          {formatScore(
                            demoData.chronological_evaluation?.comparative_metrics?.regularized_statistical_model?.mean_brier_score
                          )}
                        </td>
                        <td>
                          <small>Fits a regularized chronological slope to identify emerging topics while damping noise.</small>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div style={{ marginTop: 14, fontSize: '0.8rem', color: 'var(--muted)', lineHeight: 1.5 }}>
                  * <strong>Precision@3</strong>: Proportion of the model's top 3 recommended topics that were genuinely tested in the held-out target session.
                  <br />
                  * <strong>Recall@3</strong>: Proportion of all tested topics in the held-out session captured within the model's top 3 recommendations.
                  <br />
                  * <strong>Brier Score</strong>: Mean squared error between predicted scores and actual binary presence (lower values indicate superior probability calibration).
                </div>
              </div>

              {/* WALK-FORWARD CHRONOLOGICAL FOLDS BREAKDOWN */}
              {Array.isArray(demoData.chronological_evaluation?.splits_evaluated) && (
                <div className="c2-evidence-panel">
                  <div className="c2-panel-head-row">
                    <div>
                      <h4>Walk-Forward Evaluation Folds (Zero Future-Data Leakage)</h4>
                      <p className="c2-panel-desc">
                        Demonstration of the chronological validation sequence: in each fold, the model was fitted strictly on prior sessions and evaluated on the subsequent session.
                      </p>
                    </div>
                  </div>

                  <div className="c2-table-wrap">
                    <table className="c2-table">
                      <thead>
                        <tr>
                          <th>Fold</th>
                          <th>Training Sessions (Prior Only)</th>
                          <th>Test Target Session</th>
                          <th>Actual Topics Tested</th>
                          <th>Validation Standard</th>
                        </tr>
                      </thead>
                      <tbody>
                        {demoData.chronological_evaluation.splits_evaluated.map((split) => (
                          <tr key={split.split_index}>
                            <td>
                              <strong>Fold {split.split_index}</strong>
                            </td>
                            <td>
                              {split.train_academic_years?.join(', ') || `${split.train_sessions_count} sessions`} ({split.train_sessions_count} past sessions)
                            </td>
                            <td>
                              <strong>{split.test_session_id}</strong> ({split.test_academic_year})
                            </td>
                            <td>
                              {split.actual_topics_count} topics ({split.actual_topics_tested?.map(displayTopicName).join(', ')})
                            </td>
                            <td>
                              <span className="pill status-approved" style={{ fontSize: '0.72rem' }}>
                                Strictly Past Data (Zero Leakage)
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Research Methodology and Limitations */}
              {Array.isArray(demoData.chronological_evaluation?.sample_size_limitations) && (
                <div className="c2-evidence-limitations">
                  <h3>Demonstration Scope & Research Integrity Standards</h3>
                  <ul>
                    {demoData.chronological_evaluation.sample_size_limitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                    <li>
                      <strong>Zero Leakage Assurance:</strong> Under no circumstances is future examination data visible during historical feature extraction or baseline evaluation.
                    </li>
                    <li>
                      <strong>Reversibility:</strong> Returning to Authentic Evidence restores standard institutional verification controls without impacting any lecturer review queues or persistent exam databases.
                    </li>
                  </ul>
                </div>
              )}

              {/* Bottom Actions Row */}
              <div className="c2-demo-actions-row">
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => setIsDemoMode(false)}
                >
                  ← Return to Authentic Evidence
                </button>

                <button
                  type="button"
                  className="btn primary"
                  onClick={onProceedToSetup}
                >
                  Configure Practice Mock (Stage 3) ➔
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        /* ======================================================== */
        /* AUTHENTIC HISTORICAL EVIDENCE VIEW (PRESERVED)           */
        /* ======================================================== */
        <>
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
                      <strong>What you can do right now:</strong> You can explore our synthetic experimental prediction demo to see how the M20 models work, or proceed directly to Stage 3 to practice with authentic questions and development fixtures.
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
                    <button
                      type="button"
                      className="c2-demo-toggle-btn"
                      onClick={() => setIsDemoMode(true)}
                      style={{ marginLeft: 10 }}
                    >
                      🔬 Explore Prediction Models — Synthetic Demo
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
        </>
      )}
    </section>
  );
}
