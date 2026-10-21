export default function ComingSoon({ title, owner, text }) {
  return (
    <div>
      <h1>{title}</h1>
      <div className="panel soon">
        <span className="chip">Coming soon</span>
        <p className="muted">{text || `${owner} is building this section.`}</p>
        {text && <p className="muted small">Built by {owner}.</p>}
      </div>
    </div>
  );
}
