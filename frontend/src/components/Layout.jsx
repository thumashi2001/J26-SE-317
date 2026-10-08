import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import ErrorBoundary from './ErrorBoundary.jsx';

// One shell for every role. Each role passes its own menu (see config/menus.js).
export default function Layout({ menu, roleLabel }) {
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
        <div className="side-role">{roleLabel}</div>
        <nav>
          {menu.filter((m) => !m.onlyBeforeDiagnostic || diagnosticDone === false).map((m, i) =>
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
              {user.role === 'student' ? `${user.student_id}, ${user.semester}` : user.id}
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
