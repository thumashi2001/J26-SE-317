import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { LECTURER_SECTIONS } from '../../config/menus.js';
import { getClassInsights } from '../../services/lecturerApi.js';
import { prettyTopic } from '../../utils/topics.js';
import useCountUp from '../../hooks/useCountUp.js';
import '../../components/admin/c1card.css';
import './lecturerhome.css';

function Stat({ icon, tone, value, suffix = '', label, none = 'None yet' }) {
  const n = useCountUp(typeof value === 'number' ? value : null);
  return (
    <div className={`c1a-tile ${tone}`}>
      <span className="ico" aria-hidden="true">{icon}</span>
      <strong>{typeof value === 'number' ? `${Math.round(n)}${suffix}` : none}</strong>
      <span className="lbl">{label}</span>
    </div>
  );
}

// A short live look at the class (Component 1), so the first page is never empty.
function ClassSnapshot() {
  const [d, setD] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    getClassInsights().then(setD).catch(() => setFailed(true));
  }, []);

  if (failed) return null; // the Class insights page shows the proper error
  if (!d) return <div className="panel skeleton" style={{ minHeight: 160 }} />;

  const hard = d.weakestTopics?.[0];
  return (
    <section className="panel c1a lh-snap" aria-labelledby="lh-snap-title">
      <div className="c1a-head">
        <h3 id="lh-snap-title">Your class right now</h3>
        <Link className="lh-link" to="/lecturer/c1">Open class insights &rarr;</Link>
      </div>
      <div className="c1a-tiles">
        <Stat icon={'\u{1F393}'} tone="t1" value={d.students} label="registered students" />
        <Stat icon={'\u{1F9ED}'} tone="t2" value={d.diagnosticDone} label="took the diagnostic" />
        <Stat icon={'\u{26A1}'} tone="t3" value={d.activeThisWeek} label="active this week" />
        <Stat icon={'\u{1F4C8}'} tone="t4" value={d.averageLevel ? d.averageLevel.score : null} suffix="%" label={d.averageLevel ? `average level, ${d.averageLevel.label}` : 'no diagnostics yet'} />
      </div>
      {d.students === 0 && <p className="muted small">No students have registered yet. Numbers appear here as soon as they do.</p>}
      {d.students > 0 && d.diagnosticDone === 0 && <p className="muted small">Students have registered but nobody has taken the diagnostic yet.</p>}
      {hard && <p className="lh-hard">Hardest topic for the class: <strong>{prettyTopic(hard.topic)}</strong> ({hard.average}% average)</p>}
    </section>
  );
}

export default function LecturerHome() {
  const { user } = useAuth();
  return (
    <div>
      <section className="hero ad-hero">
        <div className="ad-orb" aria-hidden="true" />
        <div>
          <span className="hero-tag">Lecturer area</span>
          <h1>Welcome, {user.name}</h1>
          <p>Your account is approved. Below is a quick look at your class. Tools for the other components will appear as the team finishes them.</p>
        </div>
        <div className="hero-id">
          <span className="small">Lecturer ID</span>
          <strong>{user.id}</strong>
        </div>
      </section>

      <ClassSnapshot />

      <h2>Your tools</h2>
      <div className="sections">
        {LECTURER_SECTIONS.map((s) => (
          <Link key={s.to} to={s.to} className="section-card">
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
