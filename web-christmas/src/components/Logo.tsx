import React from 'react'

interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const Logo: React.FC<LogoProps> = ({ className = '', size = 'md' }) => {
  const dimensions = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12'
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Christmas Tree Logo SVG */}
      <div className={`${dimensions[size]} relative`}>
        <svg
          viewBox="0 0 40 40"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Christmas Tree */}
          <path d="M20 5 L28 15 L26 15 L32 23 L30 23 L35 32 L5 32 L10 23 L8 23 L14 15 L12 15 Z"
                fill="#10b981" className="drop-shadow-lg" />

          {/* Tree ornaments */}
          <circle cx="15" cy="18" r="1.5" fill="#ef4444" className="animate-pulse"
                  style={{ animationDuration: '2s' }} />
          <circle cx="25" cy="20" r="1.5" fill="#fbbf24" className="animate-pulse"
                  style={{ animationDuration: '2.5s', animationDelay: '0.5s' }} />
          <circle cx="20" cy="25" r="1.5" fill="#3b82f6" className="animate-pulse"
                  style={{ animationDuration: '3s', animationDelay: '1s' }} />
          <circle cx="12" cy="27" r="1.5" fill="#a855f7" className="animate-pulse"
                  style={{ animationDuration: '2.5s', animationDelay: '1.5s' }} />
          <circle cx="28" cy="27" r="1.5" fill="#ec4899" className="animate-pulse"
                  style={{ animationDuration: '2s', animationDelay: '2s' }} />

          {/* Star on top */}
          <path d="M20 3 L21 6 L24 6 L21.5 8 L22.5 11 L20 9 L17.5 11 L18.5 8 L16 6 L19 6 Z"
                fill="#fbbf24" className="sparkle" />

          {/* Tree trunk */}
          <rect x="17" y="32" width="6" height="5" fill="#92400e" rx="1" />

          {/* Snowflakes */}
          <text x="5" y="10" fontSize="8" fill="#bae6fd" className="sparkle">❄</text>
          <text x="33" y="12" fontSize="6" fill="#bae6fd" className="sparkle"
                style={{ animationDelay: '1s' }}>❄</text>
          <text x="8" y="36" fontSize="7" fill="#bae6fd" className="sparkle"
                style={{ animationDelay: '2s' }}>❄</text>
          <text x="32" y="35" fontSize="6" fill="#bae6fd" className="sparkle"
                style={{ animationDelay: '1.5s' }}>❄</text>
        </svg>
      </div>

      {/* Station Name */}
      <div className="flex flex-col">
        <h1 className="text-xl font-bold text-white font-pirate tracking-wide">
          Raido Christmas
        </h1>
        <p className="text-xs text-blue-300 font-medium -mt-1">
          AI Holiday Radio
        </p>
      </div>
    </div>
  )
}

export default Logo