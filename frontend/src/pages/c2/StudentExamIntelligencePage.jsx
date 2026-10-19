import React, { useEffect, useState, useCallback, useMemo } from 'react';

import {
  getC2Modules,
  getC2StudentQuestions,
  getC2TopicPredictions,
  generateC2MockExam,
  generateC2MockFromTwin,
  generateC2SyntheticMockExam,
  submitC2MockAttempt,
  getC2MockAttempts,
} from '../../services/c2Api.js';

import ExamIntelligenceStepper from './components/ExamIntelligenceStepper.jsx';
import ActiveAttemptView from './components/ActiveAttemptView.jsx';
import AttemptResultView from './components/AttemptResultView.jsx';
import AttemptHistoryView from './components/AttemptHistoryView.jsx';

import './studentExamIntelligence.css';

const PAGE_SIZE = 10;

// --------------------------------------------------
// Helpers
// --------------------------------------------------

function getModuleKey(module) {
  return typeof module === 'string'
    ? module
    : module?.module_key || '';
}

function moduleLabel(module) {
  if (typeof module !== 'string') {
    return (
      module?.module_name ||
      module?.moduleName ||
      module?.name ||
      module?.module_key ||
      'Unnamed module'
    );
  }

  return module
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function display(value) {
  if (value === null || value === undefined || value === '') {
    return 'Not available';
  }
  return String(value).replaceAll('_', ' ');
}

function normalizeLimitations(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) =>
    typeof item === 'string' ? item : JSON.stringify(item)
  );
}

// --------------------------------------------------
// Statistics Card
// --------------------------------------------------

function StatCard({ label, value, note, tone = 'blue' }) {
  return (
    <div className={`c2-student-stat c2-tone-${tone}`}>
      <span className="c2-student-stat-label">{label}</span>
      <strong className="c2-student-stat-value">{value}</strong>
      <span className="c2-student-stat-note">{note}</span>
    </div>
  );
}

// --------------------------------------------------
// Question Card (Question Explorer & Practice Preview)
// --------------------------------------------------

function QuestionCard({ question, number, practice = false }) {
  const isSynthetic = question.source_type === 'synthetic';
  const marksDisplay =
    question.marks !== null && question.marks !== undefined
      ? `${question.marks} marks`
      : 'Unassessed';

  return (
    <article className="c2-student-question">
      <div className="c2-student-question-heading">
        <div className="c2-student-question-title">
          <span className="c2-student-question-number">Q{number}</span>
          <div>
            <span className="c2-student-question-caption">
              {isSynthetic
                ? 'SYNTHETIC PRACTICE QUESTION (EXPERIMENTAL)'
                : practice
                  ? 'PRACTICE MOCK QUESTION'
                  : 'AUTHENTIC EXAMINATION QUESTION'}
            </span>
            <h3>Question {number}</h3>
          </div>
        </div>

        <span className="c2-student-pill">{marksDisplay}</span>
      </div>

      <p className="c2-student-question-text">
        {question.question_text || 'Question text unavailable'}
      </p>

      <div className="c2-student-metadata">
        <div>
          <span>Topic</span>
          <strong>{display(question.topic_id || question.topic)}</strong>
        </div>

        <div>
          <span>Difficulty</span>
          <strong>{display(question.difficulty)}</strong>
        </div>

        <div>
          <span>Source</span>
          <strong>{display(question.source_type)}</strong>
        </div>

        <div>
          <span>Verification</span>
          <strong>{display(question.verification_status || 'unverified')}</strong>
        </div>

        {!practice && (
          <>
            <div>
              <span>Bloom level</span>
              <strong>{display(question.bloom_level)}</strong>
            </div>

            <div>
              <span>Classification</span>
              <strong>{display(question.classification_method)}</strong>
            </div>

            <div>
              <span>Exam year</span>
              <strong>{display(question.calendar_year)}</strong>
            </div>
          </>
        )}
      </div>

      {!practice && question.verification_status !== 'verified' && (
        <p className="c2-student-warning">
          Topic classification has not been verified by course lecturers.
        </p>
      )}
    </article>
  );
}

// --------------------------------------------------
// Main Student Exam Intelligence Component
// --------------------------------------------------

export default function StudentExamIntelligencePage() {
  // Navigation Stage: 'overview' | 'evidence' | 'setup' | 'attempt' | 'results'
  const [stage, setStage] = useState('overview');

  // Module selection
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('');
  const [refresh, setRefresh] = useState(0);

  // Stage 1: Question bank explorer data
  const [page, setPage] = useState(1);
  const [questionBankResult, setQuestionBankResult] = useState(null);
  const [questionBankLoading, setQuestionBankLoading] = useState(false);
  const [questionBankError, setQuestionBankError] = useState('');
  const [showQuestionExplorer, setShowQuestionExplorer] = useState(false);

  // Stage 2: Historical topic evidence
  const [prediction, setPrediction] = useState(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState('');

  // Stage 3: Practice mock exam configuration
  const [generationMode, setGenerationMode] = useState('standard'); // 'standard' | 'twin' | 'synthetic'
  const [targetMarks, setTargetMarks] = useState(100);
  const [maxQuestions, setMaxQuestions] = useState(20);
  const [difficulty, setDifficulty] = useState('');
  const [topicsInput, setTopicsInput] = useState('');
  const [generatingMock, setGeneratingMock] = useState(false);
  const [generationError, setGenerationError] = useState('');
  const [generatedPaper, setGeneratedPaper] = useState(null);
  const [paperResultMode, setPaperResultMode] = useState(null);

  // Stage 4: Active exam attempt
  const [activeAttempt, setActiveAttempt] = useState(null);
  const [submittingAttempt, setSubmittingAttempt] = useState(false);
  const [attemptError, setAttemptError] = useState('');

  // Stage 5: Results & History
  const [selectedResultAttempt, setSelectedResultAttempt] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [loadingAttempts, setLoadingAttempts] = useState(false);

  // --------------------------------------------------
  // 1. Load Modules
  // --------------------------------------------------
  useEffect(() => {
    let active = true;

    async function loadModules() {
      try {
        const response = await getC2Modules();
        const items = Array.isArray(response)
          ? response
          : response?.modules || [];

        if (!active) return;
        setModules(items);

        setModuleKey((prev) => {
          if (prev && items.some((item) => getModuleKey(item) === prev)) {
            return prev;
          }
          return items.length > 0 ? getModuleKey(items[0]) : '';
        });
      } catch (err) {
        console.error('Failed to load C2 modules:', err);
      }
    }

    loadModules();
    return () => {
      active = false;
    };
  }, []);

  // --------------------------------------------------
  // 2. Load Attempt History for Selected Module
  // --------------------------------------------------
  const loadAttempts = useCallback(async () => {
    if (!moduleKey) {
      setAttempts([]);
      return;
    }
    setLoadingAttempts(true);
    try {
      const data = await getC2MockAttempts({ moduleKey });
      const list = Array.isArray(data) ? data : data?.attempts || [];
      setAttempts(list);
    } catch (err) {
      console.warn('Unable to load attempt history:', err);
    } finally {
      setLoadingAttempts(false);
    }
  }, [moduleKey]);

  useEffect(() => {
    loadAttempts();
  }, [loadAttempts, refresh]);

  // --------------------------------------------------
  // 3. Load Topic Predictions & Historical Evidence
  // --------------------------------------------------
  useEffect(() => {
    if (!moduleKey) {
      setPrediction(null);
      return;
    }
    let active = true;

    async function loadEvidence() {
      setPredictionLoading(true);
      setPredictionError('');
      try {
        const data = await getC2TopicPredictions(moduleKey);
        if (active) setPrediction(data);
      } catch (err) {
        if (active) {
          setPredictionError(err?.message || 'Unable to load topic evidence.');
        }
      } finally {
        if (active) setPredictionLoading(false);
      }
    }

    loadEvidence();
    return () => {
      active = false;
    };
  }, [moduleKey, refresh]);

  // --------------------------------------------------
  // 4. Load Question Bank Explorer
  // --------------------------------------------------
  useEffect(() => {
    if (!moduleKey) {
      setQuestionBankResult(null);
      return;
    }
    let active = true;

    async function loadQuestions() {
      setQuestionBankLoading(true);
      setQuestionBankError('');
      try {
        const data = await getC2StudentQuestions({
          moduleKey,
          page,
          pageSize: PAGE_SIZE,
        });
        if (active) setQuestionBankResult(data);
      } catch (err) {
        if (active) {
          setQuestionBankError(err?.message || 'Unable to load questions.');
        }
      } finally {
        if (active) setQuestionBankLoading(false);
      }
    }

    loadQuestions();
    return () => {
      active = false;
    };
  }, [moduleKey, page, refresh]);

  // --------------------------------------------------
  // Module Switching Logic & Safeguards
  // --------------------------------------------------
  function handleModuleChange(newKey) {
    if (newKey === moduleKey) return;

    if (activeAttempt) {
      const confirmChange = window.confirm(
        'You have an active exam attempt in progress. Changing modules will discard your current attempt. Do you want to proceed?'
      );
      if (!confirmChange) return;
    }

    setModuleKey(newKey);
    setPage(1);
    setGeneratedPaper(null);
    setPaperResultMode(null);
    setActiveAttempt(null);
    setGenerationError('');
    setAttemptError('');

    // If changing module while on attempt or results view, safely return to overview
    if (stage === 'attempt' || stage === 'results') {
      setSelectedResultAttempt(null);
      setStage('overview');
    }
  }

  // --------------------------------------------------
  // Stage 3: Mock Generation Handler
  // --------------------------------------------------
  async function handleGenerateMock(e) {
    if (e) e.preventDefault();
    if (!moduleKey || generatingMock) return;

    const maximum = Number(maxQuestions);
    const requestedMode = generationMode;

    if (requestedMode === 'synthetic') {
      if (!Number.isInteger(maximum) || maximum < 1 || maximum > 20) {
        setGenerationError('Enter a valid question count between 1 and 20.');
        return;
      }
    } else {
      const marks = Number(targetMarks);
      if (
        !Number.isInteger(marks) ||
        marks < 1 ||
        marks > 200 ||
        !Number.isInteger(maximum) ||
        maximum < 1 ||
        maximum > 30
      ) {
        setGenerationError('Enter valid target marks (1-200) and max questions (1-30).');
        return;
      }
    }

    const preferredTopics = topicsInput
      .split(',')
      .map((topic) => topic.trim())
      .filter(Boolean);

    const options = {
      moduleKey,
      targetMarks: Number(targetMarks),
      maxQuestions: maximum,
      seed: 42,
    };

    setGeneratingMock(true);
    setGenerationError('');
    setGeneratedPaper(null);
    setPaperResultMode(null);

    try {
      let response;
      if (requestedMode === 'synthetic') {
        response = await generateC2SyntheticMockExam({
          moduleKey,
          questionCount: maximum,
          seed: 42,
        });
      } else if (requestedMode === 'twin') {
        response = await generateC2MockFromTwin(options);
      } else {
        response = await generateC2MockExam({
          ...options,
          preferredTopics,
          difficulty: difficulty || null,
        });
      }

      setGeneratedPaper(response);
      setPaperResultMode(requestedMode);
    } catch (err) {
      setGenerationError(err?.message || 'Unable to generate practice mock exam.');
    } finally {
      setGeneratingMock(false);
    }
  }

  // --------------------------------------------------
  // Stage 4: Attempt Submission Handler
  // --------------------------------------------------
  async function handleSubmitAttempt(payload) {
    setSubmittingAttempt(true);
    setAttemptError('');
    try {
      const submitted = await submitC2MockAttempt(payload);
      setActiveAttempt(null);
      setSelectedResultAttempt(submitted);
      setStage('results');
      loadAttempts();
      return submitted;
    } catch (err) {
      const message =
        err?.message || 'Failed to submit practice attempt. Please try again.';
      setAttemptError(message);
      throw err;
    } finally {
      setSubmittingAttempt(false);
    }
  }

  // --------------------------------------------------
  // Derived Data
  // --------------------------------------------------
  const selectedModule = modules.find((m) => getModuleKey(m) === moduleKey);
  const currentModuleName = selectedModule
    ? moduleLabel(selectedModule)
    : 'Select a module';

  const evidence = prediction?.historical_evidence;
  const authenticQuestionsCount = evidence?.authentic_questions ?? questionBankResult?.total ?? 0;
  const distinctPapersCount = evidence?.distinct_papers ?? 0;
  const verifiedTopicCount = evidence?.verified_topic_questions ?? 0;
  const coverageRatio = Number(evidence?.verified_topic_coverage ?? 0);
  const coveragePercent = `${(Number.isFinite(coverageRatio) ? coverageRatio * 100 : 0).toFixed(0)}%`;

  // Academic years
  const academicYears = useMemo(() => {
    if (Array.isArray(evidence?.calendar_years) && evidence.calendar_years.length > 0) {
      const sorted = [...evidence.calendar_years].sort();
      return sorted.length === 1 ? `${sorted[0]}` : `${sorted[0]} – ${sorted[sorted.length - 1]}`;
    }
    if (evidence?.year_distribution && Object.keys(evidence.year_distribution).length > 0) {
      const years = Object.keys(evidence.year_distribution).sort();
      return years.length === 1 ? `${years[0]}` : `${years[0]} – ${years[years.length - 1]}`;
    }
    return 'None recorded';
  }, [evidence]);

  // Normalized paper structure
  const paper =
    generatedPaper?.mock ??
    generatedPaper?.mock_exam ??
    generatedPaper?.paper ??
    generatedPaper?.mockExam ??
    generatedPaper;

  const paperQuestions = Array.isArray(paper?.questions) ? paper.questions : [];
  const isSyntheticPaper =
    paper?.source_type === 'synthetic' || paperResultMode === 'synthetic';
  const paperTotalMarks = paper?.total_marks ?? paper?.totalMarks ?? 0;
  const paperRequestedMarks = paper?.target_marks ?? paper?.targetMarks ?? targetMarks;
  const paperLimitations = [
    ...normalizeLimitations(paper?.limitations),
    ...(paper !== generatedPaper ? normalizeLimitations(generatedPaper?.limitations) : []),
  ];

  const personalization =
    generatedPaper?.personalization ?? paper?.personalization ?? null;
  const personalizationApplied = personalization?.applied === true;
  const personalizationStatus =
    personalization?.status ?? personalization?.reason ?? 'unavailable';

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------
  return (
    <main className="c2-student" aria-label="Student Exam Intelligence Dashboard">
      {/* ======================================================== */}
      {/* TOP HEADER & MODULE SELECTION BAR                        */}
      {/* ======================================================== */}
      <section className="c2-student-top">
        <div className="c2-student-hero">
          <span className="c2-student-eyebrow">COMPONENT 2 — EXAM INTELLIGENCE</span>
          <h1>Prepare Smarter for Software Engineering Exams</h1>
          <p>
            Connected 5-stage student journey: historical evidence, topic predictions,
            curated practice mock generation, exam attempt, and pending evaluation tracking.
          </p>

          <div className="c2-student-hero-footer">
            <span className="c2-student-hero-chip">AdaptiveLearnSE C2</span>
            <span className="c2-student-hero-chip">{modules.length} Modules Supported</span>
            <span className="c2-student-hero-chip">Active: {currentModuleName}</span>
          </div>
        </div>

        <div className="c2-student-module-panel">
          <span className="c2-student-panel-eyebrow">ACTIVE MODULE</span>
          <h2>Select Examination Module</h2>
          <p>Module selection is preserved across all 5 workflow stages.</p>

          <label htmlFor="c2-module-select">Module</label>
          <select
            id="c2-module-select"
            value={moduleKey}
            disabled={modules.length === 0}
            onChange={(e) => handleModuleChange(e.target.value)}
          >
            {modules.length === 0 && (
              <option value="">No modules available</option>
            )}
            {modules.map((m) => {
              const key = getModuleKey(m);
              return (
                <option key={key} value={key}>
                  {moduleLabel(m)}
                </option>
              );
            })}
          </select>

          <button
            className="c2-student-refresh"
            type="button"
            onClick={() => setRefresh((v) => v + 1)}
            disabled={!moduleKey || predictionLoading || questionBankLoading}
            title="Refresh questions, evidence and attempts from the server"
          >
            {predictionLoading || questionBankLoading
              ? 'Refreshing...'
              : '🔄 Refresh Dataset & Evidence'}
          </button>
        </div>
      </section>

      {/* ======================================================== */}
      {/* 5-STAGE WORKFLOW STEPPER NAVIGATION                      */}
      {/* ======================================================== */}
      <ExamIntelligenceStepper
        currentStage={stage}
        onSelectStage={(newStage) => setStage(newStage)}
        canAccessAttempt={Boolean(generatedPaper)}
        canAccessResults={Boolean(selectedResultAttempt || attempts.length > 0)}
        hasActiveAttempt={Boolean(activeAttempt)}
      />

      {/* ======================================================== */}
      {/* STAGE 1 — EXAM INTELLIGENCE OVERVIEW                     */}
      {/* ======================================================== */}
      {stage === 'overview' && (
        <div className="c2-stage-container" aria-label="Stage 1: Exam Intelligence Overview">
          {/* Statistics Grid */}
          <section className="c2-student-stats" aria-label="Module statistics">
            <StatCard
              label="Authentic Questions"
              value={authenticQuestionsCount}
              note="From verified past papers"
              tone="blue"
            />
            <StatCard
              label="Historical Papers"
              value={distinctPapersCount}
              note="Distinct examined papers"
              tone="teal"
            />
            <StatCard
              label="Academic Years"
              value={academicYears}
              note="Covered in historical data"
              tone="sky"
            />
            <StatCard
              label="Topic Coverage"
              value={coveragePercent}
              note={`${verifiedTopicCount} verified labels`}
              tone="indigo"
            />
          </section>

          {/* Module Intelligence & Readiness Summary */}
          <section className="c2-student-bank">
            <div className="c2-student-bank-header">
              <div>
                <span className="c2-student-panel-eyebrow">STAGE 1 — OVERVIEW</span>
                <h2>{currentModuleName} Examination Readiness</h2>
                <p>
                  Explore historical evidence, topic distributions, and take practice examinations.
                </p>
              </div>

              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => setStage('evidence')}
                >
                  📊 Topic Evidence (Stage 2) ➔
                </button>
                <button
                  type="button"
                  className="btn primary"
                  onClick={() => setStage('setup')}
                >
                  ✍️ Practice Setup (Stage 3) ➔
                </button>
              </div>
            </div>

            <div className="c2-practice-modes-overview">
              <div className="c2-mode-card">
                <span className="c2-mode-badge authentic">📜 Authentic Past-Paper Practice</span>
                <h4>Real SLIIT Examination Questions</h4>
                <p>
                  {authenticQuestionsCount > 0
                    ? `${authenticQuestionsCount} authentic questions available across ${distinctPapersCount} past examination papers.`
                    : 'Authentic past-paper questions are not yet ingested for this module.'}
                </p>
                <span className="c2-student-caption">
                  Status: {authenticQuestionsCount > 0 ? '✅ Available' : '⚠️ Limited data'}
                </span>
              </div>

              <div className="c2-mode-card">
                <span className="c2-mode-badge twin">🧬 C1 Digital Twin Personalized</span>
                <h4>Personalized Revision Mock</h4>
                <p>
                  Uses Component 1 student diagnostic mastery when verified topic mappings exist. Falls back to standard practice if mastery is unavailable.
                </p>
                <span className="c2-student-caption">
                  Status: {verifiedTopicCount > 0 ? '✅ Personalized' : 'ℹ️ Standard fallback'}
                </span>
              </div>

              <div className="c2-mode-card">
                <span className="c2-mode-badge synthetic">🧪 Synthetic Practice (Experimental)</span>
                <h4>M16 Synthetic Question Fixtures</h4>
                <p>
                  Available for all 8 modules (100 synthetic development questions per module). Unassessed marks, ideal for revision format familiarity.
                </p>
                <span className="c2-student-caption">
                  Status: ✅ Supported across all 8 modules
                </span>
              </div>
            </div>

            {/* Recent Mock Attempts for this module */}
            <div className="c2-overview-recent-attempts" style={{ marginTop: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Recent Practice Exam Attempts</h3>
                {attempts.length > 0 && (
                  <button
                    type="button"
                    className="btn secondary small-btn"
                    onClick={() => {
                      setSelectedResultAttempt(attempts[0]);
                      setStage('results');
                    }}
                  >
                    View All Results (Stage 5) ➔
                  </button>
                )}
              </div>

              {loadingAttempts && (
                <div className="c2-student-loading">Loading recent attempts...</div>
              )}

              {!loadingAttempts && attempts.length === 0 && (
                <div className="c2-student-empty" style={{ padding: '20px' }}>
                  <p className="c2-student-muted" style={{ margin: 0 }}>
                    No practice mock attempts recorded yet for {currentModuleName}.
                  </p>
                  <button
                    type="button"
                    className="btn primary small-btn"
                    style={{ marginTop: 10 }}
                    onClick={() => setStage('setup')}
                  >
                    Start Your First Practice Exam
                  </button>
                </div>
              )}

              {!loadingAttempts && attempts.length > 0 && (
                <div className="c2-recent-attempts-list">
                  {attempts.slice(0, 3).map((att) => (
                    <div key={att.attemptId} className="c2-recent-attempt-row">
                      <div>
                        <strong>{att.attemptId}</strong>
                        <span className="c2-student-muted" style={{ marginLeft: 10, fontSize: '0.82rem' }}>
                          {att.submittedAt ? new Date(att.submittedAt).toLocaleDateString() : 'Recent'}
                        </span>
                        <span className="pill status-pending" style={{ marginLeft: 10, fontSize: '0.74rem' }}>
                          Pending Marking
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span className="c2-student-muted" style={{ fontSize: '0.85rem' }}>
                          {att.answeredCount} / {att.questionCount} questions
                        </span>
                        <button
                          type="button"
                          className="btn secondary small-btn"
                          onClick={() => {
                            setSelectedResultAttempt(att);
                            setStage('results');
                          }}
                        >
                          View Result ➔
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Toggleable Question Explorer */}
            <div style={{ marginTop: 24, paddingTop: 18, borderTop: '1px solid var(--line)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Browse Authentic Question Bank</h3>
                  <p className="c2-student-muted" style={{ margin: '4px 0 0' }}>
                    Inspect individual authentic examination questions, Bloom levels, and marks.
                  </p>
                </div>

                <button
                  type="button"
                  className="btn secondary small-btn"
                  onClick={() => setShowQuestionExplorer((v) => !v)}
                >
                  {showQuestionExplorer ? 'Hide Question Explorer ▲' : 'Open Question Explorer ▼'}
                </button>
              </div>

              {showQuestionExplorer && (
                <div style={{ marginTop: 16 }}>
                  {questionBankLoading && (
                    <div className="c2-student-loading">Loading examination questions...</div>
                  )}

                  {questionBankError && (
                    <div className="c2-student-error" role="alert">
                      <strong>Unable to load questions</strong>
                      <p>{questionBankError}</p>
                    </div>
                  )}

                  {!questionBankLoading && questionBankResult && (
                    <>
                      {questionBankResult.questions?.length === 0 ? (
                        <div className="c2-student-empty">
                          <h4>No questions available</h4>
                          <p className="c2-student-muted">
                            No processed questions found for this module.
                          </p>
                        </div>
                      ) : (
                        <div className="c2-student-question-list">
                          {questionBankResult.questions.map((q, idx) => (
                            <QuestionCard
                              key={q.question_id || idx}
                              question={q}
                              number={(page - 1) * PAGE_SIZE + idx + 1}
                            />
                          ))}
                        </div>
                      )}

                      {/* Pagination */}
                      {questionBankResult.total_pages > 1 && (
                        <div className="c2-student-pagination" style={{ marginTop: 16 }}>
                          <span>
                            Page <strong>{page}</strong> of{' '}
                            <strong>{questionBankResult.total_pages}</strong>
                          </span>
                          <div className="c2-student-pagination-actions">
                            <button
                              type="button"
                              disabled={page <= 1}
                              onClick={() => setPage((v) => v - 1)}
                            >
                              Previous
                            </button>
                            <button
                              type="button"
                              disabled={page >= questionBankResult.total_pages}
                              onClick={() => setPage((v) => v + 1)}
                            >
                              Next
                            </button>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </section>
        </div>
      )}

      {/* ======================================================== */}
      {/* STAGE 2 — TOPIC PREDICTIONS & HISTORICAL EVIDENCE        */}
      {/* ======================================================== */}
      {stage === 'evidence' && (
        <section className="c2-student-bank" aria-label="Stage 2: Topic Evidence and Historical Analysis">
          <div className="c2-student-bank-header">
            <div>
              <span className="c2-student-panel-eyebrow">STAGE 2 — HISTORICAL EVIDENCE</span>
              <h2>Historical Examination Topic Evidence</h2>
              <p>
                Descriptive analysis of verified past-paper questions for {currentModuleName}.
              </p>
            </div>

            <button
              type="button"
              className="btn primary"
              onClick={() => setStage('setup')}
            >
              Configure Practice Mock (Stage 3) ➔
            </button>
          </div>

          {/* Academic Integrity Disclaimer Banner */}
          <div className="c2-attempt-integrity-box">
            <strong>Critical Academic Integrity Requirement:</strong>
            <p style={{ margin: '4px 0 0' }}>
              Future-exam predictive machine learning (M20) is currently under active research.
              The distributions and study priorities displayed below represent <strong>descriptive historical frequencies</strong> from
              available authentic past papers. They do <strong>NOT</strong> represent probability percentages of appearing on the next examination.
            </p>
          </div>

          {predictionLoading && (
            <div className="c2-student-loading" role="status">
              Loading historical topic evidence...
            </div>
          )}

          {predictionError && (
            <div className="c2-student-error" role="alert">
              <strong>Unable to load topic evidence</strong>
              <p>{predictionError}</p>
            </div>
          )}

          {!predictionLoading && prediction && (
            <>
              {/* Stat Cards */}
              <div className="c2-evidence-grid">
                <StatCard
                  label="Authentic questions"
                  value={evidence?.authentic_questions ?? 0}
                  note="Available historical questions"
                  tone="blue"
                />
                <StatCard
                  label="Past papers"
                  value={evidence?.distinct_papers ?? 0}
                  note="Distinct source papers"
                  tone="teal"
                />
                <StatCard
                  label="Verified topic labels"
                  value={evidence?.verified_topic_questions ?? 0}
                  note="Academically verified classifications"
                  tone="indigo"
                />
                <StatCard
                  label="Topic coverage"
                  value={coveragePercent}
                  note="Verified share of authentic questions"
                  tone="sky"
                />
              </div>

              {/* Study priorities or insufficient evidence message */}
              {prediction.prediction_ready === true ? (
                <div className="c2-evidence-message">
                  <h3>Historical Topic Frequencies & Study Priorities</h3>
                  <p>
                    These priorities describe historical topic frequency from verified examination questions.
                    They are not probabilities of appearing in the next examination.
                  </p>

                  {Array.isArray(prediction.study_priorities) && prediction.study_priorities.length > 0 && (
                    <div className="c2-priority-list">
                      {prediction.study_priorities.map((topic, index) => (
                        <div className="c2-priority-item" key={topic.topic_id || index}>
                          <strong>
                            {topic.rank ?? index + 1}. {display(topic.topic_id)}
                          </strong>
                          <span>{topic.question_count ?? 0} historical questions</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="c2-evidence-message">
                  <h3>Insufficient Evidence for Topic Ranking</h3>
                  <p>
                    Available historical papers and verified classifications do not yet support a defensible topic ranking for {currentModuleName}.
                  </p>
                  <p className="c2-student-muted">
                    You can still generate practice mock examinations using authentic questions or synthetic development fixtures.
                  </p>
                </div>
              )}

              {/* Limitations */}
              {Array.isArray(prediction.limitations) && prediction.limitations.length > 0 && (
                <div className="c2-evidence-limitations">
                  <h3>Evidence Limitations</h3>
                  <ul>
                    {prediction.limitations.map((lim, idx) => (
                      <li key={idx}>{typeof lim === 'string' ? lim : JSON.stringify(lim)}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn primary"
                  onClick={() => setStage('setup')}
                >
                  Proceed to Practice Setup (Stage 3) ➔
                </button>
              </div>
            </>
          )}
        </section>
      )}

      {/* ======================================================== */}
      {/* STAGE 3 — PRACTICE SETUP                                 */}
      {/* ======================================================== */}
      {stage === 'setup' && (
        <section className="c2-student-bank" aria-label="Stage 3: Practice Mock Exam Setup">
          <div className="c2-student-bank-header">
            <div>
              <span className="c2-student-panel-eyebrow">STAGE 3 — PRACTICE SETUP</span>
              <h2>Configure Practice Mock Examination</h2>
              <p>
                Configure exam parameters for {currentModuleName}. Choose between authentic past papers, personalized revision, or synthetic practice.
              </p>
            </div>

            <button
              type="button"
              className="btn secondary"
              onClick={() => setStage('evidence')}
            >
              ⬅ View Topic Evidence
            </button>
          </div>

          <form className="c2-mock-form" onSubmit={handleGenerateMock}>
            {/* Practice Mode Selector */}
            <div className="c2-mock-field c2-mock-wide">
              <label htmlFor="c2-practice-mode-select">Practice Mode</label>
              <select
                id="c2-practice-mode-select"
                value={generationMode}
                disabled={generatingMock}
                onChange={(e) => {
                  const newMode = e.target.value;
                  setGenerationMode(newMode);
                  if (newMode === 'synthetic' && maxQuestions > 20) {
                    setMaxQuestions(5);
                  }
                  setGeneratedPaper(null);
                  setPaperResultMode(null);
                  setGenerationError('');
                }}
              >
                <option value="standard">
                  1. Authentic Past-Paper Practice (Verified Historical Questions)
                </option>
                <option value="twin">
                  2. C1 Digital Twin Personalized Practice (Diagnostic Mastery Guided)
                </option>
                <option value="synthetic">
                  3. Synthetic Practice (Experimental — All 8 Modules Supported)
                </option>
              </select>

              <small>
                {generationMode === 'synthetic'
                  ? 'Synthetic Practice mode generates questions from the M16 synthetic question bank across all 8 modules. Questions are unverified practice fixtures and marks are unassessed.'
                  : generationMode === 'twin'
                    ? 'Digital Twin mode uses your C1 diagnostic mastery information when verified topic mappings and eligible authentic questions are available. Falls back to standard practice if mastery data is absent.'
                    : 'Standard practice builds papers from eligible authentic past-paper questions.'}
              </small>
            </div>

            {/* Mode-Specific Controls */}
            {generationMode === 'synthetic' ? (
              <div className="c2-mock-field">
                <label htmlFor="c2-synth-q-count">Number of Synthetic Questions</label>
                <input
                  id="c2-synth-q-count"
                  type="number"
                  min="1"
                  max="20"
                  step="1"
                  value={maxQuestions}
                  disabled={generatingMock}
                  onChange={(e) => setMaxQuestions(e.target.value)}
                  required
                />
                <small>Select between 1 and 20 synthetic questions.</small>
              </div>
            ) : (
              <>
                <div className="c2-mock-field">
                  <label htmlFor="c2-target-marks">Target Marks</label>
                  <input
                    id="c2-target-marks"
                    type="number"
                    min="1"
                    max="200"
                    step="1"
                    value={targetMarks}
                    disabled={generatingMock}
                    onChange={(e) => setTargetMarks(e.target.value)}
                    required
                  />
                  <small>Target marks for the examination paper (e.g. 100).</small>
                </div>

                <div className="c2-mock-field">
                  <label htmlFor="c2-max-questions">Maximum Questions</label>
                  <input
                    id="c2-max-questions"
                    type="number"
                    min="1"
                    max="30"
                    step="1"
                    value={maxQuestions}
                    disabled={generatingMock}
                    onChange={(e) => setMaxQuestions(e.target.value)}
                    required
                  />
                  <small>Maximum number of questions (1 to 30).</small>
                </div>

                {generationMode === 'standard' && (
                  <>
                    <div className="c2-mock-field">
                      <label htmlFor="c2-difficulty">Preferred Difficulty (Optional)</label>
                      <select
                        id="c2-difficulty"
                        value={difficulty}
                        disabled={generatingMock}
                        onChange={(e) => setDifficulty(e.target.value)}
                      >
                        <option value="">Any difficulty</option>
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>

                    <div className="c2-mock-field c2-mock-wide">
                      <label htmlFor="c2-preferred-topics">Preferred Topic IDs (Optional)</label>
                      <input
                        id="c2-preferred-topics"
                        type="text"
                        value={topicsInput}
                        disabled={generatingMock}
                        placeholder="e.g. indexing, normalization, transactions"
                        onChange={(e) => setTopicsInput(e.target.value)}
                      />
                      <small>
                        Topic preferences are prioritized only when supported by eligible, verified topic labels.
                      </small>
                    </div>
                  </>
                )}
              </>
            )}

            <div className="c2-mock-actions">
              <button
                type="submit"
                className="c2-mock-button"
                disabled={!moduleKey || generatingMock}
              >
                {generatingMock
                  ? 'Generating Practice Mock...'
                  : generationMode === 'synthetic'
                    ? '🧪 Generate Synthetic Practice Paper'
                    : generationMode === 'twin'
                      ? '🧬 Generate Personalized Twin Paper'
                      : '📜 Generate Authentic Practice Paper'}
              </button>
            </div>
          </form>

          {generationError && (
            <div className="c2-student-error" role="alert" style={{ marginTop: 16 }}>
              <strong>Mock generation failed</strong>
              <p>{generationError}</p>
            </div>
          )}

          {/* Generated Exam Preview */}
          {!generatingMock && generatedPaper && (
            <div className="c2-mock-results" style={{ marginTop: 24 }}>
              {isSyntheticPaper && (
                <div className="c2-evidence-message" style={{ borderLeft: '4px solid #f59e0b', background: 'rgba(245, 158, 11, 0.06)' }}>
                  <h3 style={{ color: '#d97706' }}>🧪 Synthetic Practice Paper (Experimental)</h3>
                  <p>
                    This practice paper contains <strong>M16 synthetic development questions</strong>.
                    These are <strong>NOT authentic past-paper questions</strong> and have not been verified by SLIIT lecturers.
                  </p>
                  <p className="c2-student-muted">
                    Marks and difficulty levels are intentionally <strong>unassessed</strong> to prevent fabricating academic assessment criteria.
                  </p>
                </div>
              )}

              {paperResultMode === 'twin' && (
                <div className="c2-evidence-message">
                  <h3>Digital Twin Personalization</h3>
                  {personalizationApplied ? (
                    <p>
                      The backend reports that C1 diagnostic mastery information was successfully applied using verified topic mappings.
                    </p>
                  ) : (
                    <p className="c2-student-warning">
                      Verified topic personalization was not applied. Standard practice questions were selected as a fallback.
                    </p>
                  )}
                  <p className="c2-student-muted">
                    Personalization status: {display(personalizationStatus)}
                  </p>
                </div>
              )}

              {/* Paper Summary Card */}
              <div className="c2-mock-summary">
                <div>
                  <span className="c2-student-panel-eyebrow">
                    {isSyntheticPaper ? 'SYNTHETIC PRACTICE PAPER' : 'GENERATED PRACTICE PAPER'}
                  </span>
                  <h3>{currentModuleName}</h3>
                  <p>
                    {paperQuestions.length} questions selected • {isSyntheticPaper ? 'Unassessed marks' : `${paperTotalMarks}/${paperRequestedMarks} marks`}
                  </p>
                </div>

                <div className="c2-mock-summary-actions">
                  <button
                    type="button"
                    className="c2-attempt-start-btn"
                    onClick={() => {
                      setActiveAttempt(paper);
                      setStage('attempt');
                    }}
                  >
                    ✍️ Start Exam Attempt (Stage 4)
                  </button>

                  <button
                    type="button"
                    className="btn secondary"
                    onClick={handleGenerateMock}
                    disabled={generatingMock}
                  >
                    🔄 Regenerate Paper
                  </button>
                </div>
              </div>

              {/* Limitations */}
              {paperLimitations.length > 0 && (
                <div className="c2-evidence-limitations">
                  <h3>Practice Paper Limitations</h3>
                  <ul>
                    {paperLimitations.map((lim, idx) => (
                      <li key={idx}>{lim}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Questions Preview */}
              <div style={{ marginTop: 16 }}>
                <h4>Paper Questions Preview ({paperQuestions.length} questions)</h4>
                {paperQuestions.length === 0 ? (
                  <div className="c2-student-empty">
                    <p className="c2-student-muted">No eligible questions returned.</p>
                  </div>
                ) : (
                  <div className="c2-student-question-list">
                    {paperQuestions.map((q, idx) => (
                      <QuestionCard
                        key={q.question_id || q.questionId || idx}
                        question={q}
                        number={idx + 1}
                        practice
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      )}

      {/* ======================================================== */}
      {/* STAGE 4 — EXAM ATTEMPT                                   */}
      {/* ======================================================== */}
      {stage === 'attempt' && (
        <section className="c2-student-bank" aria-label="Stage 4: Active Practice Exam Attempt">
          {activeAttempt || paper ? (
            <ActiveAttemptView
              paper={activeAttempt || paper}
              moduleKey={moduleKey}
              moduleName={currentModuleName}
              onSubmitAttempt={handleSubmitAttempt}
              onSubmitSuccess={(submitted) => {
                setActiveAttempt(null);
                setSelectedResultAttempt(submitted);
                setStage('results');
                loadAttempts();
              }}
              onCancel={() => {
                setActiveAttempt(null);
                setAttemptError('');
                setStage('setup');
              }}
              submitting={submittingAttempt}
              error={attemptError}
            />
          ) : (
            <div className="c2-student-empty" style={{ padding: '36px 20px' }}>
              <h3>No Practice Paper Active</h3>
              <p className="c2-student-muted">
                Please generate a practice mock examination in Stage 3 first before starting an exam attempt.
              </p>
              <button
                type="button"
                className="btn primary"
                style={{ marginTop: 14 }}
                onClick={() => setStage('setup')}
              >
                Go to Practice Setup (Stage 3)
              </button>
            </div>
          )}
        </section>
      )}

      {/* ======================================================== */}
      {/* STAGE 5 — RESULTS & FEEDBACK                             */}
      {/* ======================================================== */}
      {stage === 'results' && (
        <AttemptResultView
          attempt={selectedResultAttempt || (attempts.length > 0 ? attempts[0] : null)}
          moduleName={currentModuleName}
          moduleKey={moduleKey}
          onStartAnother={() => {
            setGeneratedPaper(null);
            setStage('setup');
          }}
          onReturnOverview={() => setStage('overview')}
          allAttempts={attempts}
          loadingAttempts={loadingAttempts}
          onRefreshAttempts={loadAttempts}
          onSelectAttempt={(att) => setSelectedResultAttempt(att)}
        />
      )}
    </main>
  );
}
