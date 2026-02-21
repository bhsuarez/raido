import React from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { HomeIcon, SettingsIcon, RadioIcon, WifiIcon, WifiOffIcon, LibraryIcon, Sparkles, LogOut, LogIn } from 'lucide-react'
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
  const { isConnected, nowPlaying } = useRadioStore((state) => ({
    isConnected: state.isConnected,
    nowPlaying: state.nowPlaying,
  }))
  const { isAuthenticated, clearAuth } = useAuthStore()
  useWebSocket()

  const navigation = [
    { name: 'Now Playing', href: '/now-playing', icon: HomeIcon },
    { name: 'DJ Admin', href: '/raido/admin', icon: SettingsIcon },
    { name: 'Stations', href: '/stations', icon: RadioIcon },
    { name: 'Media', href: '/media', icon: LibraryIcon },
    { name: 'Enrich', href: '/raido/enrich', icon: Sparkles },
  ]

  function handleLogout() {
    clearAuth()
    navigate('/login')
  }

  const trackTitle = nowPlaying?.track?.title?.trim()
  const trackArtist = nowPlaying?.track?.artist?.trim()
  const songLabel = trackTitle ? (trackArtist ? `${trackTitle} — ${trackArtist}` : trackTitle) : null

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Top Header */}
      <header className="bg-gray-900/95 backdrop-blur-md border-b border-gray-800 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="flex items-center h-14 gap-4">
            {/* Logo */}
            <Link to="/" className="flex-shrink-0">
              <Logo size="sm" />
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1 ml-2">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'text-primary-400 bg-primary-500/10'
                        : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
                    }`}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </Link>
                )
              })}
            </nav>

            {/* Now playing ticker — desktop only */}
            {songLabel && (
              <div className="hidden md:block flex-1 min-w-0 mx-4">
                <div className="flex items-center gap-2">
                  <span className="live-dot flex-shrink-0" aria-hidden="true" />
                  <span className="text-sm text-gray-300 truncate" title={songLabel}>
                    {songLabel}
                  </span>
                </div>
              </div>
            )}

            {/* Connection status + logout */}
            <div className="ml-auto flex-shrink-0 flex items-center gap-3">
              <div
                className={`flex items-center gap-1.5 text-xs font-medium ${
                  isConnected ? 'text-green-400' : 'text-red-400'
                }`}
                role="status"
                aria-label={isConnected ? 'Connected' : 'Disconnected'}
              >
                {isConnected ? (
                  <WifiIcon className="h-4 w-4" />
                ) : (
                  <WifiOffIcon className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">{isConnected ? 'Live' : 'Offline'}</span>
              </div>
              {isAuthenticated() ? (
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              ) : (
                <Link
                  to="/login"
                  title="Sign in"
                  className="text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <LogIn className="h-4 w-4" />
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Mobile: now playing strip below header */}
        {songLabel && (
          <div className="md:hidden border-t border-gray-800 px-4 py-2 bg-gray-900/80">
            <div className="flex items-center gap-2">
              <span className="live-dot flex-shrink-0" aria-hidden="true" />
              <span className="text-xs text-gray-300 truncate">{songLabel}</span>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-6 pb-24 md:pb-8">
        {children}
      </main>

      {/* Mobile Bottom Navigation */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-gray-900/95 backdrop-blur-md border-t border-gray-800 safe-bottom"
        aria-label="Mobile navigation"
      >
        <div className="flex items-stretch justify-around px-2 py-1">
          {navigation.map((item) => {
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
