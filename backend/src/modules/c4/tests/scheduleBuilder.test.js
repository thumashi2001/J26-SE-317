import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildDailySchedule,
  parseSchedulePrefs,
  isoDate,
} from '../services/scheduleBuilder.js';

test('rejects invalid date range and negative budget', () => {
  assert.throws(
    () => parseSchedulePrefs({ studyStartDate: '2026-10-20', examDate: '2026-10-10' }),
    (e) => e.status === 400
  );
  assert.throws(
    () => parseSchedulePrefs({ dailyMinutesBudget: -5 }),
    (e) => e.status === 400
  );
  assert.throws(
    () => parseSchedulePrefs({ estimatedMinutesPerActivity: 90, dailyMinutesBudget: 60 }),
    (e) => e.status === 400
  );
});

test('schedules within budget and reports unscheduled explicitly', () => {
  const now = new Date(2026, 9, 15); // Thu
  const prefs = parseSchedulePrefs(
    {
      studyStartDate: isoDate(now),
      dailyMinutesBudget: 30,
      estimatedMinutesPerActivity: 15,
      planDayCount: 2,
      studyDays: [1, 2, 3, 4, 5],
    },
    now
  );
  const activities = Array.from({ length: 8 }, (_, i) => ({
    activity_id: `a${i}`,
    topic: `t${i}`,
    kind: 'c1_practice',
    launch_path: `/c1/practice/t${i}`,
    status: 'pending',
    recommendation_reason: 'test',
  }));
  const built = buildDailySchedule({ activities, prefs, now });
  assert.ok(built.unscheduled.length > 0);
  assert.ok(built.summary.unscheduledCount > 0);
  const scheduledMins = built.days.reduce((s, d) => s + d.totalEstimatedMinutes, 0);
  assert.ok(scheduledMins <= prefs.dailyMinutesBudget * prefs.planDayCount);
  assert.match(built.summary.estimatedMinutesNote, /estimate/i);
});

test('marks overdue pending items before today', () => {
  const now = new Date(2026, 9, 20);
  const prefs = parseSchedulePrefs(
    {
      studyStartDate: '2026-10-15',
      dailyMinutesBudget: 60,
      estimatedMinutesPerActivity: 15,
      planDayCount: 3,
      studyDays: [1, 2, 3, 4, 5],
    },
    new Date(2026, 9, 15)
  );
  const activities = [
    {
      activity_id: 'a1',
      topic: 't1',
      kind: 'c1_practice',
      launch_path: '/c1/practice/t1',
      status: 'pending',
      recommendation_reason: 'x',
    },
  ];
  const built = buildDailySchedule({ activities, prefs, now });
  const a = built.activities.find((x) => x.activity_id === 'a1');
  assert.ok(a);
  if (a.scheduled_date && a.scheduled_date < isoDate(now)) {
    assert.equal(a.status, 'overdue');
  }
});
