import React, { useState, useEffect } from 'react'
import { XIcon, SearchIcon, CheckIcon, MusicIcon, ExternalLinkIcon, MicIcon, RefreshCwIcon } from 'lucide-react'
import { Track, MBCandidate, useMusicBrainzSearch, useUpdateTrack } from '../hooks/useMediaLibrary'
import { apiHelpers } from '../utils/api'

interface VoicingCache {
  status: string
  genre_persona: string | null
  script_text: string | null
  audio_filename: string | null
  input_tokens: number | null
  output_tokens: number | null
  estimated_cost_usd: number | null
  version: number
  updated_at: string | null
}

function useTrackVoicing(trackId: number) {
  const [voicing, setVoicing] = useState<VoicingCache | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchVoicing = async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(apiHelpers.apiUrl(`/api/v1/voicing/tracks/${trackId}`))
      if (r.status === 404) { setVoicing(null); setLoading(false); return }
      if (!r.ok) throw new Error('fetch failed')
      setVoicing(await r.json())
    } catch {
      setError('Failed to load voicing data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchVoicing() }, [trackId])

  const regenerate = async () => {
    try {
      await fetch(apiHelpers.apiUrl(`/api/v1/voicing/tracks/${trackId}/regenerate`), { method: 'POST' })
      await fetchVoicing()
    } catch {
      setError('Regeneration failed')
    }
  }

  return { voicing, loading, error, refetch: fetchVoicing, regenerate }
}

interface Props {
  track: Track
  onClose: () => void
  onTrackUpdated: (track: Track) => void
}

function VoicingStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ready: 'bg-green-500/20 text-green-400 border-green-500/30',
    ready_text_only: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    generating: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    pending: 'bg-gray-700 text-gray-400 border-gray-600',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${map[status] ?? map.pending}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

function formatDuration(sec: number | null): string {
  if (!sec) return '—'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export default function TrackMetadataPanel({ track, onClose, onTrackUpdated }: Props) {
  const [form, setForm] = useState({
    title: track.title ?? '',
    artist: track.artist ?? '',
    album: track.album ?? '',
    year: track.year?.toString() ?? '',
    genre: track.genre ?? '',
  })
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const { voicing, loading: voicingLoading, error: voicingError, regenerate } = useTrackVoicing(track.id)
  const [regenerating, setRegenerating] = useState(false)
  const [manualMbid, setManualMbid] = useState('')
  const [manualLoading, setManualLoading] = useState(false)
  const [manualError, setManualError] = useState('')
  const [manualCandidate, setManualCandidate] = useState<MBCandidate | null>(null)

  const { data: mbCandidates, isFetching: mbLoading, refetch: fetchMB, isError: mbError } =
    useMusicBrainzSearch(track.id)

  const updateTrack = useUpdateTrack()

  const handleSave = async () => {
    setSaveStatus('saving')
    try {
      const updated = await updateTrack.mutateAsync({
        id: track.id,
        data: {
          title: form.title || undefined,
          artist: form.artist || undefined,
          album: form.album || undefined,
          year: form.year ? parseInt(form.year) : undefined,
          genre: form.genre || undefined,
        },
      })
      onTrackUpdated(updated)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }

  const handleApplyCandidate = async (candidate: MBCandidate) => {
    const updated = await updateTrack.mutateAsync({
      id: track.id,
      data: {
        title: candidate.title,
        artist: candidate.artist,
        album: candidate.album ?? undefined,
        year: candidate.year ?? undefined,
        recording_mbid: candidate.recording_mbid,
        release_mbid: candidate.release_mbid ?? undefined,
        artwork_url: candidate.artwork_url ?? undefined,
      },
    })
    onTrackUpdated(updated)
    setForm({
      title: updated.title,
      artist: updated.artist,
      album: updated.album ?? '',
      year: updated.year?.toString() ?? '',
      genre: updated.genre ?? '',
    })
  }

  const handleManualLookup = async () => {
    // Accept full MB URL or bare UUID
    const match = manualMbid.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i)
    if (!match) {
      setManualError('Not a valid MusicBrainz UUID or URL')
      return
    }
    const mbid = match[1]
    setManualLoading(true)
    setManualError('')
    try {
      const res = await apiHelpers.lookupMBRelease(track.id, mbid)
      const candidate: MBCandidate = res.data
      // Prepend to candidates list if we have one, otherwise show inline
      setManualCandidate(candidate)
    } catch (e: any) {
      setManualError(e?.response?.data?.detail || 'Lookup failed')
    } finally {
      setManualLoading(false)
    }
  }

  const resolveArtwork = (url: string | null) => apiHelpers.resolveStaticUrl(url)

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="flex-1 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="w-full max-w-md bg-gray-900 border-l border-gray-800 flex flex-col overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800 sticky top-0 bg-gray-900 z-10">
          <h2 className="font-semibold text-white truncate">{track.title}</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors">
            <XIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 p-5 space-y-6">
          {/* Current artwork */}
          <div className="flex gap-4 items-start">
            <div className="w-20 h-20 rounded-xl overflow-hidden bg-gray-800 flex-shrink-0">
              {track.artwork_url ? (
                <img
                  src={resolveArtwork(track.artwork_url) ?? ''}
                  alt={track.album ?? track.title}
                  className="w-full h-full object-cover"
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <MusicIcon className="h-8 w-8 text-gray-600" />
                </div>
              )}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-white truncate">{track.title}</p>
              <p className="text-xs text-gray-400">{track.artist}</p>
              {track.album && <p className="text-xs text-gray-500">{track.album}</p>}
            </div>
          </div>

          {/* Edit metadata */}
          <section>
            <p className="section-header mb-3">Edit Metadata</p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Title</label>
                <input
                  className="input w-full text-sm"
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Artist</label>
                <input
                  className="input w-full text-sm"
                  value={form.artist}
                  onChange={e => setForm(f => ({ ...f, artist: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Album</label>
                <input
                  className="input w-full text-sm"
                  value={form.album}
                  onChange={e => setForm(f => ({ ...f, album: e.target.value }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Year</label>
                  <input
                    className="input w-full text-sm"
                    value={form.year}
                    onChange={e => setForm(f => ({ ...f, year: e.target.value }))}
                    placeholder="e.g. 2021"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Genre</label>
                  <input
                    className="input w-full text-sm"
                    value={form.genre}
                    onChange={e => setForm(f => ({ ...f, genre: e.target.value }))}
                  />
                </div>
              </div>
              <button
                onClick={handleSave}
                disabled={saveStatus === 'saving'}
                className={`btn-primary w-full flex items-center justify-center gap-2 text-sm ${
                  saveStatus === 'saved' ? 'bg-green-600 hover:bg-green-500' :
                  saveStatus === 'error' ? 'bg-red-600 hover:bg-red-500' : ''
                }`}
              >
                {saveStatus === 'saving' && <span className="spinner w-4 h-4" />}
                {saveStatus === 'saved' && <CheckIcon className="h-4 w-4" />}
                {saveStatus === 'saving' ? 'Saving…' :
                 saveStatus === 'saved' ? 'Saved!' :
                 saveStatus === 'error' ? 'Error saving' : 'Save'}
              </button>
            </div>
          </section>

          {/* MusicBrainz lookup */}
          <section>
            <p className="section-header mb-3">MusicBrainz Lookup</p>
            <button
              onClick={() => fetchMB()}
              disabled={mbLoading}
              className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"
            >
              <SearchIcon className="h-4 w-4" />
              {mbLoading ? 'Searching…' : 'Search MusicBrainz'}
            </button>

            {/* Manual MBID input */}
            <div className="mt-3 flex gap-2">
              <input
                type="text"
                placeholder="Paste MB release URL or UUID…"
                value={manualMbid}
                onChange={e => { setManualMbid(e.target.value); setManualError('') }}
                className="input flex-1 text-xs py-2"
              />
              <button
                onClick={handleManualLookup}
                disabled={manualLoading || !manualMbid.trim()}
                className="btn-secondary text-xs py-2 px-3 flex-shrink-0"
              >
                {manualLoading ? '…' : 'Lookup'}
              </button>
            </div>
            {manualError && <p className="text-xs text-red-400 mt-1">{manualError}</p>}
            {manualCandidate && (
              <div className="mt-2 card-elevated p-3 flex items-start gap-3">
                <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-700 flex-shrink-0">
                  {manualCandidate.artwork_url ? (
                    <img src={manualCandidate.artwork_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <MusicIcon className="h-5 w-5 text-gray-600" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0 text-xs space-y-0.5">
                  <p className="font-medium text-white truncate">{manualCandidate.title}</p>
                  <p className="text-gray-400 truncate">{manualCandidate.artist}</p>
                  {manualCandidate.album && <p className="text-gray-500 truncate">{manualCandidate.album}</p>}
                  <div className="flex gap-2 text-gray-600 flex-wrap">
                    {manualCandidate.year && <span>{manualCandidate.year}</span>}
                    {manualCandidate.country && <span>{manualCandidate.country}</span>}
                    {manualCandidate.label && <span className="truncate">{manualCandidate.label}</span>}
                    {manualCandidate.genre && <span className="text-primary-600">{manualCandidate.genre}</span>}
                  </div>
                </div>
                <div className="flex-shrink-0 flex flex-col items-end gap-1.5">
                  <button
                    onClick={() => { handleApplyCandidate(manualCandidate); setManualCandidate(null); setManualMbid('') }}
                    disabled={updateTrack.isPending}
                    className="btn-primary text-xs py-1.5 px-3"
                  >
                    Apply
                  </button>
                  {manualCandidate.release_mbid && (
                    <a
                      href={`https://musicbrainz.org/release/${manualCandidate.release_mbid}`}
                      target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-0.5 text-xs text-gray-500 hover:text-primary-400 transition-colors"
                      onClick={e => e.stopPropagation()}
                    >
                      <ExternalLinkIcon className="h-3 w-3" />
                      release
                    </a>
                  )}
                </div>
              </div>
            )}

            {mbError && (
              <p className="text-xs text-red-400 mt-2">MusicBrainz search failed. Try again.</p>
            )}

            {mbCandidates && mbCandidates.length === 0 && (
              <p className="text-xs text-gray-500 mt-2">No candidates found.</p>
            )}

            {mbCandidates && mbCandidates.length > 0 && (
              <div className="mt-3 space-y-2">
                {mbCandidates.map(candidate => (
                  <div
                    key={candidate.recording_mbid}
                    className="card-elevated p-3 flex items-start gap-3"
                  >
                    {/* Artwork thumbnail */}
                    <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-700 flex-shrink-0">
                      {candidate.artwork_url ? (
                        <img
                          src={candidate.artwork_url}
                          alt={candidate.album ?? candidate.title}
                          className="w-full h-full object-cover"
                          onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <MusicIcon className="h-5 w-5 text-gray-600" />
                        </div>
                      )}
                    </div>

                    {/* Candidate info */}
                    <div className="flex-1 min-w-0 text-xs space-y-0.5">
                      <p className="font-medium text-white truncate">{candidate.title}</p>
                      <p className="text-gray-400 truncate">{candidate.artist}</p>
                      {candidate.album && (
                        <p className="text-gray-500 truncate">{candidate.album}</p>
                      )}
                      <div className="flex gap-2 text-gray-600 flex-wrap">
                        {candidate.year && <span>{candidate.year}</span>}
                        {candidate.country && <span>{candidate.country}</span>}
                        {candidate.label && <span className="truncate">{candidate.label}</span>}
                        {candidate.genre && <span className="text-primary-600">{candidate.genre}</span>}
                      </div>
                    </div>

                    {/* Links + Apply */}
                    <div className="flex-shrink-0 flex flex-col items-end gap-1.5">
                      <button
                        onClick={() => handleApplyCandidate(candidate)}
                        disabled={updateTrack.isPending}
                        className="btn-primary text-xs py-1.5 px-3"
                      >
                        Apply
                      </button>
                      <div className="flex gap-1.5">
                        {candidate.release_mbid && (
                          <a
                            href={`https://musicbrainz.org/release/${candidate.release_mbid}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-0.5 text-xs text-gray-500 hover:text-primary-400 transition-colors"
                            title="View release on MusicBrainz"
                            onClick={e => e.stopPropagation()}
                          >
                            <ExternalLinkIcon className="h-3 w-3" />
                            release
                          </a>
                        )}
                        <a
                          href={`https://musicbrainz.org/recording/${candidate.recording_mbid}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-0.5 text-xs text-gray-500 hover:text-primary-400 transition-colors"
                          title="View recording on MusicBrainz"
                          onClick={e => e.stopPropagation()}
                        >
                          <ExternalLinkIcon className="h-3 w-3" />
                          rec
                        </a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Voice of Raido */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <p className="section-header flex items-center gap-1.5">
                <MicIcon className="h-3.5 w-3.5" />
                Voice of Raido
              </p>
              <button
                onClick={async () => { setRegenerating(true); await regenerate(); setRegenerating(false) }}
                disabled={regenerating}
                className="btn-secondary text-xs py-1 px-2 flex items-center gap-1"
                title="Queue regeneration of DJ script and audio"
              >
                <RefreshCwIcon className={`h-3 w-3 ${regenerating ? 'animate-spin' : ''}`} />
                Regenerate
              </button>
            </div>
            {voicingLoading && (
              <div className="h-16 bg-gray-800/50 rounded-xl animate-pulse" />
            )}
            {voicingError && (
              <p className="text-xs text-red-400">{voicingError}</p>
            )}
            {!voicingLoading && !voicingError && !voicing && (
              <div className="card p-3 text-xs text-gray-500 text-center">
                Not yet voiced — start the Voicing Engine from the Media page.
              </div>
            )}
            {!voicingLoading && voicing && (
              <div className="card p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Status</span>
                  <VoicingStatusBadge status={voicing.status} />
                </div>
                {voicing.genre_persona && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">Persona</span>
                    <span className="text-xs text-gray-300">{voicing.genre_persona}</span>
                  </div>
                )}
                {voicing.script_text && (
                  <div className="mt-1">
                    <p className="text-xs text-gray-500 mb-1">Cached Script</p>
                    <p className="text-xs text-gray-300 bg-gray-800 rounded-lg p-2 leading-relaxed">
                      {voicing.script_text}
                    </p>
                  </div>
                )}
                {voicing.audio_filename && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">Audio</span>
                    <span className="text-xs text-green-400">Cached</span>
                  </div>
                )}
                {voicing.estimated_cost_usd !== null && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">Cost</span>
                    <span className="text-xs text-gray-500">${voicing.estimated_cost_usd?.toFixed(5)}</span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">Version</span>
                  <span className="text-xs text-gray-600">v{voicing.version}</span>
                </div>
              </div>
            )}
          </section>

          {/* File info */}
          <section>
            <p className="section-header mb-3">File Info</p>
            <div className="card p-3 space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">File</span>
                <span className="text-gray-300 break-all text-right font-mono">
{track.file_path}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Duration</span>
                <span className="text-gray-300">{formatDuration(track.duration_sec)}</span>
              </div>
              {track.bitrate && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Bitrate</span>
                  <span className="text-gray-300">{track.bitrate} kbps</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500">Play count</span>
                <span className="text-gray-300">{track.play_count}</span>
              </div>
              {track.last_played_at && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Last played</span>
                  <span className="text-gray-300">
                    {new Date(track.last_played_at).toLocaleDateString()}
                  </span>
                </div>
              )}
              {track.recording_mbid && (
                <div className="flex justify-between">
                  <span className="text-gray-500">MBID</span>
                  <span className="text-gray-500 font-mono truncate max-w-[60%]">
                    {track.recording_mbid.slice(0, 8)}…
                  </span>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
