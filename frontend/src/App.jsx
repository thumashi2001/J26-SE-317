import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import HomeRedirect from './pages/HomeRedirect.jsx';
import ComingSoon from './pages/ComingSoon.jsx';
import DiagnosticPage from './pages/c1/DiagnosticPage.jsx';
import DashboardPage from './pages/c1/DashboardPage.jsx';
import TopicPage from './pages/c1/TopicPage.jsx';

// Each teammate replaces their ComingSoon routes with real pages.
// Add your routes under your own prefix (/c2, /c3, /c4) and keep this file small.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<HomeRedirect />} />

        <Route path="/c1/diagnostic" element={<DiagnosticPage />} />
        <Route path="/c1/dashboard" element={<DashboardPage />} />
        <Route path="/c1/topic/:topic" element={<TopicPage />} />

        <Route path="/c2/*" element={<ComingSoon title="Exam Intelligence" owner="Rupasinghe H T N N" />} />
        <Route path="/c3/*" element={<ComingSoon title="Automated Marking" owner="Edirisinghe T P V K" />} />
        <Route path="/c4/*" element={<ComingSoon title="Adaptive Learning Path" owner="Muthumali W G G A S" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
