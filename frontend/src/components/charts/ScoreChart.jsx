import { useState } from 'react';

// Line chart of one topic's score over time.
//  - solid line: the score right after each answer
//  - dashed line: the score fading between answers (straight line between the two values)
// Points are spaced evenly, not by date, so answers logged minutes apart stay readable.
// The exact time of every point is in the tooltip and the table view.

const W = 640;
const H = 300;
const PAD = { top: 20, right: 28, bottom: 44, left: 44 };
const INK = '#13222f';
const MUTED = '#5a6b7b';
const GRID = '#e3e9ef';
const LINE = '#087a63';
const WEAK = 30;

const fmtDate = (t) =>
  new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
const fmtFull = (t) =>
  new Date(t).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

export const SOURCE_LABEL = {
  diagnostic: 'Diagnostic test',
  quiz_answer: 'Practice answer',
  current: 'Current score',
};

export default function ScoreChart({ points }) {
  const [active, setActive] = useState(null);
  const [showTable, setShowTable] = useState(false);

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const x = (i) => PAD.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);
  const y = (v) => PAD.top + (1 - v / 100) * innerH;

  // solid segments: straight up or down to each new score, dashed: fading between answers
  const fade = [];
  const solid = [];
  points.forEach((p, i) => {
    if (i === 0) return;
    const fadedTo = p.afterForgetting ?? points[i - 1].score;
    fade.push(`M${x(i - 1)},${y(points[i - 1].score)} L${x(i)},${y(fadedTo)}`);
    solid.push(`M${x(i)},${y(fadedTo)} L${x(i)},${y(p.score)}`);
  });

  const ticks = [0, 25, 50, 75, 100];
  const labelIdx = points.length <= 4 ? points.map((_, i) => i) : [0, Math.floor((points.length - 1) / 2), points.length - 1];
  const last = points[points.length - 1];

  const nearest = (evt) => {
    const box = evt.currentTarget.getBoundingClientRect();
    const px = ((evt.clientX - box.left) / box.width) * W;
    let best = 0;
    points.forEach((_, i) => {
      if (Math.abs(x(i) - px) < Math.abs(x(best) - px)) best = i;
    });
    setActive(best);
  };

  const a = active === null ? null : points[active];
  const prev = active > 0 ? points[active - 1] : null;
  const tipLeft = a ? `${(x(active) / W) * 100}%` : 0;

  return (
    <figure className="chart">
      <div className="chart-key" aria-hidden="true">
        <span><i className="key-solid" /> Score after an answer</span>
        <span><i className="key-dashed" /> Fading while not practised</span>
      </div>

      <div className="chart-box">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-label={`Score history. ${points.length} ${points.length === 1 ? 'point' : 'points'}, latest score ${last.score} percent.`}
          onPointerMove={nearest}
          onPointerLeave={() => setActive(null)}
        >
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth="1" />
              <text x={PAD.left - 8} y={y(t) + 4} textAnchor="end" fontSize="12" fill={MUTED}>{t}%</text>
            </g>
          ))}
          <line x1={PAD.left} x2={W - PAD.right} y1={y(WEAK)} y2={y(WEAK)} stroke="#d6453d" strokeWidth="1" strokeDasharray="2 4" />
          <text x={PAD.left + 6} y={y(WEAK) + 15} textAnchor="start" fontSize="12" fill={MUTED}>Weak below 30%</text>

          {labelIdx.map((i) => (
            <text key={i} x={x(i)} y={H - PAD.bottom + 20} textAnchor="middle" fontSize="12" fill={MUTED}>
              {fmtDate(points[i].timestamp)}
            </text>
          ))}

          {active !== null && <line x1={x(active)} x2={x(active)} y1={PAD.top} y2={H - PAD.bottom} stroke={MUTED} strokeWidth="1" />}

          <path d={fade.join(' ')} fill="none" stroke={LINE} strokeWidth="2" strokeDasharray="5 5" opacity="0.7" />
          <path d={solid.join(' ')} fill="none" stroke={LINE} strokeWidth="2" />

          {points.map((p, i) => (
            <g key={p.version}>
              <circle cx={x(i)} cy={y(p.score)} r={active === i ? 7 : 5} fill={LINE} stroke="#fff" strokeWidth="2" />
              <circle
                cx={x(i)}
                cy={y(p.score)}
                r="14"
                fill="transparent"
                tabIndex={0}
                role="img"
                aria-label={`${SOURCE_LABEL[p.source] || 'Update'}, ${fmtFull(p.timestamp)}, score ${p.score} percent`}
                onFocus={() => setActive(i)}
                onBlur={() => setActive(null)}
              />
            </g>
          ))}

          <text x={Math.min(x(points.length - 1), W - PAD.right - 4)} y={y(last.score) - 12} textAnchor="end" fontSize="13" fontWeight="600" fill={INK}>
            {last.score}%
          </text>
        </svg>

        {a && (
          <div className="chart-tip" style={{ left: tipLeft }}>
            <div className="tip-value">{a.score}%</div>
            <div className="tip-line">{SOURCE_LABEL[a.source] || 'Update'}</div>
            <div className="tip-line">{fmtFull(a.timestamp)}</div>
            {prev && a.afterForgetting != null && (
              <div className="tip-line">
                Was {a.scoreBefore}%, faded to {a.afterForgetting}%, then {a.score >= a.afterForgetting ? 'rose' : 'fell'} to {a.score}%
              </div>
            )}
          </div>
        )}
      </div>

      <figcaption className="chart-note">
        Points are spaced evenly, not by date. Hover or tab to a point for its exact time.
        {' '}
        <button type="button" className="btn-link-dark" onClick={() => setShowTable(!showTable)}>
          {showTable ? 'Hide table' : 'Show as table'}
        </button>
      </figcaption>

      {showTable && (
        <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr><th>#</th><th>When</th><th>What happened</th><th>Before</th><th>After fading</th><th>Score</th></tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.version}>
                <td>{p.version}</td>
                <td>{fmtFull(p.timestamp)}</td>
                <td>{SOURCE_LABEL[p.source] || 'Update'}</td>
                <td>{p.scoreBefore ?? '-'}</td>
                <td>{p.afterForgetting ?? '-'}</td>
                <td>{p.score}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </figure>
  );
}
