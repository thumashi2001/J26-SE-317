// Animated world for the landing page: a turning globe with the four tools orbiting around it.
// Pure SVG and CSS, no images. Motion stops when the person prefers reduced motion.
const TOOLS = ['Digital Twin', 'Exam Intelligence', 'Automated Marking', 'Learning Path'];
const SPIN = 32; // seconds for one orbit

// One strip of rough land shapes. It is drawn twice side by side so it can slide forever.
const LAND = (
  <g fill="#7fd6c4" opacity="0.9">
    <path d="M18 78c10-14 30-18 44-10s10 22-4 30-30 4-40-6z" />
    <path d="M86 128c8-10 24-8 28 4s-2 30-12 40-22 0-20-14 0-22 4-30z" />
    <path d="M150 70c14-12 40-10 54 2s16 30 0 36-34-2-48-10-14-20-6-28z" />
    <path d="M214 124c10-6 26-2 30 10s-6 24-18 24-18-14-12-34z" />
    <path d="M250 60c10-6 24-4 30 6s-4 18-16 18-20-14-14-24z" />
    <path d="M60 170c10-4 22 0 24 10s-8 14-18 12-12-16-6-22z" />
  </g>
);

export default function JoinScene() {
  return (
    <div className="js-stage" aria-hidden="true">
      <span className="js-star s1" /><span className="js-star s2" /><span className="js-star s3" />
      <span className="js-star s4" /><span className="js-star s5" /><span className="js-star s6" />

      <div className="js-orbit">
        {TOOLS.map((t, i) => (
          <div key={t} className="js-arm" style={{ animationDelay: `${-(SPIN / TOOLS.length) * i}s`, '--i': i }}>
            <span className="js-chip" style={{ animationDelay: `${-(SPIN / TOOLS.length) * i}s`, '--i': i }}>{t}</span>
          </div>
        ))}
      </div>

      <svg className="js-globe" viewBox="0 0 300 300" role="presentation">
        <defs>
          <radialGradient id="jsSea" cx="35%" cy="30%" r="80%">
            <stop offset="0" stopColor="#5aa2ff" />
            <stop offset="0.6" stopColor="#2f6fd6" />
            <stop offset="1" stopColor="#16315a" />
          </radialGradient>
          <radialGradient id="jsShine" cx="30%" cy="25%" r="50%">
            <stop offset="0" stopColor="#fff" stopOpacity="0.55" />
            <stop offset="1" stopColor="#fff" stopOpacity="0" />
          </radialGradient>
          <clipPath id="jsClip"><circle cx="150" cy="150" r="118" /></clipPath>
        </defs>
        <circle className="js-glow" cx="150" cy="150" r="136" fill="#4f8ff0" opacity="0.15" />
        <circle cx="150" cy="150" r="118" fill="url(#jsSea)" />
        <g clipPath="url(#jsClip)">
          <g className="js-land">
            <g transform="translate(-30 10)">{LAND}</g>
            <g transform="translate(262 10)">{LAND}</g>
            <g transform="translate(554 10)">{LAND}</g>
          </g>
          <g className="js-grid" fill="none" stroke="#fff" strokeOpacity="0.28" strokeWidth="1">
            <ellipse className="m1" cx="150" cy="150" rx="118" ry="118" />
            <ellipse className="m2" cx="150" cy="150" rx="118" ry="118" />
            <ellipse className="m3" cx="150" cy="150" rx="118" ry="118" />
            <line x1="32" y1="150" x2="268" y2="150" />
            <ellipse cx="150" cy="150" rx="118" ry="50" />
            <ellipse cx="150" cy="150" rx="118" ry="92" />
          </g>
          <circle cx="150" cy="150" r="118" fill="url(#jsShine)" />
        </g>
        <g className="js-pin" transform="translate(176 118)">
          <circle className="js-ping" r="6" fill="none" stroke="#ffd166" strokeWidth="2" />
          <circle r="5" fill="#ffd166" />
        </g>
      </svg>
    </div>
  );
}
