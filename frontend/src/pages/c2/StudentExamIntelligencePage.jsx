
import { useEffect, useState } from 'react';
import {
  getC2Modules,
  getC2StudentQuestions,
} from '../../services/c2Api.js';
import './studentExamIntelligence.css';

const PAGE_SIZE = 10;

function getModuleKey(module) {
  return typeof module === 'string' ? module : module.module_key;
}

function moduleLabel(module) {
  if (typeof module !== 'string') {
    return (
      module.module_name ||
      module.moduleName ||
      module.name ||
      module.module_key ||
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

function StatCard({ label, value, note, tone }) {
  return (
    <div className={`c2-student-stat c2-tone-${tone}`}>
      <span className="c2-student-stat-label">{label}</span>
      <strong className="c2-student-stat-value">{value}</strong>
      <span className="c2-student-stat-note">{note}</span>
    </div>
  );
}

export default function StudentExamIntelligencePage() {
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('');
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
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
          setError(err.message || 'Unable to load modules.');
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
          setError(err.message || 'Unable to load questions.');
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

  const questions = Array.isArray(result?.questions)
    ? result.questions
    : [];

  const totalPages = result?.total_pages || 1;

  const classifiedCount = questions.filter(
    (question) => question.topic_id
  ).length;

  const selectedModule = modules.find(
    (module) => getModuleKey(module) === moduleKey
  );

  const currentModuleName = selectedModule
    ? moduleLabel(selectedModule)
    : 'Select a module';

  const statValue = (value) => {
    if (loading) return '...';
    if (!result) return '—';
    return typeof value === 'number'
      ? value.toLocaleString()
      : value;
  };

  return (
    <main className="c2-student">
      <section className="c2-student-top">
        <div className="c2-student-hero">
          <span className="c2-student-eyebrow">
            EXAM INTELLIGENCE
          </span>

          <h1>Prepare smarter for your exams</h1>

          <p>
            Explore available examination questions, understand
            their topic coverage, and review the supporting
            academic evidence.
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
            Choose a module to view its available question bank.
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
              <option value="">No modules available</option>
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
            onClick={() => setRefresh((value) => value + 1)}
            disabled={!moduleKey || loading}
          >
            {loading ? 'Loading...' : '↻ Refresh questions'}
          </button>
        </div>
      </section>

      {error && (
        <div className="c2-student-error" role="alert">
          <strong>Unable to load exam intelligence</strong>
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
          label="Topic classified"
          value={statValue(classifiedCount)}
          note="On the current page"
          tone="indigo"
        />

        <StatCard
          label="Current page"
          value={statValue(page)}
          note={result ? `Of ${totalPages} pages` : 'Question browser'}
          tone="sky"
        />
      </section>

      <section className="c2-student-bank">
        <div className="c2-student-bank-header">
          <div>
            <span className="c2-student-panel-eyebrow">
              QUESTION EXPLORER
            </span>

            <h2>Examination Question Bank</h2>

            <p>
              {currentModuleName} — browse available questions,
              topics, marks, and source information.
            </p>
          </div>

          {result && (
            <span className="c2-student-count-chip">
              {Number(result.total || 0).toLocaleString()} questions
            </span>
          )}
        </div>

        {loading && (
          <div className="c2-student-loading" role="status">
            Loading examination questions...
          </div>
        )}

        {!loading && result && questions.length === 0 && (
          <div className="c2-student-empty">
            <div className="c2-student-empty-icon" aria-hidden="true">
              📚
            </div>

            <h3>No questions available yet</h3>

            <p>
              There are currently no processed examination
              questions available for this module. Questions will
              appear here when they have been added to the repository.
            </p>
          </div>
        )}

        {!loading && questions.length > 0 && (
          <div className="c2-student-question-list">
            {questions.map((question, index) => (
              <article
                className="c2-student-question"
                key={question.question_id || index}
              >
                <div className="c2-student-question-heading">
                  <div className="c2-student-question-title">
                    <span className="c2-student-question-number">
                      Q{(page - 1) * PAGE_SIZE + index + 1}
                    </span>

                    <div>
                      <span className="c2-student-question-caption">
                        EXAMINATION QUESTION
                      </span>
                      <h3>
                        Question {(page - 1) * PAGE_SIZE + index + 1}
                      </h3>
                    </div>
                  </div>

                  <span className="c2-student-pill">
                    {question.marks ?? '—'} marks
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
                    <span>Bloom level</span>
                    <strong>{display(question.bloom_level)}</strong>
                  </div>

                  <div>
                    <span>Difficulty</span>
                    <strong>{display(question.difficulty)}</strong>
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

                  <div>
                    <span>Source</span>
                    <strong>{display(question.source_type)}</strong>
                  </div>
                </div>

                {question.verification_status !== 'verified' && (
                  <p className="c2-student-warning">
                    Topic classification has not been verified.
                  </p>
                )}
              </article>
            ))}
          </div>
        )}

        {!loading && result && totalPages > 1 && (
          <div className="c2-student-pagination">
            <span>
              Page <strong>{page}</strong> of{' '}
              <strong>{totalPages}</strong>
            </span>

            <div className="c2-student-pagination-actions">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((value) => value - 1)}
              >
                ← Previous
              </button>

              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((value) => value + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="c2-student-roadmap">
        <div className="c2-student-roadmap-icon" aria-hidden="true">
          ✦
        </div>

        <div>
          <h2>More exam intelligence is coming</h2>
          <p>
            Evidence-based topic trends, predictive topic ranking,
            and personalized mock examinations will be added as
            their backend services become available.
          </p>
        </div>
      </section>
    </main>
  );
}
