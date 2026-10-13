import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getStats, getLecturers, approveLecturer, rejectLecturer, getC1Summary, getC1Active } from '../../services/adminApi.js';
import LecturerRequests from '../../components/admin/LecturerRequests.jsx';
import C1Card from '../../components/admin/C1Card.jsx';
import { ADMIN_SECTIONS } from '../../config/menus.js';

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [pending, setPending] = useState([]);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState('');
  const [toast, setToast] = useState('');
  const [c1, setC1] = useState(null);
  const [c1Error, setC1Error] = useState('');
  const [c1Active, setC1Active] = useState(null);

  const load = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([getStats(), getLecturers('pending')]);
      setStats(s);
      setPending(p.lecturers);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    getC1Summary().then(setC1).catch((err) => setC1Error(err.message));
    getC1Active().then((r) => setC1Active(r.students)).catch(() => {}); // the card still works without the list
  }, []);

  const act = async (id, fn, done) => {
    setBusyId(id);
    try {
      await fn();
      setToast(done);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId('');
      setTimeout(() => setToast(''), 3000);
    }
  };

  const cards = stats && [
    { label: 'Waiting for approval', value: stats.lecturers.pending, color: 'var(--fair)' },
    { label: 'Approved lecturers', value: stats.lecturers.approved, color: 'var(--strong)' },
    { label: 'Rejected', value: stats.lecturers.rejected, color: 'var(--weak)' },
    { label: 'Students', value: stats.students, color: '#2f6fb0' },
  ];

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Admin dashboard</h1>
          <p className="muted">Welcome back, {user.name}.</p>
        </div>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <section className="stat-grid" aria-label="Summary">
        {!cards && !error && [0, 1, 2, 3].map((i) => <div key={i} className="stat skeleton" />)}
        {cards && cards.map((c) => (
          <div key={c.label} className="stat" style={{ '--c': c.color }}>
            <div className="stat-num">{c.value}</div>
            <div className="stat-label">{c.label}</div>
          </div>
        ))}
      </section>

      <h2>Waiting for approval</h2>
      <div className="panel flush">
        <LecturerRequests
          lecturers={pending.slice(0, 5)}
          busyId={busyId}
          onApprove={(id) => act(id, () => approveLecturer(id), 'Lecturer approved')}
          onReject={(id, note) => act(id, () => rejectLecturer(id, note), 'Registration rejected')}
          emptyText="No lecturer is waiting. New registrations will appear here."
        />
        {pending.length > 5 && (
          <div className="more"><Link to="/admin/lecturers">See all {pending.length} requests</Link></div>
        )}
      </div>

      <h2>Components</h2>
      <C1Card data={c1} error={c1Error} active={c1Active} />
      {/* Other members: add your own card here, for example <C3Card ... /> */}

      <h2>Manage</h2>
      <div className="sections">
        {ADMIN_SECTIONS.map((s) => (
          <Link key={s.to} to={s.to} className="section-card">
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </Link>
        ))}
      </div>

      <div className="toast" role="status" aria-live="polite">{toast}</div>
    </div>
  );
}
