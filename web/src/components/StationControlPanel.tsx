import React, { useEffect, useState, useCallback } from 'react'
import { RadioIcon, MusicIcon, ExternalLinkIcon, ClipboardIcon, SettingsIcon, ActivityIcon } from 'lucide-react'
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
      const list = (response.data || []).filter((s: Station) => s.is_active)
      setStations(list)
      if (list.length > 0) setSelectedStation(list[0].identifier)
    } catch {
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
        const res = await apiHelpers.getNowPlaying(station.identifier)
        const np = res.data
        statuses[station.identifier] = {
          station: station.identifier,
          now_playing: np?.track ? {
            title: np.track.title,
            artist: np.track.artist,
            artwork_url: np.track.artwork_url,
          } : null,
          is_playing: np?.is_playing || false,
          stream_url: `/stream/${station.identifier === 'main' ? 'raido' : station.identifier}.mp3`,
          admin_url: station.identifier === 'main' ? '/raido/admin' : `/${station.identifier}/admin`,
        }
      } catch {
        // station unreachable
      }
    }
    setStationStatuses(statuses)
  }, [stations])

  useEffect(() => { loadStations() }, [])
  useEffect(() => { localStorage.setItem('selectedStation', selectedStation) }, [selectedStation])
  useEffect(() => {
    if (stations.length === 0) return
    loadStationStatuses()
    const id = setInterval(loadStationStatuses, 5000)
    return () => clearInterval(id)
  }, [stations, loadStationStatuses])

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="section-header">Stations</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[1, 2].map(i => (
            <div key={i} className="card p-5 animate-pulse space-y-3">
              <div className="h-4 bg-gray-800 rounded w-1/2" />
              <div className="flex gap-3">
                <div className="w-14 h-14 bg-gray-800 rounded-xl" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 bg-gray-800 rounded w-3/4" />
                  <div className="h-3 bg-gray-800 rounded w-1/2" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const selected = stationStatuses[selectedStation]
  const selectedInfo = stations.find(s => s.identifier === selectedStation)

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-bold text-white">Stations</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage and monitor radio stations</p>
      </div>

      {/* Station grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {stations.map((station) => {
          const status = stationStatuses[station.identifier]
          const isSelected = selectedStation === station.identifier

          return (
            <button
              key={station.id}
              onClick={() => setSelectedStation(station.identifier)}
              className={`card p-4 text-left transition-all focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                isSelected
                  ? 'border-primary-500/50 bg-primary-500/5'
                  : 'hover:border-gray-700'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-white text-sm">{station.name}</h3>
                  {station.description && (
                    <p className="text-xs text-gray-500 mt-0.5">{station.description}</p>
                  )}
                </div>
                {status?.is_playing ? (
                  <div className="flex items-center gap-1.5">
                    <span className="live-dot" />
                    <span className="text-xs font-semibold text-green-400">LIVE</span>
                  </div>
                ) : (
                  <span className="text-xs text-gray-600">Offline</span>
                )}
              </div>

              {status?.now_playing ? (
                <div className="flex gap-2.5 items-center">
                  {status.now_playing.artwork_url ? (
                    <img
                      src={status.now_playing.artwork_url}
                      alt="Album art"
                      className="w-10 h-10 rounded-lg object-cover flex-shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0">
                      <MusicIcon className="w-4 h-4 text-gray-600" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-gray-200 truncate">{status.now_playing.title}</p>
                    <p className="text-xs text-gray-500 truncate">{status.now_playing.artist}</p>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2.5 items-center">
                  <div className="w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0">
                    <RadioIcon className="w-4 h-4 text-gray-600" />
                  </div>
                  <p className="text-xs text-gray-600">No track playing</p>
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* Selected station detail */}
      {selected && selectedInfo && (
        <div className="card overflow-hidden">
          {/* Header */}
          <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div>
                <h2 className="font-semibold text-white">{selectedInfo.name}</h2>
                <p className="text-xs text-gray-500 font-mono">{selectedStation}</p>
              </div>
              {selected.is_playing ? (
                <span className="flex items-center gap-1.5 text-xs font-semibold text-green-400 bg-green-500/10 border border-green-500/20 px-2.5 py-1 rounded-full">
                  <span className="live-dot" />
                  LIVE
                </span>
              ) : (
                <span className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-2.5 py-1 rounded-full">
                  OFFLINE
                </span>
              )}
            </div>
            <a
              href={selected.stream_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary flex items-center gap-1.5 text-sm"
            >
              <ExternalLinkIcon className="w-3.5 h-3.5" />
              Listen
            </a>
          </div>

          {/* Now Playing large view */}
          <div className="p-5">
            {selected.now_playing ? (
              <div className="flex gap-4 mb-5">
                {selected.now_playing.artwork_url ? (
                  <img
                    src={selected.now_playing.artwork_url}
                    alt="Album artwork"
                    className="w-20 h-20 sm:w-24 sm:h-24 rounded-xl object-cover flex-shrink-0 border border-gray-800"
                  />
                ) : (
                  <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-xl bg-gray-800 flex items-center justify-center flex-shrink-0">
                    <MusicIcon className="w-8 h-8 text-gray-600" />
                  </div>
                )}
                <div className="flex-1 min-w-0 flex flex-col justify-center">
                  <p className="section-header mb-1">Now Playing</p>
                  <p className="font-bold text-white text-lg leading-tight truncate">
                    {selected.now_playing.title}
                  </p>
                  <p className="text-gray-400 truncate">{selected.now_playing.artist}</p>
                </div>
              </div>
            ) : (
              <div className="flex gap-4 mb-5 items-center">
                <div className="w-20 h-20 rounded-xl bg-gray-800 flex items-center justify-center flex-shrink-0">
                  <RadioIcon className="w-8 h-8 text-gray-600" />
                </div>
                <p className="text-gray-500">No track currently playing</p>
              </div>
            )}

            {/* Info grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
              <div className="bg-gray-800 rounded-xl p-3.5">
                <p className="section-header mb-1.5">Status</p>
                <p className={`text-sm font-medium flex items-center gap-1.5 ${selected.is_playing ? 'text-green-400' : 'text-red-400'}`}>
                  <ActivityIcon className="w-3.5 h-3.5" />
                  {selected.is_playing ? 'Online' : 'Offline'}
                </p>
              </div>
              <div className="bg-gray-800 rounded-xl p-3.5">
                <p className="section-header mb-1.5">Stream URL</p>
                <p className="text-sm text-gray-300 font-mono truncate">{selected.stream_url}</p>
              </div>
              <div className="bg-gray-800 rounded-xl p-3.5">
                <p className="section-header mb-1.5">Station ID</p>
                <p className="text-sm text-gray-300 font-mono">{selectedStation}</p>
              </div>
            </div>

            {/* Quick actions */}
            <div className="flex flex-wrap gap-2">
              <a
                href={selected.admin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary flex items-center gap-1.5 text-sm"
              >
                <SettingsIcon className="w-3.5 h-3.5" />
                DJ Admin
              </a>
              <button
                onClick={() => window.open(`/api/v1/now/?station=${selectedStation}`, '_blank')}
                className="btn-secondary flex items-center gap-1.5 text-sm"
              >
                <ExternalLinkIcon className="w-3.5 h-3.5" />
                View API
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(selected.stream_url)
                  toast.success('Stream URL copied')
                }}
                className="btn-secondary flex items-center gap-1.5 text-sm"
              >
                <ClipboardIcon className="w-3.5 h-3.5" />
                Copy URL
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StationControlPanel
