import { useState } from 'react';

// A list of lecturer registrations with Approve and Reject buttons.
// Used on the admin overview (pending only) and on the full approvals page.
const STATUS_TEXT = { pending: 'Pending', approved: 'Approved', rejected: 'Rejected' };

const initials = (name) =>
  name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');

const when = (t) => new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export default function LecturerRequests({ lecturers, busyId, onApprove, onReject, emptyText }) {
  const [rejecting, setRejecting] = useState(null); // id of the row whose reject box is open
  const [note, setNote] = useState('');

  if (lecturers.length === 0) return <p className="empty">{emptyText}</p>;

  const confirmReject = async (id) => {
    await onReject(id, note);
    setRejecting(null);
    setNote('');
  };

  return (
    <ul className="reqs">
      {lecturers.map((l) => (
        <li key={l.id} className={`req ${l.status}`}>
          <div className="req-avatar" aria-hidden="true">{initials(l.name)}</div>
          <div className="req-info">
            <div className="req-name">{l.name}</div>
            <div className="req-meta">
              <span className="req-id">{l.id}</span>
              <span>{l.email}</span>
              <span>Registered {when(l.registeredAt)}</span>
            </div>
            {l.status === 'rejected' && l.note && <div className="req-note">Reason: {l.note}</div>}
          </div>
          <span className={`pill status-${l.status}`}>{STATUS_TEXT[l.status]}</span>
          <div className="req-actions">
            {l.status !== 'approved' && (
              <button className="btn small-btn" disabled={busyId === l.id} onClick={() => onApprove(l.id)}>
                Approve
              </button>
            )}
            {l.status !== 'rejected' && (
              <button className="btn small-btn danger" disabled={busyId === l.id} onClick={() => { setRejecting(l.id); setNote(''); }}>
                {l.status === 'approved' ? 'Remove access' : 'Reject'}
              </button>
            )}
          </div>
          {rejecting === l.id && (
            <form className="req-reject" onSubmit={(e) => { e.preventDefault(); confirmReject(l.id); }}>
              <label htmlFor={`note-${l.id}`} className="small">Reason (optional, the lecturer will not see it, it is kept for the record)</label>
              <input id={`note-${l.id}`} value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} autoFocus />
              <div className="req-reject-actions">
                <button type="submit" className="btn small-btn danger" disabled={busyId === l.id}>Confirm</button>
                <button type="button" className="btn small-btn secondary" onClick={() => setRejecting(null)}>Cancel</button>
              </div>
            </form>
          )}
        </li>
      ))}
    </ul>
  );
}
