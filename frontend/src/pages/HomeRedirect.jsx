import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

// Sends each person to their own home page after login.
//   admin -> /admin, lecturer -> /lecturer,
//   student: first visit -> the diagnostic test, after that -> the learning state.
export default function HomeRedirect() {
  const { user, diagnosticDone } = useAuth();
  if (user.role === 'admin') return <Navigate to="/admin" replace />;
  if (user.role === 'lecturer') return <Navigate to="/lecturer" replace />;
  if (diagnosticDone === null) return <p className="muted">Loading...</p>;
  return <Navigate to={diagnosticDone ? '/c1/dashboard' : '/c1/diagnostic'} replace />;
}
