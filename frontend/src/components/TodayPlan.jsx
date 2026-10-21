import { Link } from 'react-router-dom';
import { prettyTopic } from '../utils/topics.js';
import './plan.css';

const KIND_TEXT = {
  start: 'Start',
  revise: 'Revise now',
  slow_down: 'Slow down',
  read_first: 'Read, then practise',
  speed: 'Build speed',
  keep_sharp: 'Keep sharp',
  practise: 'Practise',
};

// Today's tasks. They come from the forgetting curve (what is fading), the way the student answers
// (guessing, slow, strong) and the number of days left before the exam.
export default function TodayPlan({ plan }) {
  if (!plan) return <section className="panel plan-card"><p className="muted">Working out today's plan...</p></section>;
  const { today, daysLeft, slowDown, nextExam, hasExamDates } = plan;
  const tasks = today.tasks;
  return (
    <section className="panel plan-card" aria-labelledby="today-title">
      <header className="plan-head">
        <div>
          <h2 id="today-title">Today's plan</h2>
          <p className="muted small">
            {tasks.length === 0
              ? 'Nothing is due today. Enjoy the rest.'
              : `${tasks.length} short ${tasks.length === 1 ? 'quiz' : 'quizzes'}, about ${today.minutes} minutes.`}
            {nextExam && ` Next exam: ${nextExam.module} in ${daysLeft} ${daysLeft === 1 ? 'day' : 'days'}.`}
          </p>
        </div>
        {nextExam && (
          <div className="countdown" aria-label={`${daysLeft} days to the ${nextExam.module} exam`}>
            <strong>{daysLeft}</strong>
            <span>{nextExam.module}</span>
          </div>
        )}
      </header>

      {!hasExamDates && (
        <p className="plan-note">Add the exam date of each module in the calendar and this plan will count down to them. Until then it plans the next 2 weeks.</p>
      )}
      {slowDown && (
        <p className="plan-note warm">Your recent answers were quick, so every task below asks you to slow down. Fast correct answers count less.</p>
      )}

      <ol className="plan-list">
        {tasks.map((t, i) => (
          <li key={t.topic} className={`plan-task k-${t.kind}`}>
            <span className="plan-num" aria-hidden="true">{i + 1}</span>
            <div className="plan-body">
              <div className="plan-line">
                <span className="plan-mod">{t.module}</span>
                <Link to={`/c1/topic/${t.topic}`} className="plan-name">{prettyTopic(t.topic)}</Link>
                <span className={`plan-tag k-${t.kind}`}>{KIND_TEXT[t.kind] || t.label}</span>
              </div>
              <p className="plan-why">{t.why}</p>
              {t.tips.map((tip, k) => <p key={k} className="plan-tip">{tip}</p>)}
            </div>
            <div className="plan-side">
              <span className="plan-score" title="Estimated score now">{t.scoreNow}%</span>
              <Link className="btn plan-go" to={`/c1/practice/${t.topic}`}>Practise</Link>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
