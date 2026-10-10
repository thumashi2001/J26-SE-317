import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getTwin, getAlerts, getPracticeTopics, getInsights, getBehaviour } from '../../services/c1Api.js';
import { prettyTopic, scoreBand } from '../../utils/topics.js';
import WelcomePopup from '../../components/WelcomePopup.jsx';
import AnswerStyle from '../../components/AnswerStyle.jsx';
import './practice.css';

const READ_ICON = { strong: '\u2713', slow_right: '\u23F1', guessing: '\u26A0', revise: '\u21BB', building: '\u2026' };

const seenWelcome = () => {
  try {
    return sessionStorage.getItem('c1_welcome_seen') === '1';
  } catch {
    return true; // storage blocked: do not nag
  }
};
const markWelcome = () => {
  try {
    sessionStorage.setItem('c1_welcome_seen', '1');
  } catch {
    /* ignore */
  }
};

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
  const [insights, setInsights] = useState(null);
  const [behaviour, setBehaviour] = useState(null);
  const [error, setError] = useState('');
  const [welcome, setWelcome] = useState(false);

  const load = useCallback(async () => {
    try {
      const [t, a, pt, ins, beh] = await Promise.all([
        getTwin(user.student_id),
        getAlerts(user.student_id),
        getPracticeTopics().catch(() => ({ topics: [] })), // no practice list is not a reason to hide the page
        getInsights(user.student_id).catch(() => null), // the page still works without the extra insights
        getBehaviour(user.student_id).catch(() => null),
      ]);
      setTwin(t);
      setAlerts(a.alerts);
      setPracticable(pt.topics);
      setInsights(ins);
      setBehaviour(beh);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [user.student_id]);

  useEffect(() => {
    load();
  }, [load]);

  // Show the welcome popup once per login, after the first successful load.
  const ready = !!twin && twin.diagnosticCompleted;
  useEffect(() => {
    if (ready && !seenWelcome()) {
      setWelcome(true);
      markWelcome();
    }
  }, [ready]);
  const closeWelcome = useCallback(() => setWelcome(false), []);

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
  // Use the estimated score now (forgetting applied) when the AI service gave one, else the stored score.
  const info = (t) => (insights && insights.topics ? insights.topics[t] : null);
  const shown = (t, m) => {
    const i = info(t);
    return i && i.estimatedNow !== null && i.estimatedNow !== undefined ? i.estimatedNow : m.score;
  };
  const average = Math.round(topics.reduce((sum, [t, m]) => sum + shown(t, m), 0) / (topics.length || 1));
  const weak = topics.filter(([t, m]) => shown(t, m) < 30).length;
  const eng = insights ? insights.engagement : null;
  const risk = twin.riskLevel;
  const canPractise = (t) => practicable.includes(t);
  // lowest score among the topics that have practice questions
  const weakest = topics.filter(([t]) => canPractise(t)).sort((x, y) => shown(x[0], x[1]) - shown(y[0], y[1]))[0];

  const firstName = (user.name || '').split(' ')[0];
  const reads = behaviour && behaviour.topics ? behaviour.topics : {};
  const focus = weakest ? { topic: weakest[0], name: prettyTopic(weakest[0]), score: Math.round(shown(weakest[0], weakest[1])) } : null;
  const attention = alerts.length;
  const sessionsTotal = topics.reduce((sum, [, m]) => sum + (m.practice_sessions || 0), 0);

  return (
    <div className="dash">
      {welcome && (
        <WelcomePopup
          name={firstName}
          focus={focus}
          alertCount={attention}
          headline={behaviour ? behaviour.headline : 'Take a quiz to see how you answer.'}
          onClose={closeWelcome}
        />
      )}

      <div className="dash-top">
        <section className="dhero">
          <div className="dhero-text">
            <p className="dhero-kicker">My learning state</p>
            <h1>Hello{firstName ? `, ${firstName}` : ''}</h1>
            <p className="dhero-sub">
              {weak === 0 ? 'No topic is below 30%. Keep the rhythm going.' : `${weak} ${weak === 1 ? 'topic is' : 'topics are'} below 30%. Start with the weakest one.`}
            </p>
            <div className="dhero-chips">
              <span className={`badge risk-${(risk || 'none').toLowerCase()}`}>
                {risk ? `${risk} risk of falling behind` : 'Risk not assessed yet'}
              </span>
              <span className="chip-soft">{sessionsTotal} practice {sessionsTotal === 1 ? 'session' : 'sessions'}</span>
            </div>
            {focus && (
              <div className="next-up">
                <Link className="btn" to={`/c1/practice/${focus.topic}`}>
                  Practise your weakest topic
                </Link>
                <span className="muted small">{focus.name} is at about {focus.score}%</span>
              </div>
            )}
          </div>
          <div className="dhero-ring">
            <Ring value={average} />
            <span className="muted small">Overall mastery across {topics.length} topics</span>
          </div>
        </section>

        <aside className="dash-side">
          {eng && (
            <section className="panel side-card">
              <div className="engage-head">
                <strong>Engagement</strong>
                <span className={`tag eng-${eng.label.toLowerCase().replace(' ', '-')}`}>{eng.label}</span>
              </div>
              <div className="meter" role="img" aria-label={`Engagement index ${eng.index} out of 100`}>
                <span style={{ width: `${Math.max(2, eng.index)}%` }} />
              </div>
              <p className="muted small">{eng.why}</p>
            </section>
          )}
          <section className="panel side-card">
            <strong>Alerts</strong>
            {alerts.length === 0 ? (
              <p className="muted small">Nothing needs your attention right now.</p>
            ) : (
              <ul className="alerts alerts-scroll">
                {alerts.map((a, i) => (
                  <li key={i} className={`alert ${a.severity === 'High' ? 'high' : 'medium'}`}>
                    <span aria-hidden="true">{a.type === 'guessing' ? '\u26A0' : a.type === 'sudden_drop' ? '\u2198' : '\u2757'}</span>
                    <span>{a.topic ? a.message.replace(a.topic, prettyTopic(a.topic)) : a.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>

      {behaviour && <AnswerStyle data={behaviour} />}

      <h2>Topics</h2>
      <p className="muted small">Scores show your estimated level now, including forgetting since you last practised. Select a topic to see why, or press Practise.</p>
      <p className="muted small">Score reliability shows how far you can trust a score, based on how many recent, honest answers we have. It does not show how well you know the topic.</p>
      <div className="heat">
        {topics.map(([topic, m]) => {
          const score = shown(topic, m);
          const i = info(topic);
          const r = reads[topic];
          const faded = i && i.estimatedNow !== null && m.score - score >= 1;
          return (
            <div key={topic} className="topic-cell">
              <Link to={`/c1/topic/${topic}`} className={`topic link ${scoreBand(score)}`}>
                <div className="topic-name">{prettyTopic(topic)}</div>
                <div className="topic-score">{Math.round(score)}%</div>
                <div className="bar">
                  <span style={{ width: `${Math.max(3, score)}%` }} />
                </div>
                <div className="muted small">
                  {m.practice_sessions ?? 0} {m.practice_sessions === 1 ? 'practice session' : 'practice sessions'}
                </div>
                {faded && <div className="muted small">Was {Math.round(m.score)}% when last practised</div>}
                {r && (
                  <div className={`topic-read read-${r.key}`} title={r.tip}>
                    <span aria-hidden="true">{READ_ICON[r.key]}</span> {r.label}
                  </div>
                )}
                {i && (
                  <div className="topic-foot">
                    <span className={`tag conf-${i.confidenceLabel.toLowerCase()}`} title={i.confidenceWhy}>
                      Score reliability: {i.confidenceLabel}
                    </span>
                  </div>
                )}
              </Link>
              {canPractise(topic) ? (
                <Link className="btn secondary practise-btn" to={`/c1/practice/${topic}`} aria-label={`Practise ${prettyTopic(topic)}`}>
                  Practise
                </Link>
              ) : (
                <span className="practise-btn practise-off">No practice questions yet</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
