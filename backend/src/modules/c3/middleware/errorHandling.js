// Error handling owned by the C3 router. It covers unknown /api/v1/c3/* paths and errors thrown inside C3 handlers.
// (Errors raised before the request reaches this router, such as malformed JSON bodies or unknown non-C3 paths,
// are handled by the shared application and are outside this module.)
//
// SIMPLE ENGLISH: these two functions make sure C3 always answers with a short JSON message like {"error": "..."},
// never an HTML page, a stack trace or an internal address.

// Any /api/v1/c3/... path that no route matched.
export function c3NotFound(req, res) {
  res.status(404).json({ error: 'Not found' });
}

// Client errors keep their message; server errors never expose internal details.
export function c3ErrorHandler(err, req, res, next) {
  if (res.headersSent) return next(err);
  const status = Number.isInteger(err?.status) ? err.status : 500;
  // 5xx problems are logged on the server (message only) and shown to the user as a generic sentence.
  if (status >= 500) console.error('[c3] unhandled error:', err?.message);
  res.status(status).json({ error: status >= 500 ? 'The request could not be completed' : String(err.message || 'Request failed') });
}
