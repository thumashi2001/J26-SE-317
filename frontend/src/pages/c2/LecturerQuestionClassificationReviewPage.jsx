import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  getC2Modules,
  getC2QuestionClassificationReviews,
  submitC2QuestionClassificationReview,
  getC2QuestionClassificationReviewAnalytics,
  getC2TaxonomyReview,
  submitC2TaxonomyDecision,
  getC2QuestionClassificationEvaluations,
} from '../../services/c2Api.js';

import ExperimentalTopicClassifierSection from './components/ExperimentalTopicClassifierSection.jsx';
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
  if (!normalized || normalized.toLowerCase() === 'unclassified') {
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
    return <span className="pill status-approved">Verified Ground Truth</span>;
  }
  if (decision === 'rejected') {
    return <span className="pill status-rejected">Rejected</span>;
  }
  if (decision === 'deferred') {
    return <span className="pill status-deferred">Deferred Review</span>;
  }

  const suggStatus = question?.suggestion_status;
  if (suggStatus === 'suggested_for_review') {
    return <span className="pill status-suggested">Suggested for Review</span>;
  }
  if (suggStatus === 'low_confidence_review') {
    return <span className="pill status-low-confidence">Low Confidence Review</span>;
  }
  if (suggStatus === 'abstained') {
    return <span className="pill status-abstained">Abstained</span>;
  }

  if (!getProposedTopic(question)) {
    return <span className="pill status-pending">Awaiting Classification</span>;
  }

  return <span className="pill status-pending">Pending Review</span>;
}

export default function LecturerQuestionClassificationReviewPage() {
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('');
  const [activeTab, setActiveTab] = useState('queue');
  const [page, setPage] = useState(1);
  const [includeReviewed, setIncludeReviewed] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const [data, setData] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [taxonomyDetails, setTaxonomyDetails] = useState(null);
  const [evaluationInfo, setEvaluationInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [taxonomyLoading, setTaxonomyLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  // Review modal state
  const [selected, setSelected] = useState(null);
  const [decision, setDecision] = useState('approved');
  const [isCorrection, setIsCorrection] = useState(false);
  const [selectedTopicId, setSelectedTopicId] = useState('');
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
          .map((item) => (typeof item === 'string' ? item : item?.module_key))
          .filter((key) => typeof key === 'string' && key.trim());

        setModules(keys);
        if (keys.length > 0) {
          setModuleKey((current) => current || keys[0]);
        }
      } catch (err) {
        if (active) {
          setError(err.message || 'Could not load modules.');
        }
      }
    }

    loadModules();
    return () => {
      active = false;
    };
  }, []);

  // Load review candidates, analytics, taxonomy details, and evaluation info.
  useEffect(() => {
    if (!moduleKey) return;

    let active = true;

    async function loadAllData() {
      setLoading(true);
      setError('');
      setData(null);

      try {
        const [reviewsRes, analyticsRes, taxonomyRes, evalRes] = await Promise.allSettled([
          getC2QuestionClassificationReviews({
            moduleKey,
            page,
            pageSize: PAGE_SIZE,
            includeReviewed,
            statusFilter: statusFilter !== 'all' ? statusFilter : undefined,
          }),
          getC2QuestionClassificationReviewAnalytics(moduleKey),
          getC2TaxonomyReview(moduleKey),
          getC2QuestionClassificationEvaluations(moduleKey),
        ]);

        if (!active) return;

        if (reviewsRes.status === 'fulfilled') {
          setData(reviewsRes.value);
        } else {
          setError(reviewsRes.reason?.message || 'Could not load reviews.');
        }

        if (analyticsRes.status === 'fulfilled') {
          setAnalytics(analyticsRes.value);
        }

        if (taxonomyRes.status === 'fulfilled') {
          setTaxonomyDetails(taxonomyRes.value);
        }

        if (evalRes.status === 'fulfilled') {
          setEvaluationInfo(evalRes.value);
        }
      } catch (err) {
        if (active) {
          setError(err.message || 'Error loading review data.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadAllData();
    return () => {
      active = false;
    };
  }, [moduleKey, page, includeReviewed, statusFilter, refreshKey]);

  const questions = Array.isArray(data?.questions) ? data.questions : [];
  const statistics = data?.statistics ?? null;
  const taxonomyStatus = data?.taxonomy_status ?? null;
  const totalPages = Math.max(1, Number(data?.total_pages) || 1);

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

  async function handleApproveTaxonomy() {
    if (!moduleKey || taxonomyLoading) return;
    setTaxonomyLoading(true);
    setError('');
    try {
      await submitC2TaxonomyDecision(moduleKey, {
        decision: 'approved',
        reviewNotes: 'Curriculum taxonomy approved by academic reviewer.',
      });
      setNotice(`Taxonomy for ${formatModule(moduleKey)} approved successfully.`);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err.message || 'Failed to approve taxonomy.');
    } finally {
      setTaxonomyLoading(false);
    }
  }

  function openReview(question, initialDecision = 'approved', correctionMode = false) {
    setSelected(question);
    setDecision(initialDecision);
    setIsCorrection(correctionMode);

    const firstCandidate = question.candidate_topics?.[0]?.topic_id;
    const proposed = getProposedTopic(question);
    const initialTopic = correctionMode
      ? (taxonomyDetails?.topics?.[0]?.topic_id || '')
      : (proposed || firstCandidate || taxonomyDetails?.topics?.[0]?.topic_id || '');

    setSelectedTopicId(initialTopic);
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
    setIsCorrection(false);
    setSelectedTopicId('');
  }

  async function handleSubmitReview(event) {
    event.preventDefault();
    if (!selected || saving || !confirmed) return;

    if (decision === 'approved' && !selectedTopicId) {
      setError('Please select an appropriate topic from the curriculum taxonomy.');
      return;
    }

    if (decision === 'rejected' && !notes.trim()) {
      setError('Please provide a reason for rejection in review notes.');
      return;
    }

    if (notes.trim().length > 2000) {
      setError('Review notes must be 2000 characters or fewer.');
      return;
    }

    setSaving(true);
    setError('');

    try {
      await submitC2QuestionClassificationReview(selected.question_id, {
        moduleKey,
        topicId: decision === 'approved' ? selectedTopicId : '',
        decision,
        reviewNotes: notes.trim(),
        isCorrection,
        allowManual: isCorrection || !getProposedTopic(selected),
      });

      setSelected(null);
      setConfirmed(false);
      setNotes('');
      setNotice(
        `Successfully saved ${decision} review for question ${selected.question_id}.`
      );
      setRefreshKey((current) => current + 1);
    } catch (err) {
      setError(err.message || 'Failed to submit review decision.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="c2-classification-review">
      <header className="c2-dashboard-head">
        <div>
          <h1>Authentic Question Topic Classification & Verification</h1>
          <p className="muted">
            Inspect authentic exam questions, examine taxonomy-aligned AI candidate rankings,
            and record auditable human verification ground truth.
          </p>
        </div>

        <nav className="c2-header-nav" aria-label="C2 Navigation">
          <Link to="/lecturer/c2" className="btn secondary small-btn">
            Syllabus Review
          </Link>
          <Link to="/lecturer/c2/synthetic-preview" className="btn secondary small-btn">
            Synthetic Preview
          </Link>
        </nav>
      </header>

      {/* Coverage & Verification Analytics Cards */}
      <section className="c2-analytics-summary" aria-label="Coverage and Verification Analytics">
        <div className="c2-analytics-card">
          <div className="c2-analytics-label">Total Authentic Questions</div>
          <div className="c2-analytics-val">
            {analytics?.total_authentic_questions ?? (statistics ? statistics.total : '—')}
          </div>
          <div className="c2-analytics-desc">Authentic SLIIT Year 3 past-paper items</div>
        </div>

        <div className="c2-analytics-card" style={{ borderLeft: '4px solid #3b82f6' }}>
          <div className="c2-analytics-label">AI Suggestion Coverage</div>
          <div className="c2-analytics-val">
            {analytics ? `${Math.round(analytics.suggestion_coverage * 100)}%` : '—'}
          </div>
          <div className="c2-analytics-desc">
            {analytics
              ? `${analytics.suggested_for_review + analytics.low_confidence_review} with candidate suggestions`
              : 'Candidate ranking suggestions'}
          </div>
        </div>

        <div className="c2-analytics-card" style={{ borderLeft: '4px solid #10b981' }}>
          <div className="c2-analytics-label">Lecturer Verified Coverage</div>
          <div className="c2-analytics-val">
            {analytics ? `${Math.round(analytics.verified_coverage * 100)}%` : '—'}
          </div>
          <div className="c2-analytics-desc">
            {analytics?.lecturer_approved ?? 0} approved ground-truth labels
          </div>
        </div>

        <div className="c2-analytics-card" style={{ borderLeft: '4px solid #8b5cf6' }}>
          <div className="c2-analytics-label">Evaluated Authentic Accuracy</div>
          <div className="c2-analytics-val" style={{ fontSize: '1.05rem', marginTop: 4 }}>
            {evaluationInfo?.evaluable
              ? `${Math.round(evaluationInfo.metrics.top1_accuracy * 100)}% Top-1`
              : 'Not Evaluable'}
          </div>
          <div className="c2-analytics-desc">
            {evaluationInfo?.evaluable
              ? `Top-3 Recall: ${Math.round(evaluationInfo.metrics.top3_candidate_recall * 100)}%`
              : 'Requires verified authentic labels'}
          </div>
        </div>
      </section>

      {/* Module Taxonomy Verification Banner */}
      <div
        className={`c2-taxonomy-banner ${taxonomyStatus?.is_verified ? 'verified' : 'unverified'}`}
        role="region"
        aria-label="Module Taxonomy Status"
      >
        <div className="c2-taxonomy-info">
          <div className="c2-taxonomy-title">
            <span>
              {taxonomyStatus?.is_verified ? '✓ Taxonomy Verified' : '⚠ Taxonomy Unverified'}:
            </span>
            <span>{formatModule(moduleKey)}</span>
            <span className="muted" style={{ fontWeight: 400, fontSize: '0.8rem' }}>
              (v{taxonomyDetails?.taxonomy_version || '1.0.0'})
            </span>
          </div>

          <div className="c2-taxonomy-topics-preview">
            Curriculum Topics: {taxonomyDetails?.topics?.map((t) => t.topic_name).join(' • ') || 'Loading topics...'}
          </div>

          {taxonomyStatus?.is_verified ? (
            <p className="muted small" style={{ margin: 0 }}>
              Curriculum taxonomy is verified by academic staff. Approved question classifications will count towards historical exam prediction evidence.
            </p>
          ) : (
            <p className="muted small" style={{ margin: 0, color: 'var(--warn, #f59e0b)' }}>
              Taxonomy must be verified before student prediction evidence can be promoted. You can review and approve the module taxonomy below.
            </p>
          )}
        </div>

        {!taxonomyStatus?.is_verified && (
          <button
            type="button"
            className="btn btn-approve small-btn"
            disabled={taxonomyLoading}
            onClick={handleApproveTaxonomy}
          >
            {taxonomyLoading ? 'Approving...' : 'Approve Module Taxonomy'}
          </button>
        )}
      </div>

      {/* Feedback messages */}
      {notice && (
        <p className="c2-feedback c2-feedback-success" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="c2-feedback c2-feedback-error" role="alert">
          {error}
        </p>
      )}

      {/* Tabs */}
      <div className="c2-view-tabs" role="tablist" aria-label="Review Workflow Tabs">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'queue'}
          className={`c2-view-tab ${activeTab === 'queue' ? 'active' : ''}`}
          onClick={() => setActiveTab('queue')}
        >
          Authentic Question Review Queue
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'classifier'}
          className={`c2-view-tab ${activeTab === 'classifier' ? 'active' : ''}`}
          onClick={() => setActiveTab('classifier')}
        >
          Experimental AI Topic Classifier Demo (M17)
        </button>
      </div>

      {activeTab === 'classifier' && (
        <ExperimentalTopicClassifierSection
          modules={modules}
          activeModuleKey={moduleKey}
          onSelectModule={setModuleKey}
        />
      )}

      {activeTab === 'queue' && (
        <section className="panel c2-main-panel">
          <div className="c2-panel-heading">
            <div>
              <h3>Question Classification Queue</h3>
              <p className="muted small">
                Authentic past paper questions with candidate topic suggestions and verification controls.
              </p>
            </div>

            <button
              type="button"
              className="btn secondary small-btn"
              disabled={loading || saving || !moduleKey}
              onClick={() => setRefreshKey((current) => current + 1)}
            >
              Refresh Queue
            </button>
          </div>

          {/* Filter Bar */}
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

            <label className="c2-module-field">
              <span>Filter Status</span>
              <select
                value={statusFilter}
                disabled={saving}
                onChange={(event) => {
                  setStatusFilter(event.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Questions</option>
                <option value="suggested_for_review">AI Suggested for Review</option>
                <option value="low_confidence_review">Low Confidence Review</option>
                <option value="abstained">Abstained (No Candidates)</option>
                <option value="verified">Verified (Approved)</option>
                <option value="rejected">Rejected Proposals</option>
                <option value="deferred">Deferred for Later Review</option>
              </select>
            </label>

            <label className="c2-search-field">
              <span>Search Questions</span>
              <input
                type="text"
                placeholder="Search by ID, text, topic..."
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
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

          {loading && (
            <div className="c2-loading" role="status">
              Loading authentic examination questions...
            </div>
          )}

          {!loading && filteredQuestions.length === 0 && (
            <div className="c2-empty">
              <h4>No questions found</h4>
              <p>
                {searchQuery.trim()
                  ? 'No questions on this page match your search filter.'
                  : 'No questions match the current filter criteria.'}
              </p>
            </div>
          )}

          {!loading && filteredQuestions.length > 0 && (
            <>
              <div className="c2-table-wrap">
                <table className="c2-table">
                  <thead>
                    <tr>
                      <th style={{ width: '28%' }}>Question Details</th>
                      <th style={{ width: '20%' }}>Source Evidence</th>
                      <th style={{ width: '27%' }}>Topic Candidates & Signals</th>
                      <th style={{ width: '13%' }}>Review Status</th>
                      <th style={{ width: '12%' }}>Action</th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredQuestions.map((question) => {
                      const reviewed = hasReview(question);
                      const candidates = question.candidate_topics || [];
                      const topCandidate = candidates[0];

                      return (
                        <tr key={question.question_id}>
                          <td>
                            <span className="c2-qid-chip">{question.question_id}</span>
                            <div className="c2-question-text">{question.question_text}</div>
                            <div className="c2-question-meta">
                              {question.marks != null && (
                                <span>
                                  <strong>{question.marks}</strong> marks
                                  {question.marks_status ? ` (${question.marks_status})` : ''}
                                </span>
                              )}
                              {question.bloom_level && <span> • Bloom: {question.bloom_level}</span>}
                              {question.difficulty && <span> • Difficulty: {question.difficulty}</span>}
                            </div>
                          </td>

                          <td>
                            <div className="c2-source-details">
                              <div className="c2-source-item">
                                <span className="pill status-authentic">Authentic</span>
                              </div>
                              <div className="c2-source-item">
                                Paper: <strong>{question.paper_id || '—'}</strong>
                              </div>
                              <div className="c2-source-item">
                                File: <strong>{question.source_filename || '—'}</strong>
                              </div>
                              <div className="c2-source-item">
                                Year: <strong>{question.calendar_year || '—'} (Sem {question.semester || '—'})</strong>
                              </div>
                              {question.part_id && (
                                <div className="c2-source-item">
                                  Part: <strong>{question.part_id}</strong>
                                </div>
                              )}
                            </div>
                          </td>

                          <td>
                            {candidates.length > 0 ? (
                              <div className="c2-candidate-container">
                                {candidates.slice(0, 3).map((cand, idx) => (
                                  <div key={cand.topic_id || idx} className="c2-candidate-item">
                                    <div className="c2-candidate-header">
                                      <span>#{idx + 1} {cand.topic_name}</span>
                                      <span className="c2-candidate-score" title="Hybrid candidate ranking score (combining keyword overlap, TF-IDF cosine similarity, and model confidence)">
                                        Rank: {cand.combined_score ? cand.combined_score.toFixed(3) : '—'}
                                      </span>
                                    </div>
                                    <div className="c2-candidate-signals">
                                      {cand.explanation || (cand.matched_terms?.length ? `Matched: ${cand.matched_terms.join(', ')}` : 'Taxonomy aligned')}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <div className="muted small" style={{ fontStyle: 'italic', padding: '6px 0' }}>
                                No confident topic candidates generated (abstained).
                              </div>
                            )}
                          </td>

                          <td>
                            <StatusBadge question={question} />
                            {reviewed && (
                              <div className="c2-review-details">
                                <div>
                                  Topic: <strong>{question.review.topic_id || 'Unassigned'}</strong>
                                </div>
                                <div>
                                  By: <strong>{question.review.reviewer_id || '—'}</strong>
                                </div>
                                {question.review.reviewed_at && (
                                  <div>
                                    Date: {new Date(question.review.reviewed_at).toLocaleDateString()}
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
                              <button
                                type="button"
                                className="btn secondary small-btn"
                                onClick={() => openReview(question, question.review.decision, true)}
                              >
                                Edit Review
                              </button>
                            ) : (
                              <div className="c2-actions-group">
                                <div className="c2-actions-row">
                                  {topCandidate && (
                                    <button
                                      type="button"
                                      className="btn-approve small-btn"
                                      disabled={saving}
                                      onClick={() => openReview(question, 'approved', false)}
                                    >
                                      Approve
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    className="btn secondary small-btn"
                                    disabled={saving}
                                    onClick={() => openReview(question, 'approved', true)}
                                  >
                                    Correct Topic
                                  </button>
                                </div>
                                <div className="c2-actions-row">
                                  <button
                                    type="button"
                                    className="btn-defer small-btn"
                                    disabled={saving}
                                    onClick={() => openReview(question, 'deferred', false)}
                                  >
                                    Defer
                                  </button>
                                  <button
                                    type="button"
                                    className="btn-reject small-btn"
                                    disabled={saving}
                                    onClick={() => openReview(question, 'rejected', false)}
                                  >
                                    Reject
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
                  Page {page} of {totalPages} ({data?.total ?? 0} total questions)
                </span>

                <div className="c2-pagination-controls">
                  <button
                    type="button"
                    className="btn secondary small-btn"
                    disabled={page <= 1 || loading || saving}
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                  >
                    Previous
                  </button>

                  <button
                    type="button"
                    className="btn secondary small-btn"
                    disabled={page >= totalPages || loading || saving}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      )}

      {/* Review Modal */}
      {selected && (
        <div className="c2-modal-backdrop" role="presentation">
          <div className="c2-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <div className="c2-modal-head">
              <h3 id="modal-title">Lecturer Question Classification Review</h3>
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
                Question ID: <strong>{selected.question_id}</strong>
              </div>
              <div className="c2-modal-summary-item">
                Paper: <strong>{selected.paper_id}</strong> ({selected.source_filename})
              </div>
              <div
                className="c2-modal-summary-item"
                style={{ marginTop: 8, fontStyle: 'italic', color: 'var(--muted)', whiteSpace: 'pre-wrap' }}
              >
                “{selected.question_text}”
              </div>
            </div>

            <form onSubmit={handleSubmitReview}>
              <fieldset className="c2-decision-fieldset">
                <legend>Review Decision</legend>
                <div className="c2-decision-options" style={{ flexWrap: 'wrap', gap: 12 }}>
                  <label className="c2-decision-option">
                    <input
                      type="radio"
                      name="decision"
                      value="approved"
                      checked={decision === 'approved' && !isCorrection}
                      disabled={saving || !(selected.candidate_topics?.length || getProposedTopic(selected))}
                      onChange={() => {
                        setDecision('approved');
                        setIsCorrection(false);
                        const firstCand = selected.candidate_topics?.[0]?.topic_id;
                        setSelectedTopicId(getProposedTopic(selected) || firstCand || '');
                      }}
                    />
                    Approve AI Suggestion
                  </label>

                  <label className="c2-decision-option">
                    <input
                      type="radio"
                      name="decision"
                      value="correction"
                      checked={decision === 'approved' && isCorrection}
                      disabled={saving}
                      onChange={() => {
                        setDecision('approved');
                        setIsCorrection(true);
                        if (!selectedTopicId && taxonomyDetails?.topics?.length) {
                          setSelectedTopicId(taxonomyDetails.topics[0].topic_id);
                        }
                      }}
                    />
                    Select / Correct Topic Manually
                  </label>

                  <label className="c2-decision-option">
                    <input
                      type="radio"
                      name="decision"
                      value="deferred"
                      checked={decision === 'deferred'}
                      disabled={saving}
                      onChange={() => {
                        setDecision('deferred');
                        setIsCorrection(false);
                      }}
                    />
                    Defer for Later Review
                  </label>

                  <label className="c2-decision-option">
                    <input
                      type="radio"
                      name="decision"
                      value="rejected"
                      checked={decision === 'rejected'}
                      disabled={saving}
                      onChange={() => {
                        setDecision('rejected');
                        setIsCorrection(false);
                      }}
                    />
                    Reject AI Proposal
                  </label>
                </div>
              </fieldset>

              {/* Topic Selection Dropdown if Approved or Corrected */}
              {decision === 'approved' && (
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: '0.86rem', fontWeight: 600 }}>
                    Select Verified Topic from Curriculum Taxonomy:
                    <select
                      className="c2-topic-select"
                      value={selectedTopicId}
                      disabled={saving}
                      onChange={(e) => setSelectedTopicId(e.target.value)}
                    >
                      <option value="">-- Choose Curriculum Topic --</option>
                      {taxonomyDetails?.topics?.map((t) => (
                        <option key={t.topic_id} value={t.topic_id}>
                          {t.topic_name} ({t.topic_id})
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              )}

              {/* Review Notes */}
              <label className="c2-notes-field">
                <span>
                  Review Notes{' '}
                  {decision === 'rejected' ? (
                    <span className="c2-notes-hint required">(Reason required for rejection)</span>
                  ) : (
                    <span className="c2-notes-hint">(Optional justification or notes)</span>
                  )}
                </span>

                <textarea
                  rows={3}
                  maxLength={2000}
                  value={notes}
                  disabled={saving}
                  placeholder={
                    decision === 'rejected'
                      ? 'Explain why this proposed classification is rejected...'
                      : decision === 'deferred'
                        ? 'Explain why this question classification is deferred for later review...'
                        : 'Optional review notes on approved curriculum topic...'
                  }
                  onChange={(event) => setNotes(event.target.value)}
                />
                <span className="c2-notes-hint">{notes.length} / 2000 characters</span>
              </label>

              <label className="c2-confirm-label">
                <input
                  type="checkbox"
                  checked={confirmed}
                  disabled={saving}
                  onChange={(event) => setConfirmed(event.target.checked)}
                />
                I confirm that I have inspected this authentic examination question and this review decision reflects verified curriculum ground truth.
              </label>

              <div className="c2-modal-actions">
                <button type="button" className="btn secondary" disabled={saving} onClick={closeReview}>
                  Cancel
                </button>

                <button
                  type="submit"
                  className={decision === 'approved' ? 'btn btn-approve' : 'btn'}
                  disabled={
                    saving ||
                    !confirmed ||
                    (decision === 'approved' && !selectedTopicId) ||
                    (decision === 'rejected' && !notes.trim())
                  }
                >
                  {saving
                    ? 'Saving Decision...'
                    : decision === 'approved'
                      ? (isCorrection ? 'Confirm Manual Topic' : 'Confirm Approval')
                      : decision === 'deferred'
                        ? 'Confirm Deferral'
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
