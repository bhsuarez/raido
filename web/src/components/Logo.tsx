import React from 'react'

interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const Logo: React.FC<LogoProps> = ({ className = '', size = 'md' }) => {
  const iconSize = { sm: 28, md: 34, lg: 40 }[size]
  const textSize = { sm: 'text-base', md: 'text-lg', lg: 'text-xl' }[size]

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* Clean radio wave icon */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Outer waves */}
        <path
          d="M6 18 Q6 8 18 8 Q30 8 30 18"
          stroke="#ec7711"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          opacity="0.5"
        />
        {/* Middle wave */}
        <path
          d="M10 18 Q10 12 18 12 Q26 12 26 18"
          stroke="#ec7711"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          opacity="0.75"
        />
        {/* Inner wave */}
        <path
          d="M14 18 Q14 15 18 15 Q22 15 22 18"
          stroke="#ec7711"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
        />
        {/* Center dot */}
        <circle cx="18" cy="20" r="2.5" fill="#ec7711" />
        {/* Stand */}
        <line x1="18" y1="22" x2="18" y2="28" stroke="#6b7280" strokeWidth="2" strokeLinecap="round" />
        <line x1="13" y1="28" x2="23" y2="28" stroke="#6b7280" strokeWidth="2" strokeLinecap="round" />
      </svg>

      {/* Station name */}
      <span className={`${textSize} font-bold text-white tracking-tight`}>
        Raido
      </span>
    </div>
  )
}

export default Logo
