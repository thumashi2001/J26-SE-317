import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import RoleRoute from './components/RoleRoute.jsx';
import { STUDENT_MENU, LECTURER_MENU, ADMIN_MENU } from './config/menus.js';
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
import PracticePage from './pages/c1/PracticePage.jsx';
import LecturerHome from './pages/lecturer/LecturerHome.jsx';
import AdminDashboard from './pages/admin/AdminDashboard.jsx';
import LecturerApprovals from './pages/admin/LecturerApprovals.jsx';

// Three areas, one for each kind of user. A person can only open their own area.
// Each teammate replaces their ComingSoon routes with real pages:
//   student pages  -> /c1, /c2, /c3, /c4
//   lecturer pages -> /lecturer/c1 ... /lecturer/c4
//   admin pages    -> /admin/...
// To show a page in the side menu, add it to src/config/menus.js.
const area = (role, menu, label) => (
  <ProtectedRoute>
    <RoleRoute allow={[role]}>
      <Layout menu={menu} roleLabel={label} />
    </RoleRoute>
  </ProtectedRoute>
);

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<ProtectedRoute><HomeRedirect /></ProtectedRoute>} />

      <Route element={area('student', STUDENT_MENU, 'Student')}>
        <Route path="/c1/diagnostic" element={<DiagnosticPage />} />
        <Route path="/c1/dashboard" element={<DashboardPage />} />
        <Route path="/c1/topic/:topic" element={<TopicPage />} />
        <Route path="/c1/practice/:topic" element={<PracticePage />} />

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

      <Route element={area('lecturer', LECTURER_MENU, 'Lecturer')}>
        <Route path="/lecturer" element={<LecturerHome />} />
        <Route path="/lecturer/c1/*" element={<ComingSoon title="Class learning state" owner="Component 1" text="Class and student learning state for lecturers." />} />
        <Route path="/lecturer/c2/*" element={<ComingSoon title="Exam intelligence" owner="Rupasinghe H T N N" text="Question papers, rubrics and exam patterns." />} />
        <Route path="/lecturer/c3/*" element={<ComingSoon title="Marking review" owner="Edirisinghe T P V K" text="Review automated marks and feedback." />} />
        <Route path="/lecturer/c4/*" element={<ComingSoon title="Adaptive paths" owner="Muthumali W G G A S" text="Study plans recommended to students." />} />
      </Route>

      <Route element={area('admin', ADMIN_MENU, 'Administrator')}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/lecturers" element={<LecturerApprovals />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
