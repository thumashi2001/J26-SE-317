import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getTwin, getPracticeTopics, getInsights, getBehaviour } from '../../services/c1Api.js';
import { prettyTopic, scoreBand, topicModule } from '../../utils/topics.js';
import { TOPIC_INFO } from '../../utils/topicLabels.js';
import AnswerStyle from '../../components/AnswerStyle.jsx';
import './practice.css';
import './dashboard.css';

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
      <Link to={`/c1/topic/${topic}`} state={{ from: '/c1/topics' }} className="tp-main" aria-label={`${prettyTopic(topic)}, ${Math.round(score)} percent. Open details.`}>
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

// Every topic with its level, and how the student answers. Moved off the dashboard so the dashboard stays short.
export default function TopicInsightsPage() {
  const { user } = useAuth();
  const [twin, setTwin] = useState(null);
  const [practicable, setPracticable] = useState([]);
  const [insights, setInsights] = useState(null);
  const [behaviour, setBehaviour] = useState(null);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [weakestFirst, setWeakestFirst] = useState(false);

  const load = useCallback(async () => {
    try {
      const [t, pt, ins, beh] = await Promise.all([
        getTwin(user.student_id),
        getPracticeTopics().catch(() => ({ topics: [] })),
        getInsights(user.student_id).catch(() => null),
        getBehaviour(user.student_id).catch(() => null),
      ]);
      setTwin(t);
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

  if (error && !twin)
    return (
      <div className="panel">
        <h2>Your topics did not load</h2>
        <p className="error">{error}</p>
      </div>
    );
  if (!twin) return <p className="muted">Loading...</p>;

  if (!twin.diagnosticCompleted)
    return (
      <div className="panel">
        <h2>Your twin does not exist yet</h2>
        <p className="muted">Take the diagnostic test first so we know your starting point.</p>
        <Link className="btn" to="/c1/diagnostic">Start the diagnostic test</Link>
      </div>
    );

  const topics = Object.entries(twin.mastery);
  // Use the estimated score now (forgetting applied) when the AI service gave one, else the stored score.
  const info = (t) => (insights && insights.topics ? insights.topics[t] : null);
  const shown = (t, m) => {
    const i = info(t);
    return i && i.estimatedNow !== null && i.estimatedNow !== undefined ? i.estimatedNow : m.score;
  };
  const reads = behaviour && behaviour.topics ? behaviour.topics : {};
  const canPractise = (t) => practicable.includes(t);

  const all = topics.map(([t, m]) => ({ topic: t, meta: m, score: shown(t, m), band: scoreBand(shown(t, m)) }));
  const count = (band) => all.filter((r) => r.band === band).length;
  const rows = all.filter((r) => filter === 'all' || r.band === filter);
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

  return (
    <div className="dash ti">
      <header className="ti-head">
        <div>
          <p className="dhero-kicker">Digital twin</p>
          <h1>Topic insights</h1>
          <p className="muted">Your level in every topic, and how you answer. {topics.length} topics in your semester.</p>
          <div className="ti-counts" aria-label="Topics by level">
            <span className="tp-avg weak">{count('weak')} just starting</span>
            <span className="tp-avg fair">{count('fair')} getting there</span>
            <span className="tp-avg strong">{count('strong')} strong</span>
          </div>
        </div>
        <Link to="/c1/dashboard" className="btn secondary back">&larr; Back to my learning state</Link>
      </header>

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

      {behaviour && (
        <div className="ti-answer">
          <AnswerStyle data={behaviour} />
        </div>
      )}
    </div>
  );
}
