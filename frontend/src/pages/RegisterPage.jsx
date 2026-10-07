import { useState } from 'react';
import { Link, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import AuthShell from '../components/AuthShell.jsx';

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ studentId: '', name: '', email: '', semester: 'Y3S1', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await register(form);
      navigate('/');
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <form className="form-block" onSubmit={submit}>
        <h1>Create your account</h1>
        <p className="muted">Your semester decides which diagnostic questions you get.</p>

        <label htmlFor="name">Full name</label>
        <input id="name" value={form.name} onChange={set('name')} autoComplete="name" required />

        <div className="two">
          <div>
            <label htmlFor="sid">Student ID</label>
            <input id="sid" value={form.studentId} onChange={set('studentId')} placeholder="IT23280588" required />
          </div>
          <div>
            <label htmlFor="sem">Semester</label>
            <select id="sem" value={form.semester} onChange={set('semester')}>
              <option value="Y3S1">Year 3, Semester 1</option>
              <option value="Y3S2">Year 3, Semester 2</option>
            </select>
          </div>
        </div>

        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={form.email} onChange={set('email')} autoComplete="email" required />

        <label htmlFor="pw">Password</label>
        <input id="pw" type="password" minLength={8} value={form.password} onChange={set('password')} autoComplete="new-password" required />
        <span className="hint">At least 8 characters.</span>

        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" disabled={busy} type="submit">
          {busy ? 'Creating account...' : 'Create account'}
        </button>
        <p className="muted">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </AuthShell>
  );
}
