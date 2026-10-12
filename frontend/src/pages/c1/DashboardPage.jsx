import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getTwin, getAlerts, getPracticeTopics, getInsights, getBehaviour, getPlan, saveExamDate } from '../../services/c1Api.js';
import { prettyTopic, scoreBand, topicModule } from '../../utils/topics.js';
import { TOPIC_INFO } from '../../utils/topicLabels.js';
import WelcomePopup from '../../components/WelcomePopup.jsx';
import AnswerStyle from '../../components/AnswerStyle.jsx';
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

const LEVEL = {
  weak: { text: 'Just starting' },
  fair: { text: 'Getting there' },
  strong: { text: 'Strong' },
};
const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'weak', label: 'Just starting' },
  { key: 'fair', label: 'Getting there' },
  { key: 'strong', label: 'Strong' },
];
const RING = 2 * Math.PI * 26;

// One topic as a card. Only what you need to choose: the ring, the level and a Practise button.
// Colour follows the level (indigo, blue, teal). Sessions and reliability live on the topic page.
function TopicCard({ topic, score, band, read, faded, practicable, index }) {
  const careful = read && (read.key === 'guessing' || read.key === 'revise');
  return (
    <article className={`tp-card ${band}`} style={{ animationDelay: `${Math.min(index, 10) * 40}ms` }}>
      {careful && <span className="tp-care" title={read.label} aria-label={read.label} />}
      <Link to={`/c1/topic/${topic}`} className="tp-main" aria-label={`${prettyTopic(topic)}, ${Math.round(score)} percent. Open details.`}>
        <svg viewBox="0 0 64 64" className="tp-ring" aria-hidden="true">
          <circle cx="32" cy="32" r="26" className="trk" />
          <circle cx="32" cy="32" r="26" className="fil" strokeDasharray={RING} strokeDashoffset={RING * (1 - Math.min(100, Math.max(0, score)) / 100)} style={{ '--full': RING }} transform="rotate(-90 32 32)" />
          <text x="32" y="37" textAnchor="middle">{Math.round(score)}</text>
        </svg>
        <span className="tp-title">
          <span className="tp-name">{prettyTopic(topic)}</span>
          <span className="tp-level">{LEVEL[band].text}{faded ? ' \u00B7 fading' : ''}</span>
        </span>
      </Link>
      {practicable ? (
        <Link className="tp-go" to={`/c1/practice/${topic}`} aria-label={`Practise ${prettyTopic(topic)}`}>
          Practise <span aria-hidden="true">{'\u2192'}</span>
        </Link>
      ) : (
        <span className="tp-go off">No questions yet</span>
      )}
    </article>
  );
}

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
  const [savingDate, setSavingDate] = useState(false);
  const [error, setError] = useState('');
  const [welcome, setWelcome] = useState(false);
  const [filter, setFilter] = useState('all');
  const [weakestFirst, setWeakestFirst] = useState(false);

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
    async (value) => {
      setSavingDate(true);
      setPlanError('');
      try {
        await saveExamDate(user.student_id, value);
        setPlan(await getPlan(user.student_id));
      } catch (err) {
        setPlanError(err.message);
      } finally {
        setSavingDate(false);
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

  const rows = topics
    .map(([t, m]) => ({ topic: t, meta: m, score: shown(t, m), band: scoreBand(shown(t, m)) }))
    .filter((r) => filter === 'all' || r.band === filter);
  let groups;
  if (weakestFirst) {
    groups = rows.length ? [{ code: 'all', name: 'All topics', avg: 0, rows: [...rows].sort((x, y) => x.score - y.score) }] : [];
  } else {
    const by = {};
    rows.forEach((r) => {
      const inf = TOPIC_INFO[r.topic] || {};
      const code = inf.module || topicModule(r.topic) || 'Other';
      (by[code] ||= { code, name: inf.moduleName || '', rows: [] }).rows.push(r);
    });
    groups = Object.values(by).map((g) => ({ ...g, avg: Math.round(g.rows.reduce((n, r) => n + r.score, 0) / g.rows.length) }));
  }

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
            <span className="kpi-label">Exam</span>
            <strong className="kpi-value">{plan && plan.daysLeft !== null ? `${plan.daysLeft} ${plan.daysLeft === 1 ? 'day' : 'days'}` : 'Not set'}</strong>
            <span className="kpi-note">{plan && plan.examDate ? new Date(plan.examDate + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long' }) : 'add it in the calendar'}</span>
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
        <TodayPlan plan={plan} />
        <ExamCalendar plan={plan} onSave={onSaveDate} saving={savingDate} error={planError} />
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

      {behaviour && <AnswerStyle data={behaviour} />}

      <div className="tp-head">
        <div>
          <h2>Your topics</h2>
          <p className="muted small">Colour shows your level now, after forgetting. A dark dot means guessing or needs revision. Open a card for the full story.</p>
        </div>
        <div className="tp-controls">
          <div className="tp-seg" role="group" aria-label="Show topics">
            {FILTERS.map((f) => (
              <button key={f.key} type="button" aria-pressed={filter === f.key} className={filter === f.key ? 'on' : ''} onClick={() => setFilter(f.key)}>
                {f.label}
              </button>
            ))}
          </div>
          <button type="button" className={'tp-sort' + (weakestFirst ? ' on' : '')} aria-pressed={weakestFirst} onClick={() => setWeakestFirst(!weakestFirst)}>
            Weakest first
          </button>
        </div>
      </div>

      {groups.map((g) => (
        <section key={g.code} className="tp-mod" aria-label={g.name || g.code}>
          {!weakestFirst && (
            <header>
              <span className="tp-code">{g.code}</span>
              <h3>{g.name}</h3>
              <span className={`tp-avg ${scoreBand(g.avg)}`}>{g.avg}% average</span>
            </header>
          )}
          <div className="tp-grid">
            {g.rows.map((r, idx) => {
              const i = info(r.topic);
              return (
                <TopicCard
                  key={r.topic}
                  topic={r.topic}
                  score={r.score}
                  band={r.band}
                  read={reads[r.topic]}
                  faded={!!(i && i.estimatedNow !== null && r.meta.score - r.score >= 1)}
                  practicable={canPractise(r.topic)}
                  index={idx}
                />
              );
            })}
          </div>
        </section>
      ))}
      {groups.length === 0 && <p className="muted">No topics match this filter.</p>}
    </div>
  );
}
