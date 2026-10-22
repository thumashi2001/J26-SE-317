// Small in-memory fixed-window rate limiter owned by the C3 module (no shared middleware, no dependency).
// It limits work that triggers model/analysis computation. Counters are per authenticated user and per group,
// so one user cannot exhaust another user's allowance. State is per process (documented limitation: not shared
// across several backend instances).
//
// C3_RATE_LIMIT_PER_MIN: allowed requests per user per group per minute (default 60; 0 disables the limiter).

const WINDOW_MS = 60_000;
const buckets = new Map();

function limit() {
  const raw = process.env.C3_RATE_LIMIT_PER_MIN;
  const n = raw === undefined || raw === '' ? 60 : Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : 60;
}

export function resetRateLimits() {
  buckets.clear();
}

export function rateLimit(group) {
  return (req, res, next) => {
    const max = limit();
    if (max === 0) return next();
    const now = Date.now();
    const key = `${group}|${req.user?.sub || req.ip}`;
    let b = buckets.get(key);
    if (!b || now - b.start >= WINDOW_MS) {
      b = { start: now, count: 0 };
      buckets.set(key, b);
    }
    b.count += 1;
    if (buckets.size > 5000) {
      for (const [k, v] of buckets) if (now - v.start >= WINDOW_MS) buckets.delete(k);
    }
    if (b.count > max) {
      const retry = Math.max(1, Math.ceil((b.start + WINDOW_MS - now) / 1000));
      res.set('Retry-After', String(retry));
      return res.status(429).json({ error: 'Too many requests. Please wait a moment and try again.' });
    }
    next();
  };
}
