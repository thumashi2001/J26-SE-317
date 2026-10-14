import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import RoleRoute from './components/RoleRoute.jsx';
import { STUDENT_MENU, LECTURER_MENU, ADMIN_MENU } from './config/menus.js';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import HomeRedirect from './pages/HomeRedirect.jsx';
import LandingPage from './pages/LandingPage.jsx';
import { useAuth } from './context/AuthContext.jsx';
import ComingSoon from './pages/ComingSoon.jsx';
import DiagnosticPage from './pages/c1/DiagnosticPage.jsx';
import DashboardPage from './pages/c1/DashboardPage.jsx';
import TopicPage from './pages/c1/TopicPage.jsx';
import PracticePage from './pages/c1/PracticePage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';
import LecturerHome from './pages/lecturer/LecturerHome.jsx';
import AdminDashboard from './pages/admin/AdminDashboard.jsx';
import LecturerApprovals from './pages/admin/LecturerApprovals.jsx';
import AssessmentPage from './pages/c3/AssessmentPage.jsx';
import LecturerQueuePage from './pages/c3/LecturerQueuePage.jsx';
import LecturerReviewPage from './pages/c3/LecturerReviewPage.jsx';

// Three areas, one for each kind of user. A person can only open their own area.
// Each teammate replaces their ComingSoon routes with real pages:
//   student pages  -> /c1, /c2, /c3, /c4
//   lecturer pages -> /lecturer/c1 ... /lecturer/c4
//   admin pages    -> /admin/...
// To show a page in the side menu, add it to src/config/menus.js.
const area = (role, menu, label) => (
  <ProtectedRoute>
    <RoleRoute allow={Array.isArray(role) ? role : [role]}>
      <Layout menu={menu} roleLabel={label} />
    </RoleRoute>
  </ProtectedRoute>
);

// The profile page opens inside the layout of whoever is logged in.
function ProfileArea() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  const cfg = {
    student: [STUDENT_MENU, 'Student'],
    lecturer: [LECTURER_MENU, 'Lecturer'],
    admin: [ADMIN_MENU, 'Administrator'],
  }[user.role] || [STUDENT_MENU, 'Student'];
  return (
    <ProtectedRoute>
      <Layout menu={cfg[0]} roleLabel={cfg[1]} />
    </ProtectedRoute>
  );
}

// The first page: the landing page for visitors, the person's own home page after login.
function Root() {
  const { user } = useAuth();
  return user ? <HomeRedirect /> : <LandingPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<Root />} />

      {/* Student Area */}
      <Route element={area('student', STUDENT_MENU, 'Student')}>
        <Route path="/c1/diagnostic" element={<DiagnosticPage />} />
        <Route path="/c1/dashboard" element={<DashboardPage />} />
        <Route path="/c1/topic/:topic" element={<TopicPage />} />
        <Route path="/c1/practice/:topic" element={<PracticePage />} />

        <Route path="/c2/*" element={<ComingSoon title="Exam Intelligence" owner="Rupasinghe H T N N" />} />

        {/* Component 3: Student Automated Marking & Assessment */}
        <Route path="/c3" element={<AssessmentPage />} />
        <Route path="/c3/*" element={<AssessmentPage />} />

        <Route path="/c4/*" element={<ComingSoon title="Adaptive Learning Path" owner="Muthumali W G G A S" />} />
      </Route>

      {/* Lecturer Area */}
      <Route element={area(['lecturer', 'admin'], LECTURER_MENU, 'Lecturer')}>
        <Route path="/lecturer" element={<LecturerHome />} />
        <Route path="/lecturer/c1/*" element={<ComingSoon title="Class learning state" owner="Component 1" text="Class and student learning state for lecturers." />} />
        <Route path="/lecturer/c2/*" element={<ComingSoon title="Exam intelligence" owner="Rupasinghe H T N N" text="Question papers, rubrics and exam patterns." />} />

        {/* Component 3: Lecturer Marking Review & Finalization */}
        <Route path="/lecturer/c3" element={<LecturerQueuePage />} />
        <Route path="/lecturer/c3/:submissionId" element={<LecturerReviewPage />} />
        <Route path="/lecturer/c3/review/:submissionId" element={<LecturerReviewPage />} />
        {/* Support direct /c3/review URLs under lecturer authorization */}
        <Route path="/c3/review" element={<LecturerQueuePage />} />
        <Route path="/c3/review/:submissionId" element={<LecturerReviewPage />} />

        <Route path="/lecturer/c4/*" element={<ComingSoon title="Adaptive paths" owner="Muthumali W G G A S" text="Study plans recommended to students." />} />
      </Route>

      {/* Administrator Area */}
      <Route element={area('admin', ADMIN_MENU, 'Administrator')}>
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/lecturers" element={<LecturerApprovals />} />
      </Route>

      {/* My profile: one page for every role, inside that role's own layout */}
      <Route path="/profile" element={<ProfileArea />}>
        <Route index element={<ProfilePage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
