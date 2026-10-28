import React from 'react';

interface WordmarkProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'dark' | 'light';
}

export const Wordmark: React.FC<WordmarkProps> = ({
  className = '',
  size = 'md',
  variant = 'dark',
}) => {
  const iconSizes = {
    sm: 'w-6 h-6',
    md: 'w-7 h-7',
    lg: 'w-9 h-9',
  };

  const textSizes = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl',
  };

  const isLight = variant === 'light';

  return (
    <div className={`flex items-center gap-2.5 font-semibold tracking-tight ${className}`}>
      {/* Inline SVG Geometric Mark: Rounded square containing a check made from two distinct strokes */}
      <svg
        className={`${iconSizes[size]} flex-shrink-0`}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <rect
          x="1"
          y="1"
          width="30"
          height="30"
          rx="7"
          fill={isLight ? '#FFFFFF' : '#1E3A5F'}
          stroke={isLight ? 'rgba(255,255,255,0.2)' : '#172E4C'}
          strokeWidth="1.5"
        />
        {/* Check mark stroke 1: downwards stroke */}
        <path
          d="M9.5 16.5L14 21"
          stroke={isLight ? '#1E3A5F' : '#FFFFFF'}
          strokeWidth="2.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Check mark stroke 2: upwards stroke with accent highlight */}
        <path
          d="M14 21L23 11"
          stroke={isLight ? '#C77700' : '#C77700'}
          strokeWidth="2.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className={`font-sans font-bold ${textSizes[size]} ${isLight ? 'text-white' : 'text-primary'}`}>
        Doc<span className={isLight ? 'text-accent-tint' : 'text-accent'}>Validate</span>
      </span>
    </div>
  );
};

