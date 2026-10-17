
import { useEffect, useState } from 'react';
import {
  getC2Modules,
  getC2ReviewQueue,
  getC2ReviewStatistics,
  submitC2Review,
} from '../../services/c2Api.js';

import './lecturerSyllabusReview.css';

const PAGE_SIZE = 10;

function formatModule(key) {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function StatusBadge({ status }) {
  const safeStatus = ['approved', 'rejected'].includes(status)
    ? status
    : 'pending';

  return (
    <span className={`pill status-${safeStatus}`}>
      {safeStatus.charAt(0).toUpperCase() + safeStatus.slice(1)}
    </span>
  );
}

export default function LecturerSyllabusReviewPage() {
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('');
  const [page, setPage] = useState(1);
  const [includeReviewed, setIncludeReviewed] = useState(false);

  const [queue, setQueue] = useState(null);
  const [statistics, setStatistics] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const [selected, setSelected] = useState(null);
  const [decision, setDecision] = useState('approved');
  const [notes, setNotes] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);

  const [refreshKey, setRefreshKey] = useState(0);

  // Load supported modules.
  useEffect(() => {
    let active = true;

    getC2Modules()
      .then((data) => {
        if (!active) return;

        const items = Array.isArray(data.modules)
          ? data.modules
          : [];

        setModules(items);

        if (items.length) {
          setModuleKey(items[0]);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message || 'Could not load modules.');
        }
      });

    return () => {
      active = false;
    };
  }, []);

  // Load review queue and module-wide statistics.
  useEffect(() => {
    let active = true;

    async function load() {
      if (!moduleKey) return;

      setLoading(true);
      setError('');
      setQueue(null);
      setStatistics(null);

      try {
        const [queueResult, statsResult] = await Promise.all([
          getC2ReviewQueue(moduleKey, {
            page,
            pageSize: PAGE_SIZE,
            includeReviewed,
          }),
          getC2ReviewStatistics(moduleKey),
        ]);

        if (!active) return;

        setQueue(queueResult);
        setStatistics(statsResult);
      } catch (err) {
        if (active) {
          setError(
            err.message || 'Could not load syllabus reviews.'
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      active = false;
    };
  }, [moduleKey, page, includeReviewed, refreshKey]);

  const candidates = queue?.candidates ?? [];
  const totalCandidates = queue?.total_candidates ?? 0;
  const totalPages = Math.max(1, queue?.total_pages ?? 1);

  function openReview(candidate, action) {
    setSelected(candidate);
    setDecision(action);
    setNotes('');
    setConfirmed(false);
    setError('');
    setNotice('');
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!selected || !confirmed || saving) return;

    if (!['approved', 'rejected'].includes(decision)) {
      setError('Invalid review decision.');
      return;
    }

    if (decision === 'rejected' && !notes.trim()) {
      setError('Please provide a reason for rejection.');
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
      await submitC2Review(
        moduleKey,
        selected.candidate_id,
        {
          decision,
          reviewNotes: notes.trim(),
        }
      );

      setSelected(null);
      setConfirmed(false);
      setNotice(
        `Review saved: ${selected.candidate_name}`
      );

      // Refresh both the queue and module-wide statistics.
      setRefreshKey((value) => value + 1);
    } catch (err) {
      setError(
        err.message || 'Could not save the review.'
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="c2-dashboard">
      <header className="c2-dashboard-head">
        <h1>Syllabus topic review</h1>
        <p className="muted">
          Review and verify syllabus topics extracted from
          lecture materials before they are used for
          examination intelligence.
        </p>
      </header>

      {/* M8: Module-wide statistics */}
      <section
        className="c2-stats stat-grid"
        aria-label="Review statistics"
      >
        <div
          className="stat"
          style={{ '--c': 'var(--primary)' }}
        >
          <div className="stat-num">
            {statistics
              ? statistics.total.toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Total candidates
          </div>
        </div>

        <div
          className="stat"
          style={{ '--c': 'var(--warn)' }}
        >
          <div className="stat-num">
            {statistics
              ? statistics.pending.toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Pending reviews
          </div>
        </div>

        <div
          className="stat"
          style={{ '--c': 'var(--good)' }}
        >
          <div className="stat-num">
            {statistics
              ? statistics.approved.toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Approved topics
          </div>
        </div>

        <div
          className="stat"
          style={{ '--c': 'var(--bad)' }}
        >
          <div className="stat-num">
            {statistics
              ? statistics.rejected.toLocaleString()
              : '—'}
          </div>
          <div className="stat-label">
            Rejected topics
          </div>
        </div>
      </section>

      <section className="panel c2-main-panel">
        <div className="c2-panel-heading">
          <div>
            <h3>Topic verification queue</h3>
            <p className="muted small">
              Select a module and inspect each
              candidate's source evidence.
            </p>
          </div>

          <button
            type="button"
            className="btn secondary small-btn"
            disabled={loading || saving || !moduleKey}
            onClick={() =>
              setRefreshKey((value) => value + 1)
            }
          >
            Refresh
          </button>
        </div>

        <div className="c2-filters">
          <label className="c2-module-field">
            <span>Module</span>
            <select
              value={moduleKey}
              disabled={saving}
              onChange={(event) => {
                setModuleKey(event.target.value);
                setPage(1);
                setNotice('');
                setSelected(null);
              }}
            >
              {modules.map((key) => (
                <option key={key} value={key}>
                  {formatModule(key)}
                </option>
              ))}
            </select>
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
            Include reviewed candidates
          </label>
        </div>

        <div className="c2-info-banner">
          <strong>Review guidance.</strong>{' '}
          Ranking scores indicate review priority,
          not topic correctness or model confidence.
          Check the source evidence before making
          a decision.
        </div>

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
            Loading syllabus candidates...
          </div>
        )}

        {!loading && queue && (
          <>
            <div className="c2-table-wrap">
              <table className="c2-table">
                <thead>
                  <tr>
                    <th>Candidate topic</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Source evidence</th>
                    <th>Review action</th>
                  </tr>
                </thead>

                <tbody>
                  {candidates.map((candidate) => {
                    const reviewed = [
                      'approved',
                      'rejected',
                    ].includes(
                      candidate.review_decision
                    );

                    return (
                      <tr key={candidate.candidate_id}>
                        <td>
                          <strong className="c2-candidate-name">
                            {candidate.candidate_name}
                          </strong>

                          <span className="c2-candidate-meta">
                            {candidate.document_count ?? 0}
                            {' '}documents ·{' '}
                            {candidate.occurrence_count ?? 0}
                            {' '}occurrences
                          </span>
                        </td>

                        <td>
                          <span className="c2-priority">
                            {candidate.ranking_score ?? '—'}
                          </span>
                        </td>

                        <td>
                          <StatusBadge
                            status={candidate.review_decision}
                          />
                        </td>

                        <td>
                          <details className="c2-evidence">
                            <summary>
                              View{' '}
                              {candidate.sources?.length ?? 0}
                              {' '}references
                            </summary>

                            <ul>
                              {(candidate.sources || []).map(
                                (source, index) => (
                                  <li key={index}>
                                    <span>
                                      {source.filename}
                                    </span>

                                    {source.line_number != null && (
                                      <small>
                                        Line {source.line_number}
                                      </small>
                                    )}
                                  </li>
                                )
                              )}
                            </ul>
                          </details>
                        </td>

                        <td>
                          {reviewed ? (
                            <span className="muted small">
                              Reviewed
                            </span>
                          ) : (
                            <div className="c2-action-group">
                              <button
                                type="button"
                                className="btn small-btn c2-approve-btn"
                                disabled={saving}
                                onClick={() =>
                                  openReview(candidate, 'approved')
                                }
                              >
                                Approve
                              </button>

                              <button
                                type="button"
                                className="btn danger small-btn"
                                disabled={saving}
                                onClick={() =>
                                  openReview(candidate, 'rejected')
                                }
                              >
                                Reject
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {!candidates.length && (
                <p className="empty">
                  No candidates available for this selection.
                </p>
              )}
            </div>

            <div className="c2-pagination">
              <span className="muted small">
                Page {page} of {totalPages} ·{' '}
                {totalCandidates.toLocaleString()}
                {' '}candidates
              </span>

              <div className="c2-action-group">
                <button
                  type="button"
                  className="btn secondary small-btn"
                  disabled={page <= 1 || loading || saving}
                  onClick={() =>
                    setPage((value) => value - 1)
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
                    setPage((value) => value + 1)
                  }
                >
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Lecturer review confirmation modal */}
      {selected && (
        <div className="c2-modal-overlay">
          <form
            className="panel c2-modal"
            onSubmit={handleSubmit}
            role="dialog"
            aria-modal="true"
            aria-labelledby="c2-modal-title"
          >
            <h2 id="c2-modal-title">
              Confirm topic review
            </h2>

            <div className="c2-modal-topic">
              <strong>
                {selected.candidate_name}
              </strong>
              <span className="muted small">
                {formatModule(moduleKey)}
              </span>
            </div>

            <fieldset
              disabled={saving}
              className="c2-decision-fieldset"
            >
              <legend>Review decision</legend>

              <label>
                <input
                  type="radio"
                  name="decision"
                  checked={decision === 'approved'}
                  onChange={() => {
                    setDecision('approved');
                    setConfirmed(false);
                  }}
                />
                Approve topic
              </label>

              <label>
                <input
                  type="radio"
                  name="decision"
                  checked={decision === 'rejected'}
                  onChange={() => {
                    setDecision('rejected');
                    setConfirmed(false);
                  }}
                />
                Reject topic
              </label>
            </fieldset>

            <label className="c2-notes-label">
              Review notes
              <textarea
                rows={4}
                maxLength={2000}
                value={notes}
                disabled={saving}
                onChange={(event) =>
                  setNotes(event.target.value)
                }
                placeholder="Enter the reason for your decision..."
              />
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
              I have reviewed this candidate and
              its source references.
            </label>

            <div className="c2-modal-actions">
              <button
                type="button"
                className="btn secondary"
                disabled={saving}
                onClick={() => setSelected(null)}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="btn"
                disabled={
                  saving ||
                  !confirmed ||
                  (decision === 'rejected' && !notes.trim())
                }
              >
                {saving
                  ? 'Saving...'
                  : `Confirm ${decision}`}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
