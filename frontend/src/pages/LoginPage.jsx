import { useState } from 'react';
import { Link, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import AuthShell from '../components/AuthShell.jsx';
import { cleanId } from '../utils/userId.js';

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [userId, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [role, setRole] = useState('student');
  const [show, setShow] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(cleanId(userId), password);
      navigate('/');
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="form-block" onSubmit={submit}>
        <h1>Welcome back</h1>
        <p className="muted">Log in to continue your learning.</p>
        <div className="segment" role="tablist" aria-label="Log in as">
          {[['student', 'Student'], ['lecturer', 'Lecturer'], ['admin', 'Admin']].map(([k, label]) => (
            <button key={k} type="button" role="tab" aria-selected={role === k} className={role === k ? 'on' : ''} onClick={() => setRole(k)}>{label}</button>
          ))}
        </div>

        <label htmlFor="sid">{role === 'student' ? 'Student ID' : role === 'lecturer' ? 'Lecturer ID' : 'Admin ID'}</label>
        <input
          id="sid"
          value={userId}
          onChange={(e) => setUserId(cleanId(e.target.value))}
          maxLength={30}
          autoComplete="username"
          required
        />

        <label htmlFor="pw">Password</label>
        <div className="pw-wrap">
          <input id="pw" type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          <button type="button" className="pw-toggle" onClick={() => setShow(!show)}>{show ? 'Hide' : 'Show'}</button>
        </div>

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
