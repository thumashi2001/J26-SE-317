import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import ErrorBoundary from './ErrorBoundary.jsx';

const MENU = [
  { heading: 'Digital twin' },
  { to: '/c1/diagnostic', label: 'Diagnostic test', onlyBeforeDiagnostic: true },
  { to: '/c1/dashboard', label: 'My learning state' },
  { heading: 'Exams' },
  { to: '/c2', label: 'Exam intelligence' },
  { heading: 'Marking' },
  { to: '/c3', label: 'Automated marking' },
  { heading: 'Study plan' },
  { to: '/c4', label: 'Adaptive path' },
];

export default function Layout() {
  const { user, logout, diagnosticDone } = useAuth();
  const navigate = useNavigate();
  const initials = user.name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="side-brand">AdaptiveLearnSE</div>
        <nav>
          {MENU.filter((m) => !m.onlyBeforeDiagnostic || diagnosticDone === false).map((m, i) =>
            m.heading ? (
              <div key={i} className="menu-heading">
                {m.heading}
              </div>
            ) : (
              <NavLink
                key={m.to}
                to={m.to}
                end={m.end}
                className={({ isActive }) => 'menu-link' + (isActive ? ' active' : '')}
              >
                {m.label}
              </NavLink>
            )
          )}
        </nav>
        <div className="side-user">
          <div className="avatar">{initials}</div>
          <div className="side-user-text">
            <div className="side-name">{user.name}</div>
            <div className="side-sub">
              {user.student_id}, {user.semester}
            </div>
          </div>
          <button
            className="btn-ghost"
            onClick={() => {
              logout();
              navigate('/login');
            }}
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="content">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
