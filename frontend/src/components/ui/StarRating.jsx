import './ui.css';

// 5 stars with half star steps. value goes from 0 to 5. The stars fill in one after another.
//   <StarRating value={3.5} />
const STAR = 'M12 2.6l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.2 1.2-6.5L2.5 9.5l6.6-.9z';

export default function StarRating({ value = 0, size = 30, label }) {
  const v = Math.max(0, Math.min(5, value));
  return (
    <span className="stars" role="img" aria-label={label || `${v} out of 5 stars`} style={{ '--ss': `${size}px` }}>
      {[0, 1, 2, 3, 4].map((i) => {
        const fill = Math.max(0, Math.min(1, v - i));
        return (
          <svg key={i} viewBox="0 0 24 24" className="star" style={{ '--d': `${i * 120}ms` }} aria-hidden="true">
            <defs>
              <linearGradient id={`sg-${i}-${Math.round(fill * 100)}`}>
                <stop offset={`${fill * 100}%`} stopColor="var(--star-on)" />
                <stop offset={`${fill * 100}%`} stopColor="var(--star-off)" />
              </linearGradient>
            </defs>
            <path d={STAR} fill={`url(#sg-${i}-${Math.round(fill * 100)})`} stroke="var(--star-on)" strokeWidth="0.8" strokeLinejoin="round" />
          </svg>
        );
      })}
    </span>
  );
}
