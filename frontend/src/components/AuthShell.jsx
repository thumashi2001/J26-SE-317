import { Link } from 'react-router-dom';
import Logo from './Logo.jsx';
import ThemeToggle from './ThemeToggle.jsx';
import '../pages/auth.css';

// Shared by the login and register pages: an animated art panel on the left,
// the form card on the right, and a Back to home button.
export default function AuthShell({ children }) {
  return (
    <div className="auth">
      <section className="auth-art" aria-hidden="true">
        <span className="orb o1" /><span className="orb o2" /><span className="orb o3" />
        <div className="auth-brand"><Logo size={40} onDark /></div>
        <div className="auth-copy">
          <h2>Know what you have forgotten before the exam does.</h2>
          <p>Your digital twin tracks what you know topic by topic, and how fast it fades.</p>
        </div>
        <div className="twin-card">
          <div className="twin-head">
            <span>Memory strength</span>
            <b>84%</b>
          </div>
          <svg viewBox="0 0 420 150" className="curve">
            <path className="curve-ghost" d="M10,20 C90,40 170,100 410,138" />
            <path className="curve-live" pathLength="1"
              d="M10,20 C50,30 100,48 150,68 L150,34 C190,40 240,56 275,74 L275,26 C315,30 355,40 410,50" />
            <circle cx="150" cy="34" r="5" className="dot-review" />
            <circle cx="275" cy="26" r="5" className="dot-review" />
          </svg>
          <div className="twin-foot"><i /> with review <i className="g" /> no review</div>
        </div>
        <span className="chip c1">Forgetting curve</span>
        <span className="chip c2">Daily plan</span>
        <span className="chip c3">Exam countdown</span>
      </section>

      <section className="auth-form">
        <div className="auth-top">
          <Link to="/" className="auth-home">
            <span aria-hidden="true">&larr;</span> Back to home
          </Link>
          <ThemeToggle />
        </div>
        <div className="auth-card">{children}</div>
        <p className="auth-foot">AdaptiveLearnSE &middot; Year 3 Software Engineering</p>
      </section>
    </div>
  );
}
