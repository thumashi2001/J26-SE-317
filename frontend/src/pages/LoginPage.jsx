import { useState } from 'react';
import { Link, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import AuthShell from '../components/AuthShell.jsx';

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [studentId, setStudentId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(studentId, password);
      navigate('/');
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="form-block" onSubmit={submit}>
        <h1>Log in</h1>
        <p className="muted">Use the student ID and password you registered with.</p>

        <label htmlFor="sid">Student ID</label>
        <input id="sid" value={studentId} onChange={(e) => setStudentId(e.target.value)} autoComplete="username" required />

        <label htmlFor="pw">Password</label>
        <input id="pw" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />

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
