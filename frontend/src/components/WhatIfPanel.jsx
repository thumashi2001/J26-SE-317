import './whatif.css';
import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { getForecast } from '../services/c1Api.js';
import ForecastChart from './charts/ForecastChart.jsx';

const DAY_MS = 24 * 60 * 60 * 1000;
const MAX_DAYS = 120;
const DEFAULT_DAYS = 21;

const startOfToday = () => {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
};
const toInputDate = (d) => {
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
};
const fmt = (d) => d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export default function WhatIfPanel({ topic }) {
  const { user } = useAuth();
  const today = useMemo(startOfToday, []);
  const minDate = useMemo(() => toInputDate(new Date(today.getTime() + DAY_MS)), [today]);
  const maxDate = useMemo(() => toInputDate(new Date(today.getTime() + MAX_DAYS * DAY_MS)), [today]);

  const [examDate, setExamDate] = useState(toInputDate(new Date(today.getTime() + DEFAULT_DAYS * DAY_MS)));
  const [perWeek, setPerWeek] = useState(3);
  const [state, setState] = useState({ status: 'loading' });

  // days until the chosen exam date, or null while the date field is empty or out of range
  const days = useMemo(() => {
    if (!examDate) return null;
    const [y, m, d] = examDate.split('-').map(Number);
    const n = Math.round((new Date(y, m - 1, d) - today) / DAY_MS);
    return n >= 1 && n <= MAX_DAYS ? n : null;
  }, [examDate, today]);

  useEffect(() => {
    if (days === null) return undefined;
    let alive = true;
    setState((s) => (s.status === 'ready' ? { ...s, busy: true } : { status: 'loading' }));
    const timer = setTimeout(() => {
      getForecast(user.student_id, topic, { days, perWeek })
        .then((data) => alive && setState({ status: 'ready', data }))
        .catch((err) => alive && setState({ status: 'error', message: err.message }));
    }, 250);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [user.student_id, topic, days, perWeek]);

  const data = state.status === 'ready' ? state.data : null;
  const dayDate = (offset) => new Date(today.getTime() + offset * DAY_MS);
  const planLabel = perWeek === 0 ? 'If you do not practise' : `If you practise ${perWeek} ${perWeek === 1 ? 'time' : 'times'} a week`;

  return (
    <section className="panel whatif" aria-labelledby="whatif-title">
      <p className="muted small">
        See where this topic could be on exam day. The forecast uses the same forgetting and learning rules as your twin.
      </p>

      <div className="whatif-controls">
        <div>
          <label htmlFor="exam-date">Exam date</label>
          <input id="exam-date" type="date" value={examDate} min={minDate} max={maxDate} onChange={(e) => setExamDate(e.target.value)} />
        </div>
        <div className="slider">
          <label htmlFor="per-week">
            Practice per week: <strong>{perWeek === 0 ? 'none' : `${perWeek} ${perWeek === 1 ? 'time' : 'times'}`}</strong>
          </label>
          <input id="per-week" type="range" min="0" max="7" step="1" value={perWeek} onChange={(e) => setPerWeek(Number(e.target.value))} />
          <div className="slider-scale" aria-hidden="true"><span>0</span><span>7</span></div>
        </div>
      </div>

      {days === null && <p className="error" role="alert">Pick an exam date between tomorrow and {fmt(dayDate(MAX_DAYS))}.</p>}
      {state.status === 'loading' && days !== null && <p className="muted">Working out the forecast...</p>}
      {state.status === 'error' && days !== null && <p className="error" role="alert">{state.message}</p>}

      {data && days !== null && (
        <div className={state.busy ? 'whatif-body busy' : 'whatif-body'}>
          <div className="outcomes">
            <div className="outcome nothing">
              <div className="outcome-label">If you do nothing</div>
              <div className="outcome-value">{data.nothing.examDayScore}%</div>
              <div className="outcome-note">
                {data.nothing.firstWeakDay === null
                  ? 'Stays above the weak line.'
                  : data.nothing.firstWeakDay === 0
                  ? 'Already in the weak zone.'
                  : `Falls below 30% on ${fmt(dayDate(data.nothing.firstWeakDay))}.`}
              </div>
            </div>
            <div className="outcome plan">
              <div className="outcome-label">{planLabel}</div>
              <div className="outcome-value">{data.plan.examDayScore}%</div>
              <div className="outcome-note">
                {data.gain > 0 ? `${data.gain} points higher on exam day.` : 'Same as doing nothing.'}
                {data.plan.firstWeakDay !== null && data.plan.firstWeakDay > 0 ? ` Still dips below 30% on ${fmt(dayDate(data.plan.firstWeakDay))}.` : ''}
              </div>
            </div>
          </div>

          <ForecastChart data={data} start={today} planLabel={planLabel} />

          <p className="chart-note">
            Assumes you answer about {Math.round(data.assumedAccuracy * 100)}% of practice questions correctly. This is a forecast, not a promise.
          </p>
        </div>
      )}
    </section>
  );
}
