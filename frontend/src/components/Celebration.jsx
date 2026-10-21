import { useEffect, useRef, useState } from 'react';

// Fireworks (and confetti for a perfect score) drawn on a canvas for a few seconds.
// It never blocks the page (pointer-events none) and is skipped when the person prefers less motion.
const COLORS = ['#ffd36b', '#0fa883', '#ff6b6b', '#4cc9f0', '#ffffff', '#f4b942', '#b388ff'];
const DURATION = 5200;

export default function Celebration({ perfect = false }) {
  const canvas = useRef(null);
  const [done, setDone] = useState(false);
  const reduce = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  useEffect(() => {
    if (reduce) return undefined;
    const el = canvas.current;
    const ctx = el.getContext('2d');
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const size = () => {
      el.width = window.innerWidth * dpr;
      el.height = window.innerHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    size();
    window.addEventListener('resize', size);

    const W = () => window.innerWidth;
    const H = () => window.innerHeight;
    const rockets = [];
    const sparks = [];
    const confetti = [];
    const rand = (a, b) => a + Math.random() * (b - a);
    const pick = () => COLORS[Math.floor(Math.random() * COLORS.length)];

    const launch = () => {
      const x = rand(W() * 0.15, W() * 0.85);
      rockets.push({ x, y: H() + 10, vx: rand(-0.6, 0.6), vy: -rand(9, 12), targetY: rand(H() * 0.15, H() * 0.45), color: pick() });
    };
    const explode = (r) => {
      const n = 70;
      const color2 = pick();
      for (let i = 0; i < n; i++) {
        const a = (Math.PI * 2 * i) / n + rand(-0.05, 0.05);
        const sp = rand(1.5, 5.2);
        sparks.push({ x: r.x, y: r.y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, life: 1, decay: rand(0.012, 0.022), color: i % 3 === 0 ? color2 : r.color });
      }
    };
    if (perfect) {
      for (let i = 0; i < 140; i++) {
        confetti.push({ x: rand(0, W()), y: rand(-H(), 0), vx: rand(-1, 1), vy: rand(1.5, 3.5), rot: rand(0, 6), vr: rand(-0.2, 0.2), w: rand(6, 11), h: rand(4, 8), color: pick() });
      }
    }

    const start = performance.now();
    let last = 0;
    let raf;
    const frame = (t) => {
      const elapsed = t - start;
      ctx.clearRect(0, 0, W(), H());
      if (elapsed < DURATION - 1500 && t - last > (perfect ? 380 : 520)) {
        launch();
        last = t;
      }
      for (let i = rockets.length - 1; i >= 0; i--) {
        const r = rockets[i];
        r.x += r.vx;
        r.y += r.vy;
        r.vy += 0.12;
        ctx.strokeStyle = r.color;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(r.x, r.y);
        ctx.lineTo(r.x - r.vx * 3, r.y - r.vy * 3);
        ctx.stroke();
        if (r.y <= r.targetY || r.vy >= -1) {
          explode(r);
          rockets.splice(i, 1);
        }
      }
      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i];
        s.x += s.vx;
        s.y += s.vy;
        s.vy += 0.045;
        s.vx *= 0.99;
        s.life -= s.decay;
        if (s.life <= 0) {
          sparks.splice(i, 1);
          continue;
        }
        ctx.globalAlpha = Math.max(0, s.life);
        ctx.fillStyle = s.color;
        ctx.beginPath();
        ctx.arc(s.x, s.y, 2.4, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      if (elapsed < DURATION - 800) {
        for (const c of confetti) {
          c.x += c.vx;
          c.y += c.vy;
          c.rot += c.vr;
          ctx.save();
          ctx.translate(c.x, c.y);
          ctx.rotate(c.rot);
          ctx.fillStyle = c.color;
          ctx.fillRect(-c.w / 2, -c.h / 2, c.w, c.h);
          ctx.restore();
        }
      }
      if (elapsed < DURATION || sparks.length || rockets.length) raf = requestAnimationFrame(frame);
      else setDone(true);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', size);
    };
  }, [perfect, reduce]);

  if (reduce || done) return null;
  return <canvas ref={canvas} className="celebration" aria-hidden="true" />;
}
