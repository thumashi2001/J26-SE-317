import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import HomeRedirect from './pages/HomeRedirect.jsx';
import ComingSoon from './pages/ComingSoon.jsx';
import DiagnosticPage from './pages/c1/DiagnosticPage.jsx';
import DashboardPage from './pages/c1/DashboardPage.jsx';
import StudentC3Dashboard from './pages/c3/StudentC3Dashboard.jsx';
import StudentAssessment from './pages/c3/StudentAssessment.jsx';
import StudentResult from './pages/c3/StudentResult.jsx';
import LecturerC3Dashboard from './pages/lecturer/c3/LecturerC3Dashboard.jsx';
import LecturerReview from './pages/lecturer/c3/LecturerReview.jsx';
import AdminC3Dashboard from './pages/admin/c3/AdminC3Dashboard.jsx';
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
        {/* Student C3 */}
        <Route path="/c3" element={<StudentC3Dashboard />} />
        <Route path="/c3/assessment/:id" element={<StudentAssessment />} />
        <Route path="/c3/result/:id" element={<StudentResult />} />

        {/* Lecturer C3 */}
        <Route path="/lecturer/c3" element={<LecturerC3Dashboard />} />
        <Route path="/lecturer/c3/review/:submissionId" element={<LecturerReview />} />

        {/* Admin C3 */}
        <Route path="/admin/c3" element={<AdminC3Dashboard />} />
        <Route path="/c4/*" element={<ComingSoon title="Adaptive Learning Path" owner="Muthumali W G G A S" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
