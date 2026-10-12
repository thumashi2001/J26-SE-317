import { useState } from 'react';
import { NavLink, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import ErrorBoundary from './ErrorBoundary.jsx';
import DiagnosticIntro from './DiagnosticIntro.jsx';
import './diagnostic.css';

// One shell for every role. Each role passes its own menu (see config/menus.js).
export default function Layout({ menu, roleLabel }) {
  const { user, logout, diagnosticDone } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [introSeen, setIntroSeen] = useState(false);
  const initials = user.name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');

  const signOut = () => {
    logout();
    navigate('/login');
  };

  // A student who has not finished the diagnostic keeps the normal layout, but only the test opens.
  // The other menu items are locked and every other page sends her back to the test.
  // The intro popup shows on every fresh login until the test is done.
  const locked = user.role === 'student' && diagnosticDone === false;
  if (user.role === 'student' && diagnosticDone === null) return <p className="muted" style={{ padding: 32 }}>Loading...</p>;
  if (locked && location.pathname !== '/c1/diagnostic') return <Navigate to="/c1/diagnostic" replace />;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="side-brand">AdaptiveLearnSE</div>
        <div className="side-role">{roleLabel}</div>
        <nav>
          {menu.filter((m) => !m.onlyBeforeDiagnostic || diagnosticDone === false).map((m, i) =>
            m.heading ? (
              <div key={i} className="menu-heading">
                {m.heading}
              </div>
            ) : locked && m.to !== '/c1/diagnostic' ? (
              <span key={m.to} className="menu-link locked" aria-disabled="true" title="Finish the diagnostic test first">
                <span aria-hidden="true">🔒</span> {m.label}
              </span>
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
              {user.role === 'student' ? `${user.student_id}, ${user.semester}` : user.id}
            </div>
          </div>
          <button
            className="btn-ghost"
            onClick={signOut}
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
      {locked && !introSeen && <DiagnosticIntro name={user.name} onStart={() => setIntroSeen(true)} onLogout={signOut} />}
    </div>
  );
}
