import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import AdaptiveLearnSELogo from './AdaptiveLearnSELogo';
import { useAuth } from '../context/AuthContext.jsx';
import ErrorBoundary from './ErrorBoundary.jsx';

import { useState } from 'react';

// One shell for every role. Each role passes its own menu (see config/menus.js).
export default function Layout({ menu, roleLabel }) {
  const { user, logout, diagnosticDone } = useAuth();
  const navigate = useNavigate();
  const [pageTitle, setPageTitle] = useState('AdaptiveLearnSE');
  const [showDropdown, setShowDropdown] = useState(false);
  
  const initials = user.name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
  const location = useLocation();
  const isC3 = location.pathname.includes('/c3');

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="side-brand">
          <AdaptiveLearnSELogo variant="dark" responsive={true} />
        </div>
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
      </aside>
      
      <div className="main-wrapper">
        <header className="top-nav">
          <h1 className="top-nav-title">{pageTitle}</h1>
          <div className="top-profile-container">
            <div className="top-user-profile" onClick={() => setShowDropdown(true)}>
              <div className="top-user-text">
                <div className="top-name">{user.name}</div>
                <div className="top-role">{user.role === 'student' ? user.student_id : roleLabel}</div>
              </div>
              <div className="avatar">{initials}</div>
              <div className="top-chevron">▼</div>
            </div>

            {showDropdown && (
              <>
                <div className="dropdown-overlay" onClick={() => setShowDropdown(false)} />
                <div className="profile-dropdown">
                  <button className="dropdown-item" onClick={() => {
                    setShowDropdown(false);
                    // Navigate to profile if implemented, or just close for now
                  }}>
                    My Profile
                  </button>
                  <button className="dropdown-item" onClick={() => {
                    setShowDropdown(false);
                    logout();
                    navigate('/login');
                  }}>
                    Log out
                  </button>
                </div>
              </>
            )}
          </div>
        </header>

        <main className={`content ${isC3 ? 'c3-main-content' : ''}`}>
          <ErrorBoundary>
            <Outlet context={{ setPageTitle }} />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
