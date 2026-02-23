/**
 * DownloadGateway — Lidarr integration panel.
 *
 * Provides:
 *  - Artist search + add to Lidarr
 *  - Current download queue with removal
 *  - Missing albums (Wanted)
 *  - Download history
 *  - Root folder / quality profile info
 */

import React, { useEffect, useState, useCallback } from 'react'
import { SearchIcon, DownloadIcon, TrashIcon, RefreshCwIcon, CheckCircleIcon, AlertCircleIcon } from 'lucide-react'
import { apiHelpers } from '../utils/api'

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const lidarrFetch = async (path: string, opts?: RequestInit) => {
  const r = await fetch(apiHelpers.apiUrl(`/api/v1/lidarr${path}`), opts)
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }))
    throw new Error(err.detail || r.statusText)
  }
  return r.json()
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LidarrArtist {
  id: number
  artistName: string
  status: string
  overview?: string
  images?: { url: string; coverType: string }[]
  qualityProfileId: number
  metadataProfileId: number
  path: string
  monitored: boolean
  foreignArtistId: string
}

interface LidarrAlbum {
  id: number
  title: string
  releaseDate: string
  artist: { artistName: string }
  images?: { url: string; coverType: string }[]
  grabbed: boolean
  monitored: boolean
}

interface QueueItem {
  id: number
  title: string
  artist?: { artistName: string }
  album?: { title: string }
  size: number
  sizeleft: number
  status: string
  protocol: string
  downloadClient: string
  indexer: string
  errorMessage?: string
}

interface HistoryItem {
  id: number
  sourceTitle: string
  quality: { quality: { name: string } }
  date: string
  eventType: string
  artist: { artistName: string }
  album: { title: string }
}

interface RootFolder {
  id: number
  path: string
  freeSpace: number
  accessible: boolean
}

interface QualityProfile {
  id: number
  name: string
  upgradeAllowed: boolean
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

function ProgressBar({ size, sizeleft }: { size: number; sizeleft: number }) {
  const pct = size > 0 ? Math.round(((size - sizeleft) / size) * 100) : 0
  return (
    <div className="mt-1 w-full bg-gray-700 rounded-full h-1.5">
      <div className="bg-primary-500 h-1.5 rounded-full transition-all" style={{ width: `${pct}%` }} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

type Tab = 'search' | 'queue' | 'wanted' | 'history'

export default function DownloadGateway() {
  const [tab, setTab] = useState<Tab>('queue')
  const [lidarrOnline, setLidarrOnline] = useState<boolean | null>(null)

  useEffect(() => {
    lidarrFetch('/health')
      .then(d => setLidarrOnline(d.ok === true))
      .catch(() => setLidarrOnline(false))
  }, [])

  if (lidarrOnline === null) {
    return <div className="card p-6 text-sm text-gray-500 animate-pulse">Connecting to Lidarr…</div>
  }

  if (!lidarrOnline) {
    return (
      <div className="card p-6 space-y-2">
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircleIcon className="h-5 w-5" />
          <span className="text-sm font-medium">Lidarr unavailable</span>
        </div>
        <p className="text-xs text-gray-500">
          Make sure the Lidarr service is running and <code className="text-gray-400">LIDARR_API_KEY</code> is set in your environment.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Download Gateway</h1>
        <div className="flex items-center gap-1.5 text-xs text-green-400">
          <CheckCircleIcon className="h-4 w-4" />
          Lidarr connected
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-800/60 rounded-xl p-1 w-fit">
        {(['queue', 'search', 'wanted', 'history'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`text-sm px-3 py-1.5 rounded-lg transition-colors capitalize ${
              tab === t
                ? 'bg-primary-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'queue' && <QueuePanel />}
      {tab === 'search' && <SearchPanel />}
      {tab === 'wanted' && <WantedPanel />}
      {tab === 'history' && <HistoryPanel />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Queue panel
// ---------------------------------------------------------------------------

function QueuePanel() {
  const [items, setItems] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const data = await lidarrFetch('/queue?pageSize=50')
      setItems(data.records ?? data ?? [])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { reload() }, [reload])

  const removeItem = async (id: number, blacklist = false) => {
    try {
      await lidarrFetch(`/queue/${id}?blacklist=${blacklist}`, { method: 'DELETE' })
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (e: any) {
      alert(`Failed to remove: ${e.message}`)
    }
  }

  if (loading) return <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-gray-800/50 rounded-xl animate-pulse" />)}</div>
  if (error) return <div className="card p-4 text-sm text-red-400">Queue error: {error}</div>

  if (items.length === 0) {
    return (
      <div className="card p-8 text-center text-sm text-gray-500">
        Queue is empty
        <button onClick={reload} className="ml-3 btn-secondary text-xs py-1 px-2">
          <RefreshCwIcon className="h-3 w-3" />
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <p className="text-xs text-gray-500">{items.length} item{items.length !== 1 ? 's' : ''}</p>
        <button onClick={reload} className="btn-secondary text-xs py-1 px-2 flex items-center gap-1">
          <RefreshCwIcon className="h-3 w-3" />
          Refresh
        </button>
      </div>
      {items.map(item => (
        <div key={item.id} className="card p-3 space-y-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-white font-medium truncate">{item.title}</p>
              <p className="text-xs text-gray-400 truncate">
                {item.artist?.artistName} — {item.album?.title}
              </p>
              <p className="text-xs text-gray-600 mt-0.5">
                {item.status} · {item.protocol} · {item.indexer}
                {item.size > 0 && ` · ${formatBytes(item.size - item.sizeleft)} / ${formatBytes(item.size)}`}
              </p>
              {item.errorMessage && (
                <p className="text-xs text-red-400 mt-0.5 truncate">{item.errorMessage}</p>
              )}
            </div>
            <button
              onClick={() => removeItem(item.id)}
              className="flex-shrink-0 p-1 text-gray-600 hover:text-red-400 transition-colors"
              title="Remove from queue"
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          </div>
          {item.size > 0 && <ProgressBar size={item.size} sizeleft={item.sizeleft} />}
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Artist search panel
// ---------------------------------------------------------------------------

function SearchPanel() {
  const [term, setTerm] = useState('')
  const [results, setResults] = useState<LidarrArtist[]>([])
  const [loading, setLoading] = useState(false)
  const [rootFolders, setRootFolders] = useState<RootFolder[]>([])
  const [qualityProfiles, setQualityProfiles] = useState<QualityProfile[]>([])
  const [metadataProfiles, setMetadataProfiles] = useState<{ id: number; name: string }[]>([])
  const [selectedRoot, setSelectedRoot] = useState('')
  const [selectedQuality, setSelectedQuality] = useState<number | null>(null)
  const [selectedMeta, setSelectedMeta] = useState<number | null>(null)
  const [addingId, setAddingId] = useState<string | null>(null)
  const [added, setAdded] = useState<Set<string>>(new Set())

  useEffect(() => {
    Promise.all([
      lidarrFetch('/rootfolder').then(d => { setRootFolders(d); if (d[0]) setSelectedRoot(d[0].path) }).catch(() => {}),
      lidarrFetch('/qualityprofile').then(d => { setQualityProfiles(d); if (d[0]) setSelectedQuality(d[0].id) }).catch(() => {}),
      lidarrFetch('/metadataprofile').then(d => { setMetadataProfiles(d); if (d[0]) setSelectedMeta(d[0].id) }).catch(() => {}),
    ])
  }, [])

  const search = async () => {
    if (!term.trim()) return
    setLoading(true)
    try {
      const data = await lidarrFetch(`/artist/search?term=${encodeURIComponent(term)}`)
      setResults(Array.isArray(data) ? data : [])
    } catch (e: any) {
      alert(`Search error: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  const addArtist = async (artist: LidarrArtist) => {
    setAddingId(artist.foreignArtistId)
    try {
      await lidarrFetch('/artist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          foreignArtistId: artist.foreignArtistId,
          artistName: artist.artistName,
          qualityProfileId: selectedQuality,
          metadataProfileId: selectedMeta,
          rootFolderPath: selectedRoot,
          monitored: true,
          addOptions: { monitor: 'all', searchForMissingAlbums: true },
        }),
      })
      setAdded(prev => new Set([...prev, artist.foreignArtistId]))
    } catch (e: any) {
      alert(`Add failed: ${e.message}`)
    } finally {
      setAddingId(null)
    }
  }

  const artistImage = (artist: LidarrArtist) =>
    artist.images?.find(i => i.coverType === 'poster')?.url

  return (
    <div className="space-y-4">
      {/* Config strip */}
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Root folder</label>
          <select value={selectedRoot} onChange={e => setSelectedRoot(e.target.value)} className="input w-full text-xs py-1">
            {rootFolders.map(f => <option key={f.id} value={f.path}>{f.path} ({formatBytes(f.freeSpace)} free)</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Quality profile</label>
          <select value={selectedQuality ?? ''} onChange={e => setSelectedQuality(Number(e.target.value))} className="input w-full text-xs py-1">
            {qualityProfiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Metadata profile</label>
          <select value={selectedMeta ?? ''} onChange={e => setSelectedMeta(Number(e.target.value))} className="input w-full text-xs py-1">
            {metadataProfiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search artists…"
            value={term}
            onChange={e => setTerm(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            className="input w-full pl-9 text-sm"
          />
        </div>
        <button
          onClick={search}
          disabled={loading}
          className="btn-primary text-sm py-2 px-4 flex items-center gap-1.5"
        >
          <SearchIcon className="h-4 w-4" />
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-2">
          {results.map(artist => (
            <div key={artist.foreignArtistId} className="card p-3 flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-800 flex-shrink-0">
                {artistImage(artist) ? (
                  <img src={artistImage(artist)} alt={artist.artistName} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-600 text-xs">♪</div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{artist.artistName}</p>
                {artist.overview && (
                  <p className="text-xs text-gray-500 truncate mt-0.5">{artist.overview}</p>
                )}
              </div>
              <button
                onClick={() => addArtist(artist)}
                disabled={addingId === artist.foreignArtistId || added.has(artist.foreignArtistId)}
                className={`flex-shrink-0 btn-secondary text-xs py-1.5 px-3 flex items-center gap-1 ${
                  added.has(artist.foreignArtistId) ? 'text-green-400 border-green-500/30' : ''
                }`}
              >
                {added.has(artist.foreignArtistId) ? (
                  <><CheckCircleIcon className="h-3.5 w-3.5" /> Added</>
                ) : addingId === artist.foreignArtistId ? (
                  'Adding…'
                ) : (
                  <><DownloadIcon className="h-3.5 w-3.5" /> Add</>
                )}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Wanted / Missing panel
// ---------------------------------------------------------------------------

function WantedPanel() {
  const [items, setItems] = useState<LidarrAlbum[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searching, setSearching] = useState<number | null>(null)

  useEffect(() => {
    lidarrFetch('/wanted/missing?pageSize=50')
      .then(d => setItems(d.records ?? d ?? []))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const triggerSearch = async (albumId: number) => {
    setSearching(albumId)
    try {
      await lidarrFetch(`/album/${albumId}/search`, { method: 'POST' })
    } catch (e: any) {
      alert(`Search failed: ${e.message}`)
    } finally {
      setSearching(null)
    }
  }

  if (loading) return <div className="h-24 bg-gray-800/50 rounded-xl animate-pulse" />
  if (error) return <div className="card p-4 text-sm text-red-400">Wanted error: {error}</div>
  if (items.length === 0) return <div className="card p-8 text-center text-sm text-gray-500">No missing albums — library complete!</div>

  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500">{items.length} missing album{items.length !== 1 ? 's' : ''}</p>
      {items.map(album => (
        <div key={album.id} className="card p-3 flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{album.title}</p>
            <p className="text-xs text-gray-400 truncate">
              {album.artist?.artistName} · {album.releaseDate?.slice(0, 4)}
            </p>
          </div>
          <button
            onClick={() => triggerSearch(album.id)}
            disabled={searching === album.id}
            className="flex-shrink-0 btn-secondary text-xs py-1.5 px-3 flex items-center gap-1"
          >
            <SearchIcon className="h-3.5 w-3.5" />
            {searching === album.id ? 'Searching…' : 'Search'}
          </button>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// History panel
// ---------------------------------------------------------------------------

function HistoryPanel() {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    lidarrFetch('/history?pageSize=50')
      .then(d => setItems(d.records ?? d ?? []))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="h-24 bg-gray-800/50 rounded-xl animate-pulse" />
  if (error) return <div className="card p-4 text-sm text-red-400">History error: {error}</div>
  if (items.length === 0) return <div className="card p-8 text-center text-sm text-gray-500">No download history</div>

  const eventColor: Record<string, string> = {
    grabbed: 'text-yellow-400',
    downloadFolderImported: 'text-green-400',
    downloadFailed: 'text-red-400',
    trackFileDeleted: 'text-orange-400',
  }

  return (
    <div className="space-y-1">
      {items.map(item => (
        <div key={item.id} className="card px-3 py-2 flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-xs text-white truncate">{item.sourceTitle}</p>
            <p className="text-xs text-gray-500 truncate">
              {item.artist?.artistName} — {item.album?.title}
            </p>
          </div>
          <div className="flex-shrink-0 text-right">
            <p className={`text-xs ${eventColor[item.eventType] ?? 'text-gray-400'}`}>
              {item.eventType.replace(/([A-Z])/g, ' $1').trim()}
            </p>
            <p className="text-xs text-gray-600">{new Date(item.date).toLocaleDateString()}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
