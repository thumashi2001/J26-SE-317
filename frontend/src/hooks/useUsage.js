import { useEffect, useRef, useState } from 'react';
import { getUsage, pingUsage } from '../services/authApi.js';

// Counts the time a person spends on the web app today.
// It ticks every second while the tab is visible, and tells the server every 30 seconds.
// The server keeps the real total, so two open tabs do not count twice.
export default function useUsage(enabled) {
  const [base, setBase] = useState(null); // what the server last said
  const [extra, setExtra] = useState(0); // seconds counted here since then
  const extraRef = useRef(0);

  useEffect(() => {
    if (!enabled) return undefined;
    let alive = true;
    getUsage()
      .then((u) => alive && setBase(u))
      .catch(() => {}); // the app works without the counter
    const visible = () => document.visibilityState === 'visible';
    const tick = setInterval(() => {
      if (!visible()) return;
      extraRef.current += 1;
      setExtra(extraRef.current);
    }, 1000);
    const ping = setInterval(() => {
      if (!visible()) return;
      pingUsage(30)
        .then((u) => {
          if (!alive) return;
          setBase(u);
          extraRef.current = 0;
          setExtra(0);
        })
        .catch(() => {});
    }, 30000);
    return () => {
      alive = false;
      clearInterval(tick);
      clearInterval(ping);
    };
  }, [enabled]);

  return { usage: base, todaySeconds: base ? base.todaySeconds + extra : null };
}
