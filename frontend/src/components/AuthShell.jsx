// Two-column layout shared by the login and register pages.
// The left side draws the idea behind the product: memory fades unless you review it.
export default function AuthShell({ children }) {
  return (
    <div className="auth">
      <section className="auth-art" aria-hidden="true">
        <div className="auth-brand">AdaptiveLearnSE</div>
        <h2>Know what you have forgotten before the exam does.</h2>
        <svg viewBox="0 0 420 220" className="curve" role="img">
          <line x1="10" y1="200" x2="410" y2="200" className="axis" />
          <line x1="10" y1="10" x2="10" y2="200" className="axis" />
          <path className="curve-ghost" d="M10,30 C90,60 170,150 405,185" />
          <path
            className="curve-live"
            pathLength="1"
            d="M10,30 C50,44 100,70 150,100 L150,55 C190,62 240,82 275,104 L275,40 C315,44 355,58 405,72"
          />
          <circle cx="150" cy="55" r="5" className="dot-review" />
          <circle cx="275" cy="40" r="5" className="dot-review" />
          <text x="18" y="216" className="chart-label">time</text>
          <text x="318" y="150" className="chart-label ghost">no review</text>
          <text x="318" y="30" className="chart-label">with review</text>
        </svg>
        <p className="auth-note">Your digital twin tracks what you know topic by topic, and how fast it fades.</p>
      </section>
      <section className="auth-form">{children}</section>
    </div>
  );
}
