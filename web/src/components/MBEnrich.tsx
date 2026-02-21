/**
 * MusicBrainz Enrichment Review UI
 *
 * Keyboard shortcuts:
 *   A  — approve top candidate
 *   S  — skip track
 *   →  — next track
 *   ←  — previous track
 */
import React, { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Check, X, SkipForward, ChevronLeft, ChevronRight, Search } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

const API = '/api/v1'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Candidate {
  id: number
  track_id: number
  status: string
  score: number | null
  mb_recording_id: string | null
  mb_release_id: string | null
  proposed_title: string | null
  proposed_artist: string | null
  proposed_album: string | null
  proposed_year: number | null
  proposed_genre: string | null
  proposed_label: string | null
  proposed_country: string | null
  proposed_artwork_url: string | null
}

interface TrackWithCandidates {
  id: number
  title: string
  artist: string
  album: string | null
  year: number | null
  genre: string | null
  artwork_url: string | null
  recording_mbid: string | null
  candidates: Candidate[]
}

interface Stats {
  total_tracks: number
  tracks_with_mbid: number
  tracks_pending: number
  tracks_approved: number
  tracks_rejected: number
  tracks_skipped: number
  tracks_unqueued: number
}

// ── API helpers ───────────────────────────────────────────────────────────────

function useAuthFetch() {
  const token = useAuthStore(s => s.token)
  return useCallback(
    (url: string, opts: RequestInit = {}) =>
      fetch(url, {
        ...opts,
        headers: { ...opts.headers, Authorization: `Bearer ${token}` },
      }),
    [token]
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return null
  const color = score >= 90 ? 'text-green-400' : score >= 70 ? 'text-yellow-400' : 'text-red-400'
  return <span className={`text-xs font-mono font-bold ${color}`}>{Math.round(score)}%</span>
}

function ArtworkThumb({ url, alt }: { url: string | null; alt: string }) {
  if (!url) return <div className="w-16 h-16 bg-gray-800 rounded flex items-center justify-center text-gray-600 text-xs">No art</div>
  return <img src={url} alt={alt} className="w-16 h-16 rounded object-cover flex-shrink-0" onError={e => { (e.target as HTMLImageElement).style.display = 'none' }} />
}

function CandidateCard({
  candidate,
  onApprove,
  onReject,
  isTop,
  loading,
}: {
  candidate: Candidate
  onApprove: (id: number) => void
  onReject: (id: number) => void
  isTop: boolean
  loading: boolean
}) {
  return (
    <div className={`flex gap-3 p-3 rounded-lg border ${isTop ? 'border-primary-600 bg-primary-950/30' : 'border-gray-700 bg-gray-800/50'}`}>
      <ArtworkThumb url={candidate.proposed_artwork_url} alt={candidate.proposed_album ?? ''} />
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <ScoreBadge score={candidate.score} />
          {isTop && <span className="text-xs bg-primary-600/30 text-primary-300 px-1.5 py-0.5 rounded">Best match</span>}
        </div>
        <p className="text-sm font-medium text-gray-100 truncate">{candidate.proposed_title}</p>
        <p className="text-xs text-gray-400 truncate">{candidate.proposed_artist}</p>
        {candidate.proposed_album && (
          <p className="text-xs text-gray-500 truncate">{candidate.proposed_album} {candidate.proposed_year ? `(${candidate.proposed_year})` : ''}</p>
        )}
        <div className="flex gap-2 text-xs text-gray-500 flex-wrap">
          {candidate.proposed_genre && <span className="bg-gray-700 px-1.5 py-0.5 rounded">{candidate.proposed_genre}</span>}
          {candidate.proposed_label && <span className="truncate">{candidate.proposed_label}</span>}
          {candidate.proposed_country && <span>{candidate.proposed_country}</span>}
          {candidate.mb_recording_id && (
            <a
              href={`https://musicbrainz.org/recording/${candidate.mb_recording_id}`}
              target="_blank"
              rel="noreferrer"
              className="text-primary-400 hover:underline"
            >MB ↗</a>
          )}
        </div>
      </div>
      <div className="flex flex-col gap-1.5 flex-shrink-0">
        <button
          onClick={() => onApprove(candidate.id)}
          disabled={loading}
          title={isTop ? 'Approve (A)' : 'Approve'}
          className="p-1.5 rounded bg-green-700/40 hover:bg-green-600/60 text-green-300 disabled:opacity-40 transition-colors"
        >
          <Check className="h-4 w-4" />
        </button>
        <button
          onClick={() => onReject(candidate.id)}
          disabled={loading}
          title="Reject"
          className="p-1.5 rounded bg-red-700/40 hover:bg-red-600/60 text-red-300 disabled:opacity-40 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function MBEnrich() {
  const navigate = useNavigate()
  const { isAuthenticated, clearAuth } = useAuthStore()
  const authFetch = useAuthFetch()

  const [stats, setStats] = useState<Stats | null>(null)
  const [tracks, setTracks] = useState<TrackWithCandidates[]>([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const toastTimer = useRef<ReturnType<typeof setTimeout>>()
  const [lookupUrl, setLookupUrl] = useState('')
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupError, setLookupError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) navigate('/login')
  }, [])

  const showToast = (msg: string) => {
    setToast(msg)
    clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 2500)
  }

  const loadStats = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/enrichment/stats`)
      if (res.status === 401) { clearAuth(); navigate('/login'); return }
      setStats(await res.json())
    } catch {}
  }, [authFetch])

  const loadQueue = useCallback(async (pg: number, append = false) => {
    setLoading(true)
    try {
      const res = await authFetch(`${API}/enrichment/queue?page=${pg}&per_page=50&status=pending`)
      if (res.status === 401) { clearAuth(); navigate('/login'); return }
      const data: TrackWithCandidates[] = await res.json()
      setTracks(prev => append ? [...prev, ...data] : data)
      setHasMore(data.length === 50)
      if (!append) setSelectedIdx(0)
    } finally {
      setLoading(false)
    }
  }, [authFetch])

  useEffect(() => { loadStats(); loadQueue(1) }, [])

  // Remove a track from the local list after action
  const removeTrack = (trackId: number) => {
    setTracks(prev => {
      const next = prev.filter(t => t.id !== trackId)
      setSelectedIdx(idx => Math.min(idx, Math.max(0, next.length - 1)))
      return next
    })
    loadStats()
  }

  const handleApprove = async (candidateId: number) => {
    if (actionLoading) return
    setActionLoading(true)
    try {
      const res = await authFetch(`${API}/enrichment/candidate/${candidateId}/approve`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) { showToast(data.detail || 'Error'); return }
      showToast('Approved!')
      removeTrack(data.track_id)
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async (candidateId: number) => {
    if (actionLoading) return
    setActionLoading(true)
    try {
      const res = await authFetch(`${API}/enrichment/candidate/${candidateId}/reject`, { method: 'POST' })
      if (!res.ok) { showToast('Error'); return }
      // Reload track to refresh its candidate list
      const track = tracks.find(t => t.candidates.some(c => c.id === candidateId))
      if (track) {
        const updated = await authFetch(`${API}/enrichment/track/${track.id}`)
        const data: TrackWithCandidates = await updated.json()
        if (data.candidates.filter(c => c.status === 'pending').length === 0) {
          removeTrack(track.id)
        } else {
          setTracks(prev => prev.map(t => t.id === track.id ? data : t))
        }
      }
      showToast('Rejected')
    } finally {
      setActionLoading(false)
    }
  }

  const handleSkip = async (trackId: number) => {
    if (actionLoading) return
    setActionLoading(true)
    try {
      const res = await authFetch(`${API}/enrichment/track/${trackId}/skip`, { method: 'POST' })
      if (!res.ok) { showToast('Error'); return }
      showToast('Skipped')
      removeTrack(trackId)
    } finally {
      setActionLoading(false)
    }
  }

  const handleLookup = async (trackId: number) => {
    if (!lookupUrl.trim() || lookupLoading) return
    setLookupLoading(true)
    setLookupError(null)
    try {
      const res = await authFetch(`${API}/enrichment/track/${trackId}/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mb_url: lookupUrl.trim() }),
      })
      const data = await res.json()
      if (!res.ok) { setLookupError(data.detail || 'Lookup failed'); return }
      // Reload track to show the new candidate at the top
      const updated = await authFetch(`${API}/enrichment/track/${trackId}`)
      const updatedData: TrackWithCandidates = await updated.json()
      setTracks(prev => prev.map(t => t.id === trackId ? updatedData : t))
      setLookupUrl('')
      showToast('Candidate added!')
    } catch {
      setLookupError('Network error')
    } finally {
      setLookupLoading(false)
    }
  }

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT') return
      const current = tracks[selectedIdx]
      if (!current) return
      const topCandidate = current.candidates.find(c => c.status === 'pending')
      if (e.key === 'ArrowRight' || e.key === 'j') setSelectedIdx(i => Math.min(i + 1, tracks.length - 1))
      else if (e.key === 'ArrowLeft' || e.key === 'k') setSelectedIdx(i => Math.max(i - 1, 0))
      else if (e.key === 'a' && topCandidate) handleApprove(topCandidate.id)
      else if (e.key === 's') handleSkip(current.id)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [tracks, selectedIdx, actionLoading])

  // Infinite scroll: load more when near end of list
  useEffect(() => {
    if (selectedIdx >= tracks.length - 5 && hasMore && !loading) {
      const nextPage = page + 1
      setPage(nextPage)
      loadQueue(nextPage, true)
    }
  }, [selectedIdx])

  // Reset lookup state when switching tracks
  const prevSelectedIdx = useRef(selectedIdx)
  useEffect(() => {
    if (prevSelectedIdx.current !== selectedIdx) {
      setLookupUrl('')
      setLookupError(null)
      prevSelectedIdx.current = selectedIdx
    }
  }, [selectedIdx])

  const selectedTrack = tracks[selectedIdx] ?? null
  const pendingCandidates = selectedTrack?.candidates.filter(c => c.status === 'pending') ?? []

  const progress = stats
    ? Math.round(((stats.tracks_approved + stats.tracks_skipped) / Math.max(stats.total_tracks, 1)) * 100)
    : 0

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      {stats && (
        <div className="card p-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Enrichment progress</span>
            <span className="text-gray-300 font-mono">
              {stats.tracks_approved + stats.tracks_skipped} / {stats.total_tracks} reviewed ({progress}%)
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div className="bg-primary-500 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
          <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
            <span><span className="text-green-400 font-medium">{stats.tracks_with_mbid}</span> matched</span>
            <span><span className="text-yellow-400 font-medium">{stats.tracks_pending}</span> pending review</span>
            <span><span className="text-gray-400 font-medium">{stats.tracks_unqueued}</span> not yet searched</span>
            <span><span className="text-gray-500 font-medium">{stats.tracks_skipped}</span> skipped</span>
          </div>
        </div>
      )}

      {/* Main split panel */}
      <div className="flex gap-4 min-h-[500px]">
        {/* Track list (left) */}
        <div className="w-72 flex-shrink-0 card overflow-y-auto max-h-[70vh]">
          {loading && tracks.length === 0 ? (
            <div className="p-4 text-gray-400 text-sm text-center">Loading…</div>
          ) : tracks.length === 0 ? (
            <div className="p-6 text-center space-y-2">
              <p className="text-gray-300 font-medium">Queue empty!</p>
              <p className="text-gray-500 text-sm">All pending candidates have been reviewed, or the enricher hasn't run yet.</p>
            </div>
          ) : (
            <ul>
              {tracks.map((t, idx) => (
                <li
                  key={t.id}
                  onClick={() => setSelectedIdx(idx)}
                  className={`px-3 py-2.5 cursor-pointer border-b border-gray-800 transition-colors ${
                    idx === selectedIdx ? 'bg-primary-900/40 border-l-2 border-l-primary-500' : 'hover:bg-gray-800/50'
                  }`}
                >
                  <p className="text-sm text-gray-100 truncate">{t.title}</p>
                  <p className="text-xs text-gray-500 truncate">{t.artist}</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    {t.candidates.filter(c => c.status === 'pending').map(c => (
                      <ScoreBadge key={c.id} score={c.score} />
                    ))}
                  </div>
                </li>
              ))}
              {hasMore && (
                <li className="px-3 py-2 text-xs text-gray-500 text-center">
                  {loading ? 'Loading more…' : 'Scroll for more'}
                </li>
              )}
            </ul>
          )}
        </div>

        {/* Detail panel (right) */}
        <div className="flex-1 min-w-0">
          {selectedTrack ? (
            <div className="card p-5 space-y-4">
              {/* Track header */}
              <div className="flex gap-4 items-start">
                <ArtworkThumb url={selectedTrack.artwork_url} alt={selectedTrack.album ?? ''} />
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-bold text-gray-100 truncate">{selectedTrack.title}</h2>
                  <p className="text-gray-400 truncate">{selectedTrack.artist}</p>
                  <div className="flex gap-3 text-xs text-gray-500 mt-1 flex-wrap">
                    {selectedTrack.album && <span>{selectedTrack.album}</span>}
                    {selectedTrack.year && <span>{selectedTrack.year}</span>}
                    {selectedTrack.genre && <span className="bg-gray-700 px-1.5 py-0.5 rounded">{selectedTrack.genre}</span>}
                    {selectedTrack.recording_mbid && (
                      <span className="text-green-400">✓ Already matched</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button
                    onClick={() => setSelectedIdx(i => Math.max(i - 1, 0))}
                    disabled={selectedIdx === 0}
                    className="p-1.5 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-30 transition-colors"
                    title="Previous (←)"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setSelectedIdx(i => Math.min(i + 1, tracks.length - 1))}
                    disabled={selectedIdx === tracks.length - 1}
                    className="p-1.5 rounded bg-gray-700 hover:bg-gray-600 disabled:opacity-30 transition-colors"
                    title="Next (→)"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleSkip(selectedTrack.id)}
                    disabled={actionLoading}
                    className="flex items-center gap-1 px-3 py-1.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm disabled:opacity-40 transition-colors"
                    title="Skip track (S)"
                  >
                    <SkipForward className="h-4 w-4" />
                    Skip
                  </button>
                </div>
              </div>

              {/* Manual MB lookup */}
              <div className="space-y-1.5">
                <p className="text-xs text-gray-500 uppercase tracking-wider">Manual lookup</p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={lookupUrl}
                    onChange={e => { setLookupUrl(e.target.value); setLookupError(null) }}
                    onKeyDown={e => e.key === 'Enter' && handleLookup(selectedTrack.id)}
                    placeholder="Paste MusicBrainz release URL or UUID…"
                    className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-primary-500"
                  />
                  <button
                    onClick={() => handleLookup(selectedTrack.id)}
                    disabled={!lookupUrl.trim() || lookupLoading}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-primary-700 hover:bg-primary-600 text-white text-sm disabled:opacity-40 transition-colors flex-shrink-0"
                  >
                    <Search className="h-3.5 w-3.5" />
                    {lookupLoading ? 'Looking up…' : 'Lookup'}
                  </button>
                </div>
                {lookupError && <p className="text-xs text-red-400">{lookupError}</p>}
              </div>

              {/* Candidates */}
              {pendingCandidates.length === 0 ? (
                <p className="text-gray-500 text-sm text-center py-4">No pending candidates.</p>
              ) : (
                <div className="space-y-2">
                  <p className="text-xs text-gray-500 uppercase tracking-wider">
                    {pendingCandidates.length} candidate{pendingCandidates.length !== 1 ? 's' : ''} — sorted by score
                  </p>
                  {pendingCandidates.map((c, i) => (
                    <CandidateCard
                      key={c.id}
                      candidate={c}
                      isTop={i === 0}
                      onApprove={handleApprove}
                      onReject={handleReject}
                      loading={actionLoading}
                    />
                  ))}
                </div>
              )}

              {/* Keyboard hint */}
              <p className="text-xs text-gray-600 pt-1">
                Shortcuts: <kbd className="bg-gray-700 px-1 rounded">A</kbd> approve top &nbsp;
                <kbd className="bg-gray-700 px-1 rounded">S</kbd> skip &nbsp;
                <kbd className="bg-gray-700 px-1 rounded">←</kbd><kbd className="bg-gray-700 px-1 rounded">→</kbd> navigate
              </p>
            </div>
          ) : (
            <div className="card p-8 text-center text-gray-500">
              {loading ? 'Loading…' : 'Select a track from the list'}
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-800 border border-gray-600 text-gray-100 px-4 py-2 rounded-lg shadow-lg text-sm z-50">
          {toast}
        </div>
      )}
    </div>
  )
}
