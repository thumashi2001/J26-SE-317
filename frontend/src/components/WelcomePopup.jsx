import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import './welcome.css';

// A short "today" summary shown once after login, before the dashboard.
// Closes with the button, the Esc key or a click outside. Focus stays inside while it is open.
export default function WelcomePopup({ name, focus, alertCount, headline, onClose }) {
  const box = useRef(null);
  const opener = useRef(typeof document !== 'undefined' ? document.activeElement : null);

  useEffect(() => {
    const el = box.current;
    const focusables = () => el.querySelectorAll('a[href], button:not([disabled])');
    focusables()[0]?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;
      const f = focusables();
      if (!f.length) return;
      const first = f[0];
      const last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    const back = opener.current;
    return () => {
      document.removeEventListener('keydown', onKey);
      back?.focus?.();
    };
  }, [onClose]);

  return (
    <div className="welcome-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="welcome" role="dialog" aria-modal="true" aria-labelledby="welcome-h" ref={box}>
        <p className="welcome-kicker">Your day at a glance</p>
        <h2 id="welcome-h">Welcome back{name ? `, ${name}` : ''}</h2>

        <ul className="welcome-list">
          <li className="welcome-item">
            <span className="welcome-icon" aria-hidden="true">&#127919;</span>
            <div>
              <strong>Today&apos;s focus</strong>
              {focus ? (
                <p>{focus.name} is your weakest topic, at about {focus.score}%.</p>
              ) : (
                <p>Pick any topic and start a short quiz.</p>
              )}
            </div>
          </li>
          <li className="welcome-item">
            <span className="welcome-icon" aria-hidden="true">{alertCount > 0 ? '⚠' : '✓'}</span>
            <div>
              <strong>Alerts</strong>
              <p>{alertCount > 0 ? `${alertCount} ${alertCount === 1 ? 'thing needs' : 'things need'} your attention.` : 'Nothing needs your attention.'}</p>
            </div>
          </li>
          <li className="welcome-item">
            <span className="welcome-icon" aria-hidden="true">&#9201;</span>
            <div>
              <strong>How you answer</strong>
              <p>{headline}</p>
            </div>
          </li>
        </ul>

        <div className="welcome-actions">
          {focus && (
            <Link className="btn" to={`/c1/practice/${focus.topic}`}>
              Practise {focus.name}
            </Link>
          )}
          <button type="button" className="btn secondary" onClick={onClose}>
            Open my dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
