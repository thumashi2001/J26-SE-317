import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  getC2Modules,
  getC2GenerationTopics,
  generateC2BloomQuestion,
  submitC2BloomQuestionDecision,
  getC2ApprovedGeneratedQuestions,
  getC2BloomClassifierEvaluation,
} from '../../services/c2Api.js';
import './lecturerQuestionGeneration.css';

const BLOOM_LEVELS = [
  { id: 'remember', label: 'Remember', desc: 'Recall definitions, list terms, state concepts' },
  { id: 'understand', label: 'Understand', desc: 'Explain principles, describe mechanisms, contrast ideas' },
  { id: 'apply', label: 'Apply', desc: 'Execute algorithms, decompose schema, write SQL/code' },
  { id: 'analyze', label: 'Analyze', desc: 'Diagnose bottlenecks, examine trade-offs, break down anomalies' },
  { id: 'evaluate', label: 'Evaluate', desc: 'Critique proposals, defend architectural choices, assess flaws' },
  { id: 'create', label: 'Create', desc: 'Design complete schemas, formulate architectures, devise models' },
];

const QUESTION_TYPES = [
  { id: 'structured', label: 'Structured (Multi-part)' },
  { id: 'short_answer', label: 'Short Answer' },
  { id: 'essay', label: 'Essay / Scenario' },
  { id: 'mcq', label: 'Multiple Choice (MCQ)' },
];

const DIFFICULTIES = [
  { id: 'easy', label: 'Easy' },
  { id: 'medium', label: 'Medium' },
  { id: 'hard', label: 'Hard' },
];

function formatModuleName(key) {
  if (!key) return '';
  return key
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export default function LecturerQuestionGenerationPage() {
  const [activeTab, setActiveTab] = useState('generator'); // 'generator' | 'repository' | 'evidence'

  // Modules & Topics
  const [modules, setModules] = useState([]);
  const [moduleKey, setModuleKey] = useState('database_systems');
  const [topics, setTopics] = useState([]);
  const [topicId, setTopicId] = useState('');
  const [topicsLoading, setTopicsLoading] = useState(false);

  // Form Parameters
  const [bloomLevel, setBloomLevel] = useState('apply');
  const [difficulty, setDifficulty] = useState('medium');
  const [questionType, setQuestionType] = useState('structured');
  const [marks, setMarks] = useState(10);
  const [instructions, setInstructions] = useState('');

  // Generation & Candidate State
  const [generating, setGenerating] = useState(false);
  const [candidate, setCandidate] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState('');
  const [editedMarks, setEditedMarks] = useState(10);

  // Review & Decision State
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');
  const [rejectionModalOpen, setRejectionModalOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  // Repository & Evidence State
  const [approvedQuestions, setApprovedQuestions] = useState([]);
  const [repoLoading, setRepoLoading] = useState(false);
  const [bloomEvaluation, setBloomEvaluation] = useState(null);
  const [evalLoading, setEvalLoading] = useState(false);

  // Feedback Messages
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  // Load modules on mount
  useEffect(() => {
    async function loadModules() {
      try {
        const res = await getC2Modules();
        const list = Array.isArray(res) ? res : res?.modules || [];
        const keys = list.map((item) => (typeof item === 'string' ? item : item.module_key)).filter(Boolean);
        setModules(keys);
        if (keys.length > 0 && !keys.includes(moduleKey)) {
          setModuleKey(keys[0]);
        }
      } catch (err) {
        setError('Failed to load modules list.');
      }
    }
    loadModules();
  }, []);

  // Load topics whenever module changes
  useEffect(() => {
    if (!moduleKey) return;
    async function loadTopics() {
      setTopicsLoading(true);
      try {
        const res = await getC2GenerationTopics(moduleKey);
        const topicList = res?.topics || [];
        setTopics(topicList);
        if (topicList.length > 0) {
          // If switching to database_systems, default to normalization topic if present
          const normTopic = topicList.find((t) => t.topic_id.includes('normalization'));
          setTopicId(normTopic ? normTopic.topic_id : topicList[0].topic_id);
        } else {
          setTopicId('');
        }
      } catch (err) {
        setError(`Failed to load curriculum topics for ${formatModuleName(moduleKey)}.`);
      } finally {
        setTopicsLoading(false);
      }
    }
    loadTopics();
  }, [moduleKey]);

  // Load approved repository questions
  useEffect(() => {
    if (activeTab === 'repository') {
      loadApprovedQuestions();
    } else if (activeTab === 'evidence') {
      loadEvaluationReport();
    }
  }, [activeTab, moduleKey]);

  async function loadApprovedQuestions() {
    setRepoLoading(true);
    try {
      const res = await getC2ApprovedGeneratedQuestions(moduleKey);
      setApprovedQuestions(res?.questions || []);
    } catch (err) {
      setError('Failed to load approved questions repository.');
    } finally {
      setRepoLoading(false);
    }
  }

  async function loadEvaluationReport() {
    setEvalLoading(true);
    try {
      const res = await getC2BloomClassifierEvaluation();
      setBloomEvaluation(res);
    } catch (err) {
      setError('Failed to load Bloom classifier evaluation.');
    } finally {
      setEvalLoading(false);
    }
  }

  // Handle Generate
  async function handleGenerate(e) {
    if (e) e.preventDefault();
    if (!moduleKey || !topicId) {
      setError('Please select both a module and a curriculum topic.');
      return;
    }

    setGenerating(true);
    setError('');
    setNotice('');
    setIsEditing(false);

    try {
      const result = await generateC2BloomQuestion({
        moduleKey,
        topicId,
        bloomLevel,
        difficulty,
        questionType,
        marks: Number(marks) || 10,
        lecturerInstructions: instructions,
      });

      setCandidate(result);
      setEditedText(result.question_text);
      setEditedMarks(result.marks);
      setNotice(`Generated ${formatModuleName(result.bloom_level)} candidate for ${result.topic_name}.`);
    } catch (err) {
      setError(err.message || 'Question generation failed.');
    } finally {
      setGenerating(false);
    }
  }

  // Handle Approve
  async function handleApprove() {
    if (!candidate || submittingDecision) return;
    setSubmittingDecision(true);
    setError('');
    setNotice('');

    try {
      const res = await submitC2BloomQuestionDecision({
        decision: 'approved',
        question: candidate,
        reviewNotes: reviewNotes.trim() || 'Approved by lecturer.',
        updatedText: isEditing ? editedText : undefined,
        updatedMarks: isEditing ? editedMarks : undefined,
      });

      setNotice(`Question ${candidate.question_id} approved and saved to repository.`);
      setCandidate((prev) => ({ ...prev, ...res.question, approval_status: 'approved' }));
      setIsEditing(false);
      setReviewNotes('');
    } catch (err) {
      setError(err.message || 'Failed to approve question.');
    } finally {
      setSubmittingDecision(false);
    }
  }

  // Handle Reject
  async function handleReject() {
    if (!candidate || submittingDecision) return;
    if (!rejectionReason.trim()) {
      setError('Please provide a reason for rejecting the candidate.');
      return;
    }

    setSubmittingDecision(true);
    setError('');
    setNotice('');

    try {
      await submitC2BloomQuestionDecision({
        decision: 'rejected',
        question: candidate,
        reviewNotes: rejectionReason.trim(),
      });

      setNotice(`Candidate ${candidate.question_id} rejected and logged for audit.`);
      setRejectionModalOpen(false);
      setRejectionReason('');
      setCandidate(null);
    } catch (err) {
      setError(err.message || 'Failed to reject candidate.');
    } finally {
      setSubmittingDecision(false);
    }
  }

  return (
    <div className="c2-generation-page">
      {/* Top Header */}
      <header className="c2-gen-header">
        <div>
          <h1>Bloom's Taxonomy-Controlled Question Generation</h1>
          <p>
            Novelty 2: Curriculum-Grounded Examination Question Authoring, Cognitive-Depth Regulation, and Multi-Dimensional Quality Validation
          </p>
        </div>
        <nav aria-label="Review Navigation">
          <Link to="/lecturer/c2/classification-review" className="btn btn-secondary small-btn">
            ← Back to Topic Classification Review
          </Link>
        </nav>
      </header>

      {/* Navigation Tabs */}
      <div className="c2-gen-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'generator'}
          className={`c2-gen-tab ${activeTab === 'generator' ? 'active' : ''}`}
          onClick={() => setActiveTab('generator')}
        >
          Question Generator & Review
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'repository'}
          className={`c2-gen-tab ${activeTab === 'repository' ? 'active' : ''}`}
          onClick={() => setActiveTab('repository')}
        >
          Approved Questions Repository ({approvedQuestions.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'evidence'}
          className={`c2-gen-tab ${activeTab === 'evidence' ? 'active' : ''}`}
          onClick={() => setActiveTab('evidence')}
        >
          Bloom Classifier Empirical Evidence
        </button>
      </div>

      {/* Feedback Messages */}
      {notice && (
        <div className="c2-feedback c2-feedback-success" role="status" style={{ marginBottom: 16 }}>
          {notice}
        </div>
      )}
      {error && (
        <div className="c2-feedback c2-feedback-error" role="alert" style={{ marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* TAB 1: GENERATOR & REVIEW */}
      {activeTab === 'generator' && (
        <div className="c2-gen-layout">
          {/* Left: Parameter Form */}
          <section className="c2-gen-form-panel" aria-label="Question Parameter Configuration">
            <h3 style={{ margin: '0 0 16px', fontSize: '1.1rem' }}>Configure Generation Parameters</h3>

            <form onSubmit={handleGenerate}>
              {/* Module Dropdown */}
              <div className="c2-form-group">
                <label htmlFor="gen-module">Target SE Module</label>
                <select
                  id="gen-module"
                  value={moduleKey}
                  onChange={(e) => setModuleKey(e.target.value)}
                  disabled={generating}
                >
                  {modules.map((key) => (
                    <option key={key} value={key}>
                      {formatModuleName(key)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Curriculum Topic Dropdown */}
              <div className="c2-form-group">
                <label htmlFor="gen-topic">Curriculum Topic (Approved Taxonomy)</label>
                <select
                  id="gen-topic"
                  value={topicId}
                  onChange={(e) => setTopicId(e.target.value)}
                  disabled={generating || topicsLoading || topics.length === 0}
                >
                  {topicsLoading ? (
                    <option value="">Loading curriculum topics...</option>
                  ) : topics.length === 0 ? (
                    <option value="">No topics configured</option>
                  ) : (
                    topics.map((t) => (
                      <option key={t.topic_id} value={t.topic_id}>
                        {t.topic_name}
                      </option>
                    ))
                  )}
                </select>
              </div>

              {/* Bloom Level Selector */}
              <div className="c2-form-group">
                <label>Bloom's Cognitive Level</label>
                <div className="c2-bloom-buttons">
                  {BLOOM_LEVELS.map((lvl) => (
                    <button
                      key={lvl.id}
                      type="button"
                      className={`c2-bloom-btn ${bloomLevel === lvl.id ? 'active' : ''}`}
                      onClick={() => setBloomLevel(lvl.id)}
                      disabled={generating}
                      title={lvl.desc}
                    >
                      {lvl.label}
                    </button>
                  ))}
                </div>
                <div className="c2-bloom-hint">
                  {BLOOM_LEVELS.find((l) => l.id === bloomLevel)?.desc}
                </div>
              </div>

              {/* Difficulty & Question Type Row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="c2-form-group">
                  <label htmlFor="gen-diff">Difficulty</label>
                  <select
                    id="gen-diff"
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    disabled={generating}
                  >
                    {DIFFICULTIES.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="c2-form-group">
                  <label htmlFor="gen-type">Question Type</label>
                  <select
                    id="gen-type"
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value)}
                    disabled={generating}
                  >
                    {QUESTION_TYPES.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Marks */}
              <div className="c2-form-group">
                <label htmlFor="gen-marks">Total Marks</label>
                <input
                  id="gen-marks"
                  type="number"
                  min="1"
                  max="100"
                  value={marks}
                  onChange={(e) => setMarks(Math.max(1, parseInt(e.target.value, 10) || 1))}
                  disabled={generating}
                />
              </div>

              {/* Optional Guidance */}
              <div className="c2-form-group">
                <label htmlFor="gen-inst">Lecturer Guidance / Context (Optional)</label>
                <textarea
                  id="gen-inst"
                  rows="2"
                  placeholder="e.g. Focus on equipment rental or e-commerce transactions..."
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  disabled={generating}
                />
              </div>

              {/* Submit Button */}
              <button type="submit" className="c2-btn-generate" disabled={generating || topicsLoading}>
                {generating ? 'Generating Question Candidate...' : '⚡ Generate Question Candidate'}
              </button>
            </form>
          </section>

          {/* Right: Candidate Review & Validation Card */}
          <section className="c2-candidate-panel" aria-label="Generated Question Candidate Review">
            {!candidate ? (
              <div className="c2-candidate-empty">
                <h3>No Question Candidate Generated Yet</h3>
                <p>
                  Select a module, topic, and Bloom's cognitive level from the left panel and click{' '}
                  <strong>Generate Question Candidate</strong> to produce an exam item grounded in SLIIT curriculum taxonomies.
                </p>
              </div>
            ) : (
              <div>
                {/* Header & Badges */}
                <div className="c2-candidate-header">
                  <div>
                    <h3 style={{ margin: '0 0 6px', fontSize: '1.15rem' }}>
                      {candidate.question_id}
                    </h3>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                      {candidate.module_name} • {candidate.topic_name}
                    </div>
                  </div>

                  <div className="c2-candidate-badges">
                    <span className="c2-badge c2-badge-bloom">{candidate.bloom_level}</span>
                    <span className="c2-badge c2-badge-marks">{candidate.marks} Marks</span>
                    <span className="c2-badge c2-badge-diff">{candidate.difficulty}</span>
                    <span className="c2-badge c2-badge-type">{candidate.question_type}</span>
                    <span className="c2-badge c2-badge-synthetic">Synthetic (Not Authentic)</span>
                  </div>
                </div>

                {/* Question Text */}
                <div className="c2-candidate-body">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <strong>Question Statement:</strong>
                    <button
                      type="button"
                      className="btn small-btn"
                      style={{ fontSize: '0.78rem' }}
                      onClick={() => setIsEditing(!isEditing)}
                    >
                      {isEditing ? 'Cancel Editing' : '✏ Edit Text & Marks'}
                    </button>
                  </div>

                  {isEditing ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      <textarea
                        rows="8"
                        style={{ width: '100%', padding: 12, borderRadius: 6, border: '1px solid #3b82f6', fontFamily: 'inherit' }}
                        value={editedText}
                        onChange={(e) => setEditedText(e.target.value)}
                      />
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Adjusted Marks:</label>
                        <input
                          type="number"
                          style={{ width: 80, padding: 6, borderRadius: 4, border: '1px solid #cbd5e1' }}
                          value={editedMarks}
                          onChange={(e) => setEditedMarks(parseInt(e.target.value, 10) || 1)}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="c2-candidate-text">{candidate.question_text}</div>
                  )}

                  {/* Subquestions breakdown if available */}
                  {candidate.subquestions && candidate.subquestions.length > 0 && (
                    <div className="c2-subquestion-box">
                      <div style={{ background: '#f8fafc', padding: '8px 14px', fontWeight: 600, fontSize: '0.85rem' }}>
                        Subquestion Structure & Mark Allocation
                      </div>
                      {candidate.subquestions.map((sq, i) => (
                        <div key={i} className="c2-subq-row">
                          <div>
                            <span className="c2-subq-part">({sq.part})</span>
                            <span>{sq.subquestion_text}</span>
                          </div>
                          <span className="c2-subq-marks">[{sq.marks} Marks]</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Marking Guide Preview */}
                  {candidate.marking_guide && (
                    <div style={{ marginTop: 14, background: '#f8fafc', padding: 12, borderRadius: 6, border: '1px solid #e2e8f0', fontSize: '0.88rem' }}>
                      <strong style={{ display: 'block', marginBottom: 4, color: '#334155' }}>
                        Evaluator Marking Guide & Solution Criteria:
                      </strong>
                      <div style={{ whiteSpace: 'pre-line', color: '#475569' }}>{candidate.marking_guide}</div>
                    </div>
                  )}
                </div>

                {/* Multi-Dimensional Validation Scorecard */}
                {candidate.validation && (
                  <div className="c2-validation-section" aria-label="Validation Scorecard">
                    <div className="c2-validation-title">
                      <span>Multi-Dimensional AI & Curriculum Quality Scorecard</span>
                      <span style={{ fontSize: '0.8rem', fontWeight: 500, color: '#64748b' }}>
                        Provenance: {candidate.generation_method}
                      </span>
                    </div>

                    <div className="c2-validation-grid">
                      {/* Topic Alignment */}
                      <div className="c2-val-card">
                        <div className="c2-val-head">
                          <span>Curriculum Alignment</span>
                          <span className={`c2-val-pill ${candidate.validation.curriculum_alignment?.status}`}>
                            {candidate.validation.curriculum_alignment?.status?.toUpperCase()}
                          </span>
                        </div>
                        <div className="c2-val-details">
                          {candidate.validation.curriculum_alignment?.details}
                          {candidate.validation.curriculum_alignment?.matched_keywords?.length > 0 && (
                            <div style={{ marginTop: 4, fontSize: '0.75rem', color: '#2563eb' }}>
                              Keywords: {candidate.validation.curriculum_alignment.matched_keywords.join(', ')}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Bloom Alignment */}
                      <div className="c2-val-card">
                        <div className="c2-val-head">
                          <span>Bloom's Cognitive Match</span>
                          <span className={`c2-val-pill ${candidate.validation.bloom_alignment?.status}`}>
                            {candidate.validation.bloom_alignment?.status?.toUpperCase()}
                          </span>
                        </div>
                        <div className="c2-val-details">
                          {candidate.validation.bloom_alignment?.details}
                          <div style={{ marginTop: 4, fontSize: '0.72rem', color: '#94a3b8' }}>
                            {candidate.validation.bloom_alignment?.limitations}
                          </div>
                        </div>
                      </div>

                      {/* Duplicate Check */}
                      <div className="c2-val-card">
                        <div className="c2-val-head">
                          <span>Duplicate Risk</span>
                          <span className={`c2-val-pill ${candidate.validation.duplicate_check?.similarity_risk}`}>
                            {candidate.validation.duplicate_check?.similarity_risk?.toUpperCase()} RISK
                          </span>
                        </div>
                        <div className="c2-val-details">
                          Max Similarity: {candidate.validation.duplicate_check?.max_similarity_pct}%
                          <div style={{ marginTop: 2 }}>{candidate.validation.duplicate_check?.details}</div>
                        </div>
                      </div>

                      {/* Structure & Marks */}
                      <div className="c2-val-card">
                        <div className="c2-val-head">
                          <span>Structural Integrity</span>
                          <span className={`c2-val-pill ${candidate.validation.structure_validation?.status}`}>
                            {candidate.validation.structure_validation?.status?.toUpperCase()}
                          </span>
                        </div>
                        <div className="c2-val-details">
                          {candidate.validation.structure_validation?.details}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Lecturer Review Actions */}
                <div className="c2-actions-toolbar">
                  {candidate.approval_status === 'approved' ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#16a34a', fontWeight: 600 }}>
                      ✓ Question Approved & Saved in Repository
                    </div>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="c2-btn-action c2-btn-regen"
                        onClick={handleGenerate}
                        disabled={generating || submittingDecision}
                      >
                        🔄 Regenerate Candidate
                      </button>

                      <button
                        type="button"
                        className="c2-btn-action c2-btn-reject"
                        onClick={() => setRejectionModalOpen(true)}
                        disabled={generating || submittingDecision}
                      >
                        ✕ Reject Candidate
                      </button>

                      <div style={{ flex: 1 }} />

                      <input
                        type="text"
                        placeholder="Optional review notes..."
                        style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: '0.88rem', minWidth: 220 }}
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        disabled={submittingDecision}
                      />

                      <button
                        type="button"
                        className="c2-btn-action c2-btn-approve"
                        onClick={handleApprove}
                        disabled={generating || submittingDecision}
                      >
                        {submittingDecision ? 'Saving...' : '✓ Approve & Save Question'}
                      </button>
                    </>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>
      )}

      {/* TAB 2: APPROVED QUESTION REPOSITORY */}
      {activeTab === 'repository' && (
        <section aria-label="Approved Questions Repository">
          <div style={{ background: '#f8fafc', padding: '14px 18px', borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 20 }}>
            <strong>Research Integrity Safeguard:</strong> All items in this repository are lecturer-reviewed synthetic questions (
            <code>is_authentic: false</code>). They are stored separately from authentic SLIIT past papers and strictly excluded from future-exam historical prediction evidence.
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <h3 style={{ margin: 0 }}>Approved Questions for {formatModuleName(moduleKey)}</h3>
            <button type="button" className="btn small-btn" onClick={loadApprovedQuestions} disabled={repoLoading}>
              {repoLoading ? 'Refreshing...' : 'Refresh Repository'}
            </button>
          </div>

          {approvedQuestions.length === 0 ? (
            <div style={{ padding: 36, textAlign: 'center', background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', color: '#64748b' }}>
              No lecturer-approved questions saved for {formatModuleName(moduleKey)} yet. Generate and approve candidates in the Generator tab.
            </div>
          ) : (
            approvedQuestions.map((q) => (
              <div key={q.question_id} className="c2-repo-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                  <div>
                    <strong style={{ fontSize: '1.05rem', color: '#1e293b' }}>{q.question_id}</strong>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                      {q.topic_name} • Approved by: {q.reviewer_id} ({new Date(q.approved_at).toLocaleDateString()})
                    </div>
                  </div>
                  <div className="c2-candidate-badges">
                    <span className="c2-badge c2-badge-bloom">{q.bloom_level}</span>
                    <span className="c2-badge c2-badge-marks">{q.marks} Marks</span>
                    <span className="c2-badge c2-badge-diff">{q.difficulty}</span>
                    <span className="c2-badge c2-badge-type">{q.question_type}</span>
                  </div>
                </div>

                <div className="c2-candidate-text" style={{ fontSize: '0.92rem' }}>{q.question_text}</div>

                {q.review_notes && (
                  <div style={{ marginTop: 8, fontSize: '0.82rem', color: '#475569' }}>
                    <em>Review Notes: {q.review_notes}</em>
                  </div>
                )}
              </div>
            ))
          )}
        </section>
      )}

      {/* TAB 3: BLOOM CLASSIFIER EMPIRICAL EVIDENCE */}
      {activeTab === 'evidence' && (
        <section aria-label="Bloom Classifier Empirical Evidence">
          <div style={{ background: '#f8fafc', padding: '14px 18px', borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 20 }}>
            <h4 style={{ margin: '0 0 6px' }}>Empirical Bloom Classification Model Evidence</h4>
            <p style={{ margin: 0, fontSize: '0.88rem', color: '#475569' }}>
              Reproducible machine learning experiment evaluating cognitive classification on the 800-question synthetic corpus (M16).
              Trained via <strong>TF-IDF (1–2 n-grams) + Multinomial Logistic Regression</strong> with module-disjoint leakage-aware splitting.
            </p>
          </div>

          {evalLoading || !bloomEvaluation ? (
            <div style={{ padding: 36, textAlign: 'center' }}>Loading evaluation metrics...</div>
          ) : (
            <div>
              {/* Summary Stats */}
              <div className="c2-experiment-grid">
                <div className="c2-stat-box">
                  <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>Test Accuracy (Cross-Module)</div>
                  <div className="c2-stat-num">{(bloomEvaluation.overall_metrics.accuracy * 100).toFixed(1)}%</div>
                  <div className="c2-stat-sub">Evaluated on {bloomEvaluation.test_sample_count} held-out module questions</div>
                </div>

                <div className="c2-stat-box">
                  <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>Macro-Averaged F1 Score</div>
                  <div className="c2-stat-num">{(bloomEvaluation.overall_metrics.macro_f1 * 100).toFixed(1)}%</div>
                  <div className="c2-stat-sub">Balanced across all 4 cognitive classes</div>
                </div>

                <div className="c2-stat-box">
                  <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>Authentic Corpus Status</div>
                  <div className="c2-stat-num" style={{ fontSize: '1.25rem', color: '#d97706', marginTop: 10 }}>
                    Not Evaluable
                  </div>
                  <div className="c2-stat-sub">443 authentic items lack verified Bloom labels</div>
                </div>
              </div>

              {/* Per-Class Metrics Table */}
              <h4 style={{ marginBottom: 10 }}>Per-Class Classification Metrics</h4>
              <table className="c2-repo-table" style={{ marginBottom: 24 }}>
                <thead>
                  <tr>
                    <th>Bloom Level</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1-Score</th>
                    <th>Test Support</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(bloomEvaluation.per_class_metrics || {}).map(([cls, met]) => (
                    <tr key={cls}>
                      <td><strong>{cls.toUpperCase()}</strong></td>
                      <td>{(met.precision * 100).toFixed(1)}%</td>
                      <td>{(met.recall * 100).toFixed(1)}%</td>
                      <td>{(met.f1_score * 100).toFixed(1)}%</td>
                      <td>{met.support} questions</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Confusion Matrix */}
              <h4 style={{ marginBottom: 10 }}>Cross-Module Confusion Matrix</h4>
              <table className="c2-conf-matrix">
                <thead>
                  <tr>
                    <th>True \ Predicted</th>
                    {bloomEvaluation.confusion_matrix.labels.map((l) => (
                      <th key={l}>{l.toUpperCase()}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bloomEvaluation.confusion_matrix.labels.map((rowLabel, i) => (
                    <tr key={rowLabel}>
                      <td><strong>{rowLabel.toUpperCase()}</strong></td>
                      {bloomEvaluation.confusion_matrix.matrix[i].map((val, j) => (
                        <td key={j} style={{ background: i === j ? '#dbeafe' : 'transparent', fontWeight: i === j ? 700 : 400 }}>
                          {val}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Research Integrity Disclaimer */}
              <div style={{ marginTop: 24, padding: 14, background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: 8, fontSize: '0.85rem', color: '#92400e' }}>
                <strong>VIVA Defense Notice:</strong> Zero-shot cross-module accuracy reflects strict domain transfer without data leakage. Authentic past-paper evaluation remains uncalculated to prevent fraudulent claims of authentic accuracy before academic lecturers verify real exam questions.
              </div>
            </div>
          )}
        </section>
      )}

      {/* Rejection Reason Modal */}
      {rejectionModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div style={{ background: '#ffffff', padding: 24, borderRadius: 8, width: 440, maxWidth: '90%' }}>
            <h3 style={{ margin: '0 0 12px' }}>Reject Question Candidate</h3>
            <p style={{ margin: '0 0 14px', fontSize: '0.88rem', color: '#64748b' }}>
              Please state why this generated candidate is being rejected. This feedback is logged for quality auditing.
            </p>
            <textarea
              rows="4"
              style={{ width: '100%', padding: 10, borderRadius: 6, border: '1px solid #cbd5e1', marginBottom: 14, fontFamily: 'inherit' }}
              placeholder="e.g. Scenario context is ambiguous or cognitive depth is too shallow for 10 marks..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                className="btn btn-secondary small-btn"
                onClick={() => setRejectionModalOpen(false)}
                disabled={submittingDecision}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn small-btn"
                style={{ background: '#dc2626', color: '#ffffff' }}
                onClick={handleReject}
                disabled={submittingDecision || !rejectionReason.trim()}
              >
                {submittingDecision ? 'Submitting...' : 'Confirm Rejection'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
