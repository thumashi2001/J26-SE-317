// REQUEST RATE LIMIT for expensive C3 routes.
// SIMPLE ENGLISH: each logged-in user may call a route group at most N times per minute (default 60); extra calls get
// HTTP 429 "too many requests" plus a Retry-After header. It stops one user from flooding the marking service.
//
// Small in-memory fixed-window rate limiter owned by the C3 module (no shared middleware, no dependency).
// It limits work that triggers model/analysis computation. Counters are per authenticated user and per group,
// so one user cannot exhaust another user's allowance. State is per process (documented limitation: not shared
// across several backend instances).
//
// C3_RATE_LIMIT_PER_MIN: allowed requests per user per group per minute (default 60; 0 disables the limiter).

const WINDOW_MS = 60_000;      // length of one counting window: one minute
const buckets = new Map();     // "group|user" -> { start of window, count so far }

// Read the configured limit (falls back to 60 if the variable is missing or invalid).
function limit() {
  const raw = process.env.C3_RATE_LIMIT_PER_MIN;
  const n = raw === undefined || raw === '' ? 60 : Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : 60;
}

// Used by tests to start from a clean state.
export function resetRateLimits() {
  buckets.clear();
}

// Express middleware factory: rateLimit('assess') limits the "assess" group per user.
export function rateLimit(group) {
  return (req, res, next) => {
    const max = limit();
    if (max === 0) return next();  // 0 = limiter switched off
    const now = Date.now();
    const key = `${group}|${req.user?.sub || req.ip}`;
    let b = buckets.get(key);
    // Start a new window if there is none yet or the old one has expired.
    if (!b || now - b.start >= WINDOW_MS) {
      b = { start: now, count: 0 };
      buckets.set(key, b);
    }
    b.count += 1;
    // Housekeeping: drop expired windows so memory cannot grow without bound.
    if (buckets.size > 5000) {
      for (const [k, v] of buckets) if (now - v.start >= WINDOW_MS) buckets.delete(k);
    }
    // Over budget: tell the client how many seconds to wait.
    if (b.count > max) {
      const retry = Math.max(1, Math.ceil((b.start + WINDOW_MS - now) / 1000));
      res.set('Retry-After', String(retry));
      return res.status(429).json({ error: 'Too many requests. Please wait a moment and try again.' });
    }
    next();
  };
}
