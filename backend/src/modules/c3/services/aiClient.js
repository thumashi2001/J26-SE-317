// HTTP CLIENT FOR THE PYTHON AI SERVICE.
// This is the ONLY place where Node.js talks to Python. For a written-answer submission the controller calls
// assessAnswer() below, which sends `POST {C3_AI_URL}/c3/assess` and returns the JSON (marks, evidence, feedback, map).
// The other four helpers call the stand-alone Python endpoints and are used only by the lecturer-only raw routes.

// Build an Error that carries an HTTP status (the controller turns it into the response status).
export function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

// POST `body` as JSON to the Python service and return the parsed JSON reply.
export async function callAi(aiUrl, path, body, options = {}) {
  // Give up after 15 s by default (C3_AI_TIMEOUT_MS overrides) so a stuck service cannot hang a student request.
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
    // Network-level failures: 504 = too slow, 502 = service not reachable (is uvicorn running on port 8003?).
    if (e.name === 'TimeoutError' || e.name === 'AbortError') {
      throw httpError(504, `C3 AI service request timed out after ${timeoutMs}ms at ${aiUrl}${path}`);
    }
    throw httpError(502, `C3 AI service unreachable at ${aiUrl}. Is it running?`);
  }

  // The Python service answered with an error status: translate it (5xx -> 502 bad gateway, other -> 400 client error).
  if (!res.ok) {
    let errorMsg = `C3 AI service returned ${res.status} for ${path}`;
    const status = res.status >= 500 ? 502 : 400;
    try {
      const errBody = await res.json();
      if (errBody.detail) {
        if (Array.isArray(errBody.detail)) {
          // FastAPI validation errors (422) arrive as a list of {loc, msg}; join them into one readable sentence.
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

// One small function per Python endpoint (the path is the only difference).
export function analyzeAnswer(aiUrl, payload) { return callAi(aiUrl, '/analysis/answer', payload); }
export function markAnswer(aiUrl, payload) { return callAi(aiUrl, '/marking/evaluate', payload); }
export function generateFeedback(aiUrl, payload) { return callAi(aiUrl, '/feedback/generate', payload); }
export function generateMindmap(aiUrl, payload) { return callAi(aiUrl, '/mindmap/generate', payload); }
// THE ONE USED BY A LIVE STUDENT SUBMISSION: analysis + marking + feedback + mind map in a single call.
export function assessAnswer(aiUrl, payload) { return callAi(aiUrl, '/c3/assess', payload); }
