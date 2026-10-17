import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getTwin, getAlerts, getPracticeTopics, getInsights, getBehaviour, getPlan, saveExamDate } from '../../services/c1Api.js';
import { prettyTopic, scoreBand } from '../../utils/topics.js';
import WelcomePopup from '../../components/WelcomePopup.jsx';
import TodayPlan from '../../components/TodayPlan.jsx';
import ExamCalendar from '../../components/ExamCalendar.jsx';
import './practice.css';
import './dashboard.css';

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

const LEVEL_TEXT = { weak: 'Just starting', fair: 'Getting there', strong: 'Strong' };

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
  const [plan, setPlan] = useState(null);
  const [planError, setPlanError] = useState('');
  const [savingDate, setSavingDate] = useState(null);
  const [error, setError] = useState('');
  const [welcome, setWelcome] = useState(false);

  const load = useCallback(async () => {
    try {
      const [t, a, pt, ins, beh, pl] = await Promise.all([
        getTwin(user.student_id),
        getAlerts(user.student_id),
        getPracticeTopics().catch(() => ({ topics: [] })), // no practice list is not a reason to hide the page
        getInsights(user.student_id).catch(() => null), // the page still works without the extra insights
        getBehaviour(user.student_id).catch(() => null),
        getPlan(user.student_id).catch(() => null), // the dashboard still works without the plan
      ]);
      setTwin(t);
      setAlerts(a.alerts);
      setPracticable(pt.topics);
      setInsights(ins);
      setBehaviour(beh);
      setPlan(pl);
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

  const onSaveDate = useCallback(
    async (module, value) => {
      setSavingDate(module);
      setPlanError('');
      try {
        await saveExamDate(user.student_id, module, value);
        setPlan(await getPlan(user.student_id));
      } catch (err) {
        setPlanError(err.message);
      } finally {
        setSavingDate(null);
      }
    },
    [user.student_id]
  );

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

  // the three lowest topics, for the short list on this page (the full list is on Topic insights)
  const lowest = topics
    .map(([t, m]) => ({ topic: t, score: shown(t, m) }))
    .sort((x, y) => x.score - y.score)
    .slice(0, 3);

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

        <div className="kpis">
          <section className="kpi k-blue">
            <span className="kpi-label">Predicted exam level</span>
            <strong className="kpi-value">{plan ? `${plan.predicted.withPlan}%` : '...'}</strong>
            <span className="kpi-note">{plan ? `if you follow the plan, ${plan.predicted.ifYouStop}% if you stop` : 'working it out'}</span>
          </section>
          <section className="kpi k-teal">
            <span className="kpi-label">Next exam</span>
            <strong className="kpi-value">{plan && plan.nextExam ? `${plan.daysLeft} ${plan.daysLeft === 1 ? 'day' : 'days'}` : 'Not set'}</strong>
            <span className="kpi-note">{plan && plan.nextExam ? `${plan.nextExam.module}, ${new Date(plan.nextExam.date + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })}` : 'add each module exam date in the calendar'}</span>
          </section>
          <section className="kpi k-indigo">
            <span className="kpi-label">Engagement</span>
            <strong className="kpi-value">{eng ? eng.label : '...'}</strong>
            <span className="kpi-note">{eng ? `${eng.index} of 100` : ''}</span>
          </section>
          <section className="kpi k-sky">
            <span className="kpi-label">Alerts</span>
            <strong className="kpi-value">{alerts.length}</strong>
            <span className="kpi-note">{alerts.length === 0 ? 'nothing needs attention' : alerts[0].topic ? alerts[0].message.replace(alerts[0].topic, prettyTopic(alerts[0].topic)) : alerts[0].message}</span>
          </section>
        </div>
      </div>

      <div className="plan-row">
        <div className="plan-col">
          <TodayPlan plan={plan} />
          <section className="panel glance-card" aria-labelledby="gl-topics">
            <header>
              <h2 id="gl-topics">Topics to work on</h2>
              <Link className="glance-link" to="/c1/topics">See all {topics.length} topics <span aria-hidden="true">{'\u2192'}</span></Link>
            </header>
            <ul className="glance-list">
              {lowest.map((r) => {
                const band = scoreBand(r.score);
                return (
                  <li key={r.topic} className={band}>
                    <Link to={`/c1/topic/${r.topic}`} state={{ from: '/c1/dashboard' }}>
                      <span className="gl-name">{prettyTopic(r.topic)}</span>
                      <span className="gl-bar" aria-hidden="true"><i style={{ width: `${Math.max(4, Math.min(100, r.score))}%` }} /></span>
                      <b>{Math.round(r.score)}%</b>
                      <small>{LEVEL_TEXT[band]}</small>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="panel glance-card" aria-labelledby="gl-style">
            <header>
              <h2 id="gl-style">How you answer</h2>
              <Link className="glance-link" to="/c1/topics">See my answer style <span aria-hidden="true">{'\u2192'}</span></Link>
            </header>
            <p className="gl-head">{behaviour ? behaviour.headline : 'Take a quiz to see how you answer.'}</p>
            {behaviour && behaviour.pattern !== 'Not enough yet' && <p className="muted small">{behaviour.advice}</p>}
          </section>
        </div>
        <ExamCalendar plan={plan} onSave={onSaveDate} savingModule={savingDate} error={planError} />
      </div>

      {alerts.length > 0 && (
        <section className="panel alert-panel">
          <strong>Alerts</strong>
          <ul className="alerts">
            {alerts.map((a, i) => (
              <li key={i} className={`alert ${a.severity === 'High' ? 'high' : 'medium'}`}>
                <span aria-hidden="true">{a.type === 'guessing' ? '\u26A0' : a.type === 'sudden_drop' ? '\u2198' : '\u2757'}</span>
                <span>{a.topic ? a.message.replace(a.topic, prettyTopic(a.topic)) : a.message}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

    </div>
  );
}
