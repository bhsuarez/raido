import React, { useEffect, useState, useCallback } from 'react'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'

interface Station {
  id: number
  identifier: string
  name: string
  description: string | null
  is_active: boolean
}

interface StationStatus {
  station: string
  now_playing: {
    title: string
    artist: string
    artwork_url?: string
  } | null
  is_playing: boolean
  stream_url: string
  admin_url: string
}

const StationControlPanel: React.FC = () => {
  const [stations, setStations] = useState<Station[]>([])
  const [stationStatuses, setStationStatuses] = useState<Record<string, StationStatus>>({})
  const [selectedStation, setSelectedStation] = useState<string>(() => {
    return localStorage.getItem('selectedStation') || 'main'
  })
  const [loading, setLoading] = useState(true)

  const loadStations = async () => {
    try {
      const response = await apiHelpers.getStations()
      const stationList = response.data || []
      setStations(stationList.filter((s: Station) => s.is_active))
      if (stationList.length > 0) {
        setSelectedStation(stationList[0].identifier)
      }
    } catch (error) {
      console.error('Failed to load stations:', error)
      toast.error('Failed to load stations')
    } finally {
      setLoading(false)
    }
  }

  const loadStationStatuses = useCallback(async () => {
    if (stations.length === 0) return

    const statuses: Record<string, StationStatus> = {}

    for (const station of stations) {
      try {
        const nowPlayingResponse = await apiHelpers.getNowPlaying(station.identifier)
        const nowPlaying = nowPlayingResponse.data

        statuses[station.identifier] = {
          station: station.identifier,
          now_playing: nowPlaying?.track ? {
            title: nowPlaying.track.title,
            artist: nowPlaying.track.artist,
            artwork_url: nowPlaying.track.artwork_url
          } : null,
          is_playing: nowPlaying?.is_playing || false,
          stream_url: `/stream/${station.identifier === 'main' ? 'raido' : station.identifier}.mp3`,
          admin_url: station.identifier === 'main' ? '/raido/admin' : `/${station.identifier}/admin`
        }
      } catch (error) {
        console.error(`Failed to get status for ${station.identifier}:`, error)
      }
    }

    setStationStatuses(statuses)
  }, [stations])

  useEffect(() => {
    loadStations()
  }, [])

  useEffect(() => {
    localStorage.setItem('selectedStation', selectedStation)
  }, [selectedStation])

  useEffect(() => {
    if (stations.length > 0) {
      loadStationStatuses() // Load immediately
      const interval = setInterval(loadStationStatuses, 5000) // Then update every 5s
      return () => clearInterval(interval)
    }
  }, [stations, loadStationStatuses])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-white">Loading stations...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            🎵 Station Control Panel
          </h1>
          <p className="text-gray-400">
            Manage and monitor all radio stations
          </p>
        </div>

        {/* Station Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {stations.map((station) => {
            const status = stationStatuses[station.identifier]
            const isSelected = selectedStation === station.identifier

            return (
              <div
                key={station.id}
                className={`
                  relative bg-gray-800 rounded-lg p-6 shadow-lg cursor-pointer
                  transition-all duration-200 hover:scale-105
                  ${isSelected ? 'ring-4 ring-pirate-500' : 'hover:bg-gray-750'}
                `}
                onClick={() => setSelectedStation(station.identifier)}
              >
                {/* Station Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-white mb-1">
                      {station.name}
                    </h3>
                    {station.description && (
                      <p className="text-sm text-gray-400">{station.description}</p>
                    )}
                  </div>
                  {status?.is_playing && (
                    <div className="flex items-center gap-2">
                      <span className="relative flex h-3 w-3">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                      </span>
                      <span className="text-xs text-green-400 font-medium">LIVE</span>
                    </div>
                  )}
                </div>

                {/* Now Playing */}
                {status?.now_playing ? (
                  <div className="flex gap-3 mb-4">
                    {status.now_playing.artwork_url ? (
                      <img
                        src={status.now_playing.artwork_url}
                        alt="Album artwork"
                        className="w-16 h-16 rounded object-cover"
                      />
                    ) : (
                      <div className="w-16 h-16 rounded bg-gray-700 flex items-center justify-center">
                        <span className="text-2xl">🎵</span>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-white font-medium truncate">
                        {status.now_playing.title}
                      </div>
                      <div className="text-gray-400 text-sm truncate">
                        {status.now_playing.artist}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-3 mb-4 text-gray-500">
                    <div className="w-16 h-16 rounded bg-gray-700 flex items-center justify-center">
                      <span className="text-2xl">🔇</span>
                    </div>
                    <div>No track playing</div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <a
                    href={status?.stream_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 px-3 py-2 bg-pirate-500 hover:bg-pirate-600 text-white rounded text-sm font-medium text-center transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    🎧 Listen
                  </a>
                  <a
                    href={status?.admin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm font-medium text-center transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    ⚙️ Admin
                  </a>
                </div>

                {/* Selected Indicator */}
                {isSelected && (
                  <div className="absolute top-2 right-2 bg-pirate-500 text-white text-xs px-2 py-1 rounded">
                    Selected
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Selected Station — Main Deck */}
        {selectedStation && stationStatuses[selectedStation] && (() => {
          const status = stationStatuses[selectedStation]
          const stationInfo = stations.find(s => s.identifier === selectedStation)
          const np = status.now_playing
          return (
            <div className="bg-gray-800 rounded-xl shadow-xl overflow-hidden">
              {/* Deck header */}
              <div className="bg-gradient-to-r from-pirate-900 to-gray-800 px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h2 className="text-2xl font-bold text-white">
                    {stationInfo?.name ?? selectedStation} — Main Deck
                  </h2>
                  {status.is_playing ? (
                    <span className="flex items-center gap-1.5 bg-green-900/50 border border-green-500/40 text-green-400 text-xs font-semibold px-3 py-1 rounded-full">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                      </span>
                      LIVE
                    </span>
                  ) : (
                    <span className="bg-red-900/50 border border-red-500/40 text-red-400 text-xs font-semibold px-3 py-1 rounded-full">OFFLINE</span>
                  )}
                </div>
                {/* Listen button */}
                <a
                  href={status.stream_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-4 py-2 bg-pirate-500 hover:bg-pirate-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  🎧 Listen Live
                </a>
              </div>

              <div className="p-6">
                {/* Now Playing — large artwork + info */}
                {np ? (
                  <div className="flex gap-6 mb-6">
                    <div className="flex-shrink-0">
                      {np.artwork_url ? (
                        <img
                          src={np.artwork_url}
                          alt="Album artwork"
                          className="w-32 h-32 rounded-xl object-cover shadow-lg ring-2 ring-pirate-500/30"
                        />
                      ) : (
                        <div className="w-32 h-32 rounded-xl bg-gray-700 flex items-center justify-center shadow-lg">
                          <span className="text-5xl">🎵</span>
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                      <div className="text-xs text-pirate-400 font-semibold uppercase tracking-widest mb-1">Now Playing</div>
                      <h3 className="text-2xl font-bold text-white truncate mb-1">{np.title}</h3>
                      <p className="text-pirate-300 font-medium text-lg truncate">{np.artist}</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center gap-4 mb-6 text-gray-500">
                    <div className="w-32 h-32 rounded-xl bg-gray-700 flex items-center justify-center">
                      <span className="text-5xl">🔇</span>
                    </div>
                    <p className="text-lg">No track currently playing</p>
                  </div>
                )}

                {/* Info grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
                  <div className="bg-gray-750 rounded-lg p-4">
                    <div className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-1">Status</div>
                    <div className="text-white font-medium">
                      {status.is_playing ? (
                        <span className="text-green-400">● Online</span>
                      ) : (
                        <span className="text-red-400">● Offline</span>
                      )}
                    </div>
                  </div>
                  <div className="bg-gray-750 rounded-lg p-4">
                    <div className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-1">Stream URL</div>
                    <div className="text-white font-mono text-sm truncate">{status.stream_url}</div>
                  </div>
                  <div className="bg-gray-750 rounded-lg p-4">
                    <div className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-1">Station ID</div>
                    <div className="text-white font-mono text-sm">{selectedStation}</div>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="flex flex-wrap gap-3">
                  <a
                    href={status.admin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-pirate-700 hover:bg-pirate-600 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    ⚙️ DJ Admin
                  </a>
                  <button
                    onClick={() => window.open(`/api/v1/now/?station=${selectedStation}`, '_blank')}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    📊 View API
                  </button>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(status.stream_url)
                      toast.success('Stream URL copied!')
                    }}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    📋 Copy Stream URL
                  </button>
                </div>
              </div>
            </div>
          )
        })()}

      </div>
    </div>
  )
}

export default StationControlPanel
