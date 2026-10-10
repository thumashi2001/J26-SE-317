import { prettyTopic } from '../utils/topics.js';
import './answerstyle.css';

const HEAD_ICON = { Steady: '✓', Careful: '✓', Rushing: '⚠', Struggling: '⚠', Guessing: '⚠' };
const TONE = { Steady: 'good', Careful: 'good', Rushing: 'warn', Struggling: 'warn', Guessing: 'bad' };

// Speed on one side, correctness on the other: where each topic sits.
const CELLS = [
  { key: 'quick_right', icon: '✓', title: 'Strong and quick', tone: 'good', tip: 'You know these. Try mixed or timed practice.' },
  { key: 'slow_right', icon: '⏱', title: 'Knows it, needs speed', tone: 'info', tip: 'Right but slow. Short quizzes build speed.' },
  { key: 'quick_wrong', icon: '⚠', title: 'Guessing or careless', tone: 'bad', tip: 'Slow down and read all four options.' },
  { key: 'slow_wrong', icon: '↻', title: 'Needs revision', tone: 'warn', tip: 'Read your notes first, then retry.' },
];

export default function AnswerStyle({ data }) {
  const ready = data.pattern !== 'Not enough yet';
  const topics = Object.entries(data.topics || {});
  const inCell = (key) => topics.filter(([, r]) => r.quadrant === key);
  const building = topics.filter(([, r]) => r.quadrant === null);

  return (
    <section className="panel answer-style" aria-labelledby="as-h">
      <h2 id="as-h">How you answer</h2>
      <div className={`as-headline ${ready ? TONE[data.pattern] : 'none'}`}>
        <span className="as-icon" aria-hidden="true">{ready ? HEAD_ICON[data.pattern] : '…'}</span>
        <div>
          <strong>{data.headline}</strong>
          <p>{ready ? data.advice : data.why}</p>
        </div>
      </div>

      {ready && (
        <div className="as-tiles">
          <div className="as-tile"><span>{data.medianSec} s</span><small>Typical time per question</small></div>
          <div className="as-tile"><span>{data.fast}</span><small>Very fast answers</small></div>
          <div className="as-tile"><span>{data.slow}</span><small>Very slow answers</small></div>
          <div className="as-tile"><span>{data.accuracy}%</span><small>Answers right</small></div>
        </div>
      )}

      <h3 className="as-sub">What your speed and answers say about each topic</h3>
      {topics.length === 0 ? (
        <p className="muted small">Answer at least 4 questions in a topic and it will appear here.</p>
      ) : (
        <>
          <div className="as-axes" aria-hidden="true">
            <span />
            <span>Quick</span>
            <span>Slower than your average</span>
          </div>
          <div className="as-grid">
            {CELLS.map((c, i) => {
              const list = inCell(c.key);
              return (
                <div key={c.key} className={`as-cell ${c.tone}${list.length ? '' : ' as-empty'}`} style={{ gridArea: ['a', 'b', 'c', 'd'][i] }}>
                  <div className="as-cell-title"><span aria-hidden="true">{c.icon}</span> {c.title}</div>
                  {list.length ? (
                    <>
                      <div className="as-chips">
                        {list.map(([t, r]) => (
                          <span key={t} className="as-chip" title={`${r.accuracy}% right, about ${r.medianSec} s`}>{prettyTopic(t)}</span>
                        ))}
                      </div>
                      <p className="as-tip">{c.tip}</p>
                    </>
                  ) : (
                    <p className="as-none">No topics here</p>
                  )}
                </div>
              );
            })}
            <div className="as-side as-row1" aria-hidden="true">Mostly right</div>
            <div className="as-side as-row2" aria-hidden="true">Mostly wrong</div>
          </div>
          {building.length > 0 && (
            <p className="muted small as-building">
              Still getting there: {building.map(([t]) => prettyTopic(t)).join(', ')}. A mix of right and wrong answers.
            </p>
          )}
        </>
      )}
    </section>
  );
}
