import { useState } from 'react';

// Two futures for one topic, drawn on the same axis:
//  - orange dashed: the student stops practising
//  - green solid:   the student follows the practice plan (dots mark the practice days)
// Colours checked for colour-blind readers, and the lines also differ by dash and by end label.

const W = 640;
const H = 320;
const PAD = { top: 22, right: 76, bottom: 44, left: 44 };
const INK = 'var(--text)';
const MUTED = 'var(--muted)';
const GRID = 'var(--track)';
const PLAN = 'var(--good)';
const NOTHING = 'var(--bad)';
const WEAK = 30;

const dateOf = (start, offset) => {
  const d = new Date(start);
  d.setDate(d.getDate() + offset);
  return d;
};
const fmtDay = (d) => d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
const fmtFull = (d) => d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });

export default function ForecastChart({ data, start, planLabel }) {
  const [active, setActive] = useState(null);
  const [showTable, setShowTable] = useState(false);

  const n = data.nothing.series.length; // days + 1
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const x = (i) => PAD.left + (i / (n - 1)) * innerW;
  const y = (v) => PAD.top + (1 - v / 100) * innerH;
  const line = (series) => series.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');

  const ticks = [0, 25, 50, 75, 100];
  const labelIdx = n <= 8 ? [...Array(n).keys()] : [0, Math.round((n - 1) / 3), Math.round(((n - 1) * 2) / 3), n - 1];
  const lastN = data.nothing.series[n - 1];
  const lastP = data.plan.series[n - 1];
  // keep the two end labels from sitting on top of each other
  const gap = Math.abs(y(lastN) - y(lastP));
  const nudge = gap < 16 ? (16 - gap) / 2 : 0;
  const pY = y(lastP) + (lastP >= lastN ? -nudge : nudge);
  const nY = y(lastN) + (lastP >= lastN ? nudge : -nudge);

  const nearest = (evt) => {
    const box = evt.currentTarget.getBoundingClientRect();
    const px = ((evt.clientX - box.left) / box.width) * W;
    const i = Math.round(((px - PAD.left) / innerW) * (n - 1));
    setActive(Math.max(0, Math.min(n - 1, i)));
  };

  const tipLeft = active === null ? 0 : `${(x(active) / W) * 100}%`;
  const practiceSet = new Set(data.practiceDays);

  return (
    <figure className="chart">
      <div className="chart-key" aria-hidden="true">
        <span><i className="key-plan" /> {planLabel}</span>
        <span><i className="key-nothing" /> If you do nothing</span>
      </div>

      <div className="chart-box">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Forecast to exam day. Doing nothing ends at ${lastN} percent. ${planLabel} ends at ${lastP} percent.`}
          onPointerMove={nearest}
          onPointerLeave={() => setActive(null)}
        >
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth="1" />
              <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fontSize="12" fill={MUTED}>{t}%</text>
            </g>
          ))}
          <line x1={PAD.left} x2={W - PAD.right} y1={y(WEAK)} y2={y(WEAK)} stroke="var(--weak)" strokeWidth="1" strokeDasharray="2 4" />
          <text x={PAD.left + 6} y={y(WEAK) + 15} fontSize="12" fill={MUTED} stroke="var(--panel)" strokeWidth="3" paintOrder="stroke">Weak below 30%</text>

          {labelIdx.map((i) => (
            <text key={i} x={x(i)} y={H - PAD.bottom + 20} textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'} fontSize="12" fill={MUTED}>
              {i === 0 ? 'Today' : i === n - 1 ? `Exam ${fmtDay(dateOf(start, i))}` : fmtDay(dateOf(start, i))}
            </text>
          ))}

          {active !== null && <line x1={x(active)} x2={x(active)} y1={PAD.top} y2={H - PAD.bottom} stroke={MUTED} strokeWidth="1" />}

          <path d={line(data.nothing.series)} fill="none" stroke={NOTHING} strokeWidth="2" strokeDasharray="6 5" />
          <path d={line(data.plan.series)} fill="none" stroke={PLAN} strokeWidth="2" />

          {data.practiceDays.map((d) => (
            <circle key={d} cx={x(d)} cy={y(data.plan.series[d])} r="3.5" fill={PLAN} stroke="var(--panel)" strokeWidth="1.5" />
          ))}

          <circle cx={x(n - 1)} cy={y(lastP)} r="5" fill={PLAN} stroke="var(--panel)" strokeWidth="2" />
          <circle cx={x(n - 1)} cy={y(lastN)} r="5" fill={NOTHING} stroke="var(--panel)" strokeWidth="2" />
          <text x={x(n - 1) + 10} y={pY + 4} fontSize="13" fontWeight="600" fill={INK}>{lastP}%</text>
          <text x={x(n - 1) + 10} y={nY + 4} fontSize="13" fontWeight="600" fill={INK}>{lastN}%</text>

          {active !== null && (
            <>
              <circle cx={x(active)} cy={y(data.plan.series[active])} r="6" fill={PLAN} stroke="var(--panel)" strokeWidth="2" />
              <circle cx={x(active)} cy={y(data.nothing.series[active])} r="6" fill={NOTHING} stroke="var(--panel)" strokeWidth="2" />
            </>
          )}
        </svg>

        {active !== null && (
          <div className="chart-tip" style={{ left: tipLeft }}>
            <div className="tip-line">{active === 0 ? 'Today' : fmtFull(dateOf(start, active))}</div>
            <div className="tip-row"><i className="swatch plan" /> <strong>{data.plan.series[active]}%</strong> with practice{practiceSet.has(active) ? ' (practice day)' : ''}</div>
            <div className="tip-row"><i className="swatch nothing" /> <strong>{data.nothing.series[active]}%</strong> doing nothing</div>
          </div>
        )}
      </div>

      <figcaption className="chart-note">
        Hover the chart to read any day. Dots on the green line are practice days.
        {' '}
        <button type="button" className="btn-link-dark" onClick={() => setShowTable(!showTable)}>
          {showTable ? 'Hide table' : 'Show as table'}
        </button>
      </figcaption>

      {showTable && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Day</th><th>Date</th><th>Doing nothing</th><th>With practice</th></tr>
            </thead>
            <tbody>
              {data.nothing.series.map((v, i) => (
                <tr key={i}>
                  <td>{i}</td>
                  <td>{fmtFull(dateOf(start, i))}</td>
                  <td>{v}%</td>
                  <td>{data.plan.series[i]}%{practiceSet.has(i) ? ' *' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="chart-note">* practice day</p>
        </div>
      )}
    </figure>
  );
}
