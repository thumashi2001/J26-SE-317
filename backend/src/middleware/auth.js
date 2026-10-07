import jwt from 'jsonwebtoken';

// Shared login checks. Any component can use them on its own routes:
//   router.use(requireAuth);                        every route needs a logged-in user
//   router.get('/class', requireRole('lecturer'), handler);   only lecturers
// After requireAuth, req.user is { sub: '<user id>', role: 'student' | 'lecturer' | 'admin' }.

const EXPIRES_IN = '7d';
const STAFF_EXPIRES_IN = '12h'; // lecturers and admins sign in again each day, so a removed lecturer loses access quickly
let warned = false;

function secret() {
  const s = process.env.AUTH_SECRET;
  if (s) return s;
  if (process.env.NODE_ENV === 'production') throw new Error('AUTH_SECRET is not set');
  if (!warned) {
    console.warn('AUTH_SECRET is not set in backend/.env. Using an insecure development secret.');
    warned = true;
  }
  return 'dev-only-secret-change-me';
}

export function signToken({ sub, role }) {
  const expiresIn = role === 'student' ? EXPIRES_IN : STAFF_EXPIRES_IN;
  return jwt.sign({ sub, role }, secret(), { algorithm: 'HS256', expiresIn });
}

export function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : '';
  if (!token) return res.status(401).json({ error: 'Please log in' });
  try {
    const payload = jwt.verify(token, secret(), { algorithms: ['HS256'] });
    req.user = { sub: payload.sub, role: payload.role };
    next();
  } catch (err) {
    const message = err.name === 'TokenExpiredError' ? 'Your session expired. Please log in again' : 'Please log in again';
    res.status(401).json({ error: message });
  }
}

export function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user || !roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'You do not have access to this page' });
    }
    next();
  };
}

// Decides whose data a request is about.
// A student always gets their own data from the token. If the request names a different
// student, it is refused. Lecturers must name the student they want to look at.
export function resolveStudentId(req, supplied) {
  const fail = (status, message) => Object.assign(new Error(message), { status });
  if (req.user.role === 'lecturer') {
    if (!supplied) throw fail(400, 'studentId is required');
    return supplied;
  }
  if (req.user.role !== 'student') throw fail(403, 'You do not have access to student data');
  if (supplied && supplied !== req.user.sub) throw fail(403, 'You can only see your own data');
  return req.user.sub;
}
