import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

// First visit: straight to the diagnostic test. After that: straight to the learning state.
export default function HomeRedirect() {
  const { diagnosticDone } = useAuth();
  if (diagnosticDone === null) return <p className="muted">Loading...</p>;
  return <Navigate to={diagnosticDone ? '/c1/dashboard' : '/c1/diagnostic'} replace />;
}
