import { useMemo, useState } from 'react';
import { prettyTopic, topicModule } from '../../utils/topics.js';
import { TOPIC_INFO } from '../../utils/topicLabels.js';
import './heatmap.css';

// Mastery heat map for lecturers (Component 1).
// Rows are students (weakest first). Columns are topics, grouped under their module.
// Each cell is the student's estimated score now (after forgetting), coloured on one smooth scale:
// low is the "weak" colour, middle is "fair", high is "strong". Grey means not practised yet.
const ORDER = Object.keys(TOPIC_INFO);
const rank = (t) => (ORDER.includes(t) ? ORDER.indexOf(t) : ORDER.length);
const short = (s, n = 24) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

// 0 to 100 -> a colour on the app's own weak / fair / strong palette
export function heatColour(v) {
  if (v === null || v === undefined) return undefined;
  const x = Math.max(0, Math.min(100, v));
  return x < 50
    ? `color-mix(in srgb, var(--fair) ${Math.round((x / 50) * 100)}%, var(--weak))`
    : `color-mix(in srgb, var(--strong) ${Math.round(((x - 50) / 50) * 100)}%, var(--fair))`;
}

export default function MasteryHeatmap({ heatmap }) {
  const [hover, setHover] = useState(null); // { r, c } or null

  const view = useMemo(() => {
    if (!heatmap) return null;
    const topics = [...heatmap.topics].sort((a, b) => rank(a) - rank(b));
    const groups = [];
    topics.forEach((t) => {
      const code = topicModule(t) || 'Other';
      const last = groups[groups.length - 1];
      if (last && last.code === code) last.topics.push(t);
      else groups.push({ code, topics: [t] });
    });
    return { topics, groups };
  }, [heatmap]);

  if (!heatmap || !view || heatmap.rows.length === 0 || view.topics.length === 0) {
    return (
      <div className="hm">
        <h4>Mastery heat map</h4>
        <p className="muted small">Shown once students finish the diagnostic test.</p>
      </div>
    );
  }

  const { rows, topicAverage, totalStudents } = heatmap;
  const { topics, groups } = view;
  const firstOfGroup = new Set(groups.map((g) => g.topics[0]));
  const readout = hover
    ? (() => {
        const row = hover.r === 'avg' ? null : rows[hover.r];
        const t = topics[hover.c];
        const v = row ? row.scores[t] : topicAverage[t];
        return `${row ? row.name : 'Class average'}, ${prettyTopic(t)}: ${v === null || v === undefined ? 'not practised yet' : `${v}%`}`;
      })()
    : 'Hover a square to see the student, the topic and the score.';

  return (
    <div className="hm">
      <div className="hm-top">
        <div>
          <h4>Mastery heat map</h4>
          <p className="muted small">
            Each row is a student and each column is a topic, grouped by module. A column that is mostly the weak colour means the class is struggling with that topic.
            {totalStudents > rows.length && ` Showing the ${rows.length} weakest of ${totalStudents} students.`}
          </p>
        </div>
        <div className="hm-scale" aria-label="Colour scale from 0 to 100 percent">
          <div className="hm-bar" />
          <div className="hm-ticks"><span>0%</span><span>50%</span><span>100%</span></div>
          <div className="hm-na"><i />Not practised</div>
        </div>
      </div>

      <p className="hm-read" aria-live="polite">{readout}</p>

      <div className="hm-scroll" role="region" aria-label="Mastery heat map, students by topic" tabIndex={0} onMouseLeave={() => setHover(null)}>
        <table className="hm-table">
          <thead>
            <tr className="hm-mods">
              <th className="hm-name hm-corner" rowSpan={2}>Student<small>average</small></th>
              {groups.map((g) => {
                const name = TOPIC_INFO[g.topics[0]]?.moduleName || g.code;
                return <th key={g.code} colSpan={g.topics.length} className="hm-mod" title={name}>{g.code}</th>;
              })}
            </tr>
            <tr>
              {topics.map((t, c) => (
                <th key={t} className={`hm-topic${firstOfGroup.has(t) ? ' first' : ''}${hover && hover.c === c ? ' on' : ''}`} title={prettyTopic(t)}>
                  <span>{short(prettyTopic(t))}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="hm-avg">
              <th className="hm-name">Class average</th>
              {topics.map((t, c) => (
                <td
                  key={t}
                  className={`${firstOfGroup.has(t) ? 'first ' : ''}${topicAverage[t] === null ? 'none' : ''}`}
                  style={{ background: heatColour(topicAverage[t]) }}
                  onMouseEnter={() => setHover({ r: 'avg', c })}
                >
                  {topicAverage[t] ?? ''}
                </td>
              ))}
            </tr>
            {rows.map((r, i) => (
              <tr key={`${r.name}-${i}`} className={hover && hover.r === i ? 'on' : ''}>
                <th className="hm-name">
                  <span className="hm-who">{r.name}</span>
                  <b style={{ background: heatColour(r.average) }}>{r.average}</b>
                </th>
                {topics.map((t, c) => (
                  <td
                    key={t}
                    className={`${firstOfGroup.has(t) ? 'first ' : ''}${r.scores[t] === null ? 'none' : ''}${hover && (hover.c === c || hover.r === i) ? ' lit' : ''}`}
                    style={{ background: heatColour(r.scores[t]) }}
                    onMouseEnter={() => setHover({ r: i, c })}
                  >
                    <span className="sr-only">{r.scores[t] ?? 'not practised'}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
