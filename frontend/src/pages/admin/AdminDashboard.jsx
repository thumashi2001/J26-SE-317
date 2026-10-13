import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext.jsx';
import { getC1Summary, getC1Active } from '../../services/adminApi.js';
import C1Card from '../../components/admin/C1Card.jsx';

// Learning insights: how students are learning, one card per component.
// Lecturer approvals is its own page (/admin/lecturers).
export default function AdminDashboard() {
  const { user } = useAuth();
  const [c1, setC1] = useState(null);
  const [c1Error, setC1Error] = useState('');
  const [c1Active, setC1Active] = useState(null);

  useEffect(() => {
    getC1Summary().then(setC1).catch((err) => setC1Error(err.message));
    getC1Active().then((r) => setC1Active(r.students)).catch(() => {}); // the card still works without the list
  }, []);

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Learning insights</h1>
          <p className="muted">Welcome back, {user.name}. This is how students are learning across the platform.</p>
        </div>
      </div>

      <C1Card data={c1} error={c1Error} active={c1Active} />
      {/* Other members: add your own card here, for example <C3Card ... /> */}
    </div>
  );
}
