import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { prettyTopic } from '../../utils/topics.js';
import {
  createExam,
  getExam,
  getExamSources,
  listExams,
  saveExamAnswers,
  submitExam,
} from './c4Api.js';

function formatRemain(ms) {
  if (ms <= 0) return '0:00';
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, '0')}`;
}

export default function ExamPanel({ focusTopic = null }) {
  const [sources, setSources] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [active, setActive] = useState(null);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);
  const [answers, setAnswers] = useState({});
  const [qIndex, setQIndex] = useState(0);
  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [questionCount, setQuestionCount] = useState(8);
  const [timeLimitMin, setTimeLimitMin] = useState(15);
  const [showPreExam, setShowPreExam] = useState(false);

  const load = useCallback(async () => {
    setError('');
    try {
      const [s, l] = await Promise.all([getExamSources(), listExams()]);
      setSources(s);
      setAttempts(l.attempts || []);
    } catch (err) {
      setError(err.message || 'Could not load exams');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!active?.expiresAt || active.status !== 'in_progress') return undefined;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [active?.expiresAt, active?.status]);

  const remainMs = useMemo(() => {
    if (!active?.expiresAt || active.status !== 'in_progress') return null;
    return new Date(active.expiresAt).getTime() - now;
  }, [active, now]);

  useEffect(() => {
    if (remainMs == null || remainMs > 0 || !active || active.status !== 'in_progress' || busy) return;
    // Server-authoritative expiry: reopen attempt to finalize grading
    (async () => {
      setBusy(true);
      setError('');
      try {
        const updated = await getExam(active.attemptId);
        setActive(updated);
        setAnswers(updated.answers || {});
        setInfo('Time limit reached — answers were graded on the server.');
        await load();
      } catch (err) {
        setError(err.message);
      } finally {
        setBusy(false);
      }
    })();
  }, [remainMs, active, busy, load]);

  const questions = active?.questions || [];
  const current = questions[qIndex] || null;
  const answeredCount = questions.filter((q) => (answers[q.questionId] || []).length > 0).length;

  const start = async () => {
    const qc = Number(questionCount);
    const mins = Number(timeLimitMin);
    if (!Number.isFinite(qc) || qc < 3 || qc > 40) {
      setError('Question count must be between 3 and 40');
      return;
    }
    if (!Number.isFinite(mins) || mins < 1 || mins > 180) {
      setError('Time limit must be between 1 and 180 minutes');
      return;
    }
    setBusy(true);
    setError('');
    setInfo('');
    setConfirmSubmit(false);
    try {
      const attempt = await createExam({
        source: 'c1_practice_bank',
        questionCount: qc,
        timeLimitSec: Math.round(mins * 60),
        clientRequestId: `exam-${Date.now()}`,
        ...(focusTopic ? { topics: [focusTopic] } : {}),
      });
      setActive(attempt);
      setAnswers(attempt.answers || {});
      setQIndex(0);
      setInfo('Quiz started from C1 practice bank (not a C2 past paper).');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const open = async (id) => {
    setBusy(true);
    setError('');
    setInfo('');
    setConfirmSubmit(false);
    try {
      const attempt = await getExam(id);
      setActive(attempt);
      setAnswers(attempt.answers || {});
      setQIndex(0);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const toggleOption = (qid, optIdx, multi) => {
    setAnswers((prev) => {
      const cur = prev[qid] || [];
      if (multi) {
        const has = cur.includes(optIdx);
        return {
          ...prev,
          [qid]: has ? cur.filter((x) => x !== optIdx) : [...cur, optIdx],
        };
      }
      return { ...prev, [qid]: [optIdx] };
    });
  };

  const save = async () => {
    if (!active) return;
    setBusy(true);
    setError('');
    try {
      const updated = await saveExamAnswers(active.attemptId, answers);
      setActive(updated);
      setAnswers(updated.answers || answers);
      if (updated.timedOut || updated.status === 'submitted') {
        setInfo('Attempt finalized on the server.');
        await load();
      } else {
        setInfo('Answers saved. You can reload and resume later.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!active) return;
    setBusy(true);
    setError('');
    setConfirmSubmit(false);
    try {
      const updated = await submitExam(active.attemptId, answers);
      setActive(updated);
      setInfo(updated.duplicate ? 'Already submitted.' : 'Submitted — server graded this attempt.');
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const c2 = sources?.sources?.find((s) => s.id === 'c2_past_paper');
  const weakTopics = (active?.result?.topicBreakdown || [])
    .filter((t) => t.accuracy < 0.6)
    .map((t) => t.topic);

  return (
    <div className="c4-exam">
      <h2>Mock quizzes</h2>
      <p className="muted">
        Source: <strong>C1 practice bank</strong> (snapshotted into a C4 attempt). Not a C2 past
        paper and not a university module exam.
      </p>

      {error && (
        <div className="panel">
          <p className="error" role="alert">
            {error}
          </p>
          <button type="button" className="btn secondary" onClick={load}>
            Retry
          </button>
        </div>
      )}
      {info && <p className="muted small">{info}</p>}

      <div className="panel">
        <h3>Start a practice-bank quiz</h3>
        <div className="c4-sim-form c4-exam-settings">
          <label className="c4-label">
            Questions (3–40)
            <input
              type="number"
              min={3}
              max={40}
              value={questionCount}
              disabled={busy}
              onChange={(e) => setQuestionCount(e.target.value)}
            />
          </label>
          <label className="c4-label">
            Time limit (minutes)
            <input
              type="number"
              min={1}
              max={180}
              value={timeLimitMin}
              disabled={busy}
              onChange={(e) => setTimeLimitMin(e.target.value)}
            />
          </label>
        </div>
        <p className="muted small">
          Eligible topics come from your C1 twin and semester. Timing and grading are enforced on
          the server.
        </p>
        {focusTopic ? (
          <p className="muted small">
            Quiz topic from the plan link: <strong>{prettyTopic(focusTopic)}</strong> ({focusTopic}
            ). Starting uses only this topic when it is eligible for your semester.
          </p>
        ) : (
          <p className="muted small">
            No topic was passed in the link. The quiz uses your eligible semester topics, weakest
            first.
          </p>
        )}
        <ul className="c4-unavailable">
          {(sources?.sources || []).map((s) => (
            <li key={s.id}>
              <strong>{s.label}</strong>
              <span className="muted">
                {' '}
                — {s.available ? 'Available' : 'Unavailable'}. {s.description}
              </span>
            </li>
          ))}
        </ul>
        {c2 && !c2.available && (
          <p className="muted small">
            C2 past papers: unavailable (no delivery API). The start button below uses the practice
            bank only.
          </p>
        )}
        <button type="button" className="btn" disabled={busy} onClick={start}>
          {busy ? 'Starting…' : 'Start practice-bank mock quiz'}
        </button>
      </div>

      <div className="panel">
        <h3>Attempt history</h3>
        {attempts.length === 0 ? (
          <p className="muted small">No attempts yet.</p>
        ) : (
          <ul className="c4-attempt-list">
            {attempts.map((a) => (
              <li key={a.attemptId}>
                <button type="button" className="btn secondary" disabled={busy} onClick={() => open(a.attemptId)}>
                  <span className="chip">{a.status}</span>
                  {a.result ? ` ${a.result.scorePercent}%` : ''} · {a.questionCount} Q ·{' '}
                  {a.createdAt ? new Date(a.createdAt).toLocaleString() : ''}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {active && (
        <div className="panel c4-exam-active">
          <div className="c4-exam-toolbar">
            <h3>
              Attempt · {active.status}
            </h3>
            {remainMs != null && active.status === 'in_progress' && (
              <span
                className={`chip ${remainMs < 60_000 ? 'bad' : 'ok'}`}
                aria-live="polite"
                aria-label={`Time remaining ${formatRemain(remainMs)}`}
              >
                {formatRemain(remainMs)} left
              </span>
            )}
          </div>
          <p className="muted small">{active.contentNote}</p>
          {active.examBlueprint && (
            <p className="muted small">
              Blueprint: weak topics first, round-robin across topics. Difficulty adaptation
              unavailable — items have no difficulty metadata.
            </p>
          )}

          <details className="c4-details" open={showPreExam} onToggle={(e) => setShowPreExam(e.target.open)}>
            <summary>Pre-exam estimate for this quiz (heuristic)</summary>
            {active.preExamModel?.assessment?.practice_quiz?.usable ? (
              <div className="c4-sim-result">
                <p className="muted small">
                  <span className="chip">heuristic · not a trained model</span>{' '}
                  {active.preExamModel.assessment.practice_quiz.supported_meaning ||
                    'Mean of topic prior accuracies for this quiz’s questions.'}
                </p>
                <p className="muted small">
                  Frozen at {active.preExamModel?.frozen_at || '—'} (cutoff{' '}
                  {active.preExamModel?.prediction_cutoff_utc || '—'}). Never updated from quiz
                  answers.
                </p>
                <p>
                  Heuristic predicted score:{' '}
                  <strong>
                    {Math.round(
                      (active.preExamModel.assessment.practice_quiz.predicted_score ?? 0) * 100
                    )}
                    %
                  </strong>
                  <span className="muted small">
                    {' '}
                    · {active.preExamModel.assessment.practice_quiz.question_count ?? active.questionCount}{' '}
                    questions · product target{' '}
                    {Math.round(
                      (active.preExamModel.assessment.practice_quiz.practice_quiz_score_target ??
                        0.6) * 100
                    )}
                    % (not institutional)
                  </span>
                </p>
                <p>
                  Meets practice-quiz target (0.6 decision rule, not a probability):{' '}
                  <strong>
                    {active.preExamModel.assessment.practice_quiz.predicted_pass ? 'Yes' : 'No'}
                  </strong>
                </p>
                <p className="muted small">
                  Pass probability for this quiz: insufficient evidence. No model is trained to
                  output P(pass) on this practice-bank blueprint.
                </p>
                {active.preExamModel.assessment.practice_quiz.cold_start ? (
                  <p className="muted small">
                    <strong>Cold start:</strong> no prior practice answers before this attempt —
                    every question uses the explicit <strong>50% default</strong> (not observed
                    performance).
                  </p>
                ) : (active.preExamModel.assessment.practice_quiz.questions_using_default_prior ||
                    0) > 0 ? (
                  <p className="muted small">
                    Partial defaults:{' '}
                    {active.preExamModel.assessment.practice_quiz.questions_using_default_prior}/
                    {active.preExamModel.assessment.practice_quiz.question_count} questions use the
                    explicit <strong>50% default</strong> (no prior attempts on that topic).
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="muted small">
                Frozen at {active.preExamModel?.frozen_at || '—'}.{' '}
                {active.preExamModel?.assessment?.practice_quiz?.reason ||
                  'This-quiz estimate unavailable.'}
              </p>
            )}
            <details className="c4-details">
              <summary>Technical detail (experimental readiness model)</summary>
              {active.preExamModel?.assessment?.exam?.usable ? (
                <div className="c4-sim-result">
                  <p className="muted small">
                    {active.preExamModel.assessment.exam.supported_meaning}
                  </p>
                  <p>
                    Simulation-trained readiness:{' '}
                    <strong>
                      {Math.round(
                        (active.preExamModel.assessment.exam.predicted_score ?? 0) * 100
                      )}
                      %
                    </strong>
                    <span className="muted small"> · different target from this quiz</span>
                  </p>
                  <p className="muted small">
                    Pass P≈
                    {Math.round(
                      (active.preExamModel.assessment.exam.pass_probability ?? 0) * 100
                    )}
                    % · synthetic label cutoff{' '}
                    {active.preExamModel.assessment.exam.pass_label_threshold ?? 0.55} (not
                    institutional)
                  </p>
                </div>
              ) : (
                <p className="muted small">
                  {active.preExamModel?.assessment?.exam?.reason ||
                    'Experimental readiness estimate unavailable.'}
                </p>
              )}
              <p className="muted small">
                Next-answer response model remains unavailable (no C1 item difficulty).
              </p>
            </details>
          </details>

          {active.status === 'in_progress' && questions.length > 0 && (
            <>
              <div className="c4-q-nav" role="navigation" aria-label="Question navigation">
                {questions.map((q, i) => {
                  const answered = (answers[q.questionId] || []).length > 0;
                  return (
                    <button
                      key={q.questionId}
                      type="button"
                      className={`c4-q-dot ${i === qIndex ? 'active' : ''} ${answered ? 'answered' : ''}`}
                      aria-label={`Question ${i + 1}${answered ? ', answered' : ', unanswered'}`}
                      aria-current={i === qIndex ? 'true' : undefined}
                      onClick={() => setQIndex(i)}
                    >
                      {i + 1}
                    </button>
                  );
                })}
              </div>
              <p className="muted small">
                Answered {answeredCount}/{questions.length}
              </p>

              {current && (
                <fieldset className="c4-exam-q">
                  <legend>
                    <span className="chip">{prettyTopic(current.topic)}</span> Q{qIndex + 1}.{' '}
                    {current.text}
                  </legend>
                  {current.options.map((opt, i) => (
                    <label key={i} className="c4-exam-opt">
                      <input
                        type={current.multi ? 'checkbox' : 'radio'}
                        name={current.questionId}
                        disabled={busy}
                        checked={(answers[current.questionId] || []).includes(i)}
                        onChange={() => toggleOption(current.questionId, i, current.multi)}
                      />
                      <span className="c4-exam-opt-text">{opt}</span>
                    </label>
                  ))}
                </fieldset>
              )}

              <div className="c4-actions">
                <button
                  type="button"
                  className="btn secondary"
                  disabled={busy || qIndex <= 0}
                  onClick={() => setQIndex((i) => Math.max(0, i - 1))}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={busy || qIndex >= questions.length - 1}
                  onClick={() => setQIndex((i) => Math.min(questions.length - 1, i + 1))}
                >
                  Next
                </button>
                <button type="button" className="btn secondary" disabled={busy} onClick={save}>
                  {busy ? 'Saving…' : 'Save answers'}
                </button>
                {!confirmSubmit ? (
                  <button type="button" className="btn" disabled={busy} onClick={() => setConfirmSubmit(true)}>
                    Submit quiz
                  </button>
                ) : (
                  <>
                    <span className="muted small">Submit and grade now?</span>
                    <button type="button" className="btn" disabled={busy} onClick={submit}>
                      Confirm submit
                    </button>
                    <button
                      type="button"
                      className="btn secondary"
                      disabled={busy}
                      onClick={() => setConfirmSubmit(false)}
                    >
                      Cancel
                    </button>
                  </>
                )}
              </div>
            </>
          )}

          {active.status === 'submitted' && active.review && (
            <div className="c4-review-list">
              <h4>Review</h4>
              {active.review.map((r) => (
                <div key={r.questionId} className="c4-exam-q">
                  <p>
                    <span className="chip">{prettyTopic(r.topic)}</span>{' '}
                    <strong>{r.isCorrect ? 'Correct' : 'Incorrect'}</strong>
                  </p>
                  <p>{r.text}</p>
                  <p className="muted small">{r.explanation}</p>
                </div>
              ))}
            </div>
          )}

          {active.result && (
            <div className="c4-sim-result">
              <h3>Observed score</h3>
              <p className="big">
                <strong>{active.result.scorePercent}%</strong> ({active.result.correctCount}/
                {active.result.total})
              </p>
              {active.preExamModel?.assessment?.practice_quiz?.usable && (
                <p className="muted small">
                  Frozen heuristic estimate (not a trained model) was{' '}
                  {Math.round(
                    (active.preExamModel.assessment.practice_quiz.predicted_score ?? 0) * 100
                  )}
                  %
                  {active.preExamModel.assessment.practice_quiz.cold_start
                    ? ' (cold-start 50% defaults)'
                    : ''}{' '}
                  (target{' '}
                  {Math.round(
                    (active.preExamModel.assessment.practice_quiz.practice_quiz_score_target ??
                      0.6) * 100
                  )}
                  %). Observed score above is from this attempt only.
                </p>
              )}
              {active.predictionOutcome && (
                <p className="muted small">
                  Prediction/outcome pair stored for future evaluation (no answer leakage into
                  features).
                </p>
              )}
              <p className="muted small">{active.result.note}</p>
              {active.result.finalizedReason === 'time_limit_exceeded' && (
                <p className="muted small">Finalized because the time limit was reached.</p>
              )}
              <h4>Topic breakdown</h4>
              <ul className="c4-unavailable">
                {(active.result.topicBreakdown || []).map((t) => (
                  <li key={t.topic}>
                    {prettyTopic(t.topic)}: {t.correct}/{t.total} ({Math.round(t.accuracy * 100)}%)
                  </li>
                ))}
              </ul>
              {weakTopics.length > 0 && (
                <div>
                  <h4>Suggested next practice</h4>
                  <p className="muted small">Based on observed weak topics in this quiz (not a live model estimate).</p>
                  <ul className="c4-day-list">
                    {weakTopics.map((t) => (
                      <li key={t}>
                        <Link className="btn secondary" to={`/c1/practice/${encodeURIComponent(t)}`}>
                          Practise {prettyTopic(t)}
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <p className="muted small">
                    Replan your study plan after practice so weak topics can influence heuristic ranking.
                  </p>
                </div>
              )}
              <p className="muted small">
                Live model-predicted score/pass remain unavailable until required inputs exist
                (shown as usable:false in pre-exam notes).
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
