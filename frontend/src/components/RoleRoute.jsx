import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

// Only lets the listed roles in. Anyone else is sent to their own home page.
//   <RoleRoute allow={['lecturer']}>...</RoleRoute>
export default function RoleRoute({ allow, children }) {
  const { user } = useAuth();
  return allow.includes(user.role) ? children : <Navigate to="/" replace />;
}
