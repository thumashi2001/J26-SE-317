import { useEffect, useRef, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { updateProfile, saveAvatar, changePassword } from '../services/authApi.js';
import { getLevel } from '../services/c1Api.js';
import { prettyTopic } from '../utils/topics.js';
import Avatar from '../components/ui/Avatar.jsx';
import StarRating from '../components/ui/StarRating.jsx';
import './profile.css';

// My profile: the same page for students, lecturers and the administrator.
// Components do not need to change anything here. Only the ID is locked.

const ROLE_TEXT = { student: 'Student', lecturer: 'Lecturer', admin: 'Administrator' };
const SEM_TEXT = { Y3S1: 'Year 3, Semester 1', Y3S2: 'Year 3, Semester 2' };
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const clock = (sec) => {
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}` : `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
};
const minutes = (sec) => (sec < 60 ? `${Math.round(sec)} s` : sec < 3600 ? `${Math.round(sec / 60)} min` : `${Math.floor(sec / 3600)} h ${Math.round((sec % 3600) / 60)} min`);

// Shrink a chosen picture to a small round-friendly square before it is sent.
function shrink(file, px = 192) {
  return new Promise((resolve, reject) => {
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) return reject(new Error('Please choose a PNG, JPG or WebP picture'));
    if (file.size > 8 * 1024 * 1024) return reject(new Error('That picture is too large. Choose one under 8 MB'));
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const side = Math.min(img.width, img.height);
      const canvas = document.createElement('canvas');
      canvas.width = px;
      canvas.height = px;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, px, px);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL('image/jpeg', 0.82));
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('That file could not be read as a picture'));
    };
    img.src = url;
  });
}

function GoalRing({ done, goal }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pct = Math.min(1, goal ? done / goal : 0);
  return (
    <svg viewBox="0 0 130 130" className="goal-ring" role="img" aria-label={`${Math.round(pct * 100)} percent of today's goal`}>
      <circle cx="65" cy="65" r={r} className="trk" />
      <circle cx="65" cy="65" r={r} className="fil" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 65 65)" />
      <text x="65" y="62" textAnchor="middle" className="g1">{pct >= 1 ? 'Goal' : clock(Math.max(0, goal - done))}</text>
      <text x="65" y="82" textAnchor="middle" className="g2">{pct >= 1 ? 'reached' : 'left today'}</text>
    </svg>
  );
}

export default function ProfilePage() {
  const { user, profile, setProfile, diagnosticDone } = useAuth();
  const { usage, todaySeconds } = useOutletContext() || {};
  const fileRef = useRef(null);
  const [form, setForm] = useState({ name: '', email: '' });
  const [info, setInfo] = useState({ type: '', text: '' });
  const [saving, setSaving] = useState(false);
  const [picBusy, setPicBusy] = useState(false);
  const [picMsg, setPicMsg] = useState({ type: '', text: '' });
  const [pw, setPw] = useState({ current: '', next: '', again: '' });
  const [pwMsg, setPwMsg] = useState({ type: '', text: '' });
  const [showPw, setShowPw] = useState(false);
  const [editPw, setEditPw] = useState(false);
  const [level, setLevel] = useState(null);
  const [levelErr, setLevelErr] = useState('');

  const isStudent = user.role === 'student';

  useEffect(() => {
    if (profile) setForm({ name: profile.name || '', email: profile.email || '' });
  }, [profile]);

  useEffect(() => {
    if (!isStudent) return undefined;
    let alive = true;
    getLevel(user.student_id)
      .then((l) => alive && setLevel(l))
      .catch((e) => alive && setLevelErr(e.message));
    return () => {
      alive = false;
    };
  }, [isStudent, user.student_id, diagnosticDone]);

  if (!profile) return <p className="muted">Loading your profile...</p>;

  const dirty = form.name.trim() !== profile.name || form.email.trim().toLowerCase() !== profile.email;

  const onSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setInfo({ type: '', text: '' });
    try {
      const r = await updateProfile({ name: form.name, email: form.email });
      setProfile(r.profile);
      try {
        const u = JSON.parse(sessionStorage.getItem('user') || 'null');
        if (u) sessionStorage.setItem('user', JSON.stringify({ ...u, name: r.profile.name, email: r.profile.email }));
      } catch {
        /* ignore */
      }
      setInfo({ type: 'ok', text: 'Your details were saved.' });
    } catch (err) {
      setInfo({ type: 'err', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const onPick = async (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = '';
    if (!file) return;
    setPicBusy(true);
    setPicMsg({ type: '', text: '' });
    try {
      const image = await shrink(file);
      const r = await saveAvatar(image);
      setProfile(r.profile);
      setPicMsg({ type: 'ok', text: 'Your picture was updated.' });
    } catch (err) {
      setPicMsg({ type: 'err', text: err.message });
    } finally {
      setPicBusy(false);
    }
  };

  const onRemove = async () => {
    setPicBusy(true);
    setPicMsg({ type: '', text: '' });
    try {
      const r = await saveAvatar(null);
      setProfile(r.profile);
      setPicMsg({ type: 'ok', text: 'Your picture was removed.' });
    } catch (err) {
      setPicMsg({ type: 'err', text: err.message });
    } finally {
      setPicBusy(false);
    }
  };

  const onPassword = async (e) => {
    e.preventDefault();
    setPwMsg({ type: '', text: '' });
    if (pw.next !== pw.again) return setPwMsg({ type: 'err', text: 'The two new passwords do not match' });
    try {
      await changePassword(pw.current, pw.next);
      setPw({ current: '', next: '', again: '' });
      setPwMsg({ type: 'ok', text: 'Your password was changed.' });
      setEditPw(false);
    } catch (err) {
      setPwMsg({ type: 'err', text: err.message });
    }
  };

  const joined = profile.joined ? new Date(profile.joined).toLocaleDateString('en-GB', { month: 'long', year: 'numeric' }) : null;
  const today = todaySeconds ?? (usage ? usage.todaySeconds : 0);
  const goal = usage ? usage.goalSeconds : 1800;
  const weekMax = usage ? Math.max(goal, ...usage.week.map((d) => d.seconds)) : goal;

  return (
    <div className="pf">
      <section className="pf-hero">
        <div className="pf-photo">
          <Avatar name={profile.name} src={profile.avatar} size={132} />
          <button type="button" className="pf-cam" onClick={() => fileRef.current && fileRef.current.click()} disabled={picBusy} aria-label="Change profile picture" title="Change profile picture">
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M9 4l-1.8 2H5a2 2 0 00-2 2v10a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-2.2L15 4H9zm3 4.5A4.5 4.5 0 1112 17a4.5 4.5 0 010-9zm0 2A2.5 2.5 0 1012 15a2.5 2.5 0 000-5z" /></svg>
          </button>
          <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={onPick} />
        </div>
        <div className="pf-who">
          <div className="pf-chips">
            <span className="pf-chip">{ROLE_TEXT[user.role] || user.role}</span>
            {profile.semester && <span className="pf-chip">{SEM_TEXT[profile.semester] || profile.semester}</span>}
            {joined && <span className="pf-chip soft">Joined {joined}</span>}
          </div>
          <h1>{profile.name}</h1>
          <p className="pf-id"><span aria-hidden="true">&#128274;</span> {profile.id}</p>
          <div className="pf-photo-actions">
            {picBusy && <span className="pf-ok">Saving...</span>}
            {profile.avatar && <button type="button" className="pf-btn ghost" onClick={onRemove} disabled={picBusy}>Remove picture</button>}
            {picMsg.text && <span className={picMsg.type === 'ok' ? 'pf-ok' : 'pf-err'} role="status">{picMsg.text}</span>}
          </div>
        </div>
      </section>

      <div className="pf-grid">
        {isStudent && (
          <section className="pf-card level">
            <h2>Knowledge level</h2>
            {level ? (
              <>
                <div className="lv-stars"><StarRating value={level.stars} size={40} label={`${level.stars} out of 5 stars`} /></div>
                <p className="lv-label"><strong>{level.label}</strong><span>{level.stars} of 5 stars, {level.score}% average</span></p>
                <div className="lv-bar" aria-hidden="true"><span style={{ width: `${Math.max(3, level.score)}%` }} /></div>
                <p className="muted small">
                  {level.nextLevelAt === null ? 'You are at the top level. Keep your topics fresh.' : `${level.nextLevelAt - level.score} more points on average moves you up a star.`}
                </p>
                <p className="muted small">
                  This follows your digital twin, so it changes when your twin changes. Strongest topic: <b>{level.strongest ? prettyTopic(level.strongest) : 'none yet'}</b>.
                </p>
                <Link className="pf-link" to="/c1/dashboard">See my learning state</Link>
              </>
            ) : levelErr ? (
              <>
                <div className="lv-stars"><StarRating value={0} size={40} /></div>
                <p className="muted">{levelErr.includes('diagnostic') ? 'Take the diagnostic test and your stars appear here.' : levelErr}</p>
                {levelErr.includes('diagnostic') && <Link className="pf-link" to="/c1/diagnostic">Start the diagnostic test</Link>}
              </>
            ) : (
              <p className="muted">Reading your twin...</p>
            )}
          </section>
        )}

        <section className="pf-card usage">
          <h2>Time on AdaptiveLearnSE</h2>
          <div className="us-main">
            <GoalRing done={today} goal={goal} />
            <div className="us-text">
              <p className="us-big">{clock(today)}</p>
              <p className="muted small">spent today. Goal: {Math.round(goal / 60)} minutes a day.</p>
              {usage && (
                <ul className="us-facts">
                  <li><b>{usage.streakDays}</b> day streak</li>
                  <li><b>{usage.daysUsed}</b> days used</li>
                  <li><b>{minutes(usage.totalSeconds + (today - usage.todaySeconds))}</b> in total</li>
                </ul>
              )}
            </div>
          </div>
          {usage && (
            <div className="us-week" aria-label="Last 7 days">
              {usage.week.map((d) => {
                const sec = d.today ? today : d.seconds;
                return (
                  <div key={d.date} className={'us-day' + (d.today ? ' now' : '')} title={`${d.date}: ${minutes(sec)}`}>
                    <span className="us-bar"><i style={{ height: `${Math.max(4, (sec / weekMax) * 100)}%` }} className={sec >= goal ? 'hit' : ''} /></span>
                    <span className="us-lab">{DAYS[new Date(d.date + 'T00:00:00').getDay()]}</span>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <form className="pf-card" onSubmit={onSave}>
          <h2>Account details</h2>
          <label htmlFor="pf-name">Full name</label>
          <input id="pf-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={80} required />

          <label htmlFor="pf-id">{isStudent ? 'Student ID' : user.role === 'admin' ? 'Admin ID' : 'Lecturer ID'}</label>
          <div className="pf-locked">
            <input id="pf-id" value={profile.id} disabled readOnly aria-describedby="pf-id-note" />
            <span aria-hidden="true">&#128274;</span>
          </div>
          <span id="pf-id-note" className="hint">Your ID cannot be changed.</span>

          <label htmlFor="pf-email">Email</label>
          <input id="pf-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />

          {isStudent && (
            <>
              <label htmlFor="pf-sem">Semester</label>
              <input id="pf-sem" value={SEM_TEXT[profile.semester] || profile.semester || ''} disabled readOnly aria-describedby="pf-sem-note" />
              <span id="pf-sem-note" className="hint">Your semester sets your diagnostic questions and topics. Ask the administrator if it is wrong.</span>
            </>
          )}

          {info.text && <p className={info.type === 'ok' ? 'pf-ok' : 'pf-err'} role="status">{info.text}</p>}
          <button className="btn" type="submit" disabled={saving || !dirty}>{saving ? 'Saving...' : 'Save changes'}</button>
        </form>

        <section className="pf-card">
          <h2>Password</h2>
          <div className="pf-pwrow">
            <span className="pf-dots" aria-label="Hidden password">&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;</span>
            {!editPw && <button type="button" className="pf-btn ghost" onClick={() => { setEditPw(true); setPwMsg({ type: '', text: '' }); }}>Change</button>}
          </div>
          {!editPw && pwMsg.type === 'ok' && <p className="pf-ok" role="status">{pwMsg.text}</p>}
          {editPw && (
          <form className="pf-pwform" onSubmit={onPassword}>
            <label htmlFor="pf-cur">Current password</label>
            <input id="pf-cur" type={showPw ? 'text' : 'password'} value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} autoComplete="current-password" required />
            <label htmlFor="pf-new">New password</label>
            <input id="pf-new" type={showPw ? 'text' : 'password'} minLength={8} value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} autoComplete="new-password" required />
            <label htmlFor="pf-again">Repeat the new password</label>
            <input id="pf-again" type={showPw ? 'text' : 'password'} minLength={8} value={pw.again} onChange={(e) => setPw({ ...pw, again: e.target.value })} autoComplete="new-password" required />
            <label className="check"><input type="checkbox" checked={showPw} onChange={(e) => setShowPw(e.target.checked)} /> Show passwords</label>
            {pwMsg.type === 'err' && <p className="pf-err" role="status">{pwMsg.text}</p>}
            <div className="pf-row-btns"><button className="btn" type="submit" disabled={!pw.current || !pw.next || !pw.again}>Save new password</button><button type="button" className="pf-btn ghost" onClick={() => { setEditPw(false); setPw({ current: '', next: '', again: '' }); setPwMsg({ type: '', text: '' }); }}>Cancel</button></div>
          </form>
          )}
        </section>
      </div>
    </div>
  );
}
