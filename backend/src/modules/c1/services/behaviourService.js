// Behaviour analysis: how a student answers, not only what they answer.
//
// All rules use quiz answers only (answers that carry a question id and a measured time).
//
// PERSONAL BASELINE   the median answer time of the student's older quiz answers (everything except the
//                     newest 7). It needs 10 answers. Before that only the fixed limits below are used.
// FAST                under 8 seconds, or under 35% of the baseline
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
// KNOWLEDGE READ PER TOPIC (latest 10 answers on the topic, at least 4 answers)
//   Time is compared with the student's own typical time (median of all quiz answers, never below 15 s).
//   quick = under 8 s or under 60% of typical     slow = over 150% of typical
//                         quick                      slower than your average
//   answers mostly right  Strong and quick           Knows it, needs speed
//   answers mostly wrong  Guessing or careless       Needs revision
//   "mostly right" = 75% or more, "mostly wrong" = under 50%, "quick" or "slow" = 40% or more of the answers.
//   In between the topic is "Getting there".
//
// TWIN WEIGHT   a correct answer raises the topic score by the normal gain times a weight
//                 weight = 1, x0.5 if the student left the tab, x0.6 if the answer was fast
//               Wrong answers are never reduced, because losing a mark is not a way to cheat.

const DAY_MS = 24 * 60 * 60 * 1000;
export const BASELINE_MIN_ANSWERS = 10;
export const RECENT_N = 7;
export const FAST_SEC = 8; // reading a question and four options takes longer than this
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

export const TYPICAL_FLOOR = 15;
export const TOPIC_MIN = 4;
export const TOPIC_N = 10;

export function typicalTime(events) {
  const m = median(events.filter(isQuiz).map((e) => e.time_sec));
  return Math.max(TYPICAL_FLOOR, m == null ? TYPICAL_FLOOR : m);
}
const speedOf = (t, typical) => (t < FAST_SEC || t < 0.6 * typical ? 'quick' : t > 1.5 * typical ? 'slow' : 'normal');

const READS = {
  strong: { label: 'Strong and quick', quadrant: 'quick_right', tip: 'You know this topic well. Try mixed practice or a timed quiz to stay sharp.' },
  slow_right: { label: 'Knows it, needs speed', quadrant: 'slow_right', tip: 'Your answers are right but slow. Short, regular quizzes will build speed.' },
  guessing: { label: 'Guessing or careless', quadrant: 'quick_wrong', tip: 'Quick and wrong. Slow down, read all four options, then read the explanation.' },
  revise: { label: 'Needs revision', quadrant: 'slow_wrong', tip: 'Taking long and still wrong means the idea is not clear yet. Read your notes first, then retry.' },
  building: { label: 'Getting there', quadrant: null, tip: 'A mix of right and wrong. Keep practising this topic.' },
};

// What speed plus correctness say about one topic.
export function topicReads(events) {
  const quiz = events.filter(isQuiz).sort(byTime);
  const typical = typicalTime(events);
  const topics = [...new Set(quiz.map((e) => e.topic))];
  const out = {};
  for (const topic of topics) {
    const last = quiz.filter((e) => e.topic === topic).slice(-TOPIC_N);
    if (last.length < TOPIC_MIN) continue;
    const n = last.length;
    const accuracy = last.filter((e) => e.correct).length / n;
    const speeds = last.map((e) => speedOf(e.time_sec, typical));
    const quick = speeds.filter((x) => x === 'quick').length / n;
    const slow = speeds.filter((x) => x === 'slow').length / n;
    let key = 'building';
    if (accuracy >= 0.75) key = slow >= 0.4 ? 'slow_right' : 'strong';
    else if (accuracy < 0.5) key = quick >= 0.4 ? 'guessing' : 'revise';
    out[topic] = {
      key,
      label: READS[key].label,
      quadrant: READS[key].quadrant,
      tip: READS[key].tip,
      answers: n,
      accuracy: Math.round(accuracy * 100),
      medianSec: Math.round(median(last.map((e) => e.time_sec))),
    };
  }
  return out;
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
      headline: 'We are still learning how you answer.',
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

  const facts = `Your last ${n} answers: ${fast + guesses} very fast, ${slow} very slow. Typical time ${medianSec} s.`;
  const text = {
    Steady: ['Your answer speed looks healthy.', 'Keep reading each option before you choose.'],
    Careful: ['You take your time and mostly get it right.', 'This is fine. Try to keep it under about a minute a question.'],
    Struggling: ['You take long and often get it wrong.', 'These topics need a short revision. Read the explanation after each answer, then try again.'],
    Rushing: ['You are answering too fast.', 'Take at least 15 seconds a question and read every option. Fast correct answers count a little less in your score.'],
    Guessing: ['Many answers were quick and wrong. That looks like guessing.', 'A guess does not help you learn. If you are unsure, read the explanation and try again.'],
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
    headline: text[0],
    why: facts,
    advice: text[1],
  };
}

export async function getBehaviour(db, studentId, now = new Date()) {
  const events = await db.collection('learning_events').find({ student_id: studentId }).toArray();
  return { studentId, ...behaviourFrom(events, now), topics: topicReads(events) };
}
