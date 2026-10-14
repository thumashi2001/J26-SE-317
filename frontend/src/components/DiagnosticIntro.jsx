import { useEffect, useRef } from 'react';
import StudentsArt from './StudentsArt.jsx';
import './diagnostic.css';

// Shown to a student who has not finished the diagnostic test yet.
// It cannot be closed: no close button, no Esc, no click outside. The only way on is the start button.
export default function DiagnosticIntro({ name, onStart, onLogout }) {
  const box = useRef(null);
  const first = (name || '').split(' ')[0];

  useEffect(() => {
    const el = box.current;
    const focusables = () => el.querySelectorAll('button:not([disabled])');
    focusables()[0]?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        return;
      }
      if (e.key !== 'Tab') return;
      const f = focusables();
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) {
        e.preventDefault();
        f[f.length - 1].focus();
      } else if (!e.shiftKey && document.activeElement === f[f.length - 1]) {
        e.preventDefault();
        f[0].focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="dxi-backdrop">
      <div className="dxi" role="dialog" aria-modal="true" aria-labelledby="dxi-title" ref={box}>
        <div className="dxi-art">
          <StudentsArt />
        </div>
        <div className="dxi-body">
          <p className="dxi-kicker">{first ? `Welcome, ${first}` : 'Welcome'}</p>
          <h2 id="dxi-title">Let&rsquo;s check your knowledge level</h2>
          <p className="dxi-lead">
            Don&rsquo;t worry, you are already on the right track. This short test shows where you stand today, so your learning twin can help you become your very best.
          </p>
          <ul className="dxi-points">
            <li><span aria-hidden="true">🎯</span> One question for every topic in your semester</li>
            <li><span aria-hidden="true">⏱️</span> A timer starts when you press the button: about 40 seconds for each question</li>
            <li><span aria-hidden="true">💚</span> No pass or fail. It only helps us help you</li>
            <li><span aria-hidden="true">🔓</span> Everything else opens as soon as you finish</li>
          </ul>
          <button type="button" className="dxi-start" onClick={onStart}>
            Start my test <span aria-hidden="true">&rarr;</span>
          </button>
          <button type="button" className="dxi-logout" onClick={onLogout}>Log out</button>
        </div>
      </div>
    </div>
  );
}
