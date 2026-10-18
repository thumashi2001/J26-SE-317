
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  getC2Modules,
  generateC2SyntheticPracticePreview,
} from '../../services/c2Api.js';

import './lecturerSyntheticPreview.css';

export default function LecturerSyntheticPreviewPage() {
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('');
  const [seed, setSeed] = useState('42');

  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function loadModules() {
      try {
        const result = await getC2Modules();

        if (!active) return;

        const list = Array.isArray(result)
          ? result
          : Array.isArray(result?.modules)
            ? result.modules
            : [];

        setModules(list);

        if (list.length > 0) {
          const first = list[0];

          setModuleKey(
            typeof first === 'string'
              ? first
              : first.module_key || first.moduleKey || ''
          );
        }
      } catch (err) {
        if (active) {
          setError(err.message || 'Unable to load modules');
        }
      }
    }

    loadModules();

    return () => {
      active = false;
    };
  }, []);

  async function handleGenerate(event) {
    event.preventDefault();

    setError('');
    setPreview(null);

    const numericSeed = Number(seed);

    if (
      !Number.isSafeInteger(numericSeed) ||
      seed.trim() === ''
    ) {
      setError('Enter a valid integer seed.');
      return;
    }

    setLoading(true);

    try {
      const result = await generateC2SyntheticPracticePreview({
        moduleKey,
        seed: numericSeed,
      });

      setPreview(result);
    } catch (err) {
      setError(
        err.message ||
          'Unable to generate synthetic practice preview'
      );
    } finally {
      setLoading(false);
    }
  }

  const mainQuestions = Array.isArray(preview?.paper?.questions)
    ? preview.paper.questions
    : [];

  const displayedSubquestionCount = mainQuestions.reduce(
    (count, mainQuestion) =>
      count +
      (Array.isArray(mainQuestion.subquestions)
        ? mainQuestion.subquestions.length
        : 0),
    0
  );

  return (
    <main className="c2-synthetic-page">
      <div className="c2-synthetic-heading">
        <div>
          <p className="c2-synthetic-eyebrow">
            Component 2 · Lecturer tools
          </p>

          <h1>Synthetic Practice Paper Preview</h1>

          <p>
            Generate and inspect development-only synthetic
            questions before academic review.
          </p>
        </div>

        <Link to="/lecturer/c2">
          Back to syllabus review
        </Link>
      </div>

      <div className="c2-synthetic-warning">
        <strong>Not approved for student release.</strong>
        {' '}
        These questions are synthetic development fixtures.
        The paper structure is experimental and must not
        be presented as an official examination format.
      </div>

      <section className="c2-synthetic-panel">
        <h2>Generate Preview</h2>

        <form onSubmit={handleGenerate}>
          <div className="c2-synthetic-fields">
            <label>
              Module

              <select
                value={moduleKey}
                onChange={(event) => {
                  setModuleKey(event.target.value);
                  setPreview(null);
                  setError('');
                }}
                required
              >
                {modules.map((module, index) => {
                  const key =
                    typeof module === 'string'
                      ? module
                      : module.module_key ||
                        module.moduleKey ||
                        '';

                  const name =
                    typeof module === 'string'
                      ? module.replaceAll('_', ' ')
                      : module.module_name ||
                        module.moduleName ||
                        module.name ||
                        key;

                  return (
                    <option key={`${key}-${index}`} value={key}>
                      {name}
                    </option>
                  );
                })}
              </select>
            </label>

            <label>
              Reproducibility seed

              <input
                type="number"
                step="1"
                value={seed}
                onChange={(event) => setSeed(event.target.value)}
                required
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={loading || !moduleKey}
          >
            {loading
              ? 'Generating preview...'
              : 'Generate synthetic preview'}
          </button>
        </form>

        {error && (
          <p className="c2-synthetic-error" role="alert">
            {error}
          </p>
        )}
      </section>

      {preview && (
        <>
          <section className="c2-synthetic-panel">
            <h2>Preview Summary</h2>

            <p>
              <strong>Module:</strong>
              {' '}
              {preview.module_name || preview.module_key}
            </p>

            <p>
              <strong>Paper ID:</strong>
              {' '}
              {preview.paper?.paper_id || 'Not available'}
            </p>

            <div className="c2-synthetic-stats">
              <div>
                <strong>{preview.question_count ?? 0}</strong>
                <span>Subquestions</span>
              </div>

              <div>
                <strong>{preview.total_marks ?? 0}</strong>
                <span>Experimental marks</span>
              </div>

              <div>
                <strong>
                  {preview.unique_scenario_count ?? 0}
                </strong>
                <span>Unique scenarios</span>
              </div>
            </div>

            <p>
              <strong>Main questions:</strong>
              {' '}
              {mainQuestions.length}
            </p>

            <p>
              <strong>Academic review:</strong>
              {' '}
              {preview.academic_review_status}
            </p>

            <p>
              <strong>Release status:</strong>
              {' '}
              {preview.release_status}
            </p>

            <p>
              <strong>Structure validation:</strong>
              {' '}
              {preview.structural_valid ? 'Passed' : 'Failed'}
            </p>

            <p>
              <strong>Diversity validation:</strong>
              {' '}
              {preview.diversity_valid ? 'Passed' : 'Failed'}
            </p>

            <p>
              <strong>Student release allowed:</strong>
              {' '}
              {preview.student_release_allowed ? 'Yes' : 'No'}
            </p>

            <p>
              <strong>Official examination structure verified:</strong>
              {' '}
              {preview.official_exam_structure_verified
                ? 'Yes'
                : 'No'}
            </p>

            {Array.isArray(preview.limitations) &&
              preview.limitations.length > 0 && (
                <div className="c2-synthetic-limitations">
                  <h3>Limitations</h3>

                  <ul>
                    {preview.limitations.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
          </section>

          <section className="c2-synthetic-panel">
            <h2>Generated Questions</h2>

            <p>
              Displaying {displayedSubquestionCount} subquestions
              across {mainQuestions.length} main questions.
            </p>

            {mainQuestions.length === 0 ? (
              <p>No questions returned.</p>
            ) : (
              mainQuestions.map((mainQuestion, mainIndex) => {
                const subquestions = Array.isArray(
                  mainQuestion.subquestions
                )
                  ? mainQuestion.subquestions
                  : [];

                return (
                  <article
                    className="c2-synthetic-main-question"
                    key={mainQuestion.number ?? mainIndex}
                  >
                    <h3>
                      Question {mainQuestion.number ?? mainIndex + 1}
                      {' — '}
                      {mainQuestion.total_marks ?? 0} marks
                    </h3>

                    {subquestions.map((subquestion, subIndex) => {
                      const detail = subquestion.question || {};

                      const label =
                        subquestion.label ||
                        String.fromCharCode(97 + subIndex);

                      return (
                        <div
                          className="c2-synthetic-subquestion"
                          key={
                            detail.question_id ||
                            `${mainIndex}-${subIndex}`
                          }
                        >
                          <h4>
                            ({label})
                            {' '}
                            {subquestion.marks ?? detail.marks ?? 0}
                            {' marks'}
                          </h4>

                          <p className="c2-synthetic-question-text">
                            {detail.question_text ||
                              'Question text unavailable'}
                          </p>

                          <div className="c2-synthetic-metadata">
                            {detail.topic_name && (
                              <span>
                                <strong>Topic:</strong>
                                {' '}
                                {detail.topic_name}
                              </span>
                            )}

                            {detail.question_type && (
                              <span>
                                <strong>Question type:</strong>
                                {' '}
                                {detail.question_type}
                              </span>
                            )}

                            {detail.response_format && (
                              <span>
                                <strong>Response format:</strong>
                                {' '}
                                {detail.response_format}
                              </span>
                            )}

                            {detail.verification_status && (
                              <span>
                                <strong>Verification:</strong>
                                {' '}
                                {detail.verification_status}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </article>
                );
              })
            )}
          </section>
        </>
      )}
    </main>
  );
}
