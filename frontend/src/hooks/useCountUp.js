import { useEffect, useState } from 'react';

// Counts from 0 up to `value` once, for number tiles. Shows the final number straight away
// when the person prefers reduced motion, or when the value is not a number.
export default function useCountUp(value, ms = 900) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return undefined;
    if (typeof window === 'undefined' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setN(value);
      return undefined;
    }
    let raf;
    const t0 = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / ms);
      setN(value * (1 - (1 - p) ** 3));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return typeof value === 'number' ? n : value;
}
