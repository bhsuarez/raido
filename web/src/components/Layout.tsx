import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  HomeIcon, 
  ClockIcon, 
  Radio,
  WifiIcon,
  WifiOffIcon,
  MicIcon,
  BarChart3Icon,
} from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const { isConnected, toggleDarkMode, isDarkMode } = useRadioStore()
  // Establish WebSocket connection for live updates
  useWebSocket()

  const navigation = [
    { name: 'Now Playing', href: '/', icon: HomeIcon },
    { name: 'DJ Admin', href: '/tts', icon: MicIcon },
    { name: 'Analytics', href: '/analytics', icon: BarChart3Icon },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900">
      {/* Header */}
      <header className="bg-gray-800 bg-opacity-95 backdrop-blur-sm border-b border-gray-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo and Title */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <Radio className="h-8 w-8 text-primary-500" />
                <div>
                  <h1 className="text-xl font-bold font-pirate text-primary-400 glitch" data-text="RAIDO">
                    RAIDO
                  </h1>
                  <p className="text-xs text-gray-400 -mt-1">AI Pirate Radio</p>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <nav className="hidden md:flex space-x-6">
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

            {/* Status and Controls */}
            <div className="flex items-center space-x-4">
              {/* Connection Status */}
              <div className={`flex items-center space-x-2 text-xs ${
                isConnected ? 'text-green-400' : 'text-red-400'
              }`}>
                {isConnected ? (
                  <WifiIcon className="h-4 w-4" />
                ) : (
                  <WifiOffIcon className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>

              {/* Dark Mode Toggle */}
              <button
                onClick={toggleDarkMode}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-md transition-colors"
                aria-label="Toggle dark mode"
              >
                {isDarkMode ? '☀️' : '🌙'}
              </button>
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
