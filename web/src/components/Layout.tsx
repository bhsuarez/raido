import React, { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  HomeIcon,
  WifiIcon,
  WifiOffIcon,
  BarChart3Icon,
  SettingsIcon,
  RadioIcon,
  ChevronDownIcon,
} from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'
import Logo from './Logo'
import { apiHelpers } from '../utils/api'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const {
    isConnected,
    nowPlaying,
    stations,
    setStations,
    currentStationSlug,
    setCurrentStationSlug,
  } = useRadioStore((state) => ({
    isConnected: state.isConnected,
    nowPlaying: state.nowPlaying,
    stations: state.stations,
    setStations: state.setStations,
    currentStationSlug: state.currentStationSlug,
    setCurrentStationSlug: state.setCurrentStationSlug,
  }))
  // Establish WebSocket connection for live updates
  useWebSocket()

  const { data: stationsData } = useQuery(['stations'], () => apiHelpers.getStations().then(res => res.data), {
    staleTime: 60000,
  })

  useEffect(() => {
    if (stationsData) {
      setStations(stationsData)
    }
  }, [stationsData, setStations])

  const currentStation = stations.find((station) => station.slug === currentStationSlug)

  const navigation = [
    { name: 'Now Playing', href: '/', icon: HomeIcon },
    { name: 'DJ Admin', href: '/tts', icon: SettingsIcon },
    { name: 'Analytics', href: '/analytics', icon: BarChart3Icon },
  ]

  const trackTitle = nowPlaying?.track?.title?.trim()
  const trackArtist = nowPlaying?.track?.artist?.trim()
  const songLabel = trackTitle ? (trackArtist ? `${trackTitle} — ${trackArtist}` : trackTitle) : null

  const handleStationChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setCurrentStationSlug(event.target.value)
  }

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
            <nav className="hidden md:flex items-center space-x-4">
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
              {stations.length > 0 ? (
                <div className="relative">
                  <label htmlFor="station-menu" className="sr-only">
                    Switch station
                  </label>
                  <div className="relative">
                    <RadioIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-primary-300" />
                    <select
                      id="station-menu"
                      className="appearance-none bg-gray-700/80 border border-gray-600 text-gray-100 text-sm pl-9 pr-8 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      value={currentStationSlug}
                      onChange={handleStationChange}
                    >
                      {stations.map((station) => (
                        <option key={station.id} value={station.slug}>
                          {station.stream_name || station.name}
                        </option>
                      ))}
                    </select>
                    <ChevronDownIcon className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-300" />
                  </div>
                </div>
              ) : null}
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
            {stations.length > 0 ? (
              <div className="mt-3">
                <label className="block text-xs uppercase tracking-wide text-gray-400 mb-1">Station</label>
                <select
                  className="w-full bg-gray-700 text-gray-100 text-sm rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={currentStationSlug}
                  onChange={handleStationChange}
                >
                  {stations.map((station) => (
                    <option key={station.id} value={station.slug}>
                      {station.stream_name || station.name}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
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
