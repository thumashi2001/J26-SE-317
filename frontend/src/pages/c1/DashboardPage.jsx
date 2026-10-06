import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getTwin, getAlerts, recordEvent } from '../../services/c1Api.js';
import { prettyTopic, scoreBand } from '../../utils/topics.js';

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
  const [error, setError] = useState('');
  const [practice, setPractice] = useState({ topic: '', correct: 'true', hint: false });
  const [last, setLast] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [t, a] = await Promise.all([getTwin(user.student_id), getAlerts(user.student_id)]);
      setTwin(t);
      setAlerts(a.alerts);
      setError('');
      const topics = Object.keys(t.mastery || {});
      setPractice((p) => (p.topic || !topics.length ? p : { ...p, topic: topics[0] }));
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

  const submitPractice = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await recordEvent({
        studentId: user.student_id,
        topic: practice.topic,
        correct: practice.correct === 'true',
        hintUsed: practice.hint,
        timeSec: 40,
      });
      setLast(res);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

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
        </div>
      </section>

      <h2>Topics</h2>
      <div className="heat">
        {topics.map(([topic, m]) => (
          <div key={topic} className={`topic ${scoreBand(m.score)}`}>
            <div className="topic-name">{prettyTopic(topic)}</div>
            <div className="topic-score">{Math.round(m.score)}%</div>
            <div className="bar">
              <span style={{ width: `${Math.max(3, m.score)}%` }} />
            </div>
            <div className="muted small">
              {m.practice_sessions ?? 0} {m.practice_sessions === 1 ? 'practice session' : 'practice sessions'}
            </div>
          </div>
        ))}
      </div>

      <div className="two-col">
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

        <section>
          <h2>Log a practice answer</h2>
          <form className="panel form-block compact" onSubmit={submitPractice}>
            <label htmlFor="topic">Topic</label>
            <select id="topic" value={practice.topic} onChange={(e) => setPractice({ ...practice, topic: e.target.value })}>
              {topics.map(([t]) => (
                <option key={t} value={t}>
                  {prettyTopic(t)}
                </option>
              ))}
            </select>
            <label htmlFor="result">Result</label>
            <select id="result" value={practice.correct} onChange={(e) => setPractice({ ...practice, correct: e.target.value })}>
              <option value="true">Correct</option>
              <option value="false">Wrong</option>
            </select>
            <label className="check">
              <input type="checkbox" checked={practice.hint} onChange={(e) => setPractice({ ...practice, hint: e.target.checked })} />
              I used a hint
            </label>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="btn" disabled={busy} type="submit">
              {busy ? 'Saving...' : 'Save answer'}
            </button>
          </form>
          {last && (
            <p className="muted small">
              {prettyTopic(last.topic)} was {last.scoreBefore}%, fell to {last.afterForgetting}% after forgetting, and is now {last.scoreAfter}%.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
