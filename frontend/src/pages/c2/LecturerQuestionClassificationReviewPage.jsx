
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  getC2Modules,
  getC2QuestionClassificationReviews,
  submitC2QuestionClassificationReview,
} from '../../services/c2Api.js';

import './lecturerQuestionClassificationReview.css';

const PAGE_SIZE = 10;

function formatModule(key) {
  if (!key) return '';

  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getProposedTopic(question) {
  const topic = question?.proposed_classification?.topic_id;

  if (typeof topic !== 'string') return null;

  const normalized = topic.trim();

  if (
    !normalized ||
    normalized.toLowerCase() === 'unclassified'
  ) {
    return null;
  }

  return normalized;
}

function hasReview(question) {
  return Boolean(question?.review);
}

function StatusBadge({ question }) {
  const decision = question?.review?.decision;

  if (decision === 'approved') {
    return (
      <span className="pill status-approved">
        Verified
      </span>
    );
  }

  if (decision === 'rejected') {
    return (
      <span className="pill status-rejected">
        Rejected
      </span>
    );
  }

  if (!getProposedTopic(question)) {
    return (
      <span className="pill status-pending">
        Awaiting Classification
      </span>
    );
  }

  return (
    <span className="pill status-pending">
      Pending Review
    </span>
  );
}

export default function LecturerQuestionClassificationReviewPage() {
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('');
  const [page, setPage] = useState(1);
  const [includeReviewed, setIncludeReviewed] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const [selected, setSelected] = useState(null);
  const [decision, setDecision] = useState('rejected');
  const [notes, setNotes] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);

  const [refreshKey, setRefreshKey] = useState(0);

  // Load modules once.
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

        const keys = list
          .map((item) =>
            typeof item === 'string'
              ? item
              : item?.module_key
          )
          .filter(
            (key) =>
              typeof key === 'string' && key.trim()
          );

        setModules(keys);

        if (keys.length > 0) {
          setModuleKey((current) => current || keys[0]);
        }
      } catch (err) {
        if (active) {
          setError(
            err.message || 'Could not load modules.'
          );
        }
      }
    }

    loadModules();

    return () => {
      active = false;
    };
  }, []);

  // Load review candidates.
  useEffect(() => {
    if (!moduleKey) return;

    let active = true;

    async function loadQuestions() {
      setLoading(true);
      setError('');
      setData(null);

      try {
        const result =
          await getC2QuestionClassificationReviews({
            moduleKey,
            page,
            pageSize: PAGE_SIZE,
            includeReviewed,
          });

        if (active) {
          setData(result);
        }
      } catch (err) {
        if (active) {
          setError(
            err.message ||
              'Could not load question classification reviews.'
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadQuestions();

    return () => {
      active = false;
    };
  }, [moduleKey, page, includeReviewed, refreshKey]);

  const questions = Array.isArray(data?.questions)
    ? data.questions
    : [];

  const statistics = data?.statistics ?? null;
  const taxonomyStatus = data?.taxonomy_status ?? null;

  const totalPages = Math.max(
    1,
    Number(data?.total_pages) || 1
  );

  const filteredQuestions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    if (!query) return questions;

    return questions.filter((question) => {
      const searchable = [
        question.question_id,
        question.question_text,
        question.paper_id,
        question.proposed_classification?.topic_id,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();

      return searchable.includes(query);
    });
  }, [questions, searchQuery]);

  function openReview(
    question,
    preferredDecision = 'rejected'
  ) {
    const proposedTopic = getProposedTopic(question);

    if (!proposedTopic) {
      setError(
        'This question has no proposed topic classification. ' +
          'A classification must be proposed before review.'
      );
      return;
    }

    if (hasReview(question)) {
      setError(
        'This question has already been reviewed.'
      );
      return;
    }

    if (
      preferredDecision === 'approved' &&
      !question.can_approve
    ) {
      setError(
        'Approval requires a verified module taxonomy ' +
          'and a valid proposed topic.'
      );
      return;
    }

    setSelected(question);
    setDecision(preferredDecision);
    setNotes('');
    setConfirmed(false);
    setError('');
    setNotice('');
  }

  function closeReview() {
    if (saving) return;

    setSelected(null);
    setNotes('');
    setConfirmed(false);
  }

  async function handleSubmitReview(event) {
    event.preventDefault();

    if (!selected || saving || !confirmed) return;

    // Never substitute "unclassified" for a missing topic.
    const proposedTopic = getProposedTopic(selected);

    if (!proposedTopic) {
      setError(
        'Cannot review a question without a proposed topic classification.'
      );
      return;
    }

    if (hasReview(selected)) {
      setError(
        'This question has already been reviewed.'
      );
      return;
    }

    if (!['approved', 'rejected'].includes(decision)) {
      setError('Invalid review decision.');
      return;
    }

    if (
      decision === 'approved' &&
      !selected.can_approve
    ) {
      setError(
        'Approval is blocked because the module taxonomy ' +
          'or proposed topic is not verified.'
      );
      return;
    }

    if (
      decision === 'rejected' &&
      !notes.trim()
    ) {
      setError(
        'Please provide a reason for rejection.'
      );
      return;
    }

    if (notes.trim().length > 2000) {
      setError(
        'Review notes must be 2000 characters or fewer.'
      );
      return;
    }

    setSaving(true);
    setError('');

    try {
      await submitC2QuestionClassificationReview(
        selected.question_id,
        {
          moduleKey,
          topicId: proposedTopic,
          decision,
          reviewNotes: notes.trim(),
        }
      );

      setSelected(null);
      setConfirmed(false);
      setNotes('');

      setNotice(
        `Successfully saved ${decision} review for question ${selected.question_id}.`
      );

      setRefreshKey((current) => current + 1);
    } catch (err) {
      setError(
        err.message ||
          'Failed to submit review decision.'
      );
    } finally {
      setSaving(false);
    }
  }

  const selectedTopic = getProposedTopic(selected);

  return (
    <div className="c2-classification-review">
      <header className="c2-dashboard-head">
        <div>
          <h1>Authentic Question Classification Review</h1>

          <p className="muted">
            Inspect authentic examination questions,
            evaluate proposed topic classifications,
            and record trusted lecturer review decisions.
          </p>
        </div>

        <nav
          className="c2-header-nav"
          aria-label="C2 Navigation"
        >
          <Link
            to="/lecturer/c2"
            className="btn secondary small-btn"
          >
            Syllabus Review
          </Link>

          <Link
            to="/lecturer/c2/synthetic-preview"
            className="btn secondary small-btn"
          >
            Synthetic Preview
          </Link>
        </nav>
      </header>

      {/* Statistics */}
      <section
        className="c2-stats stat-grid"
        aria-label="Question classification statistics"
      >
        <div
          className="stat"
          style={{ '--c': 'var(--primary)' }}
        >
          <div className="stat-num">
            {statistics
              ? Number(statistics.total ?? 0).toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Authentic Questions
          </div>
        </div>

        <div
          className="stat"
          style={{ '--c': 'var(--warn)' }}
        >
          <div className="stat-num">
            {statistics
              ? Number(statistics.pending ?? 0).toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Pending Reviews
          </div>
        </div>

        <div
          className="stat"
          style={{ '--c': 'var(--good)' }}
        >
          <div className="stat-num">
            {statistics
              ? Number(statistics.approved ?? 0).toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Verified Classifications
          </div>
        </div>

        <div
          className="stat"
          style={{ '--c': 'var(--bad)' }}
        >
          <div className="stat-num">
            {statistics
              ? Number(statistics.rejected ?? 0).toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Rejected Proposals
          </div>
        </div>
      </section>

      {/* Review queue */}
      <section className="panel c2-main-panel">
        <div className="c2-panel-heading">
          <div>
            <h3>Question Classification Queue</h3>
            <p className="muted small">
              Authentic past paper questions and their
              proposed syllabus classifications.
            </p>
          </div>

          <button
            type="button"
            className="btn secondary small-btn"
            disabled={loading || saving || !moduleKey}
            onClick={() =>
              setRefreshKey((current) => current + 1)
            }
          >
            Refresh Queue
          </button>
        </div>

        {/* Filters */}
        <div className="c2-filters">
          <label className="c2-module-field">
            <span>Target Module</span>

            <select
              value={moduleKey}
              disabled={saving}
              onChange={(event) => {
                setModuleKey(event.target.value);
                setPage(1);
                setSelected(null);
                setError('');
                setNotice('');
              }}
            >
              {modules.map((key) => (
                <option key={key} value={key}>
                  {formatModule(key)}
                </option>
              ))}
            </select>
          </label>

          <label className="c2-search-field">
            <span>Search Questions</span>

            <input
              type="text"
              placeholder="Search by ID, text, topic..."
              value={searchQuery}
              onChange={(event) =>
                setSearchQuery(event.target.value)
              }
            />
          </label>

          <label className="c2-filter-checkbox">
            <input
              type="checkbox"
              checked={includeReviewed}
              disabled={saving}
              onChange={(event) => {
                setIncludeReviewed(event.target.checked);
                setPage(1);
              }}
            />

            Include reviewed questions
          </label>
        </div>

        {/* Taxonomy status */}
        {taxonomyStatus && (
          taxonomyStatus.is_verified ? (
            <div className="c2-taxonomy-verified">
              <strong>
                Verified Syllabus Taxonomy.
              </strong>{' '}
              The taxonomy for {formatModule(moduleKey)}
              is verified. Approval still requires a valid
              proposed topic.
            </div>
          ) : (
            <div className="c2-taxonomy-warning">
              <strong>
                Research Integrity Safeguard — Taxonomy Unverified.
              </strong>{' '}
              The taxonomy for {formatModule(moduleKey)}
              is not verified. Approval is blocked.
              Lecturers may reject an actual proposed
              classification with review notes, but
              unclassified questions cannot be reviewed.
            </div>
          )
        )}

        {/* Feedback */}
        {notice && (
          <p
            className="c2-feedback c2-feedback-success"
            role="status"
          >
            {notice}
          </p>
        )}

        {error && (
          <p
            className="c2-feedback c2-feedback-error"
            role="alert"
          >
            {error}
          </p>
        )}

        {loading && (
          <div
            className="c2-loading"
            role="status"
          >
            Loading authentic examination questions...
          </div>
        )}

        {!loading && filteredQuestions.length === 0 && (
          <div className="c2-empty">
            <h4>No questions found</h4>
            <p>
              {searchQuery.trim()
                ? 'No questions on this page match your search.'
                : includeReviewed
                  ? 'There are no authentic questions registered for this module.'
                  : 'No pending questions are available. You can enable "Include reviewed questions" to inspect previous decisions.'}
            </p>
          </div>
        )}

        {/* Questions table */}
        {!loading && filteredQuestions.length > 0 && (
          <>
            <div className="c2-table-wrap">
              <table className="c2-table">
                <thead>
                  <tr>
                    <th style={{ width: '30%' }}>
                      Question Details
                    </th>
                    <th style={{ width: '22%' }}>
                      Source Evidence
                    </th>
                    <th style={{ width: '20%' }}>
                      Proposed Classification
                    </th>
                    <th style={{ width: '15%' }}>
                      Review Status
                    </th>
                    <th style={{ width: '13%' }}>
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {filteredQuestions.map((question) => {
                    const proposedTopic =
                      getProposedTopic(question);

                    const reviewed =
                      hasReview(question);

                    const canApprove =
                      Boolean(
                        proposedTopic &&
                        !reviewed &&
                        question.can_approve
                      );

                    const canReject =
                      Boolean(
                        proposedTopic &&
                        !reviewed
                      );

                    const method =
                      question.proposed_classification
                        ?.classification_method ||
                      'unclassified';

                    const confidenceValue =
                      question.proposed_classification
                        ?.confidence_score;

                    const confidence =
                      typeof confidenceValue === 'number' &&
                      Number.isFinite(confidenceValue)
                        ? `${Math.round(confidenceValue * 100)}%`
                        : '—';

                    return (
                      <tr key={question.question_id}>
                        <td>
                          <span className="c2-qid-chip">
                            {question.question_id}
                          </span>

                          <div className="c2-question-text">
                            {question.question_text}
                          </div>

                          <div className="c2-question-meta">
                            {question.marks != null && (
                              <span>
                                <strong>
                                  {question.marks}
                                </strong>{' '}
                                marks
                                {question.marks_status
                                  ? ` (${question.marks_status})`
                                  : ''}
                              </span>
                            )}

                            {question.bloom_level && (
                              <span>
                                {' '}• Bloom: {question.bloom_level}
                              </span>
                            )}

                            {question.difficulty && (
                              <span>
                                {' '}• Difficulty: {question.difficulty}
                              </span>
                            )}
                          </div>
                        </td>

                        <td>
                          <div className="c2-source-details">
                            <div className="c2-source-item">
                              <span className="pill status-authentic">
                                Authentic
                              </span>
                            </div>

                            <div className="c2-source-item">
                              Paper:{' '}
                              <strong>
                                {question.paper_id || '—'}
                              </strong>
                            </div>

                            <div className="c2-source-item">
                              File:{' '}
                              <strong>
                                {question.source_filename || '—'}
                              </strong>
                            </div>

                            <div className="c2-source-item">
                              Year:{' '}
                              <strong>
                                {question.calendar_year || '—'}
                                {' '}(Sem{' '}
                                {question.semester || '—'})
                              </strong>
                            </div>

                            {question.part_id && (
                              <div className="c2-source-item">
                                Part:{' '}
                                <strong>
                                  {question.part_id}
                                </strong>
                              </div>
                            )}
                          </div>
                        </td>

                        <td>
                          <div className="c2-topic-badge">
                            {proposedTopic || 'Unclassified'}
                          </div>

                          <div className="c2-classification-meta">
                            {!proposedTopic && (
                              <span>
                                Awaiting topic classification
                              </span>
                            )}

                            {question.proposed_classification
                              ?.subtopic && (
                              <span>
                                Subtopic:{' '}
                                {question.proposed_classification.subtopic}
                              </span>
                            )}

                            <span>
                              Method: {method}
                            </span>

                            <span>
                              Confidence: {confidence}
                            </span>
                          </div>
                        </td>

                        <td>
                          <StatusBadge question={question} />

                          {reviewed && (
                            <div className="c2-review-details">
                              <div>
                                Reviewer:{' '}
                                <strong>
                                  {question.review.reviewer_id || '—'}
                                </strong>
                              </div>

                              {question.review.reviewed_at && (
                                <div>
                                  Date:{' '}
                                  {new Date(
                                    question.review.reviewed_at
                                  ).toLocaleDateString()}
                                </div>
                              )}

                              {question.review.review_notes && (
                                <div className="c2-review-notes">
                                  “{question.review.review_notes}”
                                </div>
                              )}
                            </div>
                          )}
                        </td>

                        <td className="c2-actions-cell">
                          {reviewed ? (
                            <span className="c2-reviewed-badge muted">
                              Reviewed ({question.review.decision})
                            </span>
                          ) : !proposedTopic ? (
                            <span
                              className="c2-reviewed-badge muted"
                              title="A proposed topic is required before lecturer review."
                            >
                              Awaiting classification
                            </span>
                          ) : (
                            <div className="c2-actions-group">
                              <div className="c2-actions-row">
                                <button
                                  type="button"
                                  className="btn-reject small-btn"
                                  disabled={saving || !canReject}
                                  onClick={() =>
                                    openReview(
                                      question,
                                      'rejected'
                                    )
                                  }
                                >
                                  Reject
                                </button>

                                <button
                                  type="button"
                                  className="btn-approve small-btn"
                                  disabled={saving || !canApprove}
                                  title={
                                    canApprove
                                      ? 'Approve topic classification'
                                      : 'Approval requires a verified taxonomy and valid topic.'
                                  }
                                  onClick={() =>
                                    openReview(
                                      question,
                                      'approved'
                                    )
                                  }
                                >
                                  Approve
                                </button>
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="c2-pagination">
              <span className="muted">
                Page {page} of {totalPages}{' '}
                ({data?.total ?? 0} total questions)
              </span>

              <div className="c2-pagination-controls">
                <button
                  type="button"
                  className="btn secondary small-btn"
                  disabled={
                    page <= 1 || loading || saving
                  }
                  onClick={() =>
                    setPage((current) =>
                      Math.max(1, current - 1)
                    )
                  }
                >
                  Previous
                </button>

                <button
                  type="button"
                  className="btn secondary small-btn"
                  disabled={
                    page >= totalPages ||
                    loading ||
                    saving
                  }
                  onClick={() =>
                    setPage((current) => current + 1)
                  }
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Review modal */}
      {selected && (
        <div
          className="c2-modal-backdrop"
          role="presentation"
        >
          <div
            className="c2-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <div className="c2-modal-head">
              <h3 id="modal-title">
                Review Question Classification
              </h3>

              <button
                type="button"
                className="c2-modal-close"
                disabled={saving}
                onClick={closeReview}
                aria-label="Close modal"
              >
                &times;
              </button>
            </div>

            <div className="c2-modal-summary">
              <div className="c2-modal-summary-item">
                Question ID:{' '}
                <strong>
                  {selected.question_id}
                </strong>
              </div>

              <div className="c2-modal-summary-item">
                Paper:{' '}
                <strong>
                  {selected.paper_id}
                </strong>{' '}
                ({selected.source_filename})
              </div>

              <div className="c2-modal-summary-item">
                Proposed Topic:{' '}
                <strong>
                  {selectedTopic || 'Unclassified'}
                </strong>
              </div>

              <div
                className="c2-modal-summary-item"
                style={{
                  marginTop: 8,
                  fontStyle: 'italic',
                  color: 'var(--muted)',
                }}
              >
                “
                {selected.question_text?.length > 150
                  ? `${selected.question_text.slice(0, 150)}...`
                  : selected.question_text}
                ”
              </div>
            </div>

            <form onSubmit={handleSubmitReview}>
              <fieldset className="c2-decision-fieldset">
                <legend>Decision</legend>

                <div className="c2-decision-options">
                  <label
                    className={`c2-decision-option ${
                      !selected.can_approve
                        ? 'disabled'
                        : ''
                    }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value="approved"
                      checked={decision === 'approved'}
                      disabled={
                        saving ||
                        !selectedTopic ||
                        !selected.can_approve
                      }
                      onChange={() =>
                        setDecision('approved')
                      }
                    />

                    Approve classification
                  </label>

                  <label className="c2-decision-option">
                    <input
                      type="radio"
                      name="decision"
                      value="rejected"
                      checked={decision === 'rejected'}
                      disabled={
                        saving || !selectedTopic
                      }
                      onChange={() =>
                        setDecision('rejected')
                      }
                    />

                    Reject classification
                  </label>
                </div>
              </fieldset>

              {!selected.can_approve && (
                <p className="muted small">
                  Approval is unavailable until the
                  taxonomy and proposed topic satisfy
                  verification requirements.
                </p>
              )}

              <label className="c2-notes-field">
                <span>
                  Review notes{' '}
                  {decision === 'rejected' ? (
                    <span className="c2-notes-hint required">
                      (Reason required for rejection)
                    </span>
                  ) : (
                    <span className="c2-notes-hint">
                      (Optional)
                    </span>
                  )}
                </span>

                <textarea
                  rows={4}
                  maxLength={2000}
                  value={notes}
                  disabled={saving}
                  placeholder={
                    decision === 'rejected'
                      ? 'Explain why this proposed classification is rejected...'
                      : 'Optional notes on approved classification...'
                  }
                  onChange={(event) =>
                    setNotes(event.target.value)
                  }
                />

                <span className="c2-notes-hint">
                  {notes.length} / 2000 characters
                </span>
              </label>

              <label className="c2-confirm-label">
                <input
                  type="checkbox"
                  checked={confirmed}
                  disabled={saving}
                  onChange={(event) =>
                    setConfirmed(event.target.checked)
                  }
                />

                I have inspected this authentic
                examination question and evaluated its
                proposed classification.
              </label>

              <div className="c2-modal-actions">
                <button
                  type="button"
                  className="btn secondary"
                  disabled={saving}
                  onClick={closeReview}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className={
                    decision === 'approved'
                      ? 'btn btn-approve'
                      : 'btn'
                  }
                  disabled={
                    saving ||
                    !selectedTopic ||
                    !confirmed ||
                    (
                      decision === 'rejected' &&
                      !notes.trim()
                    ) ||
                    (
                      decision === 'approved' &&
                      !selected.can_approve
                    )
                  }
                >
                  {saving
                    ? 'Saving Decision...'
                    : decision === 'approved'
                      ? 'Confirm Approval'
                      : 'Confirm Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
