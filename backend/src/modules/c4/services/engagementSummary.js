/**
 * Engagement summary from C4 path activities.
 * Day boundaries use Asia/Colombo (UTC+5:30). Missing activity is not zero mastery.
 * Self-reported and practice-verified counts stay separate.
 */

export const ENGAGEMENT_TIMEZONE = 'Asia/Colombo';
export const ENGAGEMENT_WINDOW_DAYS = 14;

export function colomboDateKey(date) {
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: ENGAGEMENT_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(d);
}

function addDaysKey(key, delta) {
  const [y, m, d] = key.split('-').map(Number);
  const utc = Date.UTC(y, m - 1, d) + delta * 86400000;
  const x = new Date(utc);
  return `${x.getUTCFullYear()}-${String(x.getUTCMonth() + 1).padStart(2, '0')}-${String(x.getUTCDate()).padStart(2, '0')}`;
}

/**
 * @param {object[]} activities
 * @param {Date} [now]
 */
export function summarizeEngagement(activities = [], now = new Date()) {
  const today = colomboDateKey(now);
  const windowStart = addDaysKey(today, -(ENGAGEMENT_WINDOW_DAYS - 1));

  let verified = 0;
  let selfReported = 0;
  let observed = 0;
  let pending = 0;
  const completionDays = new Set();

  for (const a of activities || []) {
    const kind = a.completion_kind || a.completionKind;
    const status = a.status;
    if (kind === 'practice_verified' || status === 'practice_verified') verified += 1;
    else if (kind === 'self_reported' || status === 'self_reported_complete') selfReported += 1;
    else if (kind === 'practice_observed' || status === 'practice_observed') observed += 1;
    else pending += 1;

    const done =
      kind === 'practice_verified' ||
      kind === 'self_reported' ||
      status === 'practice_verified' ||
      status === 'self_reported_complete';
    if (done && a.completed_at) {
      const key = colomboDateKey(a.completed_at);
      if (key && key >= windowStart && key <= today) completionDays.add(key);
    }
  }

  const scheduled = verified + selfReported + observed + pending;
  const completed = verified + selfReported;
  const completionRate = scheduled > 0 ? completed / scheduled : null;

  let streak = 0;
  let cursor = today;
  const yesterday = addDaysKey(today, -1);
  if (!completionDays.has(today) && completionDays.has(yesterday)) cursor = yesterday;
  else if (!completionDays.has(today)) cursor = null;
  while (cursor && completionDays.has(cursor)) {
    streak += 1;
    cursor = addDaysKey(cursor, -1);
  }

  return {
    timezone: ENGAGEMENT_TIMEZONE,
    windowDays: ENGAGEMENT_WINDOW_DAYS,
    windowStart,
    asOf: today,
    completionRate,
    completionRateNote:
      completionRate == null
        ? 'No scheduled activities — completion rate is unavailable, not zero mastery.'
        : 'Completed (verified or self-reported) / all activities on the current plan. Self-report is not verified practice.',
    verifiedCompletions: verified,
    selfReportedCompletions: selfReported,
    observedInProgress: observed,
    pending,
    studyStreakDays: streak,
    streakNote:
      'Consecutive Asia/Colombo calendar days with at least one verified or self-reported completion, ending today (or yesterday if today has none yet).',
    activityFrequencyPerDay:
      ENGAGEMENT_WINDOW_DAYS > 0 ? completionDays.size / ENGAGEMENT_WINDOW_DAYS : null,
    activeDaysInWindow: completionDays.size,
    frequencyNote: `Distinct completion days in the last ${ENGAGEMENT_WINDOW_DAYS} Colombo days, divided by ${ENGAGEMENT_WINDOW_DAYS}.`,
  };
}
