import { useState } from 'react';
import { classifyC2TopicExperimental } from '../../../services/c2Api.js';
import './experimentalTopicClassifier.css';

const SAMPLE_QUESTIONS = {
  database_systems:
    'Scenario: A high-throughput telemetry database inserts thousands of sensor readings per second while operators run real-time anomaly queries.\nTask: Evaluate the disk I/O and page-split trade-offs between clustered versus non-clustered B-tree indexing.',
  software_architecture:
    'Scenario: An enterprise retail platform is migrating from a monolithic order system to decoupled microservices.\nTask: Contrast event-driven publish-subscribe messaging with synchronous REST RPC in terms of latency, coupling, and fault tolerance.',
  application_frameworks:
    'Scenario: A web dashboard requires bidirectional real-time state synchronization with mobile clients.\nTask: Analyze WebSocket event-driven communication versus long-polling middleware.',
  distributed_systems:
    'Scenario: A geo-distributed key-value store replicates data across three continents subject to transient network partitions.\nTask: Evaluate consistency and partition tolerance trade-offs under quorum consensus protocols.',
  case_studies_software_engineering:
    'Scenario: A legacy electronic health record system suffers severe transaction bottlenecks during peak clinic hours.\nTask: Formulate an architectural refactoring strategy and evaluate quality attribute trade-offs.',
  software_engineering_process_quality_management:
    'Scenario: A fintech engineering team adopts continuous delivery with automated compliance checks.\nTask: Design a quality gate pipeline and evaluate static code analysis metrics against ISO 25010 standards.',
  software_project_management:
    'Scenario: A software consultancy encounters scope volatility and delayed milestone deliverables for a fixed-price contract.\nTask: Apply Earned Value Management (EVM) and analyze Schedule Performance Index (SPI) trade-offs.',
  user_experience_engineering:
    'Scenario: A patient-facing medical records portal is being redesigned for elderly patients with low vision.\nTask: Evaluate WCAG 2.1 AA accessibility compliance and recommend touch target and typography heuristics.',
};

function formatModule(key) {
  if (!key) return '';
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default function ExperimentalTopicClassifierSection({
  modules = [],
  activeModuleKey = '',
  onSelectModule,
}) {
  const [moduleKey, setModuleKey] = useState(activeModuleKey || (modules[0] || 'database_systems'));
  const [questionText, setQuestionText] = useState('');
  const [threshold, setThreshold] = useState('0.38');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  // Sync internal module if prop changes and not dirty
  const currentModule = moduleKey || activeModuleKey || modules[0] || 'database_systems';

  function handleModuleChange(newKey) {
    setModuleKey(newKey);
    if (onSelectModule) {
      onSelectModule(newKey);
    }
    setError('');
  }

  function handleLoadSample() {
    const sample = SAMPLE_QUESTIONS[currentModule];
    if (sample) {
      setQuestionText(sample);
      setError('');
    }
  }

  function handleClear() {
    setQuestionText('');
    setResult(null);
    setError('');
  }

  async function handlePredict(e) {
    if (e) e.preventDefault();

    const trimmed = questionText.trim();
    if (!trimmed) {
      setError('Please enter or paste an examination question.');
      return;
    }

    if (trimmed.length > 10000) {
      setError('Question text must be 10,000 characters or fewer.');
      return;
    }

    const numericThresh = Number(threshold);
    if (Number.isNaN(numericThresh) || numericThresh < 0 || numericThresh > 10) {
      setError('Abstention threshold must be a number between 0 and 10.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await classifyC2TopicExperimental({
        moduleKey: currentModule,
        questionText: trimmed,
        abstentionThreshold: numericThresh,
      });
      setResult(response);
    } catch (err) {
      const msg = err.message || 'Topic classification request failed';
      if (err.status === 503 || msg.includes('not available')) {
        setError(
          `Model Unavailable: Topic classification model artifact for '${formatModule(currentModule)}' ` +
          'is not present on the server. Models must be trained locally using: python -m scripts.m17_train --seed 42'
        );
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel c2-experimental-section" aria-label="Experimental AI Topic Classifier">
      <div className="c2-exp-header">
        <div>
          <div className="c2-exp-badge-row">
            <span className="pill status-pending">M17 AI Research Prototype</span>
            <span className="pill status-neutral">Unverified Development Fixture</span>
          </div>
          <h3>AI Topic Classifier (Experimental Demonstration)</h3>
          <p className="muted small">
            Test the trained supervised topic classification baseline on synthetic exam questions.
            Evaluates prediction confidence, calibrates probabilities, and enforces conservative abstention.
          </p>
        </div>
      </div>

      <div className="c2-exp-disclaimer-box">
        <strong>Academic Research Safeguard Notice:</strong> This interactive classifier utilizes
        scikit-learn models trained on M16 synthetic development questions. Predictions reflect provisional,
        unverified topic classes. Authentic past paper questions remain strictly isolated and must be verified
        by an academic lecturer in the Official Review Queue.
      </div>

      <form onSubmit={handlePredict} className="c2-exp-form">
        <div className="c2-exp-form-row">
          <label className="c2-exp-field">
            <span>Target Module</span>
            <select
              value={currentModule}
              disabled={loading}
              onChange={(e) => handleModuleChange(e.target.value)}
            >
              {modules.map((key) => (
                <option key={key} value={key}>
                  {formatModule(key)}
                </option>
              ))}
            </select>
          </label>

          <div className="c2-exp-actions-inline">
            <button
              type="button"
              className="btn secondary small-btn"
              disabled={loading}
              onClick={handleLoadSample}
              title="Fill question area with an M16 synthetic scenario benchmark"
            >
              Load Sample Question
            </button>
            <button
              type="button"
              className="btn secondary small-btn"
              disabled={loading || !questionText}
              onClick={handleClear}
            >
              Clear
            </button>
          </div>
        </div>

        <label className="c2-exp-field">
          <div className="c2-exp-label-with-count">
            <span>Examination Question (Scenario + Task)</span>
            <span className="muted xsmall">{questionText.length} / 10,000 chars</span>
          </div>
          <textarea
            rows={5}
            placeholder="Paste or enter examination question text here (e.g. Scenario context and Task prompt)..."
            value={questionText}
            disabled={loading}
            onChange={(e) => setQuestionText(e.target.value)}
          />
        </label>

        <div className="c2-exp-threshold-toggle">
          <button
            type="button"
            className="link-btn small"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? 'Hide Advanced Settings ▲' : 'Advanced Confidence Settings ▼'}
          </button>
        </div>

        {showAdvanced && (
          <div className="c2-exp-advanced-box">
            <label className="c2-exp-field small-field">
              <span>Abstention Threshold (Current: {threshold})</span>
              <input
                type="number"
                step="0.01"
                min="0.0"
                max="1.0"
                value={threshold}
                disabled={loading}
                onChange={(e) => setThreshold(e.target.value)}
              />
            </label>
            <p className="muted xsmall" style={{ margin: '4px 0 0' }}>
              For 5-class topic classification, a uniform random baseline is 0.20.
              The empirically calibrated default of <strong>0.38</strong> achieves 93.8% coverage with
              zero validation errors. Predictions with confidence below this threshold are marked &apos;Needs Review&apos;.
            </p>
          </div>
        )}

        {error && (
          <div className="alert-box error" role="alert">
            {error}
          </div>
        )}

        <div className="c2-exp-submit-row">
          <button
            type="submit"
            className="btn primary"
            disabled={loading || !questionText.trim()}
          >
            {loading ? 'Classifying via M17 Model...' : 'Predict Topic'}
          </button>
        </div>
      </form>

      {/* Prediction Output Display */}
      {result && (
        <div className="c2-exp-result-card" aria-live="polite">
          <div className="c2-exp-result-head">
            <div>
              <span className="muted xsmall uppercase tracking">Model Prediction Result</span>
              <h4>{result.predicted_topic === 'unclassified' ? 'Unclassified (Abstained)' : result.predicted_topic}</h4>
            </div>
            <div>
              {result.decision === 'classified' ? (
                <span className="pill status-approved">Classified (Provisional)</span>
              ) : (
                <span className="pill status-rejected">Needs Review (Abstained)</span>
              )}
            </div>
          </div>

          <div className="c2-exp-result-grid">
            <div className="c2-exp-result-metric">
              <span className="stat-label">Decision Status</span>
              <strong>{result.decision === 'classified' ? 'Accepted' : 'Abstained by Policy'}</strong>
            </div>

            <div className="c2-exp-result-metric">
              <span className="stat-label">Confidence Score</span>
              <strong>
                {(result.confidence_score * 100).toFixed(1)}% ({result.confidence_score})
              </strong>
              <span className="muted xsmall">Type: {result.score_type}</span>
            </div>

            <div className="c2-exp-result-metric">
              <span className="stat-label">Operating Threshold</span>
              <strong>{(result.abstention_threshold * 100).toFixed(1)}% ({result.abstention_threshold})</strong>
              <span className="muted xsmall">Threshold Met: {result.abstained ? 'No (Below threshold)' : 'Yes'}</span>
            </div>

            <div className="c2-exp-result-metric">
              <span className="stat-label">Candidate Topic</span>
              <strong>{result.candidate_topic || result.predicted_topic}</strong>
              <span className="muted xsmall">ID: {result.provisional_topic_id || 'unassigned'}</span>
            </div>
          </div>

          {result.abstained ? (
            <div className="c2-exp-abstained-explainer">
              <strong>Why did the model abstain?</strong> The model&apos;s maximum class probability (
              {(result.confidence_score * 100).toFixed(1)}%) did not exceed the conservative confidence threshold (
              {(result.abstention_threshold * 100).toFixed(1)}%). To protect academic integrity, the prediction is
              flagged as <em>Needs Review</em> rather than risking a false classification. Top candidate was{' '}
              <strong>{result.candidate_topic}</strong>.
            </div>
          ) : (
            <div className="c2-exp-success-explainer">
              <strong>Provisional Prediction Accepted:</strong> The model identified <em>{result.predicted_topic}</em> with{' '}
              {(result.confidence_score * 100).toFixed(1)}% calibrated confidence, exceeding the {result.abstention_threshold} threshold.
            </div>
          )}

          <div className="c2-exp-footer-meta">
            <span className="muted xsmall">
              Model: {result.model_type} | Provenance: {result.source_type} | Verification: {result.verification_status} ({result.academic_verification})
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
