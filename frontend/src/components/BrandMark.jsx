import { useState } from 'react';
import Logo from './Logo.jsx';

// SLIIT logo (your own file: frontend/public/sliit-logo.png) next to the product name.
// If the logo file is not there yet, the text "SLIIT" is shown instead.
export default function BrandMark({ onDark = false }) {
  const [hasLogo, setHasLogo] = useState(true);
  return (
    <span className={'brandmark' + (onDark ? ' on-dark' : '')}>
      <span className="bm-logo">
        {hasLogo ? (
          <img src="/sliit-logo.png" alt="SLIIT" onError={() => setHasLogo(false)} />
        ) : (
          <span className="bm-uni">SLIIT</span>
        )}
      </span>
      <span className="bm-divider" aria-hidden="true" />
      <Logo size={36} onDark={onDark} />
    </span>
  );
}
