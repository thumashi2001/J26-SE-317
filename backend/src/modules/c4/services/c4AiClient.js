/**
 * Authenticated C4 → Python AI proxy client (port 8004 by default).
 * Browser never supplies the target URL.
 */

const DEFAULT_BASE = 'http://127.0.0.1:8004';
const DEFAULT_TIMEOUT_MS = 15_000;

export function c4AiBaseUrl() {
  const raw = (process.env.C4_AI_URL || DEFAULT_BASE).trim().replace(/\/$/, '');
  if (!/^https?:\/\//i.test(raw)) {
    const err = new Error('C4_AI_URL must be an http(s) URL configured on the server');
    err.status = 500;
    throw err;
  }
  return raw;
}

export function httpError(status, message, code) {
  const err = new Error(message);
  err.status = status;
  if (code) err.code = code;
  return err;
}

function sanitizeDetail(detail) {
  if (detail == null) return 'Upstream inference error';
  if (typeof detail === 'string') return detail.slice(0, 500);
  if (typeof detail === 'object') {
    if (typeof detail.error === 'string') return detail.error.slice(0, 500);
    if (typeof detail.detail === 'string') return detail.detail.slice(0, 500);
    if (typeof detail.message === 'string') return detail.message.slice(0, 500);
    try {
      return JSON.stringify(detail).slice(0, 500);
    } catch {
      return 'Upstream inference error';
    }
  }
  return String(detail).slice(0, 500);
}

/**
 * @param {string} method
 * @param {string} path absolute path on Python service, e.g. /v1/se-path-simulation-v1/ready
 * @param {object} [opts]
 */
export async function callC4Ai(method, path, { body, timeoutMs } = {}) {
  const base = c4AiBaseUrl();
  if (!path.startsWith('/')) {
    throw httpError(500, 'Internal proxy path must be absolute');
  }
  const url = `${base}${path}`;
  const ms = Number.isFinite(timeoutMs) ? timeoutMs : DEFAULT_TIMEOUT_MS;
  let res;
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ms);
    try {
      res = await fetch(url, {
        method,
        headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timer);
    }
  } catch (e) {
    if (e?.name === 'AbortError') {
      throw httpError(502, 'C4 AI service timed out', 'c4_ai_timeout');
    }
    throw httpError(
      502,
      'C4 AI service unreachable. Start ai-services/c4 on the configured C4_AI_URL.',
      'c4_ai_unreachable'
    );
  }

  let payload = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { detail: text.slice(0, 200) };
    }
  }

  if (res.status === 400) {
    throw httpError(400, sanitizeDetail(payload?.detail ?? payload), 'c4_ai_validation');
  }
  if (res.status === 503) {
    throw httpError(
      503,
      sanitizeDetail(payload?.detail ?? payload) || 'C4 AI model not ready',
      'c4_ai_not_ready'
    );
  }
  if (!res.ok) {
    throw httpError(
      502,
      `C4 AI returned HTTP ${res.status}`,
      'c4_ai_bad_gateway'
    );
  }
  return payload;
}
