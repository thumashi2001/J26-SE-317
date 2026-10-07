import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getHistory } from '../../services/c1Api.js';
import { prettyTopic, scoreBand } from '../../utils/topics.js';
import ScoreChart from '../../components/charts/ScoreChart.jsx';
import WhatIfPanel from '../../components/WhatIfPanel.jsx';

const BAND_TEXT = { weak: 'Weak', fair: 'Fair', strong: 'Strong' };

export default function TopicPage() {
  const { topic } = useParams();
  const { user } = useAuth();
  const [state, setState] = useState({ status: 'loading' });

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
  const band = scoreBand(current.score);
  const lastPracticed = new Date(current.lastPracticed).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  return (
    <div>
      <Link to="/c1/dashboard" className="btn secondary back">&larr; Back to my learning state</Link>
      <h1>{prettyTopic(topic)}</h1>

      <section className={`panel topic-head ${band}`}>
        <div>
          <div className="topic-score big">{Math.round(current.score)}%</div>
          <span className={`pill ${band}`}>{BAND_TEXT[band]}</span>
        </div>
        <dl className="facts">
          <div><dt>Practice sessions</dt><dd>{current.practiceSessions}</dd></div>
          <div><dt>Answers correct</dt><dd>{current.correct} of {current.answered}</dd></div>
          <div><dt>Last practised</dt><dd>{lastPracticed}</dd></div>
        </dl>
      </section>

      <h2>Score history</h2>
      <div className="panel">
        {points.length < 2 && (
          <p className="muted">Only one score so far. Each practice answer adds a point to this chart.</p>
        )}
        <ScoreChart points={points} />
      </div>

      <h2 id="whatif-title">What if I study?</h2>
      <WhatIfPanel topic={topic} />
    </div>
  );
}
