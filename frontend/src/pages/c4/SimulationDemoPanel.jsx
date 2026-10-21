import { useCallback, useEffect, useMemo, useState } from 'react';
import { prettyTopic } from '../../utils/topics.js';
import {
  getSimScenarios,
  getSimDemoReady,
  predictSimExamScore,
  predictSimPass,
  predictSimPath,
  predictSimResponse,
} from './c4Api.js';
import { visibleError } from './studentCopy.js';

function ResultBlock({ title, loading, error, empty, children }) {
  return (
    <div className="panel c4-sim-result">
      <h3>{title}</h3>
      {loading && <p className="muted small">Running synthetic prediction…</p>}
      {error && <p className="error">{visibleError(error)}</p>}
      {!loading && !error && empty && (
        <p className="muted small">No result yet — pick a scenario and run.</p>
      )}
      {!loading && !error && children}
    </div>
  );
}

function SyntheticNote({ out }) {
  if (!out) return null;
  return (
    <p className="muted small">
      Synthetic data only. This result is not saved to your study record.
      {out.semester ? ` Semester ${out.semester}.` : ''}
    </p>
  );
}

function scorePercent(value) {
  if (value == null || !Number.isFinite(Number(value))) return '—';
  const n = Number(value);
  const pct = n <= 1 ? n * 100 : n;
  return `${pct.toFixed(1)}%`;
}

export default function SimulationDemoPanel() {
  const [ready, setReady] = useState(null);
  const [scenarios, setScenarios] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [pathId, setPathId] = useState('');
  const [responseId, setResponseId] = useState('');
  const [examId, setExamId] = useState('');
  const [busy, setBusy] = useState({});
  const [errors, setErrors] = useState({});
  const [pathOut, setPathOut] = useState(null);
  const [responseOut, setResponseOut] = useState(null);
  const [examOut, setExamOut] = useState(null);
  const [passOut, setPassOut] = useState(null);

  const refreshMeta = useCallback(async () => {
    setLoadError('');
    try {
      const [r, s] = await Promise.all([getSimDemoReady(), getSimScenarios()]);
      setReady(r);
      setScenarios(s);
      setPathId((prev) => prev || s.path?.[0]?.id || '');
      setResponseId((prev) => prev || s.response?.[0]?.id || '');
      setExamId((prev) => prev || s.exam?.[0]?.id || '');
    } catch (err) {
      setReady(null);
      setScenarios(null);
      setLoadError(
        err.message || 'Could not load the simulation demo. You may need to sign in again.'
      );
    }
  }, []);

  useEffect(() => {
    refreshMeta();
  }, [refreshMeta]);

  const pathScenario = useMemo(
    () => scenarios?.path?.find((x) => x.id === pathId) || null,
    [scenarios, pathId]
  );
  const responseScenario = useMemo(
    () => scenarios?.response?.find((x) => x.id === responseId) || null,
    [scenarios, responseId]
  );
  const examScenario = useMemo(
    () => scenarios?.exam?.find((x) => x.id === examId) || null,
    [scenarios, examId]
  );

  const modelsReady = Boolean(ready?.ready);
  const canRun = modelsReady && !loadError;

  const run = async (key, fn) => {
    setBusy((b) => ({ ...b, [key]: true }));
    setErrors((e) => ({ ...e, [key]: '' }));
    try {
      return await fn();
    } catch (err) {
      setErrors((e) => ({ ...e, [key]: err.message || 'Prediction failed' }));
      return null;
    } finally {
      setBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const onPath = async () => {
    if (!pathScenario?.request) return;
    const out = await run('path', () =>
      predictSimPath({
        ...pathScenario.request,
        use_synthetic_scenario: false,
      })
    );
    if (out) setPathOut(out);
  };

  const onResponse = async () => {
    if (!responseScenario?.request) return;
    const out = await run('response', () =>
      predictSimResponse({
        features: responseScenario.request.features,
        protocol: 'se-supervised-sim-v1',
      })
    );
    if (out) setResponseOut(out);
  };

  const onExam = async () => {
    if (!examScenario?.request) return;
    const out = await run('exam', () =>
      predictSimExamScore({
        features: examScenario.request.features,
        protocol: 'se-supervised-sim-v1',
      })
    );
    if (out) setExamOut(out);
  };

  const onPass = async () => {
    if (!examScenario?.request) return;
    const out = await run('pass', () =>
      predictSimPass({
        features: examScenario.request.features,
        protocol: 'se-supervised-sim-v1',
      })
    );
    if (out) setPassOut(out);
  };

  const onExamAndPass = async () => {
    await onExam();
    await onPass();
  };

  return (
    <div className="c4-sim-demo">
      <h2>Synthetic simulation demo</h2>
      <p className="muted">
        This demo uses made-up learner data. It is not your study plan, and nothing here is saved
        to your account. Results are experimental and are not validated student performance.
      </p>
      <p className="muted small">
        A probability here is not a measure of how accurate the model is. The synthetic pass
        cutoff is not a university rule.
      </p>

      {loadError && (
        <div className="panel">
          <p className="error">{visibleError(loadError)}</p>
          <p className="muted small">
            The simulation demo is unavailable. Check that you are signed in, then try again.
          </p>
          <button type="button" className="btn secondary" onClick={refreshMeta}>
            Retry
          </button>
        </div>
      )}

      <div className="panel c4-sim-ready">
        <div className="c4-sim-ready-row">
          <span className={`chip ${modelsReady ? 'ok' : 'bad'}`}>
            {modelsReady ? 'Models ready' : 'Models not ready'}
          </span>
          <span className="chip">Synthetic only</span>
          <button type="button" className="btn secondary" onClick={refreshMeta}>
            Refresh status
          </button>
        </div>
        {(ready?.path_error || ready?.supervised_error) && (
          <p className="muted small">The simulation models are not ready.</p>
        )}
        {!modelsReady && !loadError && (
          <p className="muted small">
            Predictions stay unavailable until the simulation models are ready.
          </p>
        )}
      </div>

      <div className="c4-sim-grid">
        <div className="panel">
          <h3>1. Suggested next topic</h3>
          <label className="c4-label">
            Synthetic scenario (includes Y3S1 and Y3S2)
            <select value={pathId} onChange={(e) => setPathId(e.target.value)}>
              {(scenarios?.path || []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                  {s.semester ? ` [${s.semester}]` : ''}
                </option>
              ))}
            </select>
          </label>
          <p className="muted small">Made-up learner data for this demo. Not a real student record.</p>
          {pathScenario?.semester && (
            <p className="muted small">Includes only topics from semester {pathScenario.semester}.</p>
          )}
          <button
            type="button"
            className="btn"
            disabled={!canRun || busy.path || !pathScenario}
            onClick={onPath}
          >
            {busy.path ? 'Predicting…' : 'Predict next practice topic'}
          </button>
          <ResultBlock title="Selected topic" loading={busy.path} error={errors.path} empty={!pathOut}>
            {pathOut && (
              <>
                <p>
                  <strong>{pathOut.topic_id ? prettyTopic(pathOut.topic_id) : 'No topic returned'}</strong>
                </p>
                <SyntheticNote out={pathOut} />
                <p className="muted small">Not a recommendation for your account.</p>
              </>
            )}
          </ResultBlock>
        </div>

        <div className="panel">
          <h3>2. Next-answer correctness</h3>
          <label className="c4-label">
            Synthetic scenario
            <select value={responseId} onChange={(e) => setResponseId(e.target.value)}>
              {(scenarios?.response || []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                  {s.semester ? ` [${s.semester}]` : ''}
                </option>
              ))}
            </select>
          </label>
          <p className="muted small">Made-up practice history for this demo. Not a real student record.</p>
          <button
            type="button"
            className="btn"
            disabled={!canRun || busy.response || !responseScenario}
            onClick={onResponse}
          >
            {busy.response ? 'Predicting…' : 'Predict correctness probability'}
          </button>
          <ResultBlock
            title="Correctness probability"
            loading={busy.response}
            error={errors.response}
            empty={!responseOut}
          >
            {responseOut && (
              <>
                <p>
                  <strong>
                    Estimated chance of a correct answer: {(responseOut.p_correct * 100).toFixed(1)}%
                  </strong>
                </p>
                <SyntheticNote out={responseOut} />
                <p className="muted small">
                  This is a prediction for made-up data. It is not a real student result and not a
                  measure of model accuracy.
                </p>
              </>
            )}
          </ResultBlock>
        </div>

        <div className="panel">
          <h3>3–4. Synthetic quiz score and pass chance</h3>
          <label className="c4-label">
            Synthetic quiz scenario
            <select value={examId} onChange={(e) => setExamId(e.target.value)}>
              {(scenarios?.exam || []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                  {s.semester ? ` [${s.semester}]` : ''}
                </option>
              ))}
            </select>
          </label>
          <p className="muted small">Made-up practice totals for this demo. Not a real exam record.</p>
          <div className="c4-actions">
            <button
              type="button"
              className="btn"
              disabled={!canRun || busy.exam || !examScenario}
              onClick={onExam}
            >
              {busy.exam ? '…' : 'Predict mock score'}
            </button>
            <button
              type="button"
              className="btn"
              disabled={!canRun || busy.pass || !examScenario}
              onClick={onPass}
            >
              {busy.pass ? '…' : 'Predict pass probability'}
            </button>
            <button
              type="button"
              className="btn secondary"
              disabled={!canRun || busy.exam || busy.pass || !examScenario}
              onClick={onExamAndPass}
            >
              Run both
            </button>
          </div>
          <ResultBlock
            title="Estimated mock-exam score"
            loading={busy.exam}
            error={errors.exam}
            empty={!examOut}
          >
            {examOut && (
              <>
                <p>
                  <strong>
                    Estimated score:{' '}
                    {scorePercent(examOut.exam_score_clipped_display ?? examOut.exam_score_raw)}
                  </strong>
                </p>
                <SyntheticNote out={examOut} />
                <p className="muted small">
                  This is a fraction correct on made-up data, not a university exam mark.
                </p>
              </>
            )}
          </ResultBlock>
          <ResultBlock
            title="Mock pass probability"
            loading={busy.pass}
            error={errors.pass}
            empty={!passOut}
          >
            {passOut && (
              <>
                <p>
                  <strong>
                    Estimated chance of passing this synthetic quiz: {(passOut.p_pass * 100).toFixed(1)}%
                  </strong>
                </p>
                <SyntheticNote out={passOut} />
                <p className="muted small">
                  This uses a synthetic cutoff, not a university rule. It is not a validated result
                  for real students.
                </p>
              </>
            )}
          </ResultBlock>
        </div>
      </div>
    </div>
  );
}
