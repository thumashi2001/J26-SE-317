import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { prettyTopic } from '../utils/topics.js';
import './plan.css';

const WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const iso = (y, m, d) => `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
const todayIso = () => {
  const n = new Date();
  return iso(n.getFullYear(), n.getMonth(), n.getDate());
};
const nice = (s) => {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
};
const KIND = { today: 'Today', review: 'Review', final: 'Final revision' };

// A month calendar with the exam date and the planned practice days.
export default function ExamCalendar({ plan, onSave, saving, error }) {
  const start = new Date();
  const [cursor, setCursor] = useState({ y: start.getFullYear(), m: start.getMonth() });
  const [picked, setPicked] = useState(todayIso());
  const [draft, setDraft] = useState(plan && plan.examDate ? plan.examDate : '');

  const byDate = useMemo(() => {
    const map = {};
    ((plan && plan.days) || []).forEach((d) => { map[d.date] = d; });
    return map;
  }, [plan]);

  const first = new Date(cursor.y, cursor.m, 1);
  const lead = (first.getDay() + 6) % 7; // Monday first
  const count = new Date(cursor.y, cursor.m + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < lead; i++) cells.push(null);
  for (let d = 1; d <= count; d++) cells.push(iso(cursor.y, cursor.m, d));

  const move = (delta) => {
    const d = new Date(cursor.y, cursor.m + delta, 1);
    setCursor({ y: d.getFullYear(), m: d.getMonth() });
  };
  const today = todayIso();
  const sel = byDate[picked];
  const examDate = plan ? plan.examDate : null;
  const maxDate = iso(start.getFullYear() + 1, start.getMonth(), start.getDate());

  return (
    <section className="panel cal-card" aria-labelledby="cal-title">
      <header className="cal-head">
        <h2 id="cal-title">Exam calendar</h2>
        <div className="cal-nav">
          <button type="button" className="cal-btn" onClick={() => move(-1)} aria-label="Previous month">&lsaquo;</button>
          <strong aria-live="polite">{MONTHS[cursor.m]} {cursor.y}</strong>
          <button type="button" className="cal-btn" onClick={() => move(1)} aria-label="Next month">&rsaquo;</button>
        </div>
      </header>

      <form className="cal-set" onSubmit={(e) => { e.preventDefault(); onSave(draft || null); }}>
        <label htmlFor="exam-date-input">Exam date</label>
        <input id="exam-date-input" type="date" value={draft} min={today} max={maxDate} onChange={(e) => setDraft(e.target.value)} />
        <button className="btn" type="submit" disabled={saving || draft === (examDate || '')}>{saving ? 'Saving...' : 'Save'}</button>
        {examDate && <button type="button" className="btn secondary" disabled={saving} onClick={() => { setDraft(''); onSave(null); }}>Clear</button>}
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      {plan && plan.examPassed && <p className="plan-note">That exam date has passed. Pick a new one.</p>}

      <div className="cal-grid" role="grid" aria-label={`${MONTHS[cursor.m]} ${cursor.y}`}>
        {WEEK.map((w) => <div key={w} className="cal-dow" role="columnheader">{w}</div>)}
        {cells.map((date, i) => {
          if (!date) return <div key={`b${i}`} className="cal-cell blank" />;
          const info = byDate[date];
          const n = info ? info.items.length : 0;
          const cls = ['cal-cell'];
          if (date < today) cls.push('past');
          if (date === today) cls.push('today');
          if (date === examDate) cls.push('exam');
          if (info && info.finalRevision) cls.push('final');
          if (date === picked) cls.push('picked');
          return (
            <button
              key={date}
              type="button"
              className={cls.join(' ')}
              onClick={() => setPicked(date)}
              aria-label={`${nice(date)}${date === examDate ? ', exam day' : ''}${n ? `, ${n} planned ${n === 1 ? 'quiz' : 'quizzes'}` : ''}`}
              aria-pressed={date === picked}
            >
              <span className="cal-num">{Number(date.slice(8))}</span>
              {date === examDate ? <span className="cal-exam">Exam</span> : n > 0 && (
                <span className="cal-dots" aria-hidden="true">{Array.from({ length: Math.min(n, 4) }, (_, k) => <i key={k} />)}</span>
              )}
            </button>
          );
        })}
      </div>

      <div className="cal-key" aria-hidden="true">
        <span><i className="k-dot" /> planned quiz</span>
        <span><i className="k-final" /> final revision</span>
        <span><i className="k-exam" /> exam day</span>
      </div>

      <div className="cal-day">
        <strong>{nice(picked)}</strong>
        {picked === examDate && <p className="muted small">Exam day. Rest well, and skim your weakest topics in the morning.</p>}
        {sel && sel.items.length > 0 ? (
          <ul>
            {sel.items.map((it) => (
              <li key={it.topic}>
                <span>{prettyTopic(it.topic)} <em>{KIND[it.kind]}</em></span>
                {picked === today && <Link to={`/c1/practice/${it.topic}`}>Practise</Link>}
              </li>
            ))}
          </ul>
        ) : (
          picked !== examDate && <p className="muted small">{sel ? 'A rest day. Nothing is due.' : 'Outside the planning window.'}</p>
        )}
      </div>

      {plan && plan.predicted && (
        <p className="cal-predict">
          If you follow this plan your topics average about <strong>{plan.predicted.withPlan}%</strong> {examDate ? 'on exam day' : 'in 2 weeks'}.
          If you stop, about <strong>{plan.predicted.ifYouStop}%</strong>.
        </p>
      )}
    </section>
  );
}
