import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  createBatchSetup,
  listBatchSetups,
  getBatchSetup,
  validateBatchAnswers,
  processBatchMarking,
  finalizeBatchSubmissions,
  reviewSubmission,
  finalizeSubmission,
  getSubmission,
} from '../../services/c3Api.js';
import { C3_PRESETS } from './presets.js';
import MindMapGraph from './components/MindMapGraph.jsx';
import CriterionCard from './components/CriterionCard.jsx';
import ConceptDiagnosis from './components/ConceptDiagnosis.jsx';
import './c3.css';

export default function LecturerBatchMarkingPage() {
  // Navigation tabs: 'create_and_mark' | 'history'
  const [activeMainTab, setActiveMainTab] = useState('create_and_mark');

  // Step Tracker: 1: Setup -> 2: Add Answers -> 3: Validate & Run -> 4: Results
  const [currentStep, setCurrentStep] = useState(1);

  // --- Step 1: Shared Setup State ---
  const [moduleId, setModuleId] = useState('SE3010');
  const [questionId, setQuestionId] = useState('SE3010-Q01');
  const [assessmentTitle, setAssessmentTitle] = useState('Software Architecture Principles — Modular Abstraction');
  const [questionText, setQuestionText] = useState(
    'Explain the architectural significance of high cohesion and loose coupling in software design. Cite architectural patterns that promote them.'
  );
  const [answerType, setAnswerType] = useState('short'); // 'short' | 'essay' | 'mcq'
  const [maxMarks, setMaxMarks] = useState(4);
  const [referenceAnswer, setReferenceAnswer] = useState(
    'High cohesion ensures single-responsibility and internal coherence. Loose coupling minimizes inter-module dependencies, best exemplified by Microservices or Event-Driven architectures.'
  );
  const [expectedConceptsStr, setExpectedConceptsStr] = useState('high cohesion, loose coupling, microservices');

  // Rubric State (for Subjective)
  const [rubricTitle, setRubricTitle] = useState('Architecture Modular Design Rubric');
  const [criteria, setCriteria] = useState([
    {
      criterion_id: 'C1',
      description: 'Understanding of High Cohesion and Single Responsibility',
      max_marks: 2,
      scoring_levels: [
        { level_id: 'L0', label: 'None', mark: 0, descriptor: 'No cohesion concepts mentioned.' },
        { level_id: 'L1', label: 'Basic', mark: 1, descriptor: 'Mentions internal module cohesion.', required_concepts: ['cohesion'] },
        { level_id: 'L2', label: 'Proficient', mark: 2, descriptor: 'Explains high cohesion with single responsibility.', required_concepts: ['high cohesion'] },
      ],
    },
    {
      criterion_id: 'C2',
      description: 'Understanding of Loose Coupling & Architecture Patterns',
      max_marks: 2,
      scoring_levels: [
        { level_id: 'L0', label: 'None', mark: 0, descriptor: 'No coupling concepts mentioned.' },
        { level_id: 'L1', label: 'Basic', mark: 1, descriptor: 'Mentions loose coupling.', required_concepts: ['loose coupling'] },
        { level_id: 'L2', label: 'Proficient', mark: 2, descriptor: 'Explains loose coupling and cites microservices or event-driven design.', required_concepts: ['loose coupling', 'microservices'] },
      ],
    },
  ]);

  // MCQ State (for MCQ)
  const [mcqOptions, setMcqOptions] = useState([
    { option_id: 'A', label: 'A', text: 'Monolithic Architecture' },
    { option_id: 'B', label: 'B', text: 'Microservices Architecture' },
    { option_id: 'C', label: 'C', text: 'Pipe and Filter Architecture' },
    { option_id: 'D', label: 'D', text: 'Model-View-Controller (MVC)' },
  ]);
  const [mcqCorrectAnswer, setMcqCorrectAnswer] = useState('B');

  // Locked Setup Document from backend
  const [activeSetupDoc, setActiveSetupDoc] = useState(null);
  const [savingSetup, setSavingSetup] = useState(false);
  const [setupError, setSetupError] = useState(null);

  // --- Step 2: Student Answers Input State ---
  const [inputMode, setInputMode] = useState('csv'); // 'csv' | 'grid'
  const [csvText, setCsvText] = useState('');
  const [gridRows, setGridRows] = useState([
    { student_id: 'IT21001001', student_answer: '' },
    { student_id: 'IT21001002', student_answer: '' },
  ]);

  // --- Step 3: Validation State ---
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [validationError, setValidationError] = useState(null);

  // --- Step 4: Batch Marking Execution & Results ---
  const [processing, setProcessing] = useState(false);
  const [markingSummary, setMarkingSummary] = useState(null);
  const [markingError, setMarkingError] = useState(null);
  const [batchItems, setBatchItems] = useState([]);
  const [batchStats, setBatchStats] = useState(null);

  // Table Filters & Search
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  // Batch Finalization
  const [finalizingAll, setFinalizingAll] = useState(false);
  const [finalizeSuccessMsg, setFinalizeSuccessMsg] = useState(null);

  // --- Detail Review Modal State ---
  const [inspectingSubId, setInspectingSubId] = useState(null);
  const [inspectingDetail, setInspectingDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [overrideMarkInput, setOverrideMarkInput] = useState('');
  const [overrideReasonInput, setOverrideReasonInput] = useState('');
  const [reviewActionLoading, setReviewActionLoading] = useState(false);
  const [reviewActionMsg, setReviewActionMsg] = useState(null);

  // --- History Tab State ---
  const [existingSetups, setExistingSetups] = useState([]);
  const [loadingSetups, setLoadingSetups] = useState(false);

  // Check Criteria Sum for Subjective
  const criteriaSum = criteria.reduce((sum, c) => sum + (Number(c.max_marks) || 0), 0);
  const isCriteriaSumValid = answerType === 'mcq' || Math.abs(criteriaSum - Number(maxMarks)) < 0.001;

  // Load Presets into Setup
  const handleLoadPreset = (preset) => {
    setQuestionId(preset.payload.question_id || 'SE-Q01');
    setAssessmentTitle(preset.title);
    setQuestionText(preset.payload.question_text);
    setMaxMarks(preset.payload.max_marks || (preset.payload.rubric ? preset.payload.rubric.criteria.reduce((s, c) => s + c.max_marks, 0) : 2));
    const type = preset.payload.answer_type || (preset.payload.options ? 'mcq' : 'short');
    setAnswerType(type);

    if (preset.payload.expected_concepts) {
      setExpectedConceptsStr(preset.payload.expected_concepts.join(', '));
    }
    if (preset.payload.reference_answer) {
      setReferenceAnswer(preset.payload.reference_answer);
    }
    if (preset.payload.rubric) {
      setRubricTitle(preset.payload.rubric.title || 'Assessment Rubric');
      setCriteria(preset.payload.rubric.criteria || []);
    }
    if (preset.payload.options) {
      setMcqOptions(preset.payload.options);
      setMcqCorrectAnswer(preset.payload.correct_answer || 'B');
    }
    setActiveSetupDoc(null);
    setValidationResult(null);
    setMarkingSummary(null);
    setCurrentStep(1);
  };

  // Add/Remove Criteria
  const handleAddCriterion = () => {
    const nextIdx = criteria.length + 1;
    setCriteria([
      ...criteria,
      {
        criterion_id: `C${nextIdx}`,
        description: `Criterion ${nextIdx} Description`,
        max_marks: 1,
        scoring_levels: [
          { level_id: 'L0', label: 'None', mark: 0, descriptor: 'No evidence provided.' },
          { level_id: 'L1', label: 'Proficient', mark: 1, descriptor: 'Meets expectations.' },
        ],
      },
    ]);
  };

  const handleRemoveCriterion = (idx) => {
    if (criteria.length <= 1) return;
    setCriteria(criteria.filter((_, i) => i !== idx));
  };

  const handleUpdateCriterion = (idx, field, val) => {
    const updated = [...criteria];
    updated[idx] = { ...updated[idx], [field]: val };
    setCriteria(updated);
  };

  // Save / Lock Marking Setup in Backend
  const handleSaveSetup = async () => {
    setSavingSetup(true);
    setSetupError(null);
    try {
      const payload = {
        title: assessmentTitle,
        module_id: moduleId,
        question_id: questionId,
        question_text: questionText,
        answer_type: answerType,
        max_marks: Number(maxMarks),
        expected_concepts: expectedConceptsStr.split(',').map((s) => s.trim()).filter(Boolean),
      };

      if (answerType === 'mcq') {
        payload.options = mcqOptions;
        payload.correct_answer = mcqCorrectAnswer;
      } else {
        payload.reference_answer = referenceAnswer;
        payload.rubric = {
          title: rubricTitle,
          criteria: criteria.map((c) => ({
            ...c,
            max_marks: Number(c.max_marks),
          })),
        };
      }

      const res = await createBatchSetup(payload);
      setActiveSetupDoc(res);
      setCurrentStep(2); // Advance to Add Answers
    } catch (err) {
      console.error('Failed to save setup:', err);
      setSetupError(err.message || 'Failed to create assessment setup.');
    } finally {
      setSavingSetup(false);
    }
  };

  // CSV Parsing
  const parseCsvContent = (text) => {
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
    const parsed = [];
    for (const line of lines) {
      if (line.toLowerCase().startsWith('student_id') || line.toLowerCase().startsWith('id,')) {
        continue; // skip header
      }
      const commaIdx = line.indexOf(',');
      if (commaIdx !== -1) {
        const studentId = line.substring(0, commaIdx).trim().replace(/^["']|["']$/g, '');
        let answer = line.substring(commaIdx + 1).trim();
        if (answer.startsWith('"') && answer.endsWith('"')) {
          answer = answer.substring(1, answer.length - 1).replace(/""/g, '"');
        }
        parsed.push({ student_id: studentId, student_answer: answer, selected_option_id: answer });
      } else {
        parsed.push({ student_id: line.trim(), student_answer: '', selected_option_id: '' });
      }
    }
    return parsed;
  };

  // Pre-fill Sample Cohort Data
  const handleLoadSampleCohort = () => {
    if (answerType === 'mcq') {
      const sample = `student_id,selected_option
IT21001001,B
IT21001002,B
IT21001003,A
IT21001004,C
IT21001005,
IT21001006,Z
IT21001007,B
IT21001001,B`;
      setCsvText(sample);
    } else {
      const sample = `student_id,answer
IT21001001,"High cohesion guarantees that a software module performs one well-defined responsibility. Loose coupling minimizes interdependencies, which is achieved effectively using microservices architecture where each service operates independently."
IT21001002,"High cohesion means modules are cohesive and do one single thing. Loose coupling ensures components do not break each other."
IT21001003,"We used microservices architecture to decouple all communication channels through message queues."
IT21001004,"Cohesion and coupling are good software metrics for modularity."
IT21001005,""
IT21001006,"Irrelevant response discussing relational database normalization."
IT21001001,"Duplicate submission of student 1."`;
      setCsvText(sample);
    }
  };

  // Validate Batch Answers
  const handleValidateBatch = async () => {
    if (!activeSetupDoc?.batch_id && !activeSetupDoc?._id) {
      setValidationError('Please configure and save the assessment setup first.');
      return;
    }

    setValidating(true);
    setValidationError(null);

    let itemsToValidate = [];
    if (inputMode === 'csv') {
      itemsToValidate = parseCsvContent(csvText);
    } else {
      itemsToValidate = gridRows.filter((r) => r.student_id.trim());
    }

    if (itemsToValidate.length === 0) {
      setValidationError('Please provide at least one student answer row.');
      setValidating(false);
      return;
    }

    try {
      const res = await validateBatchAnswers({
        setup_id: activeSetupDoc.batch_id || activeSetupDoc._id,
        items: itemsToValidate,
      });
      setValidationResult(res);
      setCurrentStep(3); // Advance to Preview & Validation
    } catch (err) {
      console.error('Validation error:', err);
      setValidationError(err.message || 'Validation request failed.');
    } finally {
      setValidating(false);
    }
  };

  // Run Automated Batch Marking
  const handleRunBatchMarking = async () => {
    if (!validationResult || validationResult.valid_items.length === 0) {
      setMarkingError('No valid items ready for automated marking.');
      return;
    }

    setProcessing(true);
    setMarkingError(null);
    try {
      const res = await processBatchMarking({
        setup_id: activeSetupDoc.batch_id || activeSetupDoc._id,
        items: validationResult.valid_items,
      });
      setMarkingSummary(res);

      // Refresh batch submissions list
      await refreshBatchResults(activeSetupDoc.batch_id);
      setCurrentStep(4); // Advance to Results Table
    } catch (err) {
      console.error('Batch marking failed:', err);
      setMarkingError(err.message || 'Automated batch marking failed.');
    } finally {
      setProcessing(false);
    }
  };

  // Refresh Submissions in Batch
  const refreshBatchResults = async (batchId) => {
    try {
      const data = await getBatchSetup(batchId);
      setBatchItems(data.items || []);
      setBatchStats(data.stats || null);
    } catch (err) {
      console.error('Failed to load batch results:', err);
    }
  };

  // Finalize All Submissions in Batch
  const handleFinalizeAll = async () => {
    if (!activeSetupDoc?.batch_id) return;
    const confirm = window.confirm(
      `Are you sure you want to finalize all submissions in Batch '${activeSetupDoc.batch_id}'? This will lock scores and sync finalized events to C1.`
    );
    if (!confirm) return;

    setFinalizingAll(true);
    setFinalizeSuccessMsg(null);
    try {
      const res = await finalizeBatchSubmissions(activeSetupDoc.batch_id);
      setFinalizeSuccessMsg(`Successfully finalized ${res.finalized_count} student assessments!`);
      await refreshBatchResults(activeSetupDoc.batch_id);
    } catch (err) {
      console.error('Batch finalization failed:', err);
      alert('Finalization failed: ' + err.message);
    } finally {
      setFinalizingAll(false);
    }
  };

  // Open Detail Inspection Modal
  const handleOpenInspection = async (submissionId) => {
    setInspectingSubId(submissionId);
    setLoadingDetail(true);
    setReviewActionMsg(null);
    try {
      const data = await getSubmission(submissionId);
      setInspectingDetail(data);
      const currentFinalMark = data.result?.final_mark;
      const autoMark = data.result?.automated_mark;
      setOverrideMarkInput(currentFinalMark !== null && currentFinalMark !== undefined ? currentFinalMark : autoMark);
      setOverrideReasonInput(data.result?.override_reason || '');
    } catch (err) {
      console.error('Failed to load submission detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Submit Review Override / Accept
  const handleReviewAction = async (decision) => {
    if (!inspectingSubId) return;
    setReviewActionLoading(true);
    setReviewActionMsg(null);
    try {
      const body = {
        decision,
        new_mark: decision === 'overridden' ? Number(overrideMarkInput) : undefined,
        override_reason: decision === 'overridden' ? overrideReasonInput : undefined,
      };
      await reviewSubmission(inspectingSubId, body);
      setReviewActionMsg(`Assessment mark successfully ${decision}!`);

      // Refresh modal detail and table
      const updated = await getSubmission(inspectingSubId);
      setInspectingDetail(updated);
      if (activeSetupDoc?.batch_id) {
        await refreshBatchResults(activeSetupDoc.batch_id);
      }
    } catch (err) {
      alert('Review action failed: ' + err.message);
    } finally {
      setReviewActionLoading(false);
    }
  };

  // Finalize Individual Submission
  const handleFinalizeIndividual = async () => {
    if (!inspectingSubId) return;
    setReviewActionLoading(true);
    try {
      await finalizeSubmission(inspectingSubId);
      setReviewActionMsg('Assessment successfully finalized and synchronized with C1!');
      const updated = await getSubmission(inspectingSubId);
      setInspectingDetail(updated);
      if (activeSetupDoc?.batch_id) {
        await refreshBatchResults(activeSetupDoc.batch_id);
      }
    } catch (err) {
      alert('Finalize failed: ' + err.message);
    } finally {
      setReviewActionLoading(false);
    }
  };

  // Load Past Setups
  const loadPastSetups = async () => {
    setLoadingSetups(true);
    try {
      const res = await listBatchSetups();
      setExistingSetups(res.setups || []);
    } catch (err) {
      console.error('Failed to list setups:', err);
    } finally {
      setLoadingSetups(false);
    }
  };

  useEffect(() => {
    if (activeMainTab === 'history') {
      loadPastSetups();
    }
  }, [activeMainTab]);

  // Filtered Batch Items
  const filteredItems = batchItems.filter((item) => {
    if (statusFilter !== 'all' && item.status !== statusFilter) return false;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const matchSId = (item.student_id || '').toLowerCase().includes(term);
      const matchAns = (item.student_answer || '').toLowerCase().includes(term);
      if (!matchSId && !matchAns) return false;
    }
    return true;
  });

  return (
    <div className="c3-page">
      {/* Page Header */}
      <div className="c3-header-lead">
        <div>
          <h1>Lecturer Batch Marking Studio</h1>
          <p className="muted" style={{ margin: '4px 0 0' }}>
            AdaptiveLearnSE Component 3 • One Question & One Rubric Setup → Mark Complete Cohorts
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <Link to="/lecturer/c3" className="btn-ghost" style={{ width: 'auto', padding: '6px 14px' }}>
            📋 Assessment Review Queue →
          </Link>
          <button
            type="button"
            className={`btn ${activeMainTab === 'create_and_mark' ? 'primary' : 'secondary'}`}
            style={{ width: 'auto', padding: '6px 14px' }}
            onClick={() => setActiveMainTab('create_and_mark')}
          >
            ⚡ New Batch Marking
          </button>
          <button
            type="button"
            className={`btn ${activeMainTab === 'history' ? 'primary' : 'secondary'}`}
            style={{ width: 'auto', padding: '6px 14px' }}
            onClick={() => setActiveMainTab('history')}
          >
            🗂 Past Batches
          </button>
        </div>
      </div>

      {activeMainTab === 'create_and_mark' ? (
        <>
          {/* Step Progression Bar */}
          <div style={{ display: 'flex', gap: '12px', background: '#ffffff', padding: '12px 18px', borderRadius: '10px', border: '1px solid var(--line)', flexWrap: 'wrap' }}>
            <button
              type="button"
              className={`c3-preset-btn ${currentStep === 1 ? 'active' : ''}`}
              onClick={() => setCurrentStep(1)}
            >
              1. Assessment Setup {activeSetupDoc ? '✅' : ''}
            </button>
            <button
              type="button"
              className={`c3-preset-btn ${currentStep === 2 ? 'active' : ''}`}
              onClick={() => setCurrentStep(2)}
              disabled={!activeSetupDoc}
            >
              2. Add Student Answers
            </button>
            <button
              type="button"
              className={`c3-preset-btn ${currentStep === 3 ? 'active' : ''}`}
              onClick={() => setCurrentStep(3)}
              disabled={!validationResult}
            >
              3. Validate & Confirm
            </button>
            <button
              type="button"
              className={`c3-preset-btn ${currentStep === 4 ? 'active' : ''}`}
              onClick={() => setCurrentStep(4)}
              disabled={batchItems.length === 0}
            >
              4. Results & Review ({batchItems.length})
            </button>
          </div>

          {/* =========================================================================
              STEP 1: SETUP QUESTION & RUBRIC ONCE
             ========================================================================= */}
          {currentStep === 1 && (
            <div className="panel" style={{ margin: '0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Step 1: Configure Assessment & Rubric (Once per Cohort)</h3>
                  <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.9rem' }}>
                    Configure the authoritative question and evaluation criteria. All answers in this batch will be evaluated against this setup.
                  </p>
                </div>
                {/* Presets Bar */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.85rem', alignSelf: 'center', fontWeight: '600', color: 'var(--text-muted)' }}>Load Preset:</span>
                  {C3_PRESETS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className="btn-ghost"
                      style={{ padding: '4px 8px', fontSize: '0.82rem' }}
                      onClick={() => handleLoadPreset(p)}
                    >
                      {p.id}
                    </button>
                  ))}
                </div>
              </div>

              {setupError && (
                <div className="c3-alert c3-alert-danger" style={{ marginBottom: '16px' }}>
                  <strong>Setup Error:</strong> {setupError}
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '16px' }}>
                <div>
                  <label htmlFor="batchModuleId" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Module Code</label>
                  <input
                    id="batchModuleId"
                    value={moduleId}
                    onChange={(e) => setModuleId(e.target.value)}
                    placeholder="e.g. SE3010"
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}
                  />
                </div>
                <div>
                  <label htmlFor="batchQuestionId" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Question Identifier</label>
                  <input
                    id="batchQuestionId"
                    value={questionId}
                    onChange={(e) => setQuestionId(e.target.value)}
                    placeholder="e.g. SE3010-Q01"
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}
                  />
                </div>
                <div>
                  <label htmlFor="batchAnswerType" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Assessment Type</label>
                  <select
                    id="batchAnswerType"
                    value={answerType}
                    onChange={(e) => setAnswerType(e.target.value)}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}
                  >
                    <option value="short">Subjective — Short Answer (Rubric)</option>
                    <option value="essay">Subjective — Essay (Rubric)</option>
                    <option value="mcq">Objective — Multiple Choice Question (MCQ)</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="batchMaxMarks" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Total Max Marks</label>
                  <input
                    id="batchMaxMarks"
                    type="number"
                    min="1"
                    max="100"
                    value={maxMarks}
                    onChange={(e) => setMaxMarks(Number(e.target.value))}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label htmlFor="batchTitle" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Assessment Title</label>
                <input
                  id="batchTitle"
                  value={assessmentTitle}
                  onChange={(e) => setAssessmentTitle(e.target.value)}
                  placeholder="e.g. Midterm Assessment Question 1"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label htmlFor="batchQuestionText" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Question Text</label>
                <textarea
                  id="batchQuestionText"
                  rows="3"
                  value={questionText}
                  onChange={(e) => setQuestionText(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)', fontFamily: 'inherit' }}
                />
              </div>

              {/* Subjective Specific: Reference Answer & Rubric */}
              {answerType !== 'mcq' ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginBottom: '16px' }}>
                    <div>
                      <label htmlFor="batchReferenceAnswer" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Model / Reference Answer</label>
                      <textarea
                        id="batchReferenceAnswer"
                        rows="3"
                        value={referenceAnswer}
                        onChange={(e) => setReferenceAnswer(e.target.value)}
                        placeholder="Model answer used for semantic alignment..."
                        style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)', fontFamily: 'inherit' }}
                      />
                    </div>
                    <div>
                      <label htmlFor="batchExpectedConcepts" style={{ fontWeight: '600', fontSize: '0.88rem' }}>Expected Concepts (comma-separated)</label>
                      <textarea
                        id="batchExpectedConcepts"
                        rows="3"
                        value={expectedConceptsStr}
                        onChange={(e) => setExpectedConceptsStr(e.target.value)}
                        placeholder="e.g. encapsulation, polymorphism, inheritance"
                        style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)', fontFamily: 'inherit' }}
                      />
                    </div>
                  </div>

                  {/* Rubric Configuration */}
                  <div style={{ border: '1px solid var(--line)', borderRadius: '10px', padding: '16px', background: 'var(--paper)', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                      <h4 style={{ margin: 0 }}>Evaluation Rubric: {rubricTitle}</h4>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: '600', color: isCriteriaSumValid ? '#1d6f42' : '#c92a2a' }}>
                          Criteria Marks Sum: {criteriaSum} / {maxMarks} {isCriteriaSumValid ? '✅' : '❌ (Must Match Total Max Marks)'}
                        </span>
                        <button type="button" className="btn secondary" style={{ padding: '4px 10px', fontSize: '0.82rem' }} onClick={handleAddCriterion}>
                          ➕ Add Criterion
                        </button>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {criteria.map((c, idx) => (
                        <div key={idx} style={{ background: '#ffffff', border: '1px solid var(--line)', borderRadius: '8px', padding: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}>
                            <div style={{ display: 'flex', gap: '8px', flex: 1 }}>
                              <input
                                value={c.criterion_id}
                                onChange={(e) => handleUpdateCriterion(idx, 'criterion_id', e.target.value)}
                                style={{ width: '80px', padding: '4px 8px', fontWeight: '700' }}
                                placeholder="ID"
                              />
                              <input
                                value={c.description}
                                onChange={(e) => handleUpdateCriterion(idx, 'description', e.target.value)}
                                style={{ flex: 1, padding: '4px 8px' }}
                                placeholder="Criterion description..."
                              />
                            </div>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                              <label style={{ fontSize: '0.8rem', fontWeight: '600' }}>Marks:</label>
                              <input
                                type="number"
                                min="0.5"
                                step="0.5"
                                value={c.max_marks}
                                onChange={(e) => handleUpdateCriterion(idx, 'max_marks', Number(e.target.value))}
                                style={{ width: '60px', padding: '4px 6px' }}
                              />
                              <button
                                type="button"
                                className="btn-ghost"
                                style={{ color: '#c92a2a', padding: '4px 8px' }}
                                onClick={() => handleRemoveCriterion(idx)}
                                title="Remove Criterion"
                              >
                                ✕
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : (
                /* MCQ Specific: Options & Key */
                <div style={{ border: '1px solid var(--line)', borderRadius: '10px', padding: '16px', background: 'var(--paper)', marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <h4 style={{ margin: 0 }}>Authoritative MCQ Options & Key</h4>
                    <span style={{ fontSize: '0.85rem', fontWeight: '600', color: 'var(--primary)' }}>
                      Authoritative Key: Option {mcqCorrectAnswer}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {mcqOptions.map((opt, idx) => (
                      <div key={idx} style={{ display: 'flex', gap: '12px', alignItems: 'center', background: '#ffffff', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}>
                        <input
                          type="radio"
                          name="correctKeyRadio"
                          checked={mcqCorrectAnswer === opt.option_id || mcqCorrectAnswer === opt.label}
                          onChange={() => setMcqCorrectAnswer(opt.option_id)}
                          title="Set as correct answer"
                        />
                        <span style={{ fontWeight: '700', width: '24px' }}>{opt.label}.</span>
                        <input
                          value={opt.text}
                          onChange={(e) => {
                            const updated = [...mcqOptions];
                            updated[idx] = { ...updated[idx], text: e.target.value };
                            setMcqOptions(updated);
                          }}
                          style={{ flex: 1, padding: '4px 8px', border: '1px solid var(--line)', borderRadius: '4px' }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Save & Lock Button */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
                <button
                  type="button"
                  className="btn primary"
                  disabled={savingSetup || !isCriteriaSumValid}
                  onClick={handleSaveSetup}
                  style={{ width: 'auto', padding: '10px 24px', fontWeight: '600' }}
                >
                  {savingSetup ? 'Saving Setup...' : '💾 Lock Setup & Proceed to Add Answers →'}
                </button>
              </div>
            </div>
          )}

          {/* =========================================================================
              STEP 2: ADD STUDENT ANSWERS (CSV OR GRID)
             ========================================================================= */}
          {currentStep === 2 && (
            <div className="panel" style={{ margin: '0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Step 2: Add Student Answers (Cohort Input)</h3>
                  <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.9rem' }}>
                    Active Setup: <strong>{activeSetupDoc?.batch_id}</strong> • {activeSetupDoc?.question_id} ({activeSetupDoc?.answer_type.toUpperCase()})
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    className={`btn ${inputMode === 'csv' ? 'primary' : 'secondary'}`}
                    style={{ padding: '6px 12px' }}
                    onClick={() => setInputMode('csv')}
                  >
                    📄 Structured CSV
                  </button>
                  <button
                    type="button"
                    className={`btn ${inputMode === 'grid' ? 'primary' : 'secondary'}`}
                    style={{ padding: '6px 12px' }}
                    onClick={() => setInputMode('grid')}
                  >
                    ✏️ Row Grid
                  </button>
                  <button
                    type="button"
                    className="btn secondary"
                    style={{ padding: '6px 12px' }}
                    onClick={handleLoadSampleCohort}
                  >
                    ⚡ Fill Sample Cohort
                  </button>
                </div>
              </div>

              {validationError && (
                <div className="c3-alert c3-alert-danger" style={{ marginBottom: '16px' }}>
                  {validationError}
                </div>
              )}

              {inputMode === 'csv' ? (
                <div>
                  <div style={{ marginBottom: '8px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Format: <code>student_id,answer</code> (or <code>student_id,selected_option</code> for MCQs). Paste lines below or click 'Fill Sample Cohort':
                  </div>
                  <textarea
                    rows="10"
                    value={csvText}
                    onChange={(e) => setCsvText(e.target.value)}
                    placeholder={`student_id,answer\nIT21001001,"High cohesion guarantees modularity..."\nIT21001002,"Loose coupling minimizes dependencies..."`}
                    style={{
                      width: '100%',
                      padding: '12px',
                      borderRadius: '8px',
                      border: '1px solid var(--line)',
                      fontFamily: 'monospace',
                      fontSize: '0.9rem',
                    }}
                  />
                </div>
              ) : (
                <div>
                  <table className="c3-queue-table" style={{ width: '100%', marginBottom: '12px' }}>
                    <thead>
                      <tr>
                        <th style={{ width: '60px' }}>#</th>
                        <th style={{ width: '180px' }}>Student ID</th>
                        <th>Student Typed Answer / Option Key</th>
                        <th style={{ width: '80px' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gridRows.map((row, idx) => (
                        <tr key={idx}>
                          <td>{idx + 1}</td>
                          <td>
                            <input
                              value={row.student_id}
                              onChange={(e) => {
                                const updated = [...gridRows];
                                updated[idx].student_id = e.target.value;
                                setGridRows(updated);
                              }}
                              placeholder="e.g. IT21001001"
                              style={{ width: '100%', padding: '6px 8px' }}
                            />
                          </td>
                          <td>
                            <input
                              value={row.student_answer}
                              onChange={(e) => {
                                const updated = [...gridRows];
                                updated[idx].student_answer = e.target.value;
                                setGridRows(updated);
                              }}
                              placeholder={answerType === 'mcq' ? 'Option (e.g. B)' : 'Student typed answer...'}
                              style={{ width: '100%', padding: '6px 8px' }}
                            />
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn-ghost"
                              style={{ color: '#c92a2a', padding: '4px 8px' }}
                              onClick={() => setGridRows(gridRows.filter((_, i) => i !== idx))}
                            >
                              ✕
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <button
                    type="button"
                    className="btn secondary"
                    style={{ padding: '6px 14px' }}
                    onClick={() => setGridRows([...gridRows, { student_id: '', student_answer: '' }])}
                  >
                    ➕ Add Row
                  </button>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
                <button type="button" className="btn secondary" onClick={() => setCurrentStep(1)}>
                  ← Back to Setup
                </button>
                <button
                  type="button"
                  className="btn primary"
                  disabled={validating}
                  onClick={handleValidateBatch}
                >
                  {validating ? 'Validating Answers...' : '🔍 Validate Batch Answers →'}
                </button>
              </div>
            </div>
          )}

          {/* =========================================================================
              STEP 3: PREVIEW & CONFIRM BATCH
             ========================================================================= */}
          {currentStep === 3 && validationResult && (
            <div className="panel" style={{ margin: '0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Step 3: Preview & Confirm Cohort Marking</h3>
                  <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.9rem' }}>
                    Shared Setup: <strong>{validationResult.question_id}</strong> ({validationResult.answer_type.toUpperCase()})
                  </p>
                </div>
              </div>

              {/* KPI Badges */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                <div style={{ background: '#eaf4ee', border: '1px solid #1d6f42', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: '700', color: '#1d6f42' }}>{validationResult.valid_count}</div>
                  <div style={{ fontSize: '0.85rem', color: '#1d6f42', fontWeight: '500' }}>Valid Answers Ready</div>
                </div>
                <div style={{ background: validationResult.invalid_count > 0 ? '#fdf0ed' : '#f8f9fa', border: `1px solid ${validationResult.invalid_count > 0 ? '#d9381e' : 'var(--line)'}`, borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: '700', color: validationResult.invalid_count > 0 ? '#d9381e' : 'var(--text)' }}>
                    {validationResult.invalid_count}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: validationResult.invalid_count > 0 ? '#d9381e' : 'var(--text-muted)', fontWeight: '500' }}>
                    Invalid / Ignored Rows
                  </div>
                </div>
                <div style={{ background: '#ffffff', border: '1px solid var(--line)', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '1.4rem', fontWeight: '700' }}>{validationResult.total_rows}</div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Total Submitted Rows</div>
                </div>
              </div>

              {/* Invalid Rows Warning */}
              {validationResult.invalid_items?.length > 0 && (
                <div className="c3-alert c3-alert-warning" style={{ marginBottom: '16px' }}>
                  <strong>{validationResult.invalid_items.length} Invalid Row(s) Detected:</strong> These rows will not be graded.
                  <ul style={{ margin: '8px 0 0', paddingLeft: '20px' }}>
                    {validationResult.invalid_items.map((inv, idx) => (
                      <li key={idx}>
                        Row {inv.row} ({inv.student_id || 'No ID'}): {inv.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Preview Table of Valid Items */}
              <div style={{ overflowX: 'auto', marginBottom: '20px' }}>
                <table className="c3-queue-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th style={{ width: '60px' }}>#</th>
                      <th style={{ width: '160px' }}>Student ID</th>
                      <th>Student Answer Preview</th>
                      <th style={{ width: '120px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {validationResult.valid_items.map((item, idx) => (
                      <tr key={idx}>
                        <td>{item.row}</td>
                        <td style={{ fontWeight: '600' }}>{item.student_id}</td>
                        <td style={{ fontSize: '0.88rem' }}>
                          {item.student_answer ? (
                            item.student_answer.length > 120
                              ? item.student_answer.substring(0, 120) + '...'
                              : item.student_answer
                          ) : (
                            <span style={{ color: '#d9901a', fontStyle: 'italic' }}>[Empty / Unanswered]</span>
                          )}
                        </td>
                        <td>
                          <span className="c3-status-badge c3-status-pending" style={{ fontSize: '0.8rem' }}>
                            Ready to Mark
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {markingError && (
                <div className="c3-alert c3-alert-danger" style={{ marginBottom: '16px' }}>
                  <strong>Batch Marking Error:</strong> {markingError}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <button type="button" className="btn secondary" onClick={() => setCurrentStep(2)}>
                  ← Back to Input
                </button>
                <button
                  type="button"
                  className="btn primary"
                  disabled={processing || validationResult.valid_count === 0}
                  onClick={handleRunBatchMarking}
                  style={{ padding: '10px 24px', fontWeight: '600' }}
                >
                  {processing ? `Evaluating Cohort (${validationResult.valid_count} Students)...` : `🚀 Run Automated Marking (${validationResult.valid_count} Students) →`}
                </button>
              </div>
            </div>
          )}

          {/* =========================================================================
              STEP 4: BATCH RESULTS & LECTURER REVIEW
             ========================================================================= */}
          {currentStep === 4 && (
            <div className="panel" style={{ margin: '0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Batch Assessment Results: {activeSetupDoc?.batch_id}</h3>
                  <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.9rem' }}>
                    Shared Question: {activeSetupDoc?.question_id} • Max Marks: {activeSetupDoc?.max_marks}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <button
                    type="button"
                    className="btn secondary"
                    style={{ padding: '6px 14px' }}
                    onClick={() => refreshBatchResults(activeSetupDoc.batch_id)}
                  >
                    🔄 Refresh Results
                  </button>
                  <button
                    type="button"
                    className="btn primary"
                    style={{ padding: '6px 18px', fontWeight: '600', background: '#1d6f42' }}
                    disabled={finalizingAll || batchItems.length === 0}
                    onClick={handleFinalizeAll}
                  >
                    {finalizingAll ? 'Finalizing...' : '✅ Finalize Entire Batch'}
                  </button>
                </div>
              </div>

              {finalizeSuccessMsg && (
                <div className="c3-alert c3-alert-success" style={{ marginBottom: '16px' }}>
                  {finalizeSuccessMsg}
                </div>
              )}

              {/* Stats Grid */}
              {batchStats && (
                <div className="c3-queue-stats-grid" style={{ marginBottom: '16px' }}>
                  <div className="c3-queue-stat-card">
                    <span className="c3-queue-stat-num">{batchStats.total_count}</span>
                    <span className="c3-queue-stat-label">Total Graded</span>
                  </div>
                  <div className="c3-queue-stat-card" style={{ borderLeft: '4px solid #d9901a' }}>
                    <span className="c3-queue-stat-num" style={{ color: '#7a5200' }}>{batchStats.pending_count}</span>
                    <span className="c3-queue-stat-label">Pending Review</span>
                  </div>
                  <div className="c3-queue-stat-card" style={{ borderLeft: '4px solid #005a9c' }}>
                    <span className="c3-queue-stat-num" style={{ color: '#005a9c' }}>{batchStats.reviewed_count}</span>
                    <span className="c3-queue-stat-label">Reviewed / Overridden</span>
                  </div>
                  <div className="c3-queue-stat-card" style={{ borderLeft: '4px solid #1d6f42' }}>
                    <span className="c3-queue-stat-num" style={{ color: '#1d6f42' }}>{batchStats.finalized_count}</span>
                    <span className="c3-queue-stat-label">Finalized</span>
                  </div>
                  <div className="c3-queue-stat-card">
                    <span className="c3-queue-stat-num">{batchStats.average_mark} / {batchStats.max_marks}</span>
                    <span className="c3-queue-stat-label">Average Cohort Mark</span>
                  </div>
                </div>
              )}

              {/* Search & Filter Toolbar */}
              <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder="🔍 Search student ID or answer snippet..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{ flex: 1, minWidth: '220px', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}
                />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--line)' }}
                >
                  <option value="all">All Statuses</option>
                  <option value="pending_review">Pending Review</option>
                  <option value="reviewed">Reviewed</option>
                  <option value="finalized">Finalized</option>
                </select>
              </div>

              {/* Results Table */}
              <div style={{ overflowX: 'auto' }}>
                <table className="c3-queue-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th style={{ width: '140px' }}>Student ID</th>
                      <th>Student Response</th>
                      <th style={{ width: '120px' }}>AI Mark</th>
                      <th style={{ width: '120px' }}>Final Mark</th>
                      <th style={{ width: '120px' }}>Status</th>
                      <th style={{ width: '140px' }}>Lecturer Review</th>
                      <th style={{ width: '120px' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item, idx) => {
                      const isOverridden = item.lecturer_decision === 'overridden';
                      return (
                        <tr key={idx}>
                          <td style={{ fontWeight: '600' }}>{item.student_id}</td>
                          <td style={{ fontSize: '0.85rem' }}>
                            {item.student_answer ? (
                              item.student_answer.length > 90
                                ? item.student_answer.substring(0, 90) + '...'
                                : item.student_answer
                            ) : (
                              <span style={{ color: '#d9901a', fontStyle: 'italic' }}>[No Answer]</span>
                            )}
                          </td>
                          <td>
                            <span style={{ fontWeight: '600' }}>
                              {item.automated_mark !== null ? item.automated_mark : '—'} / {activeSetupDoc?.max_marks}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontWeight: '700', color: isOverridden ? '#005a9c' : 'inherit' }}>
                              {item.final_mark !== null ? `${item.final_mark} / ${activeSetupDoc?.max_marks}` : '—'}
                            </span>
                          </td>
                          <td>
                            <span className={`c3-status-badge c3-status-${item.status || 'pending'}`}>
                              {item.status === 'finalized' ? 'Finalized' : item.status === 'reviewed' ? 'Reviewed' : 'Pending'}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.82rem' }}>
                            {isOverridden ? (
                              <span style={{ color: '#005a9c', fontWeight: '500' }}>Overridden (Reason logged)</span>
                            ) : item.lecturer_decision === 'accepted' ? (
                              <span style={{ color: '#1d6f42', fontWeight: '500' }}>AI Mark Accepted</span>
                            ) : (
                              <span className="muted">Not reviewed</span>
                            )}
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn secondary"
                              style={{ padding: '4px 10px', fontSize: '0.82rem' }}
                              onClick={() => handleOpenInspection(item.submission_id)}
                            >
                              🔍 Review
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'space-between' }}>
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => setCurrentStep(2)}
                >
                  ➕ Add More Students to this Batch
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => {
                    setActiveSetupDoc(null);
                    setCurrentStep(1);
                  }}
                >
                  ✨ Start Another Assessment Batch
                </button>
              </div>
            </div>
          )}
        </>
      ) : (
        /* =========================================================================
            HISTORY TAB: VIEW PAST BATCHES
           ========================================================================= */
        <div className="panel" style={{ margin: '0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0 }}>Past Assessment Batch Setups</h3>
              <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.9rem' }}>
                All configured cohorts and questions created for automated marking
              </p>
            </div>
            <button
              type="button"
              className="btn secondary"
              style={{ padding: '6px 14px' }}
              onClick={loadPastSetups}
              disabled={loadingSetups}
            >
              🔄 Refresh List
            </button>
          </div>

          {loadingSetups ? (
            <div style={{ padding: '24px', textAlign: 'center' }}>Loading batch records...</div>
          ) : existingSetups.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No batch marking setups found. Click 'New Batch Marking' to create your first cohort assessment.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table className="c3-queue-table" style={{ width: '100%' }}>
                <thead>
                  <tr>
                    <th>Batch ID</th>
                    <th>Assessment Title</th>
                    <th>Module & Question</th>
                    <th>Type</th>
                    <th>Max Marks</th>
                    <th>Total Students</th>
                    <th>Status Breakdown</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {existingSetups.map((s, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: '700' }}>{s.batch_id}</td>
                      <td>{s.title}</td>
                      <td>{s.module_id} • {s.question_id}</td>
                      <td>
                        <span className="c3-badge-research" style={{ textTransform: 'uppercase' }}>
                          {s.answer_type}
                        </span>
                      </td>
                      <td>{s.max_marks}</td>
                      <td style={{ fontWeight: '600' }}>{s.stats?.total || 0}</td>
                      <td style={{ fontSize: '0.82rem' }}>
                        <span style={{ color: '#d9901a', marginRight: '6px' }}>Pending: {s.stats?.pending || 0}</span>
                        <span style={{ color: '#005a9c', marginRight: '6px' }}>Reviewed: {s.stats?.reviewed || 0}</span>
                        <span style={{ color: '#1d6f42' }}>Final: {s.stats?.finalized || 0}</span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn primary"
                          style={{ padding: '4px 12px', fontSize: '0.82rem' }}
                          onClick={async () => {
                            setActiveSetupDoc(s);
                            await refreshBatchResults(s.batch_id);
                            setActiveMainTab('create_and_mark');
                            setCurrentStep(4);
                          }}
                        >
                          Open Batch →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          INDIVIDUAL SUBMISSION INSPECTION & REVIEW MODAL
         ========================================================================= */}
      {inspectingSubId && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <div
            style={{
              background: '#ffffff',
              borderRadius: '12px',
              maxWidth: '850px',
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '24px',
              boxShadow: '0 8px 30px rgba(0,0,0,0.2)',
            }}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid var(--line)', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ margin: 0 }}>Review Student Submission: {inspectingDetail?.submission?.student_id}</h3>
                <span className="muted" style={{ fontSize: '0.85rem' }}>
                  Question: {inspectingDetail?.submission?.question_id} • Status: {inspectingDetail?.result?.status}
                </span>
              </div>
              <button
                type="button"
                className="btn-ghost"
                style={{ fontSize: '1.2rem', padding: '4px 8px' }}
                onClick={() => setInspectingSubId(null)}
              >
                ✕
              </button>
            </div>

            {loadingDetail ? (
              <div style={{ padding: '30px', textAlign: 'center' }}>Loading evaluation details...</div>
            ) : inspectingDetail ? (
              <div>
                {reviewActionMsg && (
                  <div className="c3-alert c3-alert-success" style={{ marginBottom: '16px' }}>
                    {reviewActionMsg}
                  </div>
                )}

                {/* Question & Student Answer */}
                <div style={{ background: 'var(--paper)', borderRadius: '8px', padding: '14px', marginBottom: '16px', border: '1px solid var(--line)' }}>
                  <div style={{ fontWeight: '600', marginBottom: '4px', fontSize: '0.88rem' }}>Question Prompt:</div>
                  <div style={{ fontSize: '0.92rem', marginBottom: '10px' }}>{inspectingDetail.submission.question_text}</div>
                  <div style={{ fontWeight: '600', marginBottom: '4px', fontSize: '0.88rem' }}>Student's Typed Answer:</div>
                  <div style={{ background: '#ffffff', padding: '10px', borderRadius: '6px', border: '1px solid var(--line)', fontSize: '0.9rem' }}>
                    {inspectingDetail.submission.student_answer || '<Empty Response>'}
                  </div>
                </div>

                {/* Score Summary */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginBottom: '16px' }}>
                  <div style={{ background: '#ffffff', border: '1px solid var(--line)', borderRadius: '8px', padding: '10px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>AI Automated Mark</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: '700' }}>
                      {inspectingDetail.result.automated_mark ?? '—'} / {inspectingDetail.result.total_possible_marks}
                    </div>
                  </div>
                  <div style={{ background: '#ffffff', border: '1px solid var(--line)', borderRadius: '8px', padding: '10px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Current Final Mark</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: '700', color: inspectingDetail.result.final_mark !== null ? '#005a9c' : 'inherit' }}>
                      {inspectingDetail.result.final_mark !== null ? inspectingDetail.result.final_mark : inspectingDetail.result.automated_mark} / {inspectingDetail.result.total_possible_marks}
                    </div>
                  </div>
                  <div style={{ background: '#ffffff', border: '1px solid var(--line)', borderRadius: '8px', padding: '10px' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Lecturer Decision</div>
                    <div style={{ fontSize: '1.0rem', fontWeight: '600' }}>
                      {inspectingDetail.result.lecturer_decision || 'Pending Review'}
                    </div>
                  </div>
                </div>

                {/* Subjective Criteria Breakdown */}
                {inspectingDetail.result?.ai_evaluation?.marking?.criteria_results && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ margin: '0 0 8px' }}>Criterion Mark Allocation & Evidence</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {inspectingDetail.result.ai_evaluation.marking.criteria_results.map((c, i) => (
                        <div key={i} style={{ border: '1px solid var(--line)', borderRadius: '8px', padding: '10px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <strong style={{ fontSize: '0.88rem' }}>{c.criterion_id}: {c.criterion_description}</strong>
                            <span style={{ fontWeight: '700' }}>{c.awarded_mark} / {c.max_marks} (Level: {c.selected_level_label})</span>
                          </div>
                          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>{c.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Lecturer Review & Override Controls */}
                <div style={{ border: '1px solid #005a9c', borderRadius: '8px', padding: '16px', background: '#f5f9fc', marginBottom: '16px' }}>
                  <h4 style={{ margin: '0 0 10px', color: '#005a9c' }}>Lecturer Review & Score Adjustment</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '12px', marginBottom: '12px' }}>
                    <div>
                      <label style={{ fontSize: '0.82rem', fontWeight: '600' }}>Adjusted Mark</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max={inspectingDetail.result.total_possible_marks}
                        value={overrideMarkInput}
                        onChange={(e) => setOverrideMarkInput(e.target.value)}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid var(--line)' }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: '0.82rem', fontWeight: '600' }}>Override Justification (Mandatory for overrides)</label>
                      <input
                        value={overrideReasonInput}
                        onChange={(e) => setOverrideReasonInput(e.target.value)}
                        placeholder="e.g. Student provided valid alternative implementation..."
                        style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid var(--line)' }}
                      />
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      type="button"
                      className="btn secondary"
                      style={{ padding: '6px 14px' }}
                      disabled={reviewActionLoading}
                      onClick={() => handleReviewAction('accepted')}
                    >
                      ✓ Accept AI Mark
                    </button>
                    <button
                      type="button"
                      className="btn secondary"
                      style={{ padding: '6px 14px', color: '#005a9c', borderColor: '#005a9c' }}
                      disabled={reviewActionLoading || !overrideReasonInput.trim()}
                      onClick={() => handleReviewAction('overridden')}
                    >
                      ✎ Save Override
                    </button>
                    <button
                      type="button"
                      className="btn primary"
                      style={{ padding: '6px 16px', marginLeft: 'auto', background: '#1d6f42' }}
                      disabled={reviewActionLoading || inspectingDetail.result.status === 'finalized'}
                      onClick={handleFinalizeIndividual}
                    >
                      {inspectingDetail.result.status === 'finalized' ? 'Already Finalized' : '✅ Finalize Student Result'}
                    </button>
                  </div>
                </div>
              </div>
            ) : null}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
              <button
                type="button"
                className="btn secondary"
                onClick={() => setInspectingSubId(null)}
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
