export function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

export async function callAi(aiUrl, path, body, options = {}) {
  const timeoutMs = Number(options.timeoutMs || process.env.C3_AI_TIMEOUT_MS || 15000);
  let res;
  try {
    res = await fetch(`${aiUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (e) {
    if (e.name === 'TimeoutError' || e.name === 'AbortError') {
      throw httpError(504, `C3 AI service request timed out after ${timeoutMs}ms at ${aiUrl}${path}`);
    }
    throw httpError(502, `C3 AI service unreachable at ${aiUrl}. Is it running?`);
  }
  
  if (!res.ok) {
    let errorMsg = `C3 AI service returned ${res.status} for ${path}`;
    const status = res.status >= 500 ? 502 : 400;
    try {
      const errBody = await res.json();
      if (errBody.detail) {
        if (Array.isArray(errBody.detail)) {
          const formatted = errBody.detail
            .map((d) => `${d.loc ? d.loc.slice(1).join('.') : 'field'}: ${d.msg}`)
            .join('; ');
          errorMsg = `Validation error (${res.status}): ${formatted}`;
        } else {
          errorMsg = `C3 AI service returned ${res.status}: ${typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail)}`;
        }
      }
    } catch (e) {}
    throw httpError(status, errorMsg);
  }
  return res.json();
}

export function analyzeAnswer(aiUrl, payload) { return callAi(aiUrl, '/analysis/answer', payload); }
export function markAnswer(aiUrl, payload) { return callAi(aiUrl, '/marking/evaluate', payload); }
export function generateFeedback(aiUrl, payload) { return callAi(aiUrl, '/feedback/generate', payload); }
export function generateMindmap(aiUrl, payload) { return callAi(aiUrl, '/mindmap/generate', payload); }
export function assessAnswer(aiUrl, payload) { return callAi(aiUrl, '/c3/assess', payload); }

