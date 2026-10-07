import { useState } from 'react';
import { Link, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import AuthShell from '../components/AuthShell.jsx';
import { cleanId } from '../utils/userId.js';

// Shown instead of a red error when a lecturer is not allowed in yet.
const NOTICES = {
  pending_approval: {
    tone: 'wait',
    title: 'Waiting for approval',
    text: 'Your registration was received. The administrator must approve your account before you can log in. Please try again later.',
  },
  not_approved: {
    tone: 'stop',
    title: 'Registration not approved',
    text: 'The administrator did not approve this account. Please contact the administrator for help.',
  },
};

function NoticeIcon({ tone }) {
  return tone === 'wait' ? (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 8l8 8M16 8l-8 8" />
    </svg>
  );
}

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setNotice(null);
    setBusy(true);
    try {
      await login(cleanId(userId), password);
      navigate('/');
    } catch (err) {
      if (err.code === 'pending_approval' || err.code === 'not_approved') setNotice(NOTICES[err.code]);
      else setError(err.message);
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="form-block" onSubmit={submit}>
        <h1>Log in</h1>
        <p className="muted">Students, lecturers and the administrator all log in here.</p>

        <label htmlFor="sid">ID</label>
        <input
          id="sid"
          value={userId}
          onChange={(e) => setUserId(cleanId(e.target.value))}
          maxLength={30}
          autoComplete="username"
          required
        />

        <label htmlFor="pw">Password</label>
        <input id="pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />

        {notice && (
          <div className={`notice ${notice.tone}`} role="status">
            <span className="notice-icon"><NoticeIcon tone={notice.tone} /></span>
            <div>
              <strong>{notice.title}</strong>
              <p>{notice.text}</p>
            </div>
          </div>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" disabled={busy} type="submit">
          {busy ? 'Logging in...' : 'Log in'}
        </button>
        <p className="muted">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </form>
    </AuthShell>
  );
}
