import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { getDiagnostic, submitDiagnostic } from '../../services/c1Api.js';
import { prettyTopic, scoreBand } from '../../utils/topics.js';

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

export default function DiagnosticPage() {
  const { user, markDiagnosticDone } = useAuth();
  const [state, setState] = useState({ status: 'loading' });
  const [index, setIndex] = useState(0);
  const [chosen, setChosen] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

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

  if (state.status === 'done')
    return (
      <div className="panel">
        <h2>You have already taken the diagnostic</h2>
        <p className="muted">Your twin was built from those answers. Keep it current by logging practice answers.</p>
        <Link className="btn" to="/c1/dashboard">
          Open my learning state
        </Link>
      </div>
    );

  if (state.status === 'error')
    return (
      <div className="panel">
        <h2>The test did not load</h2>
        <p className="error">{state.message}</p>
        <p className="muted">Make sure the backend (port 3000) and the AI service (port 8001) are running.</p>
      </div>
    );

  if (state.status === 'result')
    return (
      <div>
        <h1>Your starting profile</h1>
        <p className="muted">This is where your twin begins. It changes every time you practise.</p>
        <div className="heat">
          {Object.entries(state.mastery).map(([topic, m]) => (
            <div key={topic} className={`topic ${scoreBand(m.score)}`}>
              <div className="topic-name">{prettyTopic(topic)}</div>
              <div className="topic-score">{Math.round(m.score)}%</div>
              <div className="bar">
                <span style={{ width: `${Math.max(3, m.score)}%` }} />
              </div>
              <div className="muted small">
                {m.correct} of {m.answered} correct
              </div>
            </div>
          ))}
        </div>
        <Link className="btn" to="/c1/dashboard">
          Open my learning state
        </Link>
      </div>
    );

  const { questions } = state.data;
  const q = questions[index];
  const options = normaliseOptions(q.options);
  const answeredCount = Object.keys(chosen).length;
  const isLast = index === questions.length - 1;

  const submit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const answers = questions.map((x) => ({ question_id: x.question_id, selected: chosen[x.question_id] || null }));
      const result = await submitDiagnostic(user.student_id, answers);
      setState({ status: 'result', mastery: result.mastery });
      markDiagnosticDone();
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  return (
    <div className="quiz">
      <div className="quiz-head">
        <h1>Diagnostic test</h1>
        <span className="muted">
          {answeredCount} of {questions.length} answered
        </span>
      </div>

      <div className="steps" aria-label="Progress">
        {questions.map((x, i) => (
          <button
            key={x.question_id}
            className={'step' + (i === index ? ' current' : '') + (chosen[x.question_id] ? ' done' : '')}
            onClick={() => setIndex(i)}
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

      {error && <p className="error" role="alert">{error}</p>}

      <div className="row">
        <button className="btn secondary" disabled={index === 0} onClick={() => setIndex(index - 1)}>
          Previous
        </button>
        <span className="muted small">
          Question {index + 1} of {questions.length}
        </span>
        {!isLast ? (
          <button className="btn" onClick={() => setIndex(index + 1)}>
            Next
          </button>
        ) : (
          <button className="btn" disabled={submitting} onClick={submit}>
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
