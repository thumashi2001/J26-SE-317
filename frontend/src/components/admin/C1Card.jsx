import { useState } from 'react';
import { prettyTopic } from '../../utils/topics.js';
import Avatar from '../ui/Avatar.jsx';
import './c1card.css';

const RISK = [
  { key: 'Low', text: 'Low risk', cls: 'low' },
  { key: 'Medium', text: 'Medium risk', cls: 'mid' },
  { key: 'High', text: 'High risk', cls: 'high' },
];

// Component 1 (Cognitive Digital Twin) summary for the administrator. Totals only, no student names or IDs.
// Other components: copy this file for your own card and add it to the admin dashboard.
const SEM = { Y3S1: 'Y3S1', Y3S2: 'Y3S2' };
const when = (iso) => new Date(iso).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
const SHOWN = 8;

export default function C1Card({ data, error, active = null }) {
  const [all, setAll] = useState(false);
  if (error) return <div className="panel c1a"><h3>Cognitive Digital Twin</h3><p className="error" role="alert">{error}</p></div>;
  if (!data) return <div className="panel c1a skeleton" style={{ minHeight: 220 }} />;

  const riskTotal = RISK.reduce((a, r) => a + (data.risk[r.key] || 0), 0);
  const m = data.model;
  return (
    <section className="panel c1a" aria-labelledby="c1a-title">
      <div className="c1a-head">
        <h3 id="c1a-title">Cognitive Digital Twin</h3>
        <span className={`c1a-chip ${data.aiService}`}>AI service {data.aiService}</span>
      </div>

      <div className="c1a-tiles">
        <div><strong>{data.diagnosticDone}<small> of {data.students}</small></strong><span>took the diagnostic</span></div>
        <div><strong>{data.activeThisWeek}</strong><span>active this week</span></div>
        <div><strong>{data.answers.total}</strong><span>practice answers<br />({data.answers.thisWeek} this week)</span></div>
        <div><strong>{data.averageLevel ? `${data.averageLevel.score}%` : 'None yet'}</strong><span>{data.averageLevel ? `average level, ${data.averageLevel.label}` : 'no diagnostics yet'}</span></div>
      </div>

      <div className="c1a-active">
        <h4>Active this week ({active ? active.length : data.activeThisWeek})</h4>
        {active && active.length === 0 && <p className="muted small">No student has practised in the last 7 days.</p>}
        {active && active.length > 0 && (
          <>
            <ol className="c1a-people">
              {(all ? active : active.slice(0, SHOWN)).map((p, i) => (
                <li key={`${p.name}-${i}`}>
                  <span className="no">{i + 1}</span>
                  <Avatar name={p.name} src={p.avatar} size={36} />
                  <span className="who"><strong>{p.name}</strong>{p.semester && <em>{SEM[p.semester] || p.semester}</em>}</span>
                  <span className="num">{p.answersThisWeek} {p.answersThisWeek === 1 ? 'answer' : 'answers'}</span>
                  <span className="last">last on {when(p.lastActive)}</span>
                </li>
              ))}
            </ol>
            {active.length > SHOWN && (
              <button type="button" className="c1a-more" onClick={() => setAll(!all)}>{all ? 'Show fewer' : `Show all ${active.length}`}</button>
            )}
          </>
        )}
      </div>

      <div className="c1a-cols">
        <div>
          <h4>Risk of falling behind</h4>
          {riskTotal === 0 ? <p className="muted small">No students with a diagnostic yet.</p> : (
            <>
              <div className="c1a-risk" role="img" aria-label={RISK.map((r) => `${data.risk[r.key]} ${r.text}`).join(', ')}>
                {RISK.map((r) => data.risk[r.key] > 0 && <span key={r.key} className={r.cls} style={{ flex: data.risk[r.key] }} />)}
              </div>
              <ul className="c1a-legend">
                {RISK.map((r) => <li key={r.key}><i className={r.cls} />{r.text}: <strong>{data.risk[r.key]}</strong></li>)}
              </ul>
            </>
          )}
        </div>
        <div>
          <h4>Weakest topics across students</h4>
          {data.weakestTopics.length === 0 ? <p className="muted small">Nothing to show yet.</p> : (
            <ul className="c1a-weak">
              {data.weakestTopics.map((t) => (
                <li key={t.topic}>
                  <span>{prettyTopic(t.topic)}</span>
                  <div className="bar" aria-hidden="true"><i style={{ width: `${Math.max(3, t.average)}%` }} /></div>
                  <b>{t.average}%</b>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="c1a-model">
        <h4>Trained model in use</h4>
        {m ? (
          <p><strong>{m.name}</strong> predicts the chance of a correct answer. On students it had not seen it scores {m.score} (AUC), against {m.ruleBasedScore} for the rule-based twin. Trained on {m.trainedOn}.</p>
        ) : (
          <p className="muted small">Training report not found on this server.</p>
        )}
      </div>
    </section>
  );
}
