import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { startPractice, answerPractice } from '../../services/c1Api.js';
import { prettyTopic } from '../../utils/topics.js';
import './practice.css';

const LETTERS = ['A', 'B', 'C', 'D'];

// ["B"] -> "B", ["A","C"] -> "A and C", ["B","C","D"] -> "B, C and D"
const joinLetters = (l) => (l.length <= 1 ? l.join('') : `${l.slice(0, -1).join(', ')} and ${l[l.length - 1]}`);

export default function PracticePage() {
  const { topic } = useParams();
  const [state, setState] = useState({ status: 'loading' });
  const [session, setSession] = useState(null);
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState([]);
  const [feedback, setFeedback] = useState(null); // set after the student checks an answer
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const shownAt = useRef(Date.now());
  const startedFor = useRef(null);

  const begin = useCallback(async () => {
    setState({ status: 'loading' });
    setFeedback(null);
    setPicked([]);
    setError('');
    try {
      const s = await startPractice(topic);
      setSession(s);
      const firstOpen = s.questions.findIndex((q) => !q.answered);
      setIndex(firstOpen === -1 ? s.questions.length : firstOpen);
      shownAt.current = Date.now();
      setState({ status: 'ready' });
    } catch (err) {
      setState({ status: 'error', message: err.message });
    }
  }, [topic]);

  // Start once per topic. React's development mode runs effects twice, which would start two sessions.
  useEffect(() => {
    if (startedFor.current === topic) return;
    startedFor.current = topic;
    begin();
  }, [topic, begin]);

  const back = <Link to={`/c1/topic/${topic}`} className="btn secondary back">&larr; Back to {prettyTopic(topic)}</Link>;

  if (state.status === 'loading') return <p className="muted">Getting your questions...</p>;
  if (state.status === 'error')
    return (
      <div>
        {back}
        <div className="panel">
          <h2>The quiz did not start</h2>
          <p className="error">{state.message}</p>
        </div>
      </div>
    );

  const total = session.questions.length;
  const finished = index >= total;
  const q = finished ? null : session.questions[index];
  const locked = !!feedback;

  const toggle = (i) => {
    if (locked) return;
    if (q.multi) setPicked((p) => (p.includes(i) ? p.filter((x) => x !== i) : [...p, i].sort()));
    else setPicked([i]);
  };

  const check = async () => {
    setBusy(true);
    setError('');
    try {
      const timeSec = Math.max(1, Math.round((Date.now() - shownAt.current) / 1000));
      const res = await answerPractice({ sessionId: session.sessionId, questionId: q.id, selected: picked, timeSec });
      setFeedback(res);
      setSession((s) => ({ ...s, scoreNow: res.session.scoreNow, correctCount: res.session.correctCount }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const next = () => {
    setFeedback(null);
    setPicked([]);
    setIndex((i) => i + 1);
    shownAt.current = Date.now();
  };

  // ---- summary
  if (finished) {
    const gained = Math.round((session.scoreNow - session.scoreStart) * 10) / 10;
    return (
      <div>
        {back}
        <div className="quiz-head"><h1>{prettyTopic(topic)}</h1></div>
        <section className="quiz-card quiz-summary" aria-live="polite">
          <div className="quiz-big">{session.correctCount} of {total}</div>
          <p className="muted">questions fully correct</p>
          <div className="quiz-change">
            <div><span className="muted small">Topic score before</span><strong>{Math.round(session.scoreStart)}%</strong></div>
            <span className="arrow" aria-hidden="true">&rarr;</span>
            <div><span className="muted small">Topic score now</span><strong>{Math.round(session.scoreNow)}%</strong></div>
          </div>
          <p>
            {gained > 0
              ? `Your score went up by ${Math.abs(gained)} points. Practise again in a few days to keep it from fading.`
              : gained < 0
              ? 'Your score went down this time. Read the explanations again and try another session.'
              : 'Your score stayed the same this time.'}
          </p>
          <div className="quiz-actions">
            <button type="button" className="btn" onClick={begin}>Practise again</button>
            <Link className="btn secondary" to={`/c1/topic/${topic}`}>See my score chart</Link>
          </div>
        </section>
      </div>
    );
  }

  // ---- question
  const rightSet = feedback ? feedback.correctIndexes : [];
  const headline = !feedback
    ? ''
    : feedback.correct
    ? 'Correct'
    : feedback.found > 0 && q.multi
    ? `Partly right: you found ${feedback.found} of ${feedback.totalCorrect}`
    : 'Not quite';
  const tone = !feedback ? '' : feedback.correct ? 'good' : feedback.found > 0 ? 'part' : 'bad';

  return (
    <div>
      {back}
      <div className="quiz-head">
        <h1>{prettyTopic(topic)}</h1>
      </div>

      <div className="quiz-progress">
        <div className="quiz-progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax={total} aria-valuenow={index + (locked ? 1 : 0)}>
          <span style={{ width: `${((index + (locked ? 1 : 0)) / total) * 100}%` }} />
        </div>
        <div className="quiz-progress-text">Question {index + 1} of {total}</div>
      </div>

      <section className="quiz-card" aria-labelledby="q-text">
        <span className="quiz-kind">{q.multi ? 'Select one or more' : 'Select one'}</span>
        <p id="q-text" className="quiz-question">{q.text}</p>

        <ul className="quiz-options">
          {q.options.map((text, i) => {
            const isPicked = picked.includes(i);
            const isRight = rightSet.includes(i);
            let cls = 'quiz-opt';
            if (q.multi) cls += ' multi';
            if (locked) cls += ' locked';
            if (!locked && isPicked) cls += ' picked';
            let tag = '';
            if (locked && isRight) {
              cls += ' right';
              tag = isPicked ? 'Correct, you chose it' : 'Correct answer, you missed it';
              if (!isPicked) cls += ' missed';
            } else if (locked && isPicked) {
              cls += ' wrong';
              tag = 'Not correct';
            }
            return (
              <li key={i}>
                <label className={cls}>
                  <input
                    type={q.multi ? 'checkbox' : 'radio'}
                    name={`q-${q.id}`}
                    checked={isPicked}
                    disabled={locked}
                    onChange={() => toggle(i)}
                  />
                  <span className="quiz-letter" aria-hidden="true">{LETTERS[i]}</span>
                  <span className="quiz-text"><span className="sr-only">Option {LETTERS[i]}: </span>{text}</span>
                  {tag && <span className="quiz-tag">{isRight ? '✓ ' : '✗ '}{tag}</span>}
                </label>
              </li>
            );
          })}
        </ul>

        {error && <p className="error" role="alert">{error}</p>}

        {!locked && (
          <div className="quiz-actions">
            <button type="button" className="btn" disabled={picked.length === 0 || busy} onClick={check}>
              {busy ? 'Checking...' : 'Check answer'}
            </button>
            {picked.length === 0 && <p className="muted small">{q.multi ? 'Choose at least one answer.' : 'Choose an answer.'}</p>}
          </div>
        )}

        {locked && (
          <div className={`feedback ${tone}`} role="status" aria-live="polite">
            <h3>{headline}</h3>
            <p><strong>Correct answer: {joinLetters(feedback.correctLetters)}</strong></p>
            <div className="fb-label">Why</div>
            <p>{feedback.explanation}</p>
            <div className="fb-label">How to tackle this type of question</div>
            <p className="fb-tip">{feedback.tip}</p>
            <div className="quiz-actions">
              <button type="button" className="btn" onClick={next}>
                {index + 1 >= total ? 'See my result' : 'Next question'}
              </button>
              <span className="muted small">
                Topic score now {Math.round(feedback.scoreAfter)}%
              </span>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
