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
export default function ExamCalendar({ plan, onSave, savingModule, error }) {
  const start = new Date();
  const [cursor, setCursor] = useState({ y: start.getFullYear(), m: start.getMonth() });
  const [picked, setPicked] = useState(todayIso());

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
  const modules = plan && plan.modules ? plan.modules : [];
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

      <ul className="cal-mods" aria-label="Exam date for each module">
        {modules.map((m) => (
          <li key={m.code} className={m.passed ? 'done' : ''}>
            <span className="cal-mod-code">{m.code}</span>
            <span className="cal-mod-name" title={m.name}>{m.name}</span>
            <input
              type="date"
              aria-label={`${m.code} exam date`}
              value={m.examDate || ''}
              min={today}
              max={maxDate}
              disabled={savingModule === m.code}
              onChange={(e) => onSave(m.code, e.target.value || null)}
            />
            <span className="cal-mod-left">
              {m.passed ? 'Done' : m.daysLeft === null ? 'no date' : m.daysLeft === 0 ? 'today' : `${m.daysLeft} d`}
            </span>
          </li>
        ))}
      </ul>
      {error && <p className="error" role="alert">{error}</p>}

      <div className="cal-grid" role="grid" aria-label={`${MONTHS[cursor.m]} ${cursor.y}`}>
        {WEEK.map((w) => <div key={w} className="cal-dow" role="columnheader">{w}</div>)}
        {cells.map((date, i) => {
          if (!date) return <div key={`b${i}`} className="cal-cell blank" />;
          const info = byDate[date];
          const n = info ? info.items.length : 0;
          const cls = ['cal-cell'];
          if (date < today) cls.push('past');
          if (date === today) cls.push('today');
          if (info && info.exams && info.exams.length) cls.push('exam');
          if (info && info.finalRevision) cls.push('final');
          if (date === picked) cls.push('picked');
          return (
            <button
              key={date}
              type="button"
              className={cls.join(' ')}
              onClick={() => setPicked(date)}
              aria-label={`${nice(date)}${info && info.exams.length ? `, exam: ${info.exams.map((e) => e.module).join(' and ')}` : ''}${n ? `, ${n} planned ${n === 1 ? 'quiz' : 'quizzes'}` : ''}`}
              aria-pressed={date === picked}
            >
              <span className="cal-num">{Number(date.slice(8))}</span>
              {info && info.exams.length ? <span className="cal-exam">{info.exams[0].module}{info.exams.length > 1 ? ` +${info.exams.length - 1}` : ''}</span> : n > 0 && (
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
        {sel && sel.exams.map((e) => (
          <p key={e.module} className="cal-exam-line"><b>{e.module}</b> exam{e.name ? `: ${e.name}` : ''}. Rest well, and skim your weakest topics in the morning.</p>
        ))}
        {sel && sel.items.length > 0 ? (
          <ul>
            {sel.items.map((it) => (
              <li key={it.topic}>
                <span><b className="cal-code">{it.module}</b> {prettyTopic(it.topic)} <em>{KIND[it.kind]}</em></span>
                {picked === today && <Link to={`/c1/practice/${it.topic}`}>Practise</Link>}
              </li>
            ))}
          </ul>
        ) : (
          !(sel && sel.exams.length) && <p className="muted small">{sel ? 'A rest day. Nothing is due.' : 'Outside the planning window.'}</p>
        )}
      </div>

      {modules.some((m) => m.predicted && m.daysLeft !== null) && (
        <table className="cal-pred">
          <thead><tr><th>Module</th><th>Exam</th><th>With plan</th><th>If you stop</th></tr></thead>
          <tbody>
            {modules.filter((m) => m.predicted && m.daysLeft !== null).map((m) => (
              <tr key={m.code}><td>{m.code}</td><td>{m.daysLeft} d</td><td><b>{m.predicted.withPlan}%</b></td><td>{m.predicted.ifYouStop}%</td></tr>
            ))}
          </tbody>
        </table>
      )}

      {plan && plan.predicted && (() => {
        const withPlan = plan.predicted.withPlan;
        const stop = plan.predicted.ifYouStop;
        const gain = Math.max(0, withPlan - stop);
        const pct = (v) => `${Math.max(4, Math.min(100, v))}%`;
        return (
          <div className="cal-forecast" role="group" aria-label="Forecast by exam day">
            <p className="cf-title">Your forecast by exam day</p>
            <div className="cf-row">
              <div className="cf-box up">
                <span className="cf-lab">If you follow the plan</span>
                <strong>{withPlan}%</strong>
                <span className="cf-bar" aria-hidden="true"><i style={{ width: pct(withPlan) }} /></span>
              </div>
              <div className="cf-gain" aria-label={`${gain} points better`}>
                <span aria-hidden="true">{'\u2192'}</span>
                <b>+{gain}</b>
                <small>points</small>
              </div>
              <div className="cf-box down">
                <span className="cf-lab">If you stop</span>
                <strong>{stop}%</strong>
                <span className="cf-bar" aria-hidden="true"><i style={{ width: pct(stop) }} /></span>
              </div>
            </div>
            <p className="cf-foot">
              Average of your topics{plan.hasExamDates ? ' on each exam day.' : ' in 2 weeks (no exam date is set yet).'} Small daily quizzes keep what you know from fading.
            </p>
          </div>
        );
      })()}
    </section>
  );
}
