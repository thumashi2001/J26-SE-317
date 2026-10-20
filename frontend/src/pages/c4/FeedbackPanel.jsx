import { useCallback, useEffect, useState } from 'react';
import { listFeedback, submitFeedback } from './c4Api.js';

export default function FeedbackPanel() {
  const [items, setItems] = useState([]);
  const [target, setTarget] = useState('study_plan');
  const [usefulness, setUsefulness] = useState(4);
  const [problem, setProblem] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setError('');
      const res = await listFeedback();
      setItems(res.items || []);
    } catch (err) {
      setError(err.message);
      setItems([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    setInfo('');
    try {
      await submitFeedback({
        target,
        usefulness: Number(usefulness),
        problem,
        suggestion,
      });
      setProblem('');
      setSuggestion('');
      setInfo('Thanks — feedback saved to your C4 record.');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="c4-feedback">
      <h2>Feedback</h2>
      <p className="muted">
        Rate usefulness and report problems or suggestions. Stored only in C4 feedback records for
        your account. For PP1 verification, include “PP1 test” in the problem or suggestion text.
      </p>
      {error && (
        <div className="panel">
          <p className="error" role="alert">
            {error}
          </p>
          <button type="button" className="btn secondary" onClick={load}>
            Retry load
          </button>
        </div>
      )}
      {info && <p className="muted small">{info}</p>}

      <form className="panel c4-sim-form" onSubmit={onSubmit}>
        <label className="c4-label">
          About
          <select value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="study_plan">Study plan</option>
            <option value="mock_exam">Mock quiz</option>
            <option value="simulation_demo">Model simulation demo</option>
            <option value="overall">Overall C4</option>
          </select>
        </label>
        <label className="c4-label">
          Usefulness (1–5)
          <input
            type="number"
            min={1}
            max={5}
            value={usefulness}
            onChange={(e) => setUsefulness(e.target.value)}
          />
        </label>
        <label className="c4-label">
          Problem
          <textarea value={problem} onChange={(e) => setProblem(e.target.value)} rows={3} />
        </label>
        <label className="c4-label">
          Suggestion
          <textarea value={suggestion} onChange={(e) => setSuggestion(e.target.value)} rows={3} />
        </label>
        <button type="submit" className="btn" disabled={busy}>
          {busy ? 'Sending…' : 'Submit feedback'}
        </button>
      </form>

      <div className="panel">
        <h3>Your recent feedback</h3>
        {items.length === 0 ? (
          <p className="muted small">None yet.</p>
        ) : (
          <ul className="c4-unavailable">
            {items.map((it) => (
              <li key={it.feedbackId}>
                <strong>{it.target}</strong>
                {it.usefulness != null ? ` · ${it.usefulness}/5` : ''}
                {it.problem ? ` · ${it.problem}` : ''}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
