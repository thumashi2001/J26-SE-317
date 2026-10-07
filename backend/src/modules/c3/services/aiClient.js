export function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

export async function callAi(aiUrl, path, body) {
  let res;
  try {
    res = await fetch(`${aiUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw httpError(502, `C3 AI service unreachable at ${aiUrl}. Is it running?`);
  }
  
  if (!res.ok) {
     let errorMsg = `C3 AI service returned ${res.status} for ${path}`;
     try {
       const errBody = await res.json();
       if (errBody.detail) errorMsg += `: ${JSON.stringify(errBody.detail)}`;
     } catch(e) {}
     throw httpError(502, errorMsg);
  }
  return res.json();
}

export function analyzeAnswer(aiUrl, payload) { return callAi(aiUrl, '/analysis/answer', payload); }
export function markAnswer(aiUrl, payload) { return callAi(aiUrl, '/marking/evaluate', payload); }
export function generateFeedback(aiUrl, payload) { return callAi(aiUrl, '/feedback/generate', payload); }
export function generateMindmap(aiUrl, payload) { return callAi(aiUrl, '/mindmap/generate', payload); }
