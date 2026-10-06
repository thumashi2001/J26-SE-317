export default function ComingSoon({ title, owner }) {
  return (
    <div className="panel">
      <h2>{title}</h2>
      <p className="muted">{owner} is building this section.</p>
    </div>
  );
}
