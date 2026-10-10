// Behaviour analysis: how a student answers, not only what they answer.
//
// All rules use quiz answers only (answers that carry a question id and a measured time).
//
// PERSONAL BASELINE   the median answer time of the student's older quiz answers (everything except the
//                     newest 7). It needs 10 answers. Before that only the fixed limits below are used.
// FAST                under 3 seconds, or under 35% of the baseline
// SLOW                over 120 seconds, or over 2.5 times the baseline
// LIKELY GUESS        a fast answer that is also wrong
//
// PATTERN (the latest 10 quiz answers from the last 14 days, at least 5 answers)
//   Guessing    25% or more of the answers are likely guesses
//   Rushing     40% or more of the answers are fast
//   Struggling  40% or more are slow and the accuracy is under 50%
//   Careful     40% or more are slow and the accuracy is 50% or more
//   Steady      none of the above
//
// TWIN WEIGHT   a correct answer raises the topic score by the normal gain times a weight
//                 weight = 1, x0.5 if the student left the tab, x0.6 if the answer was fast
//               Wrong answers are never reduced, because losing a mark is not a way to cheat.

const DAY_MS = 24 * 60 * 60 * 1000;
export const BASELINE_MIN_ANSWERS = 10;
export const RECENT_N = 7;
export const FAST_SEC = 3;
export const SLOW_SEC = 120;
export const FAST_RATIO = 0.35;
export const SLOW_RATIO = 2.5;
export const WINDOW_DAYS = 14;
export const MIN_ANSWERS = 5;
export const PATTERN_N = 10;

const isQuiz = (e) => e.type === 'quiz_answer' && e.question_id && e.time_sec != null;
const byTime = (a, b) => new Date(a.timestamp) - new Date(b.timestamp);

export function median(nums) {
  if (!nums.length) return null;
  const s = [...nums].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// Median time of the older answers. The newest RECENT_N answers are left out so a new habit does not hide itself.
export function baselineFrom(events) {
  const quiz = events.filter(isQuiz).sort(byTime);
  if (quiz.length < BASELINE_MIN_ANSWERS) return null;
  return median(quiz.slice(0, Math.max(BASELINE_MIN_ANSWERS, quiz.length - RECENT_N)).map((e) => e.time_sec));
}

export function isFast(timeSec, baseline) {
  return timeSec < FAST_SEC || (baseline != null && timeSec < FAST_RATIO * baseline);
}
export function isSlow(timeSec, baseline) {
  return timeSec > SLOW_SEC || (baseline != null && timeSec > SLOW_RATIO * baseline);
}

// 'guess' | 'fast' | 'slow' | 'normal'
export function classify(ev, baseline) {
  const t = Number(ev.time_sec);
  if (isFast(t, baseline)) return ev.correct ? 'fast' : 'guess';
  if (isSlow(t, baseline)) return 'slow';
  return 'normal';
}

// How much of the normal gain a correct answer keeps (0.3 to 1).
export function gainWeight({ correct, timeSec, tabLeaves }, baseline) {
  if (!correct) return 1;
  let w = 1;
  if ((tabLeaves || 0) > 0) w *= 0.5;
  if (timeSec != null && isFast(timeSec, baseline)) w *= 0.6;
  return Math.round(w * 100) / 100;
}

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

export function behaviourFrom(events, now = new Date()) {
  const quiz = events.filter(isQuiz).sort(byTime);
  const baseline = baselineFrom(events);
  const from = now.getTime() - WINDOW_DAYS * DAY_MS;
  const recent = quiz.filter((e) => new Date(e.timestamp).getTime() >= from).slice(-PATTERN_N);

  const base = {
    answers: recent.length,
    windowDays: WINDOW_DAYS,
    baselineSec: baseline == null ? null : Math.round(baseline),
    medianSec: null,
    fast: 0,
    slow: 0,
    guesses: 0,
    accuracy: null,
    tabLeaves: 0,
  };

  if (recent.length < MIN_ANSWERS) {
    return {
      ...base,
      pattern: 'Not enough yet',
      why: `We need at least ${MIN_ANSWERS} practice answers in the last ${WINDOW_DAYS} days to describe how you answer. You have ${recent.length}.`,
      advice: 'Finish a quiz or two and this card will fill in.',
    };
  }

  const kinds = recent.map((e) => classify(e, baseline));
  const count = (k) => kinds.filter((x) => x === k).length;
  const fast = count('fast');
  const guesses = count('guess');
  const slow = count('slow');
  const n = recent.length;
  const accuracy = recent.filter((e) => e.correct).length / n;
  const tabLeaves = recent.filter((e) => (e.tab_leaves || 0) > 0).length;
  const medianSec = Math.round(median(recent.map((e) => e.time_sec)));

  let pattern = 'Steady';
  if (guesses / n >= 0.25) pattern = 'Guessing';
  else if ((fast + guesses) / n >= 0.4) pattern = 'Rushing';
  else if (slow / n >= 0.4) pattern = accuracy < 0.5 ? 'Struggling' : 'Careful';

  const normal = baseline != null ? `, compared with about ${plural(Math.round(baseline), 'second', 'seconds')} before` : '';
  const facts = `You answer in about ${plural(medianSec, 'second', 'seconds')}${normal}. ${plural(fast + guesses, 'answer was', 'answers were')} very fast and ${plural(slow, 'was', 'were')} very slow out of ${n}.`;
  const text = {
    Steady: ['Your answer speed looks steady.', 'Keep reading each option before you choose.'],
    Careful: ['You take your time and mostly get it right.', 'This is fine. Try to keep it under about a minute a question.'],
    Struggling: ['You take long and often get it wrong.', 'These topics need a short revision. Read the explanation after each answer, then try again.'],
    Rushing: ['You are answering very fast.', 'Slow down and read every option. Fast answers count a little less in your score.'],
    Guessing: ['Many answers were very quick and wrong, which looks like guessing.', 'A guess does not help you learn. If you are unsure, read the explanation and try again.'],
  }[pattern];

  return {
    ...base,
    medianSec,
    fast: fast + guesses,
    slow,
    guesses,
    accuracy: Math.round(accuracy * 100),
    tabLeaves,
    pattern,
    why: `${text[0]} ${facts}`,
    advice: text[1],
  };
}

export async function getBehaviour(db, studentId, now = new Date()) {
  const events = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  return { studentId, ...behaviourFrom(events, now) };
}
