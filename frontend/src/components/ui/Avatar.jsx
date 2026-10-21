import './ui.css';

// Round picture with an animated ring. Shows the picture, or the initials when there is none.
// Shared by every page header and the profile page: <Avatar name="Pasindu J" src={profile.avatar} size={40} />
export const initialsOf = (name = '') =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('') || '?';

export default function Avatar({ name, src, size = 44, ring = true, className = '' }) {
  return (
    <span className={`avatar-ui${ring ? " av-ring" : ""} ${className}`} style={{ '--size': `${size}px` }}>
      <span className="avatar-face" aria-hidden={src ? undefined : 'true'}>
        {src ? <img src={src} alt={name ? `${name}'s picture` : 'Profile picture'} /> : <b>{initialsOf(name)}</b>}
      </span>
    </span>
  );
}
