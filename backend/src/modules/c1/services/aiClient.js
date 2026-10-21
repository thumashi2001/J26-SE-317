export function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

// Calls the Python AI service. Returns the parsed JSON reply.
export async function callAi(aiUrl, path, body) {
  let res;
  try {
    res = await fetch(`${aiUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw httpError(502, `AI service unreachable at ${aiUrl}. Is it running?`);
  }
  if (!res.ok) throw httpError(502, `AI service returned ${res.status} for ${path}`);
  return res.json();
}