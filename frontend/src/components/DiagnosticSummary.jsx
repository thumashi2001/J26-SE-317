import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import StudentsArt from './StudentsArt.jsx';
import { TOPIC_INFO } from '../utils/topicLabels.js';
import { prettyTopic, scoreBand } from '../utils/topics.js';
import './diagnostic.css';

const BAND_TEXT = { strong: 'Strong', fair: 'Getting there', weak: 'Needs work' };

// Shows the twin's scores after the diagnostic: used for the result right after the test
// (mode "result") and when a student opens the test page again later (mode "done").
export default function DiagnosticSummary({ mastery, mode = 'result', timedOut = false, name = '' }) {
  const data = useMemo(() => {
    const rows = Object.entries(mastery || {}).map(([topic, m]) => ({ topic, score: Math.round(m.score), correct: m.correct, answered: m.answered }));
    const avg = rows.length ? Math.round(rows.reduce((s, r) => s + r.score, 0) / rows.length) : 0;
    const sorted = [...rows].sort((a, b) => a.score - b.score);
    const groups = {};
    rows.forEach((r) => {
      const info = TOPIC_INFO[r.topic] || {};
      const code = info.module || 'Other';
      (groups[code] ||= { code, name: info.moduleName || '', rows: [] }).rows.push(r);
    });
    const mods = Object.values(groups).map((g) => ({ ...g, avg: Math.round(g.rows.reduce((s, r) => s + r.score, 0) / g.rows.length) }));
    return { rows, avg, best: sorted[sorted.length - 1], worst: sorted[0], mods, strong: rows.filter((r) => r.score >= 60).length, weak: rows.filter((r) => r.score < 30).length };
  }, [mastery]);

  const first = (name || '').split(' ')[0];
  const isResult = mode === 'result';
  const band = scoreBand(data.avg);

  return (
    <div className="dsum">
      <section className="dsum-hero">
        <div className="dsum-text">
          <p className="dsum-kicker">{isResult ? 'Diagnostic complete' : 'Diagnostic done'}</p>
          <h1>{isResult ? `Your twin is ready${first ? `, ${first}` : ''}` : `You have already taken the test${first ? `, ${first}` : ''}`}</h1>
          <p className="dsum-lead">
            {isResult
              ? 'This is where your twin begins. Every practice quiz you take will move these scores.'
              : 'Your twin was built from that test. Here is how your topics look right now. Practise to keep them strong.'}
          </p>
          {timedOut && <p className="dsum-note">Time ran out, so your test was sent with the answers you had. Unanswered questions count as wrong.</p>}
          <div className="dsum-cta">
            {data.worst && (
              <Link className="dsum-btn main" to={`/c1/practice/${data.worst.topic}`}>
                Practise {prettyTopic(data.worst.topic)}
              </Link>
            )}
            <Link className="dsum-btn" to="/c1/dashboard">Open my learning state</Link>
          </div>
        </div>
        <div className="dsum-art" aria-hidden="true"><StudentsArt /></div>
      </section>

      <section className="dsum-tiles" aria-label="Summary">
        <div className={'dsum-tile avg ' + band}>
          <svg viewBox="0 0 64 64" className="dsum-ring" aria-hidden="true">
            <circle cx="32" cy="32" r="26" className="trk" />
            <circle cx="32" cy="32" r="26" className="fil" strokeDasharray={2 * Math.PI * 26} strokeDashoffset={2 * Math.PI * 26 * (1 - data.avg / 100)} transform="rotate(-90 32 32)" />
          </svg>
          <div><small>Average score</small><strong>{data.avg}%</strong></div>
        </div>
        {data.best && (
          <div className="dsum-tile">
            <span className="dsum-ic good" aria-hidden="true">{'★'}</span>
            <div><small>Strongest topic</small><strong>{prettyTopic(data.best.topic)}</strong><em>{data.best.score}%</em></div>
          </div>
        )}
        {data.worst && (
          <div className="dsum-tile">
            <span className="dsum-ic warn" aria-hidden="true">{'→'}</span>
            <div><small>Start with</small><strong>{prettyTopic(data.worst.topic)}</strong><em>{data.worst.score}%</em></div>
          </div>
        )}
        <div className="dsum-tile">
          <span className="dsum-ic info" aria-hidden="true">{'▦'}</span>
          <div><small>Topics</small><strong>{data.rows.length}</strong><em>{data.strong} strong, {data.weak} weak</em></div>
        </div>
      </section>

      <div className="dsum-legend" aria-label="Colour guide">
        <span><i className="strong" /> Strong, 60% and up</span>
        <span><i className="fair" /> Getting there, 30 to 59%</span>
        <span><i className="weak" /> Needs work, below 30%</span>
      </div>

      {data.mods.map((g) => (
        <section key={g.code} className="dsum-mod">
          <header>
            <span className="dsum-code">{g.code}</span>
            <h2>{g.name}</h2>
            <span className={'dsum-avg ' + scoreBand(g.avg)}>{g.avg}% average</span>
          </header>
          <div className="dsum-grid">
            {g.rows.map((r) => {
              const b = scoreBand(r.score);
              return (
                <Link key={r.topic} to={`/c1/topic/${r.topic}`} className={'dsum-card ' + b}>
                  <span className="dsum-card-name">{prettyTopic(r.topic)}</span>
                  <span className="dsum-card-score">{r.score}%</span>
                  <span className="dsum-bar"><span style={{ width: `${Math.max(4, r.score)}%` }} /></span>
                  <span className="dsum-card-foot">{BAND_TEXT[b]}{r.answered ? ` · ${r.correct} of ${r.answered} correct` : ''}</span>
                </Link>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
