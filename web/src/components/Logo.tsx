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
      {/* Pirate Radio Logo SVG */}
      <div className={`${dimensions[size]} relative`}>
        <svg
          viewBox="0 0 40 40"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Skull base */}
          <circle cx="20" cy="18" r="12" fill="#f59e0b" className="drop-shadow-lg" />
          <circle cx="20" cy="18" r="10" fill="#fbbf24" />
          
          {/* Eye patches */}
          <circle cx="16" cy="16" r="2.5" fill="#1f2937" />
          <circle cx="24" cy="16" r="2.5" fill="#1f2937" />
          
          {/* Eye highlights */}
          <circle cx="16.5" cy="15.5" r="0.8" fill="#ef4444" />
          <circle cx="24.5" cy="15.5" r="0.8" fill="#ef4444" />
          
          {/* Nose */}
          <path d="M20 19 L18 22 L22 22 Z" fill="#d97706" />
          
          {/* Mouth/Teeth */}
          <rect x="17" y="23" width="6" height="2" fill="#1f2937" rx="1" />
          <rect x="18" y="22" width="1" height="2" fill="#f3f4f6" />
          <rect x="20" y="22" width="1" height="2" fill="#f3f4f6" />
          <rect x="22" y="22" width="1" height="2" fill="#f3f4f6" />
          
          {/* Radio waves */}
          <path
            d="M5 10 Q10 5 20 10"
            stroke="#10b981"
            strokeWidth="2"
            fill="none"
            className="animate-pulse"
          />
          <path
            d="M35 10 Q30 5 20 10"
            stroke="#10b981"
            strokeWidth="2"
            fill="none"
            className="animate-pulse"
            style={{ animationDelay: '0.5s' }}
          />
          <path
            d="M8 15 Q12 12 20 15"
            stroke="#34d399"
            strokeWidth="1.5"
            fill="none"
            className="animate-pulse"
            style={{ animationDelay: '1s' }}
          />
          <path
            d="M32 15 Q28 12 20 15"
            stroke="#34d399"
            strokeWidth="1.5"
            fill="none"
            className="animate-pulse"
            style={{ animationDelay: '1.5s' }}
          />
          
          {/* Antenna */}
          <line x1="20" y1="6" x2="20" y2="2" stroke="#6b7280" strokeWidth="2" />
          <circle cx="20" cy="2" r="1" fill="#ef4444" className="animate-ping" />
        </svg>
      </div>
      
      {/* Station Name */}
      <div className="flex flex-col">
        <h1 className="text-xl font-bold text-white font-pirate tracking-wide">
          Raido
        </h1>
        <p className="text-xs text-pirate-300 font-medium -mt-1">
          AI Pirate Radio
        </p>
      </div>
    </div>
  )
}

export default Logo