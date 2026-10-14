import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import HomeRedirect from './pages/HomeRedirect.jsx';
import ComingSoon from './pages/ComingSoon.jsx';
import DiagnosticPage from './pages/c1/DiagnosticPage.jsx';
import DashboardPage from './pages/c1/DashboardPage.jsx';
import AssessmentPage from './pages/c3/AssessmentPage.jsx';
import LecturerQueuePage from './pages/c3/LecturerQueuePage.jsx';
import LecturerReviewPage from './pages/c3/LecturerReviewPage.jsx';

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

        <Route path="/c2/*" element={<ComingSoon title="Exam Intelligence" owner="Rupasinghe H T N N" />} />

        {/* Component 3: Role-Aware Assessment & Human-In-The-Loop Verification Routes */}
        <Route path="/c3" element={<AssessmentPage />} />
        <Route
          path="/c3/review"
          element={
            <ProtectedRoute roles={['lecturer', 'admin']}>
              <LecturerQueuePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/c3/review/:submissionId"
          element={
            <ProtectedRoute roles={['lecturer', 'admin']}>
              <LecturerReviewPage />
            </ProtectedRoute>
          }
        />

        <Route path="/c4/*" element={<ComingSoon title="Adaptive Learning Path" owner="Muthumali W G G A S" />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
