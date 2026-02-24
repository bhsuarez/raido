import React, { useState, useCallback, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { SearchIcon, FilterIcon, MicIcon } from 'lucide-react'
import { useTracks, useTrackFacets, useTrack, Track, TrackFilters, TracksResult } from '../hooks/useMediaLibrary'
import TrackMetadataPanel from './TrackMetadataPanel'
import VoicingProgress from './VoicingProgress'
import StationVoicePanel from './StationVoicePanel'
import { apiHelpers } from '../utils/api'

// Status badge colours for voicing
const VOICING_BADGE: Record<string, string> = {
  ready: 'text-green-400',
  ready_text_only: 'text-blue-400',
  generating: 'text-yellow-400',
  failed: 'text-red-500',
  pending: 'text-gray-600',
}

async function fetchVoicingStatuses(ids: number[]): Promise<Record<string, string | null>> {
  if (!ids.length) return {}
  try {
    const r = await fetch(apiHelpers.apiUrl(`/api/v1/voicing/tracks/status?ids=${ids.join(',')}`))
    if (!r.ok) return {}
    return r.json()
  } catch {
    return {}
  }
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = React.useState(value)
  React.useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

function formatDuration(sec: number | null): string {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function MediaLibrary() {
  const { trackId: trackIdParam } = useParams<{ trackId?: string }>()
  const navigate = useNavigate()
  const parsedTrackId = trackIdParam ? parseInt(trackIdParam, 10) : null

  const [search, setSearch] = useState('')
  const [selectedGenre, setSelectedGenre] = useState<string>('')
  const [selectedArtist, setSelectedArtist] = useState<string>('')
  const [selectedStation, setSelectedStation] = useState<string>('')
  const [sort, setSort] = useState<TrackFilters['sort']>('artist')
  const [page, setPage] = useState(1)
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null)
  const [noArtwork, setNoArtwork] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [voicingStatuses, setVoicingStatuses] = useState<Record<string, string | null>>({})
  const [showVoicingEngine, setShowVoicingEngine] = useState(false)

  // Fetch track by ID when navigating via permalink
  const { data: trackFromParam } = useTrack(parsedTrackId)

  // When URL has no track param, clear the panel
  useEffect(() => {
    if (parsedTrackId === null) {
      setSelectedTrack(null)
    }
  }, [parsedTrackId])

  // When track data loads from permalink, open the panel
  useEffect(() => {
    if (trackFromParam) {
      setSelectedTrack(trackFromParam)
    }
  }, [trackFromParam])

  const debouncedSearch = useDebounce(search, 300)

  const filters: TrackFilters = {
    search: debouncedSearch || undefined,
    genre: selectedGenre || undefined,
    artist: selectedArtist || undefined,
    station: selectedStation || undefined,
    sort,
    page,
    per_page: 100,
    no_artwork: noArtwork || undefined,
  }

  const { data: tracksResult, isLoading, isError } = useTracks(filters)
  const tracks = tracksResult?.tracks
  const total = tracksResult?.total ?? 0
  const { data: facets } = useTrackFacets()

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value)
    setPage(1)
  }, [])

  const handleGenreChange = useCallback((genre: string) => {
    setSelectedGenre(prev => prev === genre ? '' : genre)
    setPage(1)
  }, [])

  const handleArtistChange = useCallback((artist: string) => {
    setSelectedArtist(prev => prev === artist ? '' : artist)
    setPage(1)
  }, [])

  const handleStationChange = useCallback((station: string) => {
    setSelectedStation(prev => prev === station ? '' : station)
    setPage(1)
  }, [])

  const resolveArtwork = (url: string | null) => apiHelpers.resolveStaticUrl(url)

  // Fetch voicing statuses whenever the track list changes
  useEffect(() => {
    if (tracks && tracks.length > 0) {
      fetchVoicingStatuses(tracks.map(t => t.id)).then(setVoicingStatuses)
    }
  }, [tracks])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Media Library</h1>
        <div className="flex items-center gap-2">
          <button
            className={`btn-secondary flex items-center gap-1.5 text-sm py-2 px-3 ${showVoicingEngine ? 'border-primary-500/40 text-primary-400' : ''}`}
            onClick={() => setShowVoicingEngine(v => !v)}
            title="Voice of Raido Engine"
          >
            <MicIcon className="h-4 w-4" />
            <span className="hidden sm:inline">Voice Engine</span>
          </button>
          <button
            className="md:hidden btn-secondary flex items-center gap-2 text-sm py-2 px-3"
            onClick={() => setShowFilters(f => !f)}
          >
            <FilterIcon className="h-4 w-4" />
            Filters
          </button>
        </div>
      </div>

      {/* Voicing Engine panel */}
      {showVoicingEngine && <VoicingProgress />}

      <div className="flex gap-4 items-start">
        {/* Sidebar */}
        <aside className={`w-56 flex-shrink-0 space-y-4 ${showFilters ? 'block' : 'hidden'} md:block`}>
          {/* Search */}
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search tracks…"
              value={search}
              onChange={handleSearchChange}
              className="input w-full pl-9 text-sm"
            />
          </div>

          {/* Sort */}
          <div>
            <p className="section-header mb-2">Sort</p>
            <select
              value={sort}
              onChange={e => { setSort(e.target.value as TrackFilters['sort']); setPage(1) }}
              className="input w-full text-sm"
            >
              <option value="artist">Artist</option>
              <option value="album">Album</option>
              <option value="title">Title</option>
              <option value="play_count">Most Played</option>
            </select>
          </div>

          {/* No artwork filter */}
          <button
            onClick={() => { setNoArtwork(f => !f); setPage(1) }}
            className={`w-full text-left text-sm px-3 py-2 rounded-xl border transition-colors flex items-center gap-2 ${
              noArtwork
                ? 'bg-primary-500/20 border-primary-500/40 text-primary-400'
                : 'border-gray-700 text-gray-400 hover:text-gray-100 hover:bg-gray-800'
            }`}
          >
            <span className="text-base leading-none">🖼</span>
            Missing artwork
          </button>

          {/* Genre filter */}
          {facets && facets.genres.length > 0 && (
            <div>
              <p className="section-header mb-2">Genre</p>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {facets.genres.map(genre => (
                  <button
                    key={genre}
                    onClick={() => handleGenreChange(genre)}
                    className={`w-full text-left text-sm px-2 py-1 rounded-lg transition-colors ${
                      selectedGenre === genre
                        ? 'bg-primary-500/20 text-primary-400'
                        : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
                    }`}
                  >
                    {genre}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Artist filter */}
          {facets && facets.artists.length > 0 && (
            <div>
              <p className="section-header mb-2">Artist</p>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {facets.artists.map(artist => (
                  <button
                    key={artist}
                    onClick={() => handleArtistChange(artist)}
                    className={`w-full text-left text-sm px-2 py-1 rounded-lg truncate transition-colors ${
                      selectedArtist === artist
                        ? 'bg-primary-500/20 text-primary-400'
                        : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
                    }`}
                    title={artist}
                  >
                    {artist}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Station filter */}
          {facets && facets.stations.length > 0 && (
            <div>
              <p className="section-header mb-2">Station</p>
              <div className="space-y-1">
                {facets.stations.map(s => (
                  <button
                    key={s.identifier}
                    onClick={() => handleStationChange(s.identifier)}
                    className={`w-full text-left text-sm px-2 py-1 rounded-lg truncate transition-colors ${
                      selectedStation === s.identifier
                        ? 'bg-primary-500/20 text-primary-400'
                        : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
                    }`}
                    title={s.name}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Clear filters */}
          {(selectedGenre || selectedArtist || selectedStation || search || noArtwork) && (
            <button
              className="btn-secondary w-full text-sm py-2"
              onClick={() => {
                setSearch('')
                setSelectedGenre('')
                setSelectedArtist('')
                setSelectedStation('')
                setNoArtwork(false)
                setPage(1)
              }}
            >
              Clear filters
            </button>
          )}
        </aside>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Station DJ voice panel */}
          {selectedStation && facets && (() => {
            const s = facets.stations.find(st => st.identifier === selectedStation)
            return s ? <StationVoicePanel stationIdentifier={s.identifier} stationName={s.name} /> : null
          })()}

          {/* Track count */}
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-gray-400">
              {isLoading ? 'Loading…' : (
                <>
                  <span className="font-medium text-white">{total.toLocaleString()}</span>
                  <span> tracks</span>
                  {(tracks?.length ?? 0) < total && (
                    <span className="text-gray-500"> &middot; page {page}</span>
                  )}
                </>
              )}
            </p>
            {/* Pagination */}
            <div className="flex items-center gap-2">
              <button
                className="btn-secondary text-xs py-1.5 px-3"
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                ← Prev
              </button>
              <span className="text-xs text-gray-500">Page {page}</span>
              <button
                className="btn-secondary text-xs py-1.5 px-3"
                disabled={!tracks || (page * 100) >= total}
                onClick={() => setPage(p => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>

          {/* Track list */}
          {isError && (
            <div className="card p-6 text-red-400 text-sm">Failed to load tracks.</div>
          )}

          {isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="h-14 bg-gray-800/50 rounded-xl animate-pulse" />
              ))}
            </div>
          )}

          {!isLoading && tracks && (
            <div className="space-y-1">
              {tracks.length === 0 && (
                <div className="card p-8 text-center text-gray-500 text-sm">
                  No tracks match your filters.
                </div>
              )}
              {tracks.map(track => (
                <button
                  key={track.id}
                  onClick={() => { setSelectedTrack(track); navigate(`/media/tracks/${track.id}`) }}
                  className="w-full card hover:bg-gray-800 transition-colors p-3 flex items-center gap-3 text-left"
                >
                  {/* Artwork */}
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg overflow-hidden bg-gray-800">
                    {track.artwork_url ? (
                      <img
                        src={resolveArtwork(track.artwork_url) ?? ''}
                        alt={track.album ?? track.title}
                        className="w-full h-full object-cover"
                        loading="lazy"
                        onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                      />
                    ) : (
                      <div className="w-full h-full bg-gray-700 flex items-center justify-center">
                        <span className="text-gray-500 text-xs">♪</span>
                      </div>
                    )}
                  </div>

                  {/* Track info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{track.title}</p>
                    <p className="text-xs text-gray-400 truncate">
                      {track.artist}
                      {track.album && <span className="text-gray-500"> · {track.album}</span>}
                      {track.year && <span className="text-gray-600"> · {track.year}</span>}
                    </p>
                  </div>

                  {/* Voicing status mic icon */}
                  {voicingStatuses[String(track.id)] !== undefined && (
                    <MicIcon
                      className={`hidden sm:block flex-shrink-0 h-3.5 w-3.5 ${VOICING_BADGE[voicingStatuses[String(track.id)] ?? 'pending'] ?? 'text-gray-600'}`}
                      title={`Voice: ${voicingStatuses[String(track.id)] ?? 'pending'}`}
                    />
                  )}

                  {/* Genre badge */}
                  {track.genre && (
                    <span className="hidden sm:inline-block flex-shrink-0 text-xs bg-gray-800 border border-gray-700 text-gray-400 px-2 py-0.5 rounded-full">
                      {track.genre}
                    </span>
                  )}

                  {/* Duration + play count */}
                  <div className="flex-shrink-0 text-right hidden sm:block">
                    {track.duration_sec && (
                      <p className="text-xs text-gray-500">{formatDuration(track.duration_sec)}</p>
                    )}
                    <p className="text-xs text-gray-600">{track.play_count} plays</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Track metadata panel */}
      {selectedTrack && (
        <TrackMetadataPanel
          track={selectedTrack}
          onClose={() => { setSelectedTrack(null); navigate('/media') }}
          onTrackUpdated={(updated) => setSelectedTrack(updated)}
        />
      )}
    </div>
  )
}
