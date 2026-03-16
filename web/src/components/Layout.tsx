import React, { useState, useRef, useEffect } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { MenuIcon, LogIn, UserIcon, KeyRoundIcon, LogOutIcon } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuthStore } from '../store/authStore'
import DrawerNav from './DrawerNav'


interface LayoutProps {
  children?: React.ReactNode
  /** When true, renders children full-screen (no padding). Used by NowPlayingPage. */
  fullscreen?: boolean
}

export default function Layout({ children, fullscreen = false }: LayoutProps) {
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])
  const { isConnected, selectedStation } = useRadioStore((s) => ({
    isConnected: s.isConnected,
    selectedStation: s.selectedStation,
  }))
  const { isAuthenticated, clearAuth, avatarUrl, fullName, displayName, email } = useAuthStore()
  useWebSocket()

  function handleLogout() {
    clearAuth()
    navigate('/login')
  }

  const profileLabel = displayName || fullName || email || ''
  const initials = profileLabel.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2) || '?'

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
            className="font-bold tracking-widest text-white uppercase select-none"
            style={{ fontSize: '13px', letterSpacing: '0.22em' }}
          >
            RAIDO
          </Link>
          {isConnected && (
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: '#4ade80', boxShadow: '0 0 5px rgba(74,222,128,0.7)' }}
            />
          )}
        </div>

        {/* Auth */}
        <div className="relative" ref={menuRef}>
          {isAuthenticated() ? (
            <>
              <button onClick={() => setMenuOpen(o => !o)} className="block" title="Account">
                {avatarUrl ? (
                  <img src={avatarUrl} alt="Profile" className="w-6 h-6 rounded-full object-cover" />
                ) : (
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{ background: '#1a1a32', color: '#38bdf8', border: '1px solid #2a2a48' }}
                  >
                    {initials}
                  </div>
                )}
              </button>

              {menuOpen && (
                <div
                  className="absolute right-0 top-8 flex flex-col py-1 z-50"
                  style={{
                    background: 'rgba(8,8,18,0.97)',
                    border: '1px solid #1a1a32',
                    borderRadius: '8px',
                    minWidth: '160px',
                    backdropFilter: 'blur(16px)',
                  }}
                >
                  <Link
                    to="/profile"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors"
                    style={{ color: '#808090' }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#c0c0e0' }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#808090' }}
                  >
                    <UserIcon className="w-3.5 h-3.5 flex-shrink-0" />
                    Profile
                  </Link>
                  <Link
                    to="/profile#password"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors"
                    style={{ color: '#808090' }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#c0c0e0' }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#808090' }}
                  >
                    <KeyRoundIcon className="w-3.5 h-3.5 flex-shrink-0" />
                    Change Password
                  </Link>
                  <div style={{ height: '1px', background: '#1a1a32', margin: '4px 0' }} />
                  <button
                    onClick={() => { setMenuOpen(false); handleLogout() }}
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm transition-colors w-full text-left"
                    style={{ color: '#808090' }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#f87171' }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#808090' }}
                  >
                    <LogOutIcon className="w-3.5 h-3.5 flex-shrink-0" />
                    Sign Out
                  </button>
                </div>
              )}
            </>
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

      {/* Slide-out Drawer */}
      <DrawerNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      {/* Content */}
      {fullscreen ? (
        <div className="flex-1 relative">
          {children ?? <Outlet />}
        </div>
      ) : (
        <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-6">
          {children ?? <Outlet />}
        </main>
      )}


    </div>
  )
}
