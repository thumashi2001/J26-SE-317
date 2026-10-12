import { useEffect, useState } from 'react';

// Animated landing illustration (our own drawing): a student studies on a laptop, her score climbs,
// the knowledge chart rises, and her friend cheers. It loops. With "reduce motion" it shows the end state.
const LOOP = 9.5; // seconds for one full loop
const RISE = 6; // seconds the chart takes to grow
const PTS = [30, 36, 34, 48, 58, 72, 92];
const X0 = 182, XW = 240, Y0 = 256, YH = 122;
const px = (i) => X0 + (i / (PTS.length - 1)) * XW;
const py = (v) => Y0 - (v / 100) * YH;
const ease = (t) => 1 - Math.pow(1 - t, 3);
const level = (s) => (s < 30 ? 'Just starting' : s < 60 ? 'Getting there' : s < 85 ? 'Strong' : 'Exam ready');

export default function LaptopScene() {
  const reduce = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const [p, setP] = useState(reduce ? 1 : 0);

  useEffect(() => {
    if (reduce) return undefined;
    let raf;
    const start = performance.now();
    const tick = (now) => {
      const t = ((now - start) / 1000) % LOOP;
      setP(Math.min(1, t / RISE));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduce]);

  const e = ease(p);
  const score = Math.round(34 + (92 - 34) * e);
  const high = p > 0.96;
  const line = PTS.map((v, i) => `${i ? 'L' : 'M'}${px(i)},${py(v)}`).join(' ');
  const area = `${line} L${px(PTS.length - 1)},${Y0} L${px(0)},${Y0} Z`;
  const clipW = XW + 16;
  const progW = e * clipW;
  const ringC = 2 * Math.PI * 17;

  return (
    <svg viewBox="0 0 600 420" className={'laptop-scene' + (high ? ' high' : '')} role="img" aria-label="Two students with laptops. One studies while her score and knowledge chart rise, and her friend cheers.">
      <defs>
        <linearGradient id="ls-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#bfe9dd" /><stop offset="1" stopColor="#f4fbf8" /></linearGradient>
        <linearGradient id="ls-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#0fa883" stopOpacity="0.38" /><stop offset="1" stopColor="#0fa883" stopOpacity="0.02" /></linearGradient>
        <clipPath id="ls-clip"><rect x={X0 - 8} y="120" width={progW} height="150" /></clipPath>
      </defs>

      <rect width="600" height="420" rx="26" fill="url(#ls-bg)" />
      <circle cx="520" cy="62" r="30" fill="#ffd36b" /><circle cx="520" cy="62" r="44" fill="#ffd36b" opacity="0.25" />
      <g className="ls-cloud"><ellipse cx="90" cy="64" rx="38" ry="12" fill="#fff" opacity="0.8" /><ellipse cx="116" cy="56" rx="26" ry="11" fill="#fff" opacity="0.8" /></g>

      {/* desk and floor */}
      <rect x="0" y="388" width="600" height="32" fill="#cfe7de" />
      <rect x="34" y="326" width="532" height="16" rx="8" fill="#c99b6b" />
      <rect x="64" y="342" width="14" height="46" rx="4" fill="#a87b4f" /><rect x="522" y="342" width="14" height="46" rx="4" fill="#a87b4f" />

      {/* books and plant on the desk */}
      <rect x="44" y="306" width="60" height="9" rx="2" fill="#2f7de1" /><rect x="48" y="297" width="52" height="9" rx="2" fill="#ffc23d" /><rect x="44" y="288" width="58" height="9" rx="2" fill="#0fa883" />

      {/* big laptop */}
      <rect x="150" y="84" width="304" height="228" rx="16" fill="#0e2238" />
      <rect x="162" y="96" width="280" height="204" rx="9" fill="#f7fbfc" />
      <rect x="120" y="312" width="364" height="14" rx="7" fill="#b8c7d4" />
      <rect x="270" y="312" width="64" height="6" rx="3" fill="#8fa4b6" />

      {/* screen content */}
      <text x="176" y="118" fontSize="12" fontWeight="700" fill="#0e2238" fontFamily="Bricolage Grotesque, Segoe UI, sans-serif">My learning state</text>
      <g transform="translate(402 128)">
        <circle r="17" fill="none" stroke="#e3e9ef" strokeWidth="6" />
        <circle r="17" fill="none" stroke={score >= 60 ? '#0fa883' : '#e8a63a'} strokeWidth="6" strokeLinecap="round" strokeDasharray={ringC} strokeDashoffset={ringC * (1 - score / 100)} transform="rotate(-90)" />
        <text y="4" textAnchor="middle" fontSize="11" fontWeight="700" fill="#0e2238" fontFamily="Bricolage Grotesque, Segoe UI, sans-serif">{score}%</text>
      </g>
      <g stroke="#e3e9ef" strokeWidth="1">
        {[0, 25, 50, 75, 100].map((v) => <line key={v} x1={X0 - 8} x2={X0 + XW + 8} y1={py(v)} y2={py(v)} />)}
      </g>
      <rect x={X0 - 8} y={py(30)} width={XW + 16} height={Y0 - py(30)} fill="#d6453d" opacity="0.07" />
      <g clipPath="url(#ls-clip)">
        <path d={area} fill="url(#ls-area)" />
        <path d={line} fill="none" stroke="#0fa883" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      {PTS.map((v, i) => (
        <circle key={i} cx={px(i)} cy={py(v)} r="5" fill={v >= 60 ? '#0fa883' : '#ffc23d'} stroke="#fff" strokeWidth="2" opacity={e * clipW >= (i / (PTS.length - 1)) * XW ? 1 : 0} />
      ))}
      <rect x="176" y="272" width="250" height="10" rx="5" fill="#e3e9ef" />
      <rect x="176" y="272" width={Math.max(8, 2.5 * score)} height="10" rx="5" fill={score >= 60 ? '#0fa883' : '#e8a63a'} />
      <text x="176" y="294" fontSize="10.5" fontWeight="600" fill="#5a6b7b" fontFamily="Public Sans, Segoe UI, sans-serif">Level: {level(score)}</text>

      {/* level badge */}
      <g transform="translate(404 28)" className={'ls-badge' + (high ? ' on' : '')}>
        <rect width="150" height="38" rx="19" fill="#0e2238" />
        <text x="75" y="24" textAnchor="middle" fontSize="14" fontWeight="700" fill={high ? '#ffd36b' : '#fff'} fontFamily="Bricolage Grotesque, Segoe UI, sans-serif">{high ? '★ Exam ready!' : level(score)}</text>
      </g>

      {/* student on the left, pointing at the screen */}
      <g className="ls-stu-a">
        <rect x="62" y="246" width="30" height="86" rx="10" fill="#1b3a59" />
        <rect x="96" y="246" width="30" height="86" rx="10" fill="#1b3a59" />
        <rect x="56" y="326" width="40" height="8" rx="4" fill="#0e2238" /><rect x="94" y="326" width="40" height="8" rx="4" fill="#0e2238" />
        <rect x="58" y="188" width="70" height="104" rx="30" fill="#0fa883" />
        <rect x="84" y="170" width="18" height="24" rx="8" fill="#b9774a" />
        <circle cx="93" cy="154" r="30" fill="#c58354" />
        <path d="M62 150 C60 118 126 112 124 152 C116 136 82 130 62 150 Z" fill="#2a1a12" />
        <circle cx="83" cy="158" r="3" fill="#2a1a12" /><circle cx="105" cy="158" r="3" fill="#2a1a12" />
        <path d="M84 170 Q94 178 104 170" fill="none" stroke="#2a1a12" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M118 214 L150 198" stroke="#0fa883" strokeWidth="16" strokeLinecap="round" />
        <circle cx="153" cy="196" r="8" fill="#c58354" />
        <g className={'ls-arm-up' + (high ? ' on' : '')}><path d="M66 214 L40 252" stroke="#0fa883" strokeWidth="16" strokeLinecap="round" /><circle cx="38" cy="255" r="8" fill="#c58354" /></g>
      </g>

      {/* friend on the right with a laptop on the knees */}
      <g className={'ls-stu-b' + (high ? ' cheer' : '')}>
        <rect x="462" y="326" width="96" height="20" rx="10" fill="#1b3a59" />
        <rect x="462" y="334" width="22" height="54" rx="8" fill="#1b3a59" />
        <rect x="470" y="228" width="68" height="104" rx="30" fill="#ffc23d" />
        <rect x="494" y="212" width="18" height="22" rx="8" fill="#e0a77b" />
        <circle cx="503" cy="196" r="29" fill="#e9b88d" />
        <path d="M474 192 C470 160 540 156 534 196 C528 176 492 170 474 192 Z" fill="#7a4a24" />
        <circle cx="493" cy="200" r="3" fill="#3a2414" /><circle cx="513" cy="200" r="3" fill="#3a2414" />
        <path d="M494 211 Q503 219 512 211" fill="none" stroke="#3a2414" strokeWidth="2.5" strokeLinecap="round" />
        <rect x="438" y="314" width="70" height="8" rx="4" fill="#c7d3de" />
        <path d="M444 314 L436 266" stroke="#0e2238" strokeWidth="9" strokeLinecap="round" /><path d="M444 312 L438 270" stroke="#8fd3c0" strokeWidth="4" strokeLinecap="round" />
        <path d="M488 262 L470 308" stroke="#ffc23d" strokeWidth="14" strokeLinecap="round" />
        <g className="ls-arm-b"><path d="M532 250 L556 214" stroke="#ffc23d" strokeWidth="14" strokeLinecap="round" /><circle cx="558" cy="210" r="8" fill="#e9b88d" /></g>
      </g>

      {/* floating rewards */}
      <g className={'ls-spark' + (high ? ' on' : '')} fill="#ffc23d">
        <path d="M300 50 l5 12 12 5 -12 5 -5 12 -5 -12 -12 -5 12 -5z" />
        <path d="M372 36 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" fill="#0fa883" />
        <path d="M250 38 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3z" fill="#2f7de1" />
      </g>
      <g className="ls-plus" fontFamily="Bricolage Grotesque, Segoe UI, sans-serif" fontWeight="700" fontSize="15">
        <text x="352" y="104" fill="#0fa883">+8</text>
      </g>
    </svg>
  );
}
