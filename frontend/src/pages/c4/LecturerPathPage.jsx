import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext.jsx';
import { getLecturerScope } from './c4Api.js';
import './c4.css';

/**
 * Read-only lecturer page. Live access stays disabled until an approved
 * roster or assignment source exists. This page does not list every student.
 */
export default function LecturerPathPage() {
  const { user } = useAuth();
  const [scope, setScope] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const body = await getLecturerScope();
      setScope(body);
    } catch (err) {
      setScope(null);
      setError(err.message || 'Could not check lecturer access');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role === 'lecturer') load();
    else setLoading(false);
  }, [user, load]);

  if (user?.role && user.role !== 'lecturer') {
    return (
      <div className="c4-path">
        <h1>Adaptive paths (lecturer)</h1>
        <p className="error">This page is for lecturer accounts only.</p>
      </div>
    );
  }

  return (
    <div className="c4-path">
      <h1>Adaptive paths (lecturer)</h1>
      <p className="muted">
        Read-only view of study plans recommended to students in an approved class. Lecturers
        cannot mark work complete or open private feedback.
      </p>

      {loading && <p className="muted">Checking access scope…</p>}

      {error && (
        <div className="panel">
          <p className="error" role="alert">
            {error}
          </p>
          <button type="button" className="btn secondary" onClick={load}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="panel">
          <p className="chip">Not operational</p>
          <p>{scope?.reason || 'Lecturer scope is unavailable.'}</p>
          <p className="muted small">
            Student search is disabled. C4 does not load every registered student, and a student
            ID typed here would not grant access.
          </p>
          <label className="c4-label">
            Student ID
            <input type="text" disabled value="" placeholder="Unavailable until a roster is approved" />
          </label>
        </div>
      )}
    </div>
  );
}
