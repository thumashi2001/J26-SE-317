import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Avatar from './ui/Avatar.jsx';
import './ui/ui.css';

// The strip at the top of every page after login, for every role and every component.
// The round picture opens My profile. Teammates do not need to add anything: Layout shows it for them.
const fmt = (sec) => {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m >= 60 ? `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m` : `${m}:${String(s).padStart(2, '0')}`;
};

export default function Topbar({ roleLabel, todaySeconds }) {
  const { user, profile } = useAuth();
  const name = (profile && profile.name) || user.name;
  const first = (name || '').split(' ')[0];
  return (
    <header className="topbar">
      <div className="topbar-left">
        <p className="topbar-crumb">{roleLabel} area</p>
      </div>
      <div className="topbar-right">
        {todaySeconds !== null && (
          <Link to="/profile" className="usage-chip" title="Time you have spent here today">
            <span className="usage-dot" aria-hidden="true" />
            <span className="u-label">Today</span> {fmt(todaySeconds)}
          </Link>
        )}
        <Link to="/profile" className="topbar-me" aria-label="Open my profile">
          <Avatar name={name} src={profile ? profile.avatar : null} size={34} />
          <span className="t">{first}</span>
        </Link>
      </div>
    </header>
  );
}
