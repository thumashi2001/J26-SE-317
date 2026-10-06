import { createContext, useContext, useEffect, useState } from 'react';
import { loginRequest, registerRequest } from '../services/authApi.js';
import { getTwin } from '../services/c1Api.js';

// Keeps the logged-in student. The token is sent with every API call by services/apiClient.js.
// diagnosticDone is null while we check, then true or false. It decides where a student lands.
const AuthContext = createContext(null);

function readUser() {
  try {
    return JSON.parse(sessionStorage.getItem('user'));
  } catch {
    return null;
  }
}

function save(user, token) {
  try {
    sessionStorage.setItem('user', JSON.stringify(user));
    sessionStorage.setItem('token', token);
  } catch {
    // storage unavailable, the session lasts until the page reloads
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readUser);
  const [diagnosticDone, setDiagnosticDone] = useState(null);

  useEffect(() => {
    if (!user) {
      setDiagnosticDone(null);
      return undefined;
    }
    let alive = true;
    getTwin(user.student_id)
      .then((t) => alive && setDiagnosticDone(!!t.diagnosticCompleted))
      // If the check fails, send them to the dashboard, which shows the real error.
      .catch(() => alive && setDiagnosticDone(true));
    return () => {
      alive = false;
    };
  }, [user]);

  const finish = ({ user: u, token }) => {
    save(u, token);
    setDiagnosticDone(null);
    setUser(u);
  };

  const login = async (studentId, password) => finish(await loginRequest(studentId, password));
  const register = async (form) => finish(await registerRequest(form));
  const logout = () => {
    try {
      sessionStorage.clear();
    } catch {
      // ignore
    }
    setUser(null);
  };
  const markDiagnosticDone = () => setDiagnosticDone(true);

  return (
    <AuthContext.Provider value={{ user, login, register, logout, diagnosticDone, markDiagnosticDone }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
