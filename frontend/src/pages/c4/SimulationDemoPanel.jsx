import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getSimScenarios,
  getSimDemoReady,
  predictSimExamScore,
  predictSimPass,
  predictSimPath,
  predictSimResponse,
} from './c4Api.js';

function ResultBlock({ title, loading, error, empty, children }) {
  return (
    <div className="panel c4-sim-result">
      <h3>{title}</h3>
      {loading && <p className="muted small">Running synthetic prediction…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && empty && (
        <p className="muted small">No result yet — pick a scenario and run.</p>
      )}
      {!loading && !error && children}
    </div>
  );
}

function MetaLine({ out }) {
  if (!out) return null;
  return (
    <p className="muted small">
      synthetic={String(out.synthetic ?? out.synthetic_scenario != null)} · simulation_only=
      {String(out.simulation_only)} · demo_not_persisted={String(out.demo_not_persisted)} ·{' '}
      {out.protocol}
      {out.semester ? ` · semester ${out.semester}` : ''}
    </p>
  );
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
        err.message ||
          'Could not load simulation demo metadata (Node proxy or login may be unavailable)'
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
        These controls call the imported C4 <strong>v1 simulation models</strong> through an
        authenticated Node proxy. Inputs are synthetic scenarios — not your C1 twin, and nothing
        is written to student records. The Adaptive learning path tab remains the operational
        heuristic study plan.
      </p>
      <p className="muted small">
        Prediction probabilities are <strong>not</strong> model accuracy. The 55% synthetic
        pass-label cutoff is not an institutional rule.
      </p>

      {loadError && (
        <div className="panel">
          <p className="error">{loadError}</p>
          <p className="muted small">
            Service unavailable for the demo proxy. Check Node is running on the Vite-proxied
            port (3000), you are logged in, and C4 AI is on 8004.
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
        <p className="muted small">
          Path protocol: {ready?.path?.protocol || '—'} · Supervised:{' '}
          {ready?.supervised?.protocol || '—'} · Catalogue:{' '}
          {(ready?.catalogue_hash || '').slice(0, 12) || '—'}…
        </p>
        {(ready?.path_error || ready?.supervised_error) && (
          <p className="muted small">
            {ready.path_error ? `Path: ${ready.path_error.message}. ` : ''}
            {ready.supervised_error ? `Supervised: ${ready.supervised_error.message}.` : ''} Start{' '}
            <code>uvicorn</code> on port 8004 if needed.
          </p>
        )}
        {!modelsReady && !loadError && (
          <p className="muted small">
            Predictions stay disabled until both path and supervised v1 models report ready.
          </p>
        )}
      </div>

      <div className="c4-sim-grid">
        <div className="panel">
          <h3>1. Path suggestion (MaskablePPO)</h3>
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
          <p className="muted small">{pathScenario?.description}</p>
          {pathScenario?.semester && (
            <p className="muted small">Semester mask: {pathScenario.semester} only.</p>
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
                  <strong>{pathOut.topic_id}</strong> (index {pathOut.action_index})
                </p>
                <MetaLine out={pathOut} />
                <p className="muted small">
                  Seed {pathOut.seed} · Not a live student recommendation.
                </p>
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
          <p className="muted small">{responseScenario?.description}</p>
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
                  <strong>p_correct = {(responseOut.p_correct * 100).toFixed(1)}%</strong>
                </p>
                <MetaLine out={responseOut} />
                <p className="muted small">
                  Predicted probability for a synthetic attempt — not model accuracy and not a
                  real student result. Model: {responseOut.selected_model}
                </p>
              </>
            )}
          </ResultBlock>
        </div>

        <div className="panel">
          <h3>3–4. Mock-exam score &amp; pass probability</h3>
          <label className="c4-label">
            Synthetic exam scenario (Y3S1 / Y3S2)
            <select value={examId} onChange={(e) => setExamId(e.target.value)}>
              {(scenarios?.exam || []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                  {s.semester ? ` [${s.semester}]` : ''}
                </option>
              ))}
            </select>
          </label>
          <p className="muted small">{examScenario?.description}</p>
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
                    raw = {examOut.exam_score_raw?.toFixed?.(4) ?? examOut.exam_score_raw}
                  </strong>
                  {examOut.exam_score_clipped_display != null && (
                    <>
                      {' '}
                      · display clip = {examOut.exam_score_clipped_display.toFixed(4)}
                    </>
                  )}
                </p>
                <MetaLine out={examOut} />
                <p className="muted small">
                  Fraction-correct scale [0,1] under the synthetic generator. Not a real module
                  exam mark. Model: {examOut.selected_model}
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
                  <strong>p_pass = {(passOut.p_pass * 100).toFixed(1)}%</strong>
                </p>
                <MetaLine out={passOut} />
                <p className="muted small">
                  Probability that synthetic mock fraction-correct ≥ {passOut.pass_threshold}. The{' '}
                  <strong>55% synthetic pass-label cutoff is not an institutional rule</strong>.
                  Classification probability threshold {passOut.classification_prob_threshold} is
                  separate. real_exam_validation={String(passOut.real_exam_validation)}.
                </p>
              </>
            )}
          </ResultBlock>
        </div>
      </div>
    </div>
  );
}
