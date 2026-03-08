// web/src/components/Layout.tsx
import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MenuIcon, LogOut, LogIn } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuthStore } from '../store/authStore'
import DrawerNav from './DrawerNav'

interface LayoutProps {
  children: React.ReactNode
  /** When true, renders children full-screen (no padding). Used by NowPlayingPage. */
  fullscreen?: boolean
}

export default function Layout({ children, fullscreen = false }: LayoutProps) {
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { isConnected, selectedStation } = useRadioStore((s) => ({
    isConnected: s.isConnected,
    selectedStation: s.selectedStation,
  }))
  const { isAuthenticated, clearAuth } = useAuthStore()
  useWebSocket()

  function handleLogout() {
    clearAuth()
    navigate('/login')
  }

  const stationLabel = selectedStation === 'main' ? '' : selectedStation.toUpperCase()

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--art-bg, #07070f)', transition: 'background 0.8s ease' }}>

      {/* Slim top bar */}
      <header
        className="sticky top-0 z-30 flex items-center justify-between px-4"
        style={{
          height: '44px',
          background: 'rgba(0,0,0,0.35)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        {/* Hamburger */}
        <button
          onClick={() => setDrawerOpen(true)}
          className="p-1.5 rounded-lg transition-colors"
          style={{ color: '#505070' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#505070' }}
          aria-label="Open navigation"
        >
          <MenuIcon className="w-5 h-5" />
        </button>

        {/* Wordmark + station */}
        <div className="flex items-center gap-2">
          {stationLabel && (
            <span className="font-mono text-xs" style={{ color: '#303050', letterSpacing: '0.1em', fontSize: '0.6rem' }}>
              {stationLabel}
            </span>
          )}
          <Link
            to="/now-playing"
            className="font-display font-bold tracking-widest text-white uppercase select-none"
            style={{ fontSize: '13px', letterSpacing: '0.22em' }}
          >
            RAIDO
          </Link>
          {/* Live dot */}
          {isConnected && (
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: '#4ade80', boxShadow: '0 0 5px rgba(74,222,128,0.7)' }}
            />
          )}
        </div>

        {/* Auth */}
        <div>
          {isAuthenticated() ? (
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 transition-colors"
              style={{ color: '#303050' }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#303050' }}
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          ) : (
            <Link
              to="/login"
              className="p-1.5 transition-colors"
              style={{ color: '#303050' }}
            >
              <LogIn className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </header>

      {/* Drawer */}
      <DrawerNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      {/* Content */}
      {fullscreen ? (
        <div className="flex-1 relative">
          {children}
        </div>
      ) : (
        <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-6">
          {children}
        </main>
      )}
    </div>
  )
}
