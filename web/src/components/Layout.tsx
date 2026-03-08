import React, { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { HomeIcon, SettingsIcon, RadioIcon, WifiIcon, WifiOffIcon, LibraryIcon, Sparkles, MicIcon, LogOut, LogIn } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuthStore } from '../store/authStore'
import { apiHelpers } from '../utils/api'
import Logo from './Logo'

interface LayoutProps {
  children: React.ReactNode
}

interface Station {
  id: number
  identifier: string
  name: string
  is_active: boolean
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

  const [stations, setStations] = useState<Station[]>([])
  const [selectedStation, setSelectedStation] = useState<string>(() => {
    return localStorage.getItem('selectedStation') || 'main'
  })

  useEffect(() => {
    apiHelpers.getStations().then((res) => {
      const active = (res.data || []).filter((s: Station) => s.is_active)
      setStations(active)
    }).catch(() => {})
  }, [])

  function handleStationChange(id: string) {
    setSelectedStation(id)
    localStorage.setItem('selectedStation', id)
  }

  const djAdminHref = selectedStation === 'main' ? '/raido/admin' : `/${selectedStation}/admin`

  const navigation = [
    { name: 'Now Playing', href: '/now-playing', icon: HomeIcon },
    { name: 'DJ Admin', href: djAdminHref, icon: SettingsIcon },
    { name: 'Stations', href: '/stations', icon: RadioIcon },
    { name: 'Media', href: '/media', icon: LibraryIcon },
    { name: 'Enrich', href: '/raido/enrich', icon: Sparkles },
    { name: 'Transcripts', href: '/transcripts', icon: MicIcon },
  ]

  function handleLogout() {
    clearAuth()
    navigate('/login')
  }

  const trackTitle = nowPlaying?.track?.title?.trim()
  const trackArtist = nowPlaying?.track?.artist?.trim()
  const isUnknown = (s?: string) => !s || s.toLowerCase().startsWith('unknown')
  const songLabel = !isUnknown(trackTitle)
    ? (!isUnknown(trackArtist) ? `${trackTitle} — ${trackArtist}` : trackTitle!)
    : null

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

            {/* Station picker — desktop only */}
            {stations.length > 1 && (
              <div className="hidden md:flex items-center ml-2">
                <select
                  value={selectedStation}
                  onChange={(e) => handleStationChange(e.target.value)}
                  className="text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:border-primary-500 cursor-pointer"
                >
                  {stations.map((s) => (
                    <option key={s.identifier} value={s.identifier}>{s.name}</option>
                  ))}
                </select>
              </div>
            )}

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
              <a
                href="/stream/raido.mp3"
                className={`flex items-center gap-1.5 text-xs font-medium ${
                  isConnected ? 'text-green-400 hover:text-green-300' : 'text-red-400'
                }`}
                role="status"
                aria-label={isConnected ? 'Listen live' : 'Disconnected'}
                title={isConnected ? 'Listen to stream' : undefined}
                {...(!isConnected && { onClick: (e) => e.preventDefault() })}
              >
                {isConnected ? (
                  <WifiIcon className="h-4 w-4" />
                ) : (
                  <WifiOffIcon className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">{isConnected ? 'Live' : 'Offline'}</span>
              </a>
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
