import { useEffect, useRef, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getDiagnostic, getTwin, submitDiagnostic } from '../../services/c1Api.js';
import { prettyTopic } from '../../utils/topics.js';
import DiagnosticSummary from '../../components/DiagnosticSummary.jsx';

// The database stores options as { A: "text", B: "text" }. A plain list is accepted too.
function normaliseOptions(options) {
  if (Array.isArray(options)) {
    return options.map((o, i) => {
      const key = String.fromCharCode(65 + i);
      return typeof o === 'object' && o ? { key: o.key || key, text: o.text || '' } : { key, text: String(o) };
    });
  }
  return Object.entries(options || {}).map(([key, text]) => ({ key, text: String(text) }));
}

// Shown when the test was already taken: loads the current scores and shows the same summary.
function DoneView({ user }) {
  const [twin, setTwin] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    getTwin(user.student_id).then(setTwin).catch(() => setFailed(true));
  }, [user.student_id]);
  if (twin && twin.mastery) return <DiagnosticSummary mastery={twin.mastery} mode="done" name={user.name} />;
  return (
    <div className="panel">
      <h2>You have already taken the diagnostic</h2>
      <p className="muted">{failed ? 'Your scores did not load, but your twin is safe.' : 'Loading your scores...'}</p>
      <Link className="btn" to="/c1/dashboard">Open my learning state</Link>
    </div>
  );
}

export default function DiagnosticPage() {
  const { user, markDiagnosticDone } = useAuth();
  const [state, setState] = useState({ status: 'loading' });
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Timer and per-question timing. The timer starts when the intro popup is closed.
  const { testStarted = true } = useOutletContext() || {};
  const [startedAt, setStartedAt] = useState(null);
  const [now, setNow] = useState(Date.now());
  const chosenRef = useRef({});
  const spent = useRef({});
  const leaves = useRef({});
  const shownAt = useRef(null);
  const curId = useRef(null);
  const autoTried = useRef(false);
  const isReady = state.status === 'ready';
  chosenRef.current = chosen;
  curId.current = isReady ? state.data.questions[index]?.question_id : null;

  // Adds the time since the question was shown to that question, then starts counting again.
  const flush = () => {
    if (shownAt.current && curId.current) {
      spent.current[curId.current] = (spent.current[curId.current] || 0) + (Date.now() - shownAt.current) / 1000;
    }
    shownAt.current = document.hidden ? null : Date.now();
  };
  const goTo = (i) => {
    flush();
    setIndex(i);
  };

  useEffect(() => {
    if (isReady && testStarted && startedAt === null) {
      setStartedAt(Date.now());
      shownAt.current = Date.now();
    }
  }, [isReady, testStarted, startedAt]);

  useEffect(() => {
    if (!isReady || startedAt === null) return undefined;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [isReady, startedAt]);

  // Leaving the tab is counted, and the time away is not counted as time on the question.
  useEffect(() => {
    if (!isReady || startedAt === null) return undefined;
    const onVisibility = () => {
      if (document.hidden) {
        if (curId.current) {
          leaves.current[curId.current] = (leaves.current[curId.current] || 0) + 1;
          flush();
          shownAt.current = null;
        }
      } else {
        shownAt.current = Date.now();
      }
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [isReady, startedAt]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let alive = true;
    setState({ status: 'loading' });
    getDiagnostic(user.student_id)
      .then((data) => alive && setState({ status: 'ready', data }))
      .catch((err) => {
        if (!alive) return;
        if (err.status === 409) markDiagnosticDone();
        setState({ status: err.status === 409 ? 'done' : 'error', message: err.message });
      });
    return () => {
      alive = false;
    };
  }, [user.student_id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (state.status === 'loading') return <p className="muted">Loading your test...</p>;

  if (state.status === 'done') return <DoneView user={user} />;

  if (state.status === 'error')
    return (
      <div className="panel">
        <h2>The test did not load</h2>
        <p className="error">{state.message}</p>
        <p className="muted">Make sure the backend (port 3000) and the AI service (port 8001) are running.</p>
      </div>
    );

  if (state.status === 'result') return <DiagnosticSummary mastery={state.mastery} mode="result" timedOut={state.timedOut} name={user.name} />;

  const { questions } = state.data;
  const q = questions[index];
  const options = normaliseOptions(q.options);
  const answeredCount = Object.keys(chosen).length;
  const isLast = index === questions.length - 1;

  const limit = state.data.timeLimitSec || Math.round((questions.length * 43) / 30) * 30;
  const elapsed = startedAt ? Math.floor((now - startedAt) / 1000) : 0;
  const remaining = Math.max(0, limit - elapsed);
  const clock = `${String(Math.floor(remaining / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
  const announce = startedAt && remaining <= 60 ? 'One minute left' : startedAt && remaining <= 300 ? 'Five minutes left' : '';

  const submit = async (auto = false) => {
    if (submitting) return;
    flush();
    setSubmitting(true);
    setError('');
    try {
      const answers = questions.map((x) => ({
        question_id: x.question_id,
        selected: chosenRef.current[x.question_id] || null,
        time_sec: Math.round(spent.current[x.question_id] || 0),
        tab_leaves: leaves.current[x.question_id] || 0,
      }));
      const result = await submitDiagnostic(user.student_id, answers, { timedOut: auto, totalSec: elapsed });
      setState({ status: 'result', mastery: result.mastery, timedOut: auto });
      markDiagnosticDone();
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  // Time is up: send the answers given so far, once.
  if (startedAt && remaining === 0 && !autoTried.current && !submitting) {
    autoTried.current = true;
    setTimeout(() => submit(true), 0);
  }

  return (
    <div className="quiz dx">
      <div className="quiz-head">
        <h1>Diagnostic test</h1>
        <div className="dx-meta">
          <span className="muted">
            {answeredCount} of {questions.length} answered
          </span>
          <span className={'dx-timer' + (startedAt && remaining <= 180 ? ' low' : '')} role="timer" aria-label="Time left">
            <span aria-hidden="true">⏱</span> {startedAt ? clock : 'Starts when you begin'}
          </span>
        </div>
        <span className="sr-only" role="status">{announce}</span>
      </div>

      <div className="steps" aria-label="Progress">
        {questions.map((x, i) => (
          <button
            key={x.question_id}
            className={'step' + (i === index ? ' current' : '') + (chosen[x.question_id] ? ' done' : '')}
            onClick={() => goTo(i)}
            aria-label={`Go to question ${i + 1}`}
            aria-current={i === index}
          />
        ))}
      </div>

      <div className="panel">
        <div className="chip">
          {q.module_code}, {prettyTopic(q.topic)}
        </div>
        <h2 className="question">{q.question_text}</h2>
        <div className="options" role="radiogroup" aria-label="Answer options">
          {options.map(({ key, text }) => {
            const selected = chosen[q.question_id] === key;
            return (
              <button
                key={key}
                role="radio"
                aria-checked={selected}
                className={'option' + (selected ? ' selected' : '')}
                onClick={() => setChosen({ ...chosen, [q.question_id]: key })}
              >
                <span className="option-key">{key}</span>
                <span>{text || `Option ${key}`}</span>
              </button>
            );
          })}
        </div>
      </div>

      {submitting && autoTried.current && <p className="muted" role="status">Time is up. Sending your answers...</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <div className="row">
        <button className="btn secondary" disabled={index === 0} onClick={() => goTo(index - 1)}>
          Previous
        </button>
        <span className="muted small">
          Question {index + 1} of {questions.length}
        </span>
        {!isLast ? (
          <button className="btn" onClick={() => goTo(index + 1)}>
            Next
          </button>
        ) : (
          <button className="btn" disabled={submitting} onClick={() => submit(false)}>
            {submitting ? 'Submitting...' : 'Submit test'}
          </button>
        )}
      </div>
      {isLast && answeredCount < questions.length && (
        <p className="muted small">Unanswered questions count as wrong.</p>
      )}
    </div>
  );
}
