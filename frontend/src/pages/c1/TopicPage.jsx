import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getHistory, getInsights, getPlan } from '../../services/c1Api.js';
import { prettyTopic, scoreBand, topicModule, topicLectures } from '../../utils/topics.js';
import ScoreChart from '../../components/charts/ScoreChart.jsx';
import WhatIfPanel from '../../components/WhatIfPanel.jsx';
import './practice.css';
import './topicpage.css';

// 95 -> "2 min", 3600 -> "1 h", 40 -> "40 s"
const minutesText = (sec) => (sec < 60 ? `${Math.round(sec)} s` : sec < 3600 ? `${Math.round(sec / 60)} min` : `${Math.floor(sec / 3600)} h ${Math.round((sec % 3600) / 60)} min`);

const BAND_TEXT = { weak: 'Just starting', fair: 'Getting there', strong: 'Strong' };
const RING = 2 * Math.PI * 52;
const DOTS = { low: 1, medium: 2, high: 3 };

// One dot per answer (capped), filled for correct answers.
function AnswerDots({ correct, answered }) {
  const cap = 20;
  const total = Math.min(answered, cap);
  const right = answered > cap ? Math.round((correct / answered) * cap) : correct;
  return (
    <div className="tt-dots" aria-hidden="true">
      {Array.from({ length: total }, (_, i) => <i key={i} className={i < right ? 'on' : ''} />)}
    </div>
  );
}

// A bar split into segments, the first `used` segments filled.
function Segments({ used, total }) {
  const n = Math.min(total, 14);
  const filled = total > 14 ? Math.round((used / total) * 14) : used;
  return (
    <div className="tt-seg" aria-hidden="true">
      {Array.from({ length: n }, (_, i) => <i key={i} className={i < filled ? 'on' : ''} />)}
    </div>
  );
}

export default function TopicPage() {
  const { topic } = useParams();
  const { user } = useAuth();
  const [state, setState] = useState({ status: 'loading' });
  const [info, setInfo] = useState(null); // estimated score now, confidence and the reasons
  const [examDate, setExamDate] = useState(null);

  useEffect(() => {
    let alive = true;
    setState({ status: 'loading' });
    getHistory(user.student_id, topic)
      .then((data) => alive && setState({ status: 'ready', data }))
      .catch((err) => alive && setState({ status: 'error', message: err.message }));
    return () => {
      alive = false;
    };
  }, [user.student_id, topic]);

  useEffect(() => {
    let alive = true;
    setInfo(null);
    getInsights(user.student_id)
      .then((d) => alive && setInfo((d.topics || {})[topic] || null))
      .catch(() => {}); // the page works without the extra explanation
    getPlan(user.student_id)
      .then((p) => alive && setExamDate(p.examDate))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [user.student_id, topic]);

  if (state.status === 'loading') return <p className="muted">Loading...</p>;
  if (state.status === 'error')
    return (
      <div className="panel">
        <h2>This topic did not load</h2>
        <p className="error">{state.message}</p>
        <Link className="btn" to="/c1/dashboard">Back to my learning state</Link>
      </div>
    );

  const { current, points } = state.data;
  const hasEstimate = info && info.estimatedNow !== null && info.estimatedNow !== undefined;
  const shownScore = hasEstimate ? info.estimatedNow : current.score;
  const band = scoreBand(shownScore);
  const lastPracticed = new Date(current.lastPracticed).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  const accuracy = current.answered ? Math.round((current.correct / current.answered) * 100) : null;
  const conf = info ? (info.confidenceLabel || '').toLowerCase() : '';
  const perAnswer = info && info.answers ? Math.round(info.timeSpentSec / info.answers) : null;
  const pct = Math.min(100, Math.max(0, shownScore));

  return (
    <div className="topic-page">
      <Link to="/c1/dashboard" className="btn secondary back">&larr; Back to my learning state</Link>

      <section className={`th-hero ${band}`}>
        <svg viewBox="0 0 130 130" className="th-ring" role="img" aria-label={`Score ${Math.round(shownScore)} percent`}>
          <circle cx="65" cy="65" r="52" className="trk" />
          <circle cx="65" cy="65" r="52" className="fil" strokeDasharray={RING} strokeDashoffset={RING * (1 - pct / 100)} transform="rotate(-90 65 65)" />
          <text x="65" y="74" textAnchor="middle">{Math.round(shownScore)}%</text>
        </svg>
        <div className="th-text">
          <div className="th-chips">
            {topicModule(topic) && <span className="th-chip">{topicModule(topic)}</span>}
            {topicLectures(topic) && <span className="th-chip">Lectures {topicLectures(topic)}</span>}
            <span className="th-chip level">{BAND_TEXT[band]}</span>
            {hasEstimate && <span className="th-chip">Estimated now</span>}
          </div>
          <h1>{prettyTopic(topic)}</h1>
          <p>
            {hasEstimate && current.score - shownScore >= 1
              ? `You scored ${Math.round(current.score)}% when you last practised. Forgetting has lowered it to about ${Math.round(shownScore)}%.`
              : `Your score is about ${Math.round(shownScore)}%.`}
          </p>
        </div>
        <Link className="btn th-go" to={`/c1/practice/${topic}`}>Practise this topic</Link>
      </section>

      <div className="tt-row">
        <div className="tt k-blue">
          <span className="tt-label">Practice sessions</span>
          <strong>{current.practiceSessions}</strong>
          <span className="tt-note">last on {lastPracticed}</span>
        </div>
        <div className="tt k-indigo">
          <span className="tt-label">Answers correct</span>
          <strong>{current.correct}<small> of {current.answered}</small></strong>
          <span className="tt-note">{accuracy === null ? 'no answers yet' : `${accuracy}% accuracy`}</span>
          {current.answered > 0 && <AnswerDots correct={current.correct} answered={current.answered} />}
        </div>
        <div className="tt k-sky">
          <span className="tt-label">Hints used</span>
          <strong>{info ? info.hintsUsed : 0}<small> of {info ? info.quizAnswers : 0}</small></strong>
          <span className="tt-note">practice answers</span>
          {info && info.quizAnswers > 0 && <Segments used={info.hintsUsed} total={info.quizAnswers} />}
        </div>
        <div className="tt k-teal">
          <span className="tt-label">Time answering</span>
          <strong>{info && info.timeSpentSec > 0 ? minutesText(info.timeSpentSec) : '0 s'}</strong>
          <span className="tt-note">{perAnswer ? `about ${perAnswer} s an answer` : 'no timed answers yet'}</span>
        </div>
        <div className="tt k-blue">
          <span className="tt-label">Score reliability</span>
          <strong>{info ? info.confidenceLabel : '...'}</strong>
          <span className="tt-note">{info ? `from ${info.answers} ${info.answers === 1 ? 'answer' : 'answers'}` : ''}</span>
          <div className="tt-conf" aria-hidden="true">{[1, 2, 3].map((d) => <i key={d} className={d <= (DOTS[conf] || 0) ? 'on' : ''} />)}</div>
        </div>
      </div>

      {info && (
        <section className="panel why-panel" aria-labelledby="why-title">
          <h2 id="why-title">Why this score?</h2>
          {info.scoreWhy && <p>{info.scoreWhy}</p>}
          <p>{info.confidenceWhy}</p>
        </section>
      )}

      <div className="tc-row">
        <section className="panel tc-card">
          <h2>Score history</h2>
          <p className="muted small">Each dot is one update. The shaded bands are the weak and strong zones.</p>
          {points.length < 2 && <p className="muted">Only one score so far. Each practice answer adds a point to this chart.</p>}
          <ScoreChart points={points} />
        </section>
        <div className="tc-card-wrap">
          <WhatIfPanel topic={topic} savedExamDate={examDate} />
        </div>
      </div>
    </div>
  );
}
