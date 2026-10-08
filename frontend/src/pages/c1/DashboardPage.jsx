import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getTwin, getAlerts, getPracticeTopics } from '../../services/c1Api.js';
import { prettyTopic, scoreBand } from '../../utils/topics.js';
import './practice.css';

function Ring({ value }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 130 130" className="ring" role="img" aria-label={`Overall mastery ${value} percent`}>
      <circle cx="65" cy="65" r={r} className="ring-track" />
      <circle
        cx="65"
        cy="65"
        r={r}
        className="ring-fill"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - value / 100)}
        transform="rotate(-90 65 65)"
      />
      <text x="65" y="71" textAnchor="middle" className="ring-text">
        {value}%
      </text>
    </svg>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [twin, setTwin] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [practicable, setPracticable] = useState([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [t, a, pt] = await Promise.all([
        getTwin(user.student_id),
        getAlerts(user.student_id),
        getPracticeTopics().catch(() => ({ topics: [] })), // no practice list is not a reason to hide the page
      ]);
      setTwin(t);
      setAlerts(a.alerts);
      setPracticable(pt.topics);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [user.student_id]);

  useEffect(() => {
    load();
  }, [load]);

  if (error && !twin)
    return (
      <div className="panel">
        <h2>Your learning state did not load</h2>
        <p className="error">{error}</p>
      </div>
    );
  if (!twin) return <p className="muted">Loading...</p>;

  if (!twin.diagnosticCompleted)
    return (
      <div className="panel">
        <h2>Your twin does not exist yet</h2>
        <p className="muted">Take the diagnostic test first so we know your starting point.</p>
        <Link className="btn" to="/c1/diagnostic">
          Start the diagnostic test
        </Link>
      </div>
    );

  const topics = Object.entries(twin.mastery);
  const average = Math.round(topics.reduce((s, [, m]) => s + m.score, 0) / (topics.length || 1));
  const weak = topics.filter(([, m]) => m.score < 30).length;
  const risk = twin.riskLevel;
  const canPractise = (t) => practicable.includes(t);
  // lowest score among the topics that have practice questions
  const weakest = topics.filter(([t]) => canPractise(t)).sort((x, y) => x[1].score - y[1].score)[0];

  return (
    <div>
      <h1>My learning state</h1>

      <section className="summary panel">
        <Ring value={average} />
        <div className="summary-text">
          <div className="summary-line">
            Overall mastery <strong>{average}%</strong> across {topics.length} topics
          </div>
          <div className="summary-line">
            {weak === 0 ? 'No topic is below 30%.' : `${weak} ${weak === 1 ? 'topic is' : 'topics are'} below 30%.`}
          </div>
          <span className={`badge risk-${(risk || 'none').toLowerCase()}`}>
            {risk ? `${risk} risk of falling behind` : 'Risk not assessed yet'}
          </span>
          {weakest && (
            <div className="next-up">
              <Link className="btn" to={`/c1/practice/${weakest[0]}`}>
                Practise your weakest topic
              </Link>
              <span className="muted small">
                {prettyTopic(weakest[0])} is at {Math.round(weakest[1].score)}%
              </span>
            </div>
          )}
        </div>
      </section>

      <h2>Topics</h2>
      <p className="muted small">Select a topic to see how its score changed over time, or press Practise to answer questions on it.</p>
      <div className="heat">
        {topics.map(([topic, m]) => (
          <div key={topic} className="topic-cell">
            <Link to={`/c1/topic/${topic}`} className={`topic link ${scoreBand(m.score)}`}>
              <div className="topic-name">{prettyTopic(topic)}</div>
              <div className="topic-score">{Math.round(m.score)}%</div>
              <div className="bar">
                <span style={{ width: `${Math.max(3, m.score)}%` }} />
              </div>
              <div className="muted small">
                {m.practice_sessions ?? 0} {m.practice_sessions === 1 ? 'practice session' : 'practice sessions'}
              </div>
            </Link>
            {canPractise(topic) && (
              <Link className="btn secondary practise-btn" to={`/c1/practice/${topic}`} aria-label={`Practise ${prettyTopic(topic)}`}>
                Practise
              </Link>
            )}
          </div>
        ))}
      </div>

      <section>
        <h2>Alerts</h2>
        {alerts.length === 0 ? (
          <p className="muted">Nothing needs your attention right now.</p>
        ) : (
          <ul className="alerts">
            {alerts.map((a, i) => (
              <li key={i} className={`alert ${a.severity === 'High' ? 'high' : 'medium'}`}>
                <strong>{a.severity}</strong>
                <span>{a.topic ? a.message.replace(a.topic, prettyTopic(a.topic)) : a.message}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

    </div>
  );
}
