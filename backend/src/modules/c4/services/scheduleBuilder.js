/**
 * Calendar daily schedule for C4 heuristic paths.
 * Duration values are labelled estimates (assumptions), not measured study time.
 */

const DAY_MS = 24 * 60 * 60 * 1000;
export const DEFAULT_ESTIMATED_MINUTES = 15;
export const DEFAULT_DAILY_BUDGET = 60;
export const DEFAULT_STUDY_DAYS = Object.freeze([1, 2, 3, 4, 5, 6]); // Mon–Sat
export const MAX_PLAN_DAYS = 21;
export const PREFERRED_PLAN_DAYS = 7;

function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code;
  return err;
}

export function parseIsoDate(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s || ''));
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (Number.isNaN(d.getTime()) || d.getMonth() !== Number(m[2]) - 1) return null;
  d.setHours(0, 0, 0, 0);
  return d;
}

export function isoDate(d) {
  const x = new Date(d);
  return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`;
}

function startOfDay(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function daysBetween(a, b) {
  return Math.round((startOfDay(b) - startOfDay(a)) / DAY_MS);
}

/**
 * Validate and normalise schedule preferences from create/replan body.
 */
export function parseSchedulePrefs(body = {}, now = new Date()) {
  const today = startOfDay(now);
  let studyStart = body.studyStartDate ? parseIsoDate(body.studyStartDate) : today;
  if (!studyStart) throw httpError(400, 'studyStartDate must be YYYY-MM-DD');
  if (studyStart < today) studyStart = today;

  let examDate = null;
  if (body.examDate != null && body.examDate !== '') {
    examDate = parseIsoDate(body.examDate);
    if (!examDate) throw httpError(400, 'examDate must be YYYY-MM-DD');
    if (examDate < studyStart) {
      throw httpError(400, 'examDate must be on or after studyStartDate', 'invalid_date_range');
    }
  }

  let dailyMinutesBudget = body.dailyMinutesBudget != null
    ? Number(body.dailyMinutesBudget)
    : DEFAULT_DAILY_BUDGET;
  if (!Number.isFinite(dailyMinutesBudget) || dailyMinutesBudget <= 0 || dailyMinutesBudget > 12 * 60) {
    throw httpError(400, 'dailyMinutesBudget must be a positive number of minutes (max 720)');
  }

  let estimatedMinutes = body.estimatedMinutesPerActivity != null
    ? Number(body.estimatedMinutesPerActivity)
    : DEFAULT_ESTIMATED_MINUTES;
  if (!Number.isFinite(estimatedMinutes) || estimatedMinutes <= 0 || estimatedMinutes > dailyMinutesBudget) {
    throw httpError(
      400,
      'estimatedMinutesPerActivity must be > 0 and not exceed dailyMinutesBudget',
      'invalid_budget'
    );
  }

  let studyDays = body.studyDays;
  if (studyDays == null) studyDays = [...DEFAULT_STUDY_DAYS];
  if (!Array.isArray(studyDays) || studyDays.length === 0) {
    throw httpError(400, 'studyDays must be a non-empty array of weekday numbers 0–6 (Sun=0)');
  }
  studyDays = [...new Set(studyDays.map(Number))];
  if (studyDays.some((d) => !Number.isInteger(d) || d < 0 || d > 6)) {
    throw httpError(400, 'studyDays entries must be integers 0–6 (Sunday=0)');
  }

  let planDayCount = body.planDayCount != null ? Number(body.planDayCount) : PREFERRED_PLAN_DAYS;
  if (!Number.isFinite(planDayCount) || planDayCount < 1 || planDayCount > MAX_PLAN_DAYS) {
    throw httpError(400, `planDayCount must be between 1 and ${MAX_PLAN_DAYS}`);
  }
  if (examDate) {
    const span = daysBetween(studyStart, examDate);
    if (span >= 0) planDayCount = Math.min(planDayCount, Math.max(1, span));
  }

  return {
    studyStartDate: isoDate(studyStart),
    examDate: examDate ? isoDate(examDate) : null,
    dailyMinutesBudget,
    estimatedMinutesPerActivity: estimatedMinutes,
    studyDays,
    planDayCount,
  };
}

/**
 * Assign pending activities onto study days without exceeding daily budget.
 * Excess work is listed in unscheduled with an explicit reason (never silently dropped).
 */
export function buildDailySchedule({
  activities = [],
  prefs,
  now = new Date(),
}) {
  const p = prefs || parseSchedulePrefs({}, now);
  const est = p.estimatedMinutesPerActivity;
  const budget = p.dailyMinutesBudget;
  const perDay = Math.max(1, Math.floor(budget / est));

  const studyDaySet = new Set(p.studyDays);
  const start = parseIsoDate(p.studyStartDate);
  const daySlots = [];
  let cursor = new Date(start);
  let guard = 0;
  while (daySlots.length < p.planDayCount && guard < 120) {
    if (studyDaySet.has(cursor.getDay())) {
      daySlots.push({
        date: isoDate(cursor),
        weekday: cursor.getDay(),
        activities: [],
        total_estimated_minutes: 0,
        capacity: perDay,
      });
    }
    cursor = new Date(cursor.getTime() + DAY_MS);
    guard += 1;
  }

  // practice_observed = in progress, still needs scheduling until verified/self-reported.
  const pending = activities.filter(
    (a) => a.status === 'pending' || a.status === 'overdue' || a.status === 'practice_observed'
  );
  const completed = activities.filter(
    (a) => a.status === 'self_reported_complete' || a.status === 'practice_verified'
  );

  const scheduledActivities = [];
  const unscheduled = [];
  let slotIdx = 0;
  for (const act of pending) {
    while (slotIdx < daySlots.length && daySlots[slotIdx].activities.length >= daySlots[slotIdx].capacity) {
      slotIdx += 1;
    }
    if (slotIdx >= daySlots.length) {
      unscheduled.push({
        activity_id: act.activity_id,
        topic: act.topic,
        reason:
          'Could not fit within the selected plan window and daily time budget without exceeding estimated minutes. Increase budget, study days, or plan length.',
      });
      scheduledActivities.push({
        ...act,
        scheduled_date: null,
        estimated_minutes: est,
        schedule_status: 'unscheduled',
      });
      continue;
    }
    const slot = daySlots[slotIdx];
    const enriched = {
      ...act,
      scheduled_date: slot.date,
      estimated_minutes: est,
      schedule_status: 'scheduled',
    };
    slot.activities.push({
      activity_id: act.activity_id,
      topic: act.topic,
      kind: act.kind,
      launch_path: act.launch_path,
      estimated_minutes: est,
      priority_reason: act.recommendation_reason,
      status: act.status,
      completion_kind: act.completion_kind,
      next_activity: !!act.next_activity,
      next_activity_source: act.next_activity_source || null,
    });
    slot.total_estimated_minutes += est;
    scheduledActivities.push(enriched);
  }

  const todayIso = isoDate(now);
  const days = daySlots.map((d) => {
    let bucket = 'upcoming';
    if (d.date < todayIso) bucket = 'past';
    else if (d.date === todayIso) bucket = 'today';
    return {
      date: d.date,
      weekday: d.weekday,
      bucket,
      totalEstimatedMinutes: d.total_estimated_minutes,
      capacityActivities: d.capacity,
      activities: d.activities,
      note: 'Durations are estimates (assumption), not measured study time.',
    };
  });

  // Mark overdue: pending with scheduled_date before today
  const withOverdue = [
    ...completed.map((a) => ({
      ...a,
      scheduled_date: a.scheduled_date || null,
      estimated_minutes: a.estimated_minutes || est,
      schedule_status: 'completed',
    })),
    ...scheduledActivities.map((a) => {
      if (
        a.status === 'pending' &&
        a.scheduled_date &&
        a.scheduled_date < todayIso
      ) {
        return { ...a, status: 'overdue', schedule_status: 'overdue' };
      }
      return a;
    }),
  ];

  return {
    prefs: {
      studyStartDate: p.studyStartDate,
      examDate: p.examDate,
      dailyMinutesBudget: budget,
      estimatedMinutesPerActivity: est,
      studyDays: p.studyDays,
      planDayCount: p.planDayCount,
    },
    days,
    unscheduled,
    activities: withOverdue,
    summary: {
      today: days.find((d) => d.bucket === 'today') || null,
      upcomingDays: days.filter((d) => d.bucket === 'upcoming'),
      overdueCount: withOverdue.filter((a) => a.status === 'overdue').length,
      completedCount: completed.length,
      unscheduledCount: unscheduled.length,
      estimatedMinutesNote:
        'Activity durations are planning estimates (default 15 minutes) and may not match actual time spent.',
    },
  };
}
