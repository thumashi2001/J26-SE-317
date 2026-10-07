import { useState } from 'react';
import { Link, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import AuthShell from '../components/AuthShell.jsx';
import { registerLecturerRequest } from '../services/authApi.js';
import { cleanId } from '../utils/userId.js';

const EMPTY = { id: '', name: '', email: '', semester: 'Y3S1', password: '' };

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState('student');
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(null);

  if (user) return <Navigate to="/" replace />;

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const switchRole = (next) => {
    setRole(next);
    setForm(EMPTY);
    setError('');
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    const isStudent = role === 'student';
    setBusy(true);
    try {
      if (isStudent) {
        await register({ studentId: cleanId(form.id), name: form.name, email: form.email, semester: form.semester, password: form.password });
        navigate('/');
      } else {
        const res = await registerLecturerRequest({ lecturerId: cleanId(form.id), name: form.name, email: form.email, password: form.password });
        setSent(res);
        setBusy(false);
      }
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  if (sent)
    return (
      <AuthShell>
        <div className="form-block sent" role="status">
          <span className="sent-icon" aria-hidden="true">&#10003;</span>
          <h1>Request sent</h1>
          <p>{sent.message}</p>
          <p className="muted">Your lecturer ID is <strong>{sent.user.id}</strong>. Use it to log in after the approval.</p>
          <Link className="btn" to="/login">Back to log in</Link>
        </div>
      </AuthShell>
    );

  const isStudent = role === 'student';
  return (
    <AuthShell>
      <form className="form-block" onSubmit={submit}>
        <h1>Create your account</h1>
        <div className="segment" role="tablist" aria-label="I am a">
          <button type="button" role="tab" aria-selected={isStudent} className={isStudent ? 'on' : ''} onClick={() => switchRole('student')}>Student</button>
          <button type="button" role="tab" aria-selected={!isStudent} className={!isStudent ? 'on' : ''} onClick={() => switchRole('lecturer')}>Lecturer</button>
        </div>
        <p className="muted">
          {isStudent ? 'Your semester decides which diagnostic questions you get.' : 'The administrator must approve your account before you can log in.'}
        </p>

        <label htmlFor="name">Full name</label>
        <input id="name" value={form.name} onChange={set('name')} autoComplete="name" required />

        <div className={isStudent ? 'two' : ''}>
          <div>
            <label htmlFor="sid">{isStudent ? 'Student ID' : 'Lecturer ID'}</label>
            <input
              id="sid"
              value={form.id}
              onChange={(e) => setForm({ ...form, id: cleanId(e.target.value) })}
              maxLength={30}
              required
            />
          </div>
          {isStudent && (
            <div>
              <label htmlFor="sem">Semester</label>
              <select id="sem" value={form.semester} onChange={set('semester')}>
                <option value="Y3S1">Year 3, Semester 1</option>
                <option value="Y3S2">Year 3, Semester 2</option>
              </select>
            </div>
          )}
        </div>

        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={form.email} onChange={set('email')} autoComplete="email" required />

        <label htmlFor="pw">Password</label>
        <input id="pw" type="password" minLength={8} value={form.password} onChange={set('password')} autoComplete="new-password" required />
        <span className="hint">At least 8 characters.</span>

        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn" disabled={busy} type="submit">
          {busy ? 'Please wait...' : isStudent ? 'Create account' : 'Send registration request'}
        </button>
        <p className="muted">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </AuthShell>
  );
}
