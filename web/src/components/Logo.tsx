import React from 'react'

interface LogoProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const Logo: React.FC<LogoProps> = ({ className = '', size = 'md' }) => {
  const dims = { sm: { w: 18, h: 11, text: 13 }, md: { w: 22, h: 14, text: 15 }, lg: { w: 28, h: 18, text: 19 } }[size]

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      {/* Signal mark: 5 vertical bars, center tallest — like a frequency spectrum */}
      <svg
        width={dims.w}
        height={dims.h}
        viewBox="0 0 22 14"
        fill="none"
        aria-hidden="true"
      >
        <rect x="0"    y="5"  width="2.5" height="4"  rx="1.25" fill="#38bdf8" opacity="0.4" />
        <rect x="4.9"  y="2"  width="2.5" height="10" rx="1.25" fill="#38bdf8" opacity="0.7" />
        <rect x="9.75" y="0"  width="2.5" height="14" rx="1.25" fill="#38bdf8" />
        <rect x="14.6" y="2"  width="2.5" height="10" rx="1.25" fill="#38bdf8" opacity="0.7" />
        <rect x="19.5" y="5"  width="2.5" height="4"  rx="1.25" fill="#38bdf8" opacity="0.4" />
      </svg>

      {/* Wordmark — Syne, all-caps, wide tracking */}
      <span
        className="font-display font-bold text-white tracking-widest uppercase select-none"
        style={{ fontSize: dims.text, letterSpacing: '0.22em' }}
      >
        RAIDO
      </span>
    </div>
  )
}

export default Logo
