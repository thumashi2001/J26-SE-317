import React from 'react';

/**
 * Reusable AdaptiveLearnSE Logo Component
 * Uses the official SVG assets from the Figma design.
 */
export default function AdaptiveLearnSELogo({ variant = 'dark', iconOnly = false, responsive = false, className = '' }) {
  let mainSrc = '/branding/adaptivelearnse-horizontal-dark.svg';
  
  if (variant === 'light') {
    mainSrc = '/branding/adaptivelearnse-horizontal-light.svg';
  } else if (variant === 'monochrome') {
    mainSrc = '/branding/adaptivelearnse-monochrome.svg';
  }

  const iconSrc = '/branding/adaptivelearnse-icon.svg';

  const baseStyle = { maxWidth: '100%', height: 'auto' };

  if (iconOnly) {
    return (
      <img src={iconSrc} alt="AdaptiveLearnSE" aria-label="AdaptiveLearnSE" className={`adaptivelearnse-logo ${className}`} style={baseStyle} />
    );
  }

  if (responsive) {
    return (
      <div className={`adaptivelearnse-logo-wrapper ${className}`}>
        <img 
          src={mainSrc} 
          alt="AdaptiveLearnSE" 
          aria-label="AdaptiveLearnSE"
          className="al-logo-desktop" 
          style={baseStyle} 
        />
        <img 
          src={iconSrc} 
          alt="AdaptiveLearnSE" 
          aria-label="AdaptiveLearnSE"
          className="al-logo-mobile" 
          style={baseStyle} 
        />
      </div>
    );
  }

  return (
    <img 
      src={mainSrc} 
      alt="AdaptiveLearnSE" 
      aria-label="AdaptiveLearnSE"
      className={`adaptivelearnse-logo ${className}`} 
      style={baseStyle} 
    />
  );
}
