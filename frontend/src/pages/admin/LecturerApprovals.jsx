import { useCallback, useEffect, useState } from 'react';
import { getLecturers, approveLecturer, rejectLecturer } from '../../services/adminApi.js';
import LecturerRequests from '../../components/admin/LecturerRequests.jsx';

const TABS = [
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
  { key: '', label: 'All' },
];

export default function LecturerApprovals() {
  const [tab, setTab] = useState('pending');
  const [all, setAll] = useState(null);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState('');
  const [toast, setToast] = useState('');

  const load = useCallback(async () => {
    try {
      setAll((await getLecturers()).lecturers);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (id, fn, done) => {
    setBusyId(id);
    try {
      await fn();
      setToast(done);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId('');
      setTimeout(() => setToast(''), 3000);
    }
  };

  const count = (key) => (all ? all.filter((l) => !key || l.status === key).length : 0);
  const shown = all ? all.filter((l) => !tab || l.status === tab) : [];
  const emptyText = {
    pending: 'Nobody is waiting for approval.',
    approved: 'No lecturer has been approved yet.',
    rejected: 'No registration has been rejected.',
    '': 'No lecturer has registered yet.',
  }[tab];

  return (
    <div>
      <h1>Lecturer approvals</h1>
      <p className="muted">Lecturers cannot log in until you approve them.</p>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} className={tab === t.key ? 'on' : ''} onClick={() => setTab(t.key)}>
            {t.label} <span className="tab-count">{count(t.key)}</span>
          </button>
        ))}
      </div>

      {error && <p className="error" role="alert">{error}</p>}
      {!all && !error ? (
        <p className="muted">Loading...</p>
      ) : (
        all && (
          <div className="panel flush">
            <LecturerRequests
              lecturers={shown}
              busyId={busyId}
              onApprove={(id) => act(id, () => approveLecturer(id), 'Lecturer approved')}
              onReject={(id, note) => act(id, () => rejectLecturer(id, note), 'Access removed')}
              emptyText={emptyText}
            />
          </div>
        )
      )}
      <div className="toast" role="status" aria-live="polite">{toast}</div>
    </div>
  );
}
