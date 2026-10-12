// The AdaptiveLearnSE logo, drawn here so it is our own.
// The mark shows the idea of the project: memory fades, then a review lifts it again (amber dots).
export function LogoMark({ size = 40 }) {
  return (
    <svg className="logo-mark" width={size} height={size} viewBox="0 0 48 48" role="img" aria-label="AdaptiveLearnSE logo">
      <defs>
        <linearGradient id="als-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#12304f" />
          <stop offset="1" stopColor="#0fa883" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="13" fill="url(#als-bg)" />
      <path d="M9 14 C14 14 18 20 21 29 L21 19 C25 20 29 26 32 33 L32 16 C35 16 38 18 40 22" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="21" cy="19" r="3.6" fill="#ffc23d" stroke="#12304f" strokeWidth="1.4" />
      <circle cx="32" cy="16" r="3.6" fill="#ffc23d" stroke="#0e5f58" strokeWidth="1.4" />
    </svg>
  );
}

export default function Logo({ size = 40, onDark = false, showName = true }) {
  return (
    <span className={'logo' + (onDark ? ' on-dark' : '')}>
      <LogoMark size={size} />
      {showName && (
        <span className="logo-name">
          Adaptive<b>Learn</b>SE
        </span>
      )}
    </span>
  );
}
