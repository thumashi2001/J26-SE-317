
import { useEffect, useState } from 'react';

import {
  getC2Modules,
  getC2StudentQuestions,
  getC2TopicPredictions,
  generateC2MockExam,
} from '../../services/c2Api.js';

import './studentExamIntelligence.css';

const PAGE_SIZE = 10;

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

function StatCard({ label, value, note, tone = 'blue' }) {
  return (
    <div className={`c2-student-stat c2-tone-${tone}`}>
      <span className="c2-student-stat-label">
        {label}
      </span>

      <strong className="c2-student-stat-value">
        {value}
      </strong>

      <span className="c2-student-stat-note">
        {note}
      </span>
    </div>
  );
}

function QuestionCard({
  question,
  number,
  practice = false,
}) {
  return (
    <article className="c2-student-question">
      <div className="c2-student-question-heading">
        <div className="c2-student-question-title">
          <span className="c2-student-question-number">
            Q{number}
          </span>

          <div>
            <span className="c2-student-question-caption">
              {practice
                ? 'PRACTICE MOCK QUESTION'
                : 'EXAMINATION QUESTION'}
            </span>

            <h3>Question {number}</h3>
          </div>
        </div>

        <span className="c2-student-pill">
          {question.marks ?? '-'} marks
        </span>
      </div>

      <p className="c2-student-question-text">
        {question.question_text ||
          'Question text unavailable'}
      </p>

      <div className="c2-student-metadata">
        <div>
          <span>Topic</span>
          <strong>{display(question.topic_id)}</strong>
        </div>

        <div>
          <span>Difficulty</span>
          <strong>{display(question.difficulty)}</strong>
        </div>

        <div>
          <span>Source</span>
          <strong>{display(question.source_type)}</strong>
        </div>

        {!practice && (
          <>
            <div>
              <span>Bloom level</span>
              <strong>
                {display(question.bloom_level)}
              </strong>
            </div>

            <div>
              <span>Classification</span>
              <strong>
                {display(question.classification_method)}
              </strong>
            </div>

            <div>
              <span>Verification</span>
              <strong>
                {display(question.verification_status)}
              </strong>
            </div>

            <div>
              <span>Exam year</span>
              <strong>
                {display(question.calendar_year)}
              </strong>
            </div>
          </>
        )}
      </div>

      {!practice &&
        question.verification_status !== 'verified' && (
          <p className="c2-student-warning">
            Topic classification has not been verified.
          </p>
        )}
    </article>
  );
}

function TopicEvidencePanel({
  prediction,
  loading,
  error,
  moduleKey,
}) {
  const evidence = prediction?.historical_evidence;
  const priorities = Array.isArray(
    prediction?.study_priorities
  )
    ? prediction.study_priorities
    : [];

  const limitations = Array.isArray(
    prediction?.limitations
  )
    ? prediction.limitations
    : [];

  return (
    <section className="c2-student-bank">
      <div className="c2-student-bank-header">
        <div>
          <span className="c2-student-panel-eyebrow">
            HISTORICAL EXAM EVIDENCE
          </span>

          <h2>Topic Evidence & Study Priorities</h2>

          <p>
            Review authentic historical evidence before
            deciding which topics to study.
          </p>
        </div>
      </div>

      {!moduleKey && (
        <p className="c2-student-muted">
          Select a module to view historical evidence.
        </p>
      )}

      {loading && (
        <div className="c2-student-loading" role="status">
          Loading historical topic evidence...
        </div>
      )}

      {error && (
        <div className="c2-student-error" role="alert">
          <strong>Unable to load topic evidence</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && prediction && (
        <>
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
              value={
                evidence?.verified_topic_questions ?? 0
              }
              note="Academically verified classifications"
              tone="indigo"
            />

            <StatCard
              label="Topic coverage"
              value={`${
                (
                  (evidence?.verified_topic_coverage ?? 0) *
                  100
                ).toFixed(0)
              }%`}
              note="Verified share of authentic questions"
              tone="sky"
            />
          </div>

          {prediction.prediction_ready ? (
            <div className="c2-evidence-message">
              <h3>Historical study priorities available</h3>

              <p>
                These priorities describe historical topic
                frequency. They are not probabilities of
                appearing in the next examination.
              </p>

              {priorities.length > 0 && (
                <div className="c2-priority-list">
                  {priorities.map((topic) => (
                    <div
                      className="c2-priority-item"
                      key={topic.topic_id}
                    >
                      <strong>
                        {topic.rank}.{' '}
                        {display(topic.topic_id)}
                      </strong>

                      <span>
                        {topic.question_count} historical
                        questions
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="c2-evidence-message">
              <h3>Insufficient evidence for topic ranking</h3>

              <p>
                The available historical papers and verified
                classifications do not yet support a
                defensible topic ranking.
              </p>

              <p>
                You can still browse authentic questions
                and generate a practice mock exam.
              </p>
            </div>
          )}

          {limitations.length > 0 && (
            <div className="c2-evidence-limitations">
              <h3>Evidence limitations</h3>

              <ul>
                {limitations.map((limitation, index) => (
                  <li key={`${index}-${limitation}`}>
                    {limitation}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {prediction.disclaimer && (
            <p className="c2-student-muted">
              {prediction.disclaimer}
            </p>
          )}
        </>
      )}
    </section>
  );
}

function MockExamPanel({ moduleKey, moduleName }) {
  const [targetMarks, setTargetMarks] = useState(100);
  const [maxQuestions, setMaxQuestions] = useState(20);
  const [topicsInput, setTopicsInput] = useState('');
  const [difficulty, setDifficulty] = useState('');

  const [mock, setMock] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Clear results when the selected module changes.
  useEffect(() => {
    setMock(null);
    setError('');
  }, [moduleKey]);

  async function handleGenerate(event) {
    event.preventDefault();

    if (!moduleKey || loading) return;

    const preferredTopics = topicsInput
      .split(',')
      .map((topic) => topic.trim())
      .filter(Boolean);

    setLoading(true);
    setError('');
    setMock(null);

    try {
      const response = await generateC2MockExam({
        moduleKey,
        targetMarks: Number(targetMarks),
        maxQuestions: Number(maxQuestions),
        preferredTopics,
        difficulty: difficulty || null,
        seed: 42,
      });

      setMock(response);
    } catch (err) {
      setError(
        err.message || 'Unable to generate practice mock.'
      );
    } finally {
      setLoading(false);
    }
  }

  const questions = Array.isArray(mock?.questions)
    ? mock.questions
    : [];

  return (
    <section className="c2-student-bank">
      <div className="c2-student-bank-header">
        <div>
          <span className="c2-student-panel-eyebrow">
            PRACTICE EXAMINATION
          </span>

          <h2>Generate a Practice Mock Exam</h2>

          <p>
            Build a practice paper from eligible authentic
            examination questions for {moduleName}.
          </p>
        </div>
      </div>

      <form
        className="c2-mock-form"
        onSubmit={handleGenerate}
      >
        <div className="c2-mock-field">
          <label htmlFor="c2-target-marks">
            Target marks
          </label>

          <input
            id="c2-target-marks"
            type="number"
            min="1"
            max="200"
            step="1"
            value={targetMarks}
            onChange={(event) =>
              setTargetMarks(event.target.value)
            }
            required
          />
        </div>

        <div className="c2-mock-field">
          <label htmlFor="c2-max-questions">
            Maximum questions
          </label>

          <input
            id="c2-max-questions"
            type="number"
            min="1"
            max="30"
            step="1"
            value={maxQuestions}
            onChange={(event) =>
              setMaxQuestions(event.target.value)
            }
            required
          />
        </div>

        <div className="c2-mock-field">
          <label htmlFor="c2-difficulty">
            Preferred difficulty
          </label>

          <select
            id="c2-difficulty"
            value={difficulty}
            onChange={(event) =>
              setDifficulty(event.target.value)
            }
          >
            <option value="">Any difficulty</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        <div className="c2-mock-field c2-mock-wide">
          <label htmlFor="c2-preferred-topics">
            Preferred topic IDs (optional)
          </label>

          <input
            id="c2-preferred-topics"
            type="text"
            value={topicsInput}
            placeholder="e.g. sql, indexing"
            onChange={(event) =>
              setTopicsInput(event.target.value)
            }
          />

          <small>
            Separate topic IDs with commas. Preferences
            are prioritized, not guaranteed.
          </small>
        </div>

        <div className="c2-mock-actions">
          <button
            type="submit"
            className="c2-mock-button"
            disabled={!moduleKey || loading}
          >
            {loading
              ? 'Generating practice mock...'
              : 'Generate Practice Mock'}
          </button>
        </div>
      </form>

      {error && (
        <div className="c2-student-error" role="alert">
          <strong>Mock generation failed</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && mock && (
        <div className="c2-mock-results">
          <div className="c2-mock-summary">
            <div>
              <span className="c2-student-panel-eyebrow">
                GENERATED PRACTICE PAPER
              </span>

              <h3>{moduleName}</h3>

              <p>
                {mock.question_count} questions selected
              </p>
            </div>

            <div className="c2-mock-marks">
              <strong>
                {mock.total_marks}/{mock.target_marks}
              </strong>
              <span>marks</span>
            </div>
          </div>

          {mock.status === 'partial' && (
            <p className="c2-student-warning">
              Partial practice paper: eligible questions
              could not fill the requested marks total.
            </p>
          )}

          <p className="c2-student-muted">
            Practice only. This is not an officially
            verified examination paper or a prediction
            of the next exam.
          </p>

          {Array.isArray(mock.limitations) &&
            mock.limitations.length > 0 && (
              <div className="c2-evidence-limitations">
                <h3>Practice paper limitations</h3>

                <ul>
                  {mock.limitations.map(
                    (limitation, index) => (
                      <li key={`${index}-${limitation}`}>
                        {limitation}
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}

          {questions.length === 0 ? (
            <div className="c2-student-empty">
              <h3>No eligible questions available</h3>

              <p>
                This module does not currently have
                eligible authentic questions with
                extracted marks.
              </p>
            </div>
          ) : (
            <div className="c2-student-question-list">
              {questions.map((question, index) => (
                <QuestionCard
                  key={question.question_id || index}
                  question={question}
                  number={index + 1}
                  practice
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default function StudentExamIntelligencePage() {
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('');
  const [page, setPage] = useState(1);

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [prediction, setPrediction] = useState(null);
  const [predictionLoading, setPredictionLoading] =
    useState(false);
  const [predictionError, setPredictionError] =
    useState('');

  const [refresh, setRefresh] = useState(0);

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

        if (items.length > 0) {
          setModuleKey(getModuleKey(items[0]));
        }
      } catch (err) {
        if (active) {
          setError(
            err.message || 'Unable to load modules.'
          );
        }
      }
    }

    loadModules();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!moduleKey) return;

    let active = true;

    async function loadQuestions() {
      setLoading(true);
      setError('');
      setResult(null);

      try {
        const data = await getC2StudentQuestions({
          moduleKey,
          page,
          pageSize: PAGE_SIZE,
        });

        if (active) setResult(data);
      } catch (err) {
        if (active) {
          setError(
            err.message || 'Unable to load questions.'
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadQuestions();

    return () => {
      active = false;
    };
  }, [moduleKey, page, refresh]);

  useEffect(() => {
    if (!moduleKey) return;

    let active = true;

    async function loadPrediction() {
      setPredictionLoading(true);
      setPredictionError('');
      setPrediction(null);

      try {
        const data = await getC2TopicPredictions(
          moduleKey
        );

        if (active) setPrediction(data);
      } catch (err) {
        if (active) {
          setPredictionError(
            err.message ||
              'Unable to load topic evidence.'
          );
        }
      } finally {
        if (active) {
          setPredictionLoading(false);
        }
      }
    }

    loadPrediction();

    return () => {
      active = false;
    };
  }, [moduleKey, refresh]);

  const questions = Array.isArray(result?.questions)
    ? result.questions
    : [];

  const totalPages = result?.total_pages || 1;

  const classifiedCount = questions.filter(
    (question) =>
      question.topic_id &&
      question.verification_status === 'verified'
  ).length;

  const selectedModule = modules.find(
    (module) => getModuleKey(module) === moduleKey
  );

  const currentModuleName = selectedModule
    ? moduleLabel(selectedModule)
    : 'Select a module';

  function statValue(value) {
    if (loading) return '...';
    if (!result) return '-';

    return typeof value === 'number'
      ? value.toLocaleString()
      : value;
  }

  return (
    <main className="c2-student">
      <section className="c2-student-top">
        <div className="c2-student-hero">
          <span className="c2-student-eyebrow">
            EXAM INTELLIGENCE
          </span>

          <h1>Prepare smarter for your exams</h1>

          <p>
            Explore authentic examination questions,
            understand historical topic evidence, and
            generate practice mock examinations.
          </p>

          <div className="c2-student-hero-footer">
            <span className="c2-student-hero-chip">
              Component 2
            </span>

            <span className="c2-student-hero-chip">
              {modules.length} modules
            </span>
          </div>
        </div>

        <div className="c2-student-module-panel">
          <span className="c2-student-panel-eyebrow">
            YOUR EXAM MODULE
          </span>

          <h2>Explore a module</h2>

          <p>
            Choose a module to explore questions,
            topic evidence, and practice mocks.
          </p>

          <label htmlFor="c2-module-select">
            Module
          </label>

          <select
            id="c2-module-select"
            value={moduleKey}
            disabled={modules.length === 0}
            onChange={(event) => {
              setModuleKey(event.target.value);
              setPage(1);
            }}
          >
            {modules.length === 0 && (
              <option value="">
                No modules available
              </option>
            )}

            {modules.map((module) => {
              const key = getModuleKey(module);

              return (
                <option key={key} value={key}>
                  {moduleLabel(module)}
                </option>
              );
            })}
          </select>

          <button
            className="c2-student-refresh"
            type="button"
            onClick={() =>
              setRefresh((value) => value + 1)
            }
            disabled={!moduleKey || loading}
          >
            {loading
              ? 'Loading...'
              : 'Refresh questions and evidence'}
          </button>
        </div>
      </section>

      {error && (
        <div
          className="c2-student-error"
          role="alert"
        >
          <strong>
            Unable to load examination questions
          </strong>
          <p>{error}</p>
        </div>
      )}

      <section
        className="c2-student-stats"
        aria-label="Question bank statistics"
      >
        <StatCard
          label="Total questions"
          value={statValue(result?.total)}
          note="Available in this module"
          tone="blue"
        />

        <StatCard
          label="Questions displayed"
          value={statValue(questions.length)}
          note={`Up to ${PAGE_SIZE} per page`}
          tone="teal"
        />

        <StatCard
          label="Verified topic labels"
          value={statValue(classifiedCount)}
          note="On the current page"
          tone="indigo"
        />

        <StatCard
          label="Current page"
          value={statValue(page)}
          note={
            result
              ? `Of ${totalPages} pages`
              : 'Question browser'
          }
          tone="sky"
        />
      </section>

      <TopicEvidencePanel
        moduleKey={moduleKey}
        prediction={prediction}
        loading={predictionLoading}
        error={predictionError}
      />

      <MockExamPanel
        key={moduleKey}
        moduleKey={moduleKey}
        moduleName={currentModuleName}
      />

      <section className="c2-student-bank">
        <div className="c2-student-bank-header">
          <div>
            <span className="c2-student-panel-eyebrow">
              QUESTION EXPLORER
            </span>

            <h2>Examination Question Bank</h2>

            <p>
              {currentModuleName} - browse available
              questions, topics, marks, and source
              information.
            </p>
          </div>

          {result && (
            <span className="c2-student-count-chip">
              {Number(
                result.total || 0
              ).toLocaleString()}{' '}
              questions
            </span>
          )}
        </div>

        {loading && (
          <div
            className="c2-student-loading"
            role="status"
          >
            Loading examination questions...
          </div>
        )}

        {!loading &&
          result &&
          questions.length === 0 && (
            <div className="c2-student-empty">
              <div
                className="c2-student-empty-icon"
                aria-hidden="true"
              >
                📚
              </div>

              <h3>No questions available yet</h3>

              <p>
                No processed examination questions
                are currently available for this module.
              </p>
            </div>
          )}

        {!loading && questions.length > 0 && (
          <div className="c2-student-question-list">
            {questions.map((question, index) => (
              <QuestionCard
                key={
                  question.question_id || index
                }
                question={question}
                number={
                  (page - 1) * PAGE_SIZE +
                  index +
                  1
                }
              />
            ))}
          </div>
        )}

        {!loading &&
          result &&
          totalPages > 1 && (
            <div className="c2-student-pagination">
              <span>
                Page <strong>{page}</strong> of{' '}
                <strong>{totalPages}</strong>
              </span>

              <div className="c2-student-pagination-actions">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() =>
                    setPage((value) => value - 1)
                  }
                >
                  Previous
                </button>

                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() =>
                    setPage((value) => value + 1)
                  }
                >
                  Next
                </button>
              </div>
            </div>
          )}
      </section>
    </main>
  );
}
