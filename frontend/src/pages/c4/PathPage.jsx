import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { prettyTopic } from '../../utils/topics.js';
import {
  createPath,
  getActivePath,
  getPathRevisions,
  recordProgress,
  refreshPath,
  replanPath,
} from './c4Api.js';
import SimulationDemoPanel from './SimulationDemoPanel.jsx';
import ExamPanel from './ExamPanel.jsx';
import FeedbackPanel from './FeedbackPanel.jsx';
import './c4.css';

function statusLabel(status) {
  if (status === 'practice_verified') return 'Verified practice (session finished)';
  if (status === 'practice_observed') return 'Practice in progress (not complete)';
  if (status === 'self_reported_complete') return 'Marked done (self-reported)';
  if (status === 'overdue') return 'Overdue';
  return 'Up next';
}

const TABS = [
  { id: 'plan', label: 'Study plan' },
  { id: 'progress', label: 'Progress' },
  { id: 'exams', label: 'Mock quizzes' },
  { id: 'feedback', label: 'Feedback' },
  { id: 'sim', label: 'Model simulation demo' },
];

function kindLabel(kind) {
  if (kind === 'c1_revision') return 'Revision';
  if (kind === 'c4_quiz') return 'Quiz';
  if (kind === 'c1_practice') return 'Practice';
  return kind || 'Activity';
}

function openLabel(kind) {
  if (kind === 'c1_revision') return 'Open revision';
  if (kind === 'c4_quiz') return 'Open quiz';
  return 'Open practice';
}

export default function PathPage() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState('plan');
  const [path, setPath] = useState(null);
  const [revisions, setRevisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [prefs, setPrefs] = useState({
    studyStartDate: '',
    examDate: '',
    dailyMinutesBudget: 60,
    planDayCount: 7,
    studyDays: [1, 2, 3, 4, 5, 6],
  });
  const [planView, setPlanView] = useState('today'); // today | upcoming | overdue | completed

  const DAY_LABELS = [
    { v: 0, label: 'Sun' },
    { v: 1, label: 'Mon' },
    { v: 2, label: 'Tue' },
    { v: 3, label: 'Wed' },
    { v: 4, label: 'Thu' },
    { v: 5, label: 'Fri' },
    { v: 6, label: 'Sat' },
  ];

  const toggleStudyDay = (d) => {
    setPrefs((p) => {
      const has = p.studyDays.includes(d);
      const next = has ? p.studyDays.filter((x) => x !== d) : [...p.studyDays, d].sort();
      return { ...p, studyDays: next.length ? next : p.studyDays };
    });
  };

  const prefsBody = () => {
    const body = {
      dailyMinutesBudget: Number(prefs.dailyMinutesBudget) || 60,
      planDayCount: Number(prefs.planDayCount) || 7,
      studyDays: prefs.studyDays,
    };
    if (prefs.studyStartDate) body.studyStartDate = prefs.studyStartDate;
    if (prefs.examDate) body.examDate = prefs.examDate;
    return body;
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    setInfo('');
    try {
      const active = await getActivePath();
      setPath(active);
      if (active?.schedule?.prefs) {
        setPrefs((p) => ({
          ...p,
          studyStartDate: active.schedule.prefs.studyStartDate || '',
          examDate: active.schedule.prefs.examDate || '',
          dailyMinutesBudget: active.schedule.prefs.dailyMinutesBudget || 60,
          planDayCount: active.schedule.prefs.planDayCount || 7,
          studyDays: active.schedule.prefs.studyDays || p.studyDays,
        }));
      }
      try {
        const rev = await getPathRevisions(active.pathId);
        setRevisions(rev.revisions || []);
      } catch {
        setRevisions([]);
      }
    } catch (err) {
      if (err.status === 404 || err.code === 'no_active_path') {
        setPath(null);
      } else if (err.status === 409 || err.code === 'diagnostic_required') {
        setPath(null);
        setError(err.message);
      } else {
        setPath(null);
        setError(err.message || 'Could not load your learning path');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const requested = searchParams.get('tab');
    if (TABS.some((t) => t.id === requested)) setTab(requested);
  }, [searchParams]);

  useEffect(() => {
    load();
  }, [load]);

  const onCreate = async () => {
    setBusy(true);
    setError('');
    setInfo('');
    try {
      if (!prefs.studyDays?.length) {
        setError('Select at least one study day');
        setBusy(false);
        return;
      }
      const body = {
        ...prefsBody(),
        clientRequestId: `ui-${user?.student_id || user?.sub || 'student'}-${Date.now()}`,
      };
      const created = await createPath(body);
      setPath(created);
      if (created.reused) setInfo('Showing your existing active path.');
      else setInfo('Created a daily study plan from your C1 twin (heuristic ranking).');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onComplete = async (activityId) => {
    if (!path) return;
    setBusy(true);
    setError('');
    setInfo('');
    try {
      const updated = await recordProgress(path.pathId, activityId);
      setPath(updated);
      setInfo(
        updated.progress?.duplicate
          ? 'Already marked done.'
          : 'Self-reported complete. Use Refresh after C1 practice for verified completion.'
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onReplan = async () => {
    if (!path) return;
    setBusy(true);
    setError('');
    setInfo('');
    try {
      const updated = await replanPath(path.pathId, {
        ...prefsBody(),
        expectedRevision: path.revision,
      });
      setPath(updated);
      setInfo(`Path updated to revision ${updated.revision}. Completed items were kept.`);
      const rev = await getPathRevisions(updated.pathId);
      setRevisions(rev.revisions || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const onRefresh = async () => {
    if (!path) return;
    setBusy(true);
    setError('');
    setInfo('');
    try {
      const updated = await refreshPath(path.pathId, {
        expectedRevision: path.revision,
        expectedUpdatedAt: path.updatedAt,
      });
      setPath(updated);
      setInfo(updated.refreshNote || 'Refreshed from C1.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div>
        <h1>Adaptive learning path</h1>
        <p className="muted">Loading your study plan…</p>
      </div>
    );
  }

  const diagnosticBlocked = /diagnostic/i.test(error || '');
  const schedule = path?.schedule;
  const today = schedule?.summary?.today;

  return (
    <div className="c4-path">
      <h1>Adaptive learning path</h1>
      <p className="muted">
        Personalized daily study plan from your C1 learner state, plus practice links, mock quizzes,
        and feedback. Operational ranking uses the named heuristic — not RL.
      </p>

      <div className="c4-tabs" role="tablist" aria-label="C4 sections">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`c4-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'sim' && <SimulationDemoPanel />}
      {tab === 'exams' && <ExamPanel focusTopic={searchParams.get('focusTopic')} />}
      {tab === 'feedback' && <FeedbackPanel />}

      {(tab === 'plan' || tab === 'progress') && (
        <>
          {error && (
            <div className="panel">
              <p className="error">{error}</p>
              {diagnosticBlocked && (
                <p>
                  <Link className="btn" to="/c1/diagnostic">
                    Take diagnostic
                  </Link>
                </p>
              )}
              <button type="button" className="btn secondary" onClick={load}>
                Retry
              </button>
            </div>
          )}

          {info && <p className="muted small">{info}</p>}

          {!path && !diagnosticBlocked && tab === 'plan' && (
            <div className="panel">
              <h2>Create your daily study plan</h2>
              <p className="muted">
                Uses C1 twin mastery (0–100) and practice eligibility. Durations are planning
                estimates.
              </p>
              <div className="c4-sim-form">
                <label className="c4-label">
                  Study start date
                  <input
                    type="date"
                    value={prefs.studyStartDate}
                    onChange={(e) => setPrefs({ ...prefs, studyStartDate: e.target.value })}
                  />
                </label>
                <label className="c4-label">
                  Target / exam date (optional)
                  <input
                    type="date"
                    value={prefs.examDate}
                    onChange={(e) => setPrefs({ ...prefs, examDate: e.target.value })}
                  />
                </label>
                <label className="c4-label">
                  Daily time budget (minutes)
                  <input
                    type="number"
                    min={15}
                    max={720}
                    value={prefs.dailyMinutesBudget}
                    onChange={(e) => setPrefs({ ...prefs, dailyMinutesBudget: e.target.value })}
                  />
                </label>
                <label className="c4-label">
                  Plan length (days)
                  <input
                    type="number"
                    min={1}
                    max={21}
                    value={prefs.planDayCount}
                    onChange={(e) => setPrefs({ ...prefs, planDayCount: e.target.value })}
                  />
                </label>
                <fieldset className="c4-label">
                  <legend>Study days</legend>
                  <div className="c4-day-toggles">
                    {DAY_LABELS.map((d) => (
                      <label key={d.v} className="c4-day-toggle">
                        <input
                          type="checkbox"
                          checked={prefs.studyDays.includes(d.v)}
                          onChange={() => toggleStudyDay(d.v)}
                        />
                        {d.label}
                      </label>
                    ))}
                  </div>
                </fieldset>
              </div>
              <button type="button" className="btn" disabled={busy} onClick={onCreate}>
                {busy ? 'Creating…' : 'Create learning path'}
              </button>
            </div>
          )}

          {path && tab === 'plan' && (
            <>
              <div className="panel c4-meta">
                <div>
                  <span className="chip">{path.strategy}</span>
                  <span className="muted small"> revision {path.revision}</span>
                </div>
                <div className="c4-overview" aria-label="Plan overview">
                  <span className="chip">
                    Today {schedule?.summary?.today?.activities?.length ?? 0}
                  </span>
                  <span className="chip">
                    Upcoming {(schedule?.summary?.upcomingDays || []).reduce((n, d) => n + (d.activities?.length || 0), 0)}
                  </span>
                  <span className="chip">Overdue {schedule?.summary?.overdueCount ?? 0}</span>
                  <span className="chip">Done {schedule?.summary?.completedCount ?? 0}</span>
                  {(schedule?.unscheduled || []).length > 0 && (
                    <span className="chip bad">Unscheduled {schedule.unscheduled.length}</span>
                  )}
                </div>
                <p className="muted small">
                  Snapshot{' '}
                  {path.sourceSnapshotAt ? new Date(path.sourceSnapshotAt).toLocaleString() : '—'}
                  {path.sourceSnapshot?.insights_available === false
                    ? ' · C1 insights unavailable; ranked from twin scores'
                    : ''}
                </p>
                {path.multiActionPolicy?.activated && path.multiActionPolicy?.protocol === 'se-path-multi-v2' ? (
                  <div className="panel c4-reco" aria-label="se-path-multi-v2 next activity">
                    <h3>Next activity</h3>
                    <p>
                      <strong>{prettyTopic(path.multiActionPolicy.topic)}</strong>
                      <span className="chip">{path.multiActionPolicy.action_type}</span>
                      <span className="chip">se-path-multi-v2 · synthetic validation</span>
                    </p>
                    <p className="muted small">
                      MaskablePPO selected this eligible practice, revision, or quiz. Seed{' '}
                      {path.multiActionPolicy.selected_seed ?? '—'}, revision{' '}
                      {path.multiActionPolicy.training_revision || '—'}. The checkpoint passed its
                      declared simulator floor for simulated mastery change. This is not classification
                      accuracy and not a real-student learning result. Calendar dates and time budgets
                      stay on weakest_stored_mastery_v1.
                    </p>
                    {path.multiActionPolicy.launch_path ? (
                      <Link className="btn" to={path.multiActionPolicy.launch_path}>
                        Open selected activity
                      </Link>
                    ) : null}
                    <p className="muted small">
                      Catalogue {(path.multiActionPolicy.catalogue_hash || '').slice(0, 12)}… · checkpoint{' '}
                      {(path.multiActionPolicy.checkpoint_sha256 || '').slice(0, 12)}…
                    </p>
                  </div>
                ) : (
                  <p className="muted small">
                    se-path-multi-v2 was not used
                    {path.multiActionPolicy?.reason ? ` (${path.multiActionPolicy.reason})` : ''}. The
                    list below is the heuristic plan, or an older experimental practice pin. It is not an
                    RL action.
                  </p>
                )}
                {path.modelRecommendation?.ok && path.modelRecommendation.recommended_topic ? (
                  <div className="panel c4-reco" aria-label="Experimental next practice recommendation">
                    <h3>Experimental next practice</h3>
                    <p>
                      <strong>{prettyTopic(path.modelRecommendation.recommended_topic)}</strong>
                      <span className="chip">se-path-sim-v1 · experimental</span>
                      {path.nextActivityTopic === path.modelRecommendation.recommended_topic && (
                        <span className="chip ok">pinned on plan</span>
                      )}
                    </p>
                    <p className="muted small">
                      Simulation-trained experimental recommendation for the next eligible practice
                      topic. Calendar dates and time budgets still use weakest_stored_mastery_v1 —
                      not an RL multi-day forecast. Not real-exam validated.
                    </p>
                    <Link className="btn" to={path.modelRecommendation.launch_path}>
                      Start next practice
                    </Link>
                    <details className="c4-details">
                      <summary>Serving assumptions &amp; provenance</summary>
                      <p className="muted small">
                        Protocol {path.modelRecommendation.protocol} · catalogue{' '}
                        {(path.modelRecommendation.catalogue_hash || '').slice(0, 12)}… · input{' '}
                        {path.modelRecommendation.input_timestamp
                          ? new Date(path.modelRecommendation.input_timestamp).toLocaleString()
                          : '—'}
                      </p>
                      <p className="muted small">
                        step_frac ≈ deduplicated quiz_answer attempts since episode start ÷ 40
                        (Mark done never counted) — a serving approximation of training attempt
                        units; training/serving mismatch is <em>not</em> claimed eliminated.{' '}
                        <strong>
                          prior_strength = {path.liveModelEpisode?.prior_strength ?? 0.45}
                        </strong>{' '}
                        is an <em>assumed</em> protocol constant, not measured student data.
                        Fallback ranking stays weakest_stored_mastery_v1 when the model is
                        unavailable.
                      </p>
                    </details>
                  </div>
                ) : path.multiActionPolicy?.activated &&
                  path.multiActionPolicy?.protocol === 'se-path-multi-v2' ? null : (
                  <p className="muted small">
                    Path model fallback ({path.modelRecommendation?.fallback || 'weakest_stored_mastery_v1'}
                    ):{' '}
                    {path.modelRecommendation?.reason ||
                      path.modelEstimates?.path?.reason ||
                      'unavailable — heuristic plan remains in use.'}{' '}
                    This fallback is not an RL action.
                  </p>
                )}
                <details className="c4-details">
                  <summary>Progress and engagement</summary>
                  {path.engagement ? (
                    <div className="muted small">
                      <p>
                        Completion rate:{' '}
                        {path.engagement.completionRate == null
                          ? 'unavailable'
                          : `${Math.round(path.engagement.completionRate * 100)}%`}{' '}
                        · streak {path.engagement.studyStreakDays} day(s) · active days{' '}
                        {path.engagement.activeDaysInWindow}/{path.engagement.windowDays} (
                        {path.engagement.timezone})
                      </p>
                      <p>
                        Verified {path.engagement.verifiedCompletions} · self-reported{' '}
                        {path.engagement.selfReportedCompletions} · in progress{' '}
                        {path.engagement.observedInProgress}. Self-report is not verified practice.
                      </p>
                      {path.activityTypeLimits?.coding_exercise?.scheduled === false && (
                        <p>{path.activityTypeLimits.coding_exercise.reason}</p>
                      )}
                    </div>
                  ) : (
                    <p className="muted small">Engagement summary unavailable.</p>
                  )}
                </details>
                <details className="c4-details">
                  <summary>Live model estimate status</summary>
                  <p className="muted small">
                    {path.modelEstimates
                      ? `Path inputs: ${path.modelEstimates.path?.usable ? 'usable' : 'unavailable'} (${path.modelEstimates.path?.code}). Supervised response: blocked (no item difficulty). ${path.modelEstimates.label || ''}`
                      : 'No estimate payload.'}{' '}
                    Operational daily plan uses weakest_stored_mastery_v1 — not RL.
                  </p>
                </details>
                <div className="c4-actions">
                  <button type="button" className="btn secondary" disabled={busy} onClick={onRefresh}>
                    Refresh from C1
                  </button>
                  <button type="button" className="btn secondary" disabled={busy} onClick={onReplan}>
                    Replan
                  </button>
                  <button type="button" className="btn secondary" disabled={busy} onClick={load}>
                    Reload saved plan
                  </button>
                </div>
              </div>

              <div className="c4-subtabs" role="tablist" aria-label="Plan views">
                {['today', 'upcoming', 'overdue', 'completed'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    role="tab"
                    className={`c4-tab ${planView === v ? 'active' : ''}`}
                    aria-selected={planView === v}
                    onClick={() => setPlanView(v)}
                  >
                    {v.charAt(0).toUpperCase() + v.slice(1)}
                  </button>
                ))}
              </div>

              <div className="panel">
                <h2>Schedule preferences</h2>
                <div className="c4-sim-form">
                  <label className="c4-label">
                    Study start
                    <input
                      type="date"
                      value={prefs.studyStartDate}
                      onChange={(e) => setPrefs({ ...prefs, studyStartDate: e.target.value })}
                    />
                  </label>
                  <label className="c4-label">
                    Exam / target date
                    <input
                      type="date"
                      value={prefs.examDate}
                      onChange={(e) => setPrefs({ ...prefs, examDate: e.target.value })}
                    />
                  </label>
                  <label className="c4-label">
                    Daily minutes
                    <input
                      type="number"
                      min={15}
                      max={720}
                      value={prefs.dailyMinutesBudget}
                      onChange={(e) => setPrefs({ ...prefs, dailyMinutesBudget: e.target.value })}
                    />
                  </label>
                  <label className="c4-label">
                    Plan length (days)
                    <input
                      type="number"
                      min={1}
                      max={21}
                      value={prefs.planDayCount}
                      onChange={(e) => setPrefs({ ...prefs, planDayCount: e.target.value })}
                    />
                  </label>
                  <fieldset className="c4-label">
                    <legend>Study days</legend>
                    <div className="c4-day-toggles">
                      {DAY_LABELS.map((d) => (
                        <label key={d.v} className="c4-day-toggle">
                          <input
                            type="checkbox"
                            checked={prefs.studyDays.includes(d.v)}
                            onChange={() => toggleStudyDay(d.v)}
                          />
                          {d.label}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                </div>
                <p className="muted small">
                  {schedule?.summary?.estimatedMinutesNote ||
                    'Durations are estimates used for planning only. Use Replan to apply preference changes.'}
                </p>
              </div>

              {planView === 'today' && (
                <div className="panel">
                  <h2>Today {today ? `(${today.date})` : ''}</h2>
                  {!today || today.activities.length === 0 ? (
                    <p className="muted">No activities scheduled for today.</p>
                  ) : (
                    <ul className="c4-day-list">
                      {today.activities.map((a) => (
                        <li key={a.activity_id}>
                          <strong>{prettyTopic(a.topic)}</strong>
                          <span className="chip">{a.status || 'scheduled'}</span>
                          {a.next_activity && (
                            <span className="chip ok">next {kindLabel(a.kind).toLowerCase()}</span>
                          )}
                          <span className="muted small">
                            {' '}
                            · ~{a.estimated_minutes} min (estimate) · {a.priority_reason}
                          </span>
                          <div className="c4-item-actions">
                            <Link className="btn" to={a.launch_path}>
                              {a.next_activity && a.kind === 'c1_practice'
                                ? 'Start next practice'
                                : openLabel(a.kind)}
                            </Link>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {planView === 'upcoming' && (
                <div className="panel">
                  <h2>Upcoming days</h2>
                  {(schedule?.summary?.upcomingDays || []).length === 0 ? (
                    <p className="muted small">No upcoming scheduled days.</p>
                  ) : (
                    (schedule.summary.upcomingDays || []).map((d) => (
                      <div key={d.date} className="c4-day-block">
                        <h3>{d.date}</h3>
                        <p className="muted small">
                          ~{d.totalEstimatedMinutes} estimated minutes · capacity{' '}
                          {d.capacityActivities} activities
                        </p>
                        <ul className="c4-day-list">
                          {d.activities.map((a) => (
                            <li key={a.activity_id}>
                              <Link to={a.launch_path}>{prettyTopic(a.topic)}</Link>
                              <span className="muted small"> · ~{a.estimated_minutes} min</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))
                  )}
                </div>
              )}

              {planView === 'overdue' && (
                <div className="panel">
                  <h2>Overdue</h2>
                  {path.activities.filter((a) => a.status === 'overdue').length === 0 ? (
                    <p className="muted small">Nothing overdue.</p>
                  ) : (
                    <ul className="c4-day-list">
                      {path.activities
                        .filter((a) => a.status === 'overdue')
                        .map((a) => (
                          <li key={a.activityId}>
                            <strong>{prettyTopic(a.topic)}</strong>
                            <span className="muted small">
                              {' '}
                              · scheduled {a.scheduledDate || '—'}
                            </span>
                            <div className="c4-item-actions">
                              <Link className="btn" to={a.launchPath}>
                                {openLabel(a.kind)}
                              </Link>
                            </div>
                          </li>
                        ))}
                    </ul>
                  )}
                </div>
              )}

              {planView === 'completed' && (
                <div className="panel">
                  <h2>Completed</h2>
                  {path.activities.filter(
                    (a) =>
                      a.status === 'self_reported_complete' || a.status === 'practice_verified'
                  ).length === 0 ? (
                    <p className="muted small">No completed activities yet.</p>
                  ) : (
                    <ul className="c4-day-list">
                      {path.activities
                        .filter(
                          (a) =>
                            a.status === 'self_reported_complete' ||
                            a.status === 'practice_verified'
                        )
                        .map((a) => (
                          <li key={a.activityId}>
                            <strong>{prettyTopic(a.topic)}</strong>
                            <span className="chip">{statusLabel(a.status)}</span>
                            <span className="muted small">
                              {' '}
                              · {a.completedAt ? new Date(a.completedAt).toLocaleString() : ''}
                            </span>
                          </li>
                        ))}
                    </ul>
                  )}
                </div>
              )}

              {(schedule?.unscheduled || []).length > 0 && (
                <div className="panel">
                  <h2>Could not fit in budget</h2>
                  <p className="muted small">Not silently dropped — adjust budget or plan length.</p>
                  <ul className="c4-unavailable">
                    {schedule.unscheduled.map((u) => (
                      <li key={u.activity_id}>
                        <strong>{prettyTopic(u.topic)}</strong>
                        <span className="muted"> — {u.reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {path && tab === 'progress' && (
            <>
              <div className="panel c4-meta">
                <p className="muted small">
                  Overdue: {schedule?.summary?.overdueCount ?? 0} · Completed:{' '}
                  {schedule?.summary?.completedCount ?? 0} · Path revision {path.revision}
                </p>
                <p className="muted small">
                  C1 snapshot:{' '}
                  {path.sourceSnapshotAt
                    ? new Date(path.sourceSnapshotAt).toLocaleString()
                    : '—'}
                  {path.updatedAt
                    ? ` · Plan updated ${new Date(path.updatedAt).toLocaleString()}`
                    : ''}
                </p>
                <p className="muted small">
                  Statuses distinguish self-reported completion, practice participation
                  (observed), and finished verified C1 practice sessions. No invented
                  improvement charts.
                </p>
                <div className="c4-actions">
                  <button type="button" className="btn secondary" disabled={busy} onClick={onRefresh}>
                    Refresh from C1
                  </button>
                  <button type="button" className="btn secondary" disabled={busy} onClick={onReplan}>
                    Replan from latest mastery
                  </button>
                </div>
              </div>

              <ol className="c4-list">
                {path.activities.map((a) => (
                  <li key={a.activityId} className="panel c4-item" data-status={a.status}>
                    <div className="c4-item-head">
                      <strong>{prettyTopic(a.topic)}</strong>
                      <span className="chip">{kindLabel(a.kind)}</span>
                      <span className="chip">{statusLabel(a.status)}</span>
                      {a.nextActivity && (
                        <span className="chip ok">
                          next · {a.nextActivitySource || 'model'}
                        </span>
                      )}
                    </div>
                    <p className="muted small">{a.recommendationReason}</p>
                    {a.scheduledDate && (
                      <p className="muted small">
                        Scheduled {a.scheduledDate}
                        {a.estimatedMinutes != null
                          ? ` · ~${a.estimatedMinutes} min (estimate)`
                          : ''}
                      </p>
                    )}
                    {a.rankScore != null && (
                      <p className="muted small">
                        Rank score at plan time: {a.rankScore}
                        {a.scoreSource ? ` (${a.scoreSource})` : ''} on C1 0–100 scale
                      </p>
                    )}
                    {a.completionKind && (
                      <p className="muted small">
                        Completion: {a.completionKind}
                        {a.completionKind === 'self_reported'
                          ? ' (not an assessed C1 result)'
                          : ''}
                        {a.completionKind === 'practice_observed'
                          ? ' — finish the C1 practice session to verify'
                          : ''}
                        {a.completedAt
                          ? ` · ${new Date(a.completedAt).toLocaleString()}`
                          : ''}
                      </p>
                    )}
                    {a.practiceEvidence?.sessionId && (
                      <p className="muted small">
                        Linked C1 session: {a.practiceEvidence.sessionId}
                        {a.practiceEvidence.finishedAt
                          ? ` · finished ${new Date(a.practiceEvidence.finishedAt).toLocaleString()}`
                          : a.practiceEvidence.inProgress
                            ? ' · in progress'
                            : ''}
                        {a.practiceEvidence.answered != null && a.practiceEvidence.total != null
                          ? ` · ${a.practiceEvidence.answered}/${a.practiceEvidence.total} answered`
                          : ''}
                      </p>
                    )}
                    {a.eligibleSince && (
                      <p className="muted small">
                        Eligible since {new Date(a.eligibleSince).toLocaleString()}
                      </p>
                    )}
                    <div className="c4-item-actions">
                      <Link className="btn" to={a.launchPath}>
                        {openLabel(a.kind)}
                      </Link>
                      {(a.status === 'pending' ||
                        a.status === 'overdue' ||
                        a.status === 'practice_observed') && (
                        <button
                          type="button"
                          className="btn secondary"
                          disabled={busy}
                          onClick={() => onComplete(a.activityId)}
                        >
                          Mark done
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ol>

              {path.unavailable?.length > 0 && (
                <div className="panel">
                  <h2>Not included right now</h2>
                  <ul className="c4-unavailable">
                    {path.unavailable.map((u) => (
                      <li key={u.topic}>
                        <strong>{prettyTopic(u.topic)}</strong>
                        <span className="muted"> — {u.reason}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="panel">
                <h2>Revision history</h2>
                {revisions.length === 0 ? (
                  <p className="muted small">No archived revisions yet.</p>
                ) : (
                  <ul className="c4-unavailable">
                    {revisions.map((r) => (
                      <li key={r.revisionId}>
                        Rev {r.revision} · {r.reason} ·{' '}
                        {r.archivedAt ? new Date(r.archivedAt).toLocaleString() : '—'}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
