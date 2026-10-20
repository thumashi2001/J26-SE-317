import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext.jsx';
import { getClassInsights } from '../../services/lecturerApi.js';
import { prettyTopic } from '../../utils/topics.js';
import Avatar from '../../components/ui/Avatar.jsx';
import '../../components/admin/c1card.css';
import './classinsights.css';

const RISK = [
  { key: 'Low', text: 'Low risk', cls: 'low' },
  { key: 'Medium', text: 'Medium risk', cls: 'mid' },
  { key: 'High', text: 'High risk', cls: 'high' },
  { key: 'none', text: 'Not rated yet (no practice answers)', cls: 'none' },
];
const when = (iso) => new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

// Component 1 view for lecturers: how the class is learning and who needs help.
export default function ClassInsights() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getClassInsights().then(setData).catch(() => setError('Could not load the class insights.'));
  }, []);

  const counts = data ? { ...data.risk, none: data.notRated ?? 0 } : {};

  return (
    <div className="ci">
      <header className="ci-head">
        <h1>Class insights</h1>
        <p className="muted">Welcome, {user.name}. This is how your students are learning, and who may need help.</p>
      </header>

      {data && !data.isSample && (
        <div className="ci-sample" role="note">
          <strong>All registered students.</strong> Lecturers are not linked to classes yet, so these numbers cover every student who has registered.
        </div>
      )}

      {data?.isSample && (
        <div className="ci-sample" role="note">
          <strong>Sample data.</strong> Lecturers are not linked to students yet, so the numbers below are examples, not your real class.
        </div>
      )}

      {error && <p className="error" role="alert">{error}</p>}
      {!data && !error && <div className="panel c1a skeleton" style={{ minHeight: 240 }} />}

      {data && (
        <section className="panel c1a" aria-labelledby="ci-title">
          <div className="c1a-head"><h3 id="ci-title">{data.className}</h3></div>

          <div className="c1a-tiles">
            <div><strong>{data.diagnosticDone}<small> of {data.students}</small></strong><span>took the diagnostic</span></div>
            <div><strong>{data.activeThisWeek}</strong><span>active this week</span></div>
            <div><strong>{data.answers.total}</strong><span>practice answers<br />({data.answers.thisWeek} this week)</span></div>
            <div>{data.averageLevel
              ? <><strong>{data.averageLevel.score}%</strong><span>average level, {data.averageLevel.label}</span></>
              : <><strong>-</strong><span>average level, no diagnostics yet</span></>}</div>
          </div>

          <div className="c1a-cols">
            <div>
              <h4>Risk of falling behind</h4>
              <div className="c1a-risk" role="img" aria-label={RISK.map((r) => `${counts[r.key]} ${r.text}`).join(', ')}>
                {RISK.map((r) => counts[r.key] > 0 && <span key={r.key} className={r.cls} style={{ flex: counts[r.key] }} />)}
              </div>
              <ul className="c1a-legend">
                {RISK.map((r) => <li key={r.key}><i className={r.cls} />{r.text}: <strong>{counts[r.key]}</strong></li>)}
              </ul>
            </div>
            <div>
              <h4>Topics the class finds hardest</h4>
              {data.weakestTopics.length === 0 && <p className="muted small">Shown once students finish the diagnostic test.</p>}
              <ul className="c1a-weak">
                {data.weakestTopics.map((t) => (
                  <li key={t.topic}>
                    <span>{prettyTopic(t.topic)}</span>
                    <div className="bar" aria-hidden="true"><i style={{ width: `${Math.max(3, t.average)}%` }} /></div>
                    <b>{t.average}%</b>
                  </li>
                ))}
              </ul>
              <p className="muted small ci-tip">These are good topics to revisit in the next lecture.</p>
            </div>
          </div>

          <div className="ci-attn">
            <h4>Students who may need help ({data.needAttention.length})</h4>
            {data.needAttention.length === 0 && <p className="muted small">No student is marked at risk right now.</p>}
            <ol className="c1a-people">
              {data.needAttention.map((p, i) => (
                <li key={`${p.name}-${i}`}>
                  <span className="no">{i + 1}</span>
                  <Avatar name={p.name} size={36} />
                  <span className="who"><strong>{p.name}</strong><em>{p.semester}</em><em className={`rk ${p.risk === 'High' ? 'high' : 'mid'}`}>{p.risk} risk</em></span>
                  <span className="num">level {p.level}%</span>
                  <span className="last">{p.weakest ? `weakest: ${prettyTopic(p.weakest)}` : ''}<br />{p.lastActive ? `last active ${when(p.lastActive)}` : 'no practice yet'}</span>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}
    </div>
  );
}
