import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { HomeIcon, WifiIcon, WifiOffIcon, SettingsIcon, RadioIcon } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'
import Logo from './Logo'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { isConnected, nowPlaying } = useRadioStore((state) => ({
    isConnected: state.isConnected,
    nowPlaying: state.nowPlaying,
  }))
  // Establish WebSocket connection for live updates
  useWebSocket()

  const isStationsPage = location.pathname.startsWith('/stations')

  const navigation = isStationsPage
    ? [{ name: 'Stations', href: '/stations', icon: RadioIcon }]
    : [
        { name: 'Now Playing', href: '/now-playing', icon: HomeIcon },
        { name: 'DJ Admin', href: '/raido/admin', icon: SettingsIcon },
        { name: 'Stations', href: '/stations', icon: RadioIcon },
      ]

  const trackTitle = nowPlaying?.track?.title?.trim()
  const trackArtist = nowPlaying?.track?.artist?.trim()
  const songLabel = trackTitle ? (trackArtist ? `${trackTitle} — ${trackArtist}` : trackTitle) : null

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900">
      {/* Header */}
      <header className="bg-gray-800 bg-opacity-95 backdrop-blur-sm border-b border-gray-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            {/* Logo and Title */}
            <div className="flex items-center space-x-4">
              <Link to="/" className="flex items-center hover:opacity-80 transition-opacity">
                <Logo size="md" />
              </Link>
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex items-center space-x-6">
              {navigation.map((item) => {
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? 'text-primary-400 bg-primary-900 bg-opacity-50'
                        : 'text-gray-300 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </Link>
                )
              })}
            </nav>

            {songLabel ? (
              <div className="hidden md:block max-w-xs px-4">
                <span className="block truncate text-sm font-medium text-gray-100" title={songLabel}>
                  {songLabel}
                </span>
              </div>
            ) : null}

            {/* Status and Controls */}
            <div className="ml-auto flex items-center space-x-4">
              {/* Connection Status */}
              <div
                className={`flex items-center space-x-2 text-xs ${
                  isConnected ? 'text-green-400' : 'text-red-400'
                }`}
                role="status"
                aria-live="polite"
                aria-label={`Connection status: ${isConnected ? 'Connected' : 'Disconnected'}`}
              >
                {isConnected ? (
                  <WifiIcon className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <WifiOffIcon className="h-4 w-4" aria-hidden="true" />
                )}
                <span className="hidden sm:inline">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden border-t border-gray-700">
          <div className="px-4 py-2 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'text-primary-400 bg-primary-900 bg-opacity-50'
                      : 'text-gray-300 hover:text-white hover:bg-gray-700'
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.name}</span>
                </Link>
              )
            })}
            {songLabel ? (
              <div className="mt-2 px-3 py-2 rounded-md text-sm font-medium text-gray-100 bg-gray-700/40">
                {songLabel}
              </div>
            ) : null}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 bg-opacity-50 border-t border-gray-700 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-gray-400 text-sm">
            <p>🏴‍☠️ Raido - AI Pirate Radio &copy; 2024</p>
            <p className="mt-1">
              Sailing the digital seas with AI-powered beats
            </p>
          </div>
        </div>
      </footer>

    </div>
  )
}
