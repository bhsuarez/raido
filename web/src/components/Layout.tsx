import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { HomeIcon, SettingsIcon, RadioIcon, WifiOffIcon, LibraryIcon, Sparkles, MicIcon, LogOut, LogIn } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuthStore } from '../store/authStore'
import Logo from './Logo'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { isConnected, nowPlaying, selectedStation } = useRadioStore((state) => ({
    isConnected: state.isConnected,
    nowPlaying: state.nowPlaying,
    selectedStation: state.selectedStation,
  }))
  const { isAuthenticated, clearAuth } = useAuthStore()
  useWebSocket()

  function handleLogout() {
    clearAuth()
    navigate('/login')
  }

  const djAdminHref = selectedStation === 'main' ? '/raido/admin' : `/${selectedStation}/admin`

  const navItems = [
    { name: 'Now Playing', href: '/now-playing',   icon: HomeIcon },
    { name: 'DJ Admin',    href: djAdminHref,       icon: SettingsIcon },
    { name: 'Stations',    href: '/stations',       icon: RadioIcon },
    { name: 'Media',       href: '/media',          icon: LibraryIcon },
    { name: 'Enrich',      href: '/raido/enrich',   icon: Sparkles },
    { name: 'Transcripts', href: '/transcripts',    icon: MicIcon },
  ]

  const track = nowPlaying?.track
  const isUnknown = (s?: string) => !s || s.toLowerCase().startsWith('unknown')
  const songLabel = track && !isUnknown(track.title)
    ? (!isUnknown(track.artist) ? `${track.title} — ${track.artist}` : track.title!)
    : null

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#07070f' }}>

      {/* ── Top Header ─────────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-40"
        style={{
          background: 'rgba(7, 7, 15, 0.92)',
          backdropFilter: 'blur(16px)',
          borderBottom: '1px solid #1a1a32',
        }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="flex items-center h-14 gap-5">

            {/* Logo */}
            <Link to="/" className="flex-shrink-0">
              <Logo size="sm" />
            </Link>

            {/* Desktop navigation — text-only, uppercase, Syne */}
            <nav className="hidden md:flex items-center gap-1 ml-1">
              {navItems.map((item) => {
                const isActive = location.pathname === item.href
                  || (item.href !== '/now-playing' && location.pathname.startsWith(item.href.split('?')[0].replace(/\/admin$/, '')))
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className="relative px-3 py-1.5 text-xs font-display font-bold uppercase tracking-widest transition-colors duration-150"
                    style={{
                      color: isActive ? '#38bdf8' : '#404060',
                      letterSpacing: '0.1em',
                    }}
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = '#8080a0' }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = '#404060' }}
                  >
                    {item.name}
                    {isActive && (
                      <span
                        className="absolute bottom-0 left-3 right-3 h-px rounded-full"
                        style={{ background: 'linear-gradient(90deg, transparent, #38bdf8, transparent)' }}
                      />
                    )}
                  </Link>
                )
              })}
            </nav>

            {/* Now playing ticker */}
            {songLabel && (
              <div className="hidden md:flex flex-1 min-w-0 items-center gap-2 mx-3 overflow-hidden">
                <span className="live-dot flex-shrink-0" aria-hidden="true" />
                <span
                  className="text-xs truncate"
                  style={{ color: '#505070', fontFamily: 'Manrope, sans-serif', letterSpacing: '0.02em' }}
                  title={songLabel}
                >
                  {songLabel}
                </span>
              </div>
            )}

            {/* Status + auth */}
            <div className="ml-auto flex-shrink-0 flex items-center gap-3">
              {isConnected ? (
                <a
                  href="/stream/raido.mp3"
                  className="flex items-center gap-1.5 text-xs font-mono transition-colors"
                  style={{ color: '#4ade80' }}
                  title="Listen live"
                >
                  <span className="live-dot glow-live" />
                  <span className="hidden sm:inline" style={{ letterSpacing: '0.08em' }}>ON AIR</span>
                </a>
              ) : (
                <span className="flex items-center gap-1.5 text-xs font-mono" style={{ color: '#503030' }}>
                  <WifiOffIcon className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">OFFLINE</span>
                </span>
              )}

              {isAuthenticated() ? (
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  style={{ color: '#303050' }}
                  className="transition-colors hover:text-gray-400"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              ) : (
                <Link
                  to="/login"
                  title="Sign in"
                  style={{ color: '#303050' }}
                  className="transition-colors hover:text-gray-400"
                >
                  <LogIn className="h-3.5 w-3.5" />
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Mobile: now playing strip */}
        {songLabel && (
          <div className="md:hidden px-4 py-2" style={{ borderTop: '1px solid #0f0f20' }}>
            <div className="flex items-center gap-2">
              <span className="live-dot flex-shrink-0" />
              <span className="text-xs truncate" style={{ color: '#404060' }}>{songLabel}</span>
            </div>
          </div>
        )}
      </header>

      {/* ── Main Content ────────────────────────────────────────────── */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-8">
        {children}
      </main>

      {/* ── Mobile Bottom Navigation ────────────────────────────────── */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 safe-bottom"
        style={{
          background: 'rgba(7, 7, 15, 0.95)',
          backdropFilter: 'blur(16px)',
          borderTop: '1px solid #1a1a32',
        }}
        aria-label="Mobile navigation"
      >
        <div className="flex items-stretch justify-around px-2 py-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`nav-item flex-1 ${isActive ? 'nav-item-active' : 'nav-item-inactive'}`}
                aria-current={isActive ? 'page' : undefined}
                aria-label={item.name}
              >
                <item.icon className="h-5 w-5" />
              </Link>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
