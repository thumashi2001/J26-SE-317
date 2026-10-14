import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { LECTURER_SECTIONS } from '../../config/menus.js';

export default function LecturerHome() {
  const { user } = useAuth();
  return (
    <div>
      <section className="hero">
        <div>
          <span className="hero-tag">Lecturer area</span>
          <h1>Welcome, {user.name}</h1>
          <p>Your account is approved. The tools for each component will appear here as the team finishes them.</p>
        </div>
        <div className="hero-id">
          <span className="small">Lecturer ID</span>
          <strong>{user.id}</strong>
        </div>
      </section>

      <h2>Your tools</h2>
      <div className="sections">
        {LECTURER_SECTIONS.map((s) => (
          <Link key={s.to} to={s.to} className="section-card">
            <span className="chip">{s.owner}</span>
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
