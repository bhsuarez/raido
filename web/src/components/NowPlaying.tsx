import React from 'react'
import { Link } from 'react-router-dom'
import { SkipForwardIcon, MusicIcon } from 'lucide-react'
import { useNowPlaying } from '../hooks/useNowPlaying'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'
import { useRadioStore } from '../store/radioStore'
import { NowPlayingSkeleton } from './LoadingSkeleton'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMGQwZDFhIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iNjAiIGZpbGw9IiMxMzEzMjciLz4KPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTUwIiByPSIyMCIgZmlsbD0iIzFhMWEzMiIvPgo8L3N2Zz4K'

function formatTime(seconds: number | null | undefined): string {
  if (!seconds || isNaN(seconds)) return '0:00'
  const total = Math.floor(seconds)
  const mins = Math.floor(total / 60)
  const secs = total % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const NowPlaying: React.FC = () => {
  const { data: nowPlaying, isLoading, error } = useNowPlaying()
  const selectedStation = useRadioStore((s) => s.selectedStation)
  const track = nowPlaying?.track
  const progress = nowPlaying?.progress
  const total = track?.duration_sec ?? progress?.total_seconds ?? 0
  const [elapsed, setElapsed] = React.useState(progress?.elapsed_seconds ?? 0)
  const [isSkipping, setIsSkipping] = React.useState(false)

  React.useEffect(() => {
    setElapsed(progress?.elapsed_seconds ?? 0)
  }, [progress?.elapsed_seconds, track?.id])

  React.useEffect(() => {
    if (!track || !total) return
    const interval = setInterval(() => {
      setElapsed(prev => Math.min(prev + 1, total))
    }, 1000)
    return () => clearInterval(interval)
  }, [track?.id, total])

  const handleSkip = async () => {
    if (isSkipping) return
    setIsSkipping(true)
    try {
      await apiHelpers.skipTrack(selectedStation)
      toast.success('Track skipped')
    } catch {
      toast.error('Failed to skip track')
    } finally {
      setTimeout(() => setIsSkipping(false), 2000)
    }
  }

  if (isLoading) return <NowPlayingSkeleton />

  if (error || !track) {
    return (
      <section
        className="card p-10 flex flex-col items-center justify-center gap-3 text-center min-h-[200px]"
        aria-label="Now Playing"
      >
        <MusicIcon className="w-10 h-10" style={{ color: '#252545' }} />
        <p className="font-display font-bold text-sm uppercase tracking-widest" style={{ color: '#404060' }}>
          Signal Lost
        </p>
        <p className="text-xs font-mono" style={{ color: '#303050' }}>No track currently broadcasting</p>
      </section>
    )
  }

  const pct = total ? Math.min(100, (elapsed / total) * 100) : 0
  const remaining = total ? Math.max(0, total - elapsed) : 0

  return (
    <section
      className="card overflow-hidden"
      aria-label="Now Playing"
      style={{ boxShadow: '0 0 0 1px #1a1a32, 0 20px 60px rgba(0,0,0,0.6)' }}
    >
      <div className="flex flex-col lg:flex-row">

        {/* ── Album Artwork ─────────────────────────────────── */}
        <div className="lg:w-72 lg:flex-shrink-0 relative">
          <div
            className="aspect-square lg:h-72 lg:w-72 overflow-hidden relative"
            style={{ background: '#0d0d1a' }}
          >
            <img
              src={track.artwork_url || FALLBACK_ART}
              alt={`${track.album || track.title} artwork`}
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
              style={{ display: 'block' }}
            />

            {/* Glow overlay — subtle blue light from below */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: 'linear-gradient(to top, rgba(14,165,233,0.12) 0%, transparent 50%)',
              }}
            />

            {/* ON AIR badge */}
            <div
              className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full"
              style={{ background: 'rgba(7, 7, 15, 0.75)', backdropFilter: 'blur(8px)' }}
            >
              <span className="live-dot glow-live" />
              <span
                className="text-xs font-display font-bold uppercase"
                style={{ color: '#4ade80', letterSpacing: '0.12em', fontSize: '0.6rem' }}
              >
                ON AIR
              </span>
            </div>
          </div>

          {/* Artwork glow halo — positioned below the artwork */}
          <div
            className="absolute inset-0 pointer-events-none -z-10 rounded-2xl"
            style={{ boxShadow: '0 0 60px rgba(14,165,233,0.15), 0 0 120px rgba(14,165,233,0.05)' }}
          />
        </div>

        {/* ── Track Info & Controls ─────────────────────────── */}
        <div className="flex-1 flex flex-col justify-between p-5 lg:p-7 gap-6">

          {/* Track metadata */}
          <div className="space-y-2">
            {/* Genre badge */}
            {track.genre && (
              <div
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono uppercase"
                style={{
                  background: 'rgba(14, 165, 233, 0.08)',
                  border: '1px solid rgba(14, 165, 233, 0.2)',
                  color: '#0ea5e9',
                  letterSpacing: '0.1em',
                  fontSize: '0.6rem',
                }}
              >
                {track.genre}
              </div>
            )}

            {/* Title — Syne display font, dramatic */}
            <h2 className="font-display font-bold leading-tight" style={{ fontSize: 'clamp(1.4rem, 4vw, 2rem)', color: '#f0f0ff' }}>
              <Link
                to={`/media/tracks/${track.id}`}
                className="transition-colors duration-150 hover:text-primary-400"
                style={{ color: '#f0f0ff' }}
              >
                {track.title}
              </Link>
            </h2>

            {/* Artist */}
            <p className="text-base font-medium" style={{ color: '#8080a8' }}>
              {track.artist}
            </p>

            {/* Album · Year */}
            {(track.album || track.year) && (
              <p className="text-xs font-mono" style={{ color: '#383858', letterSpacing: '0.04em' }}>
                {[track.album, track.year].filter(Boolean).join('  ·  ')}
              </p>
            )}
          </div>

          {/* Progress + EQ section */}
          <div className="space-y-3">
            {/* EQ bars (live animation) */}
            {nowPlaying?.is_playing && (
              <div className="flex items-end gap-0.5 h-4">
                {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                  <div
                    key={i}
                    className="audio-bar flex-1 rounded-sm"
                    style={{ animationDelay: `${i * -0.18}s`, minHeight: '20%' }}
                  />
                ))}
              </div>
            )}

            {/* Progress bar — thin, glowing */}
            <div
              className="relative w-full overflow-hidden rounded-full"
              style={{ height: '2px', background: '#1a1a32' }}
              role="progressbar"
              aria-valuenow={elapsed}
              aria-valuemin={0}
              aria-valuemax={total}
            >
              <div
                className="absolute left-0 top-0 h-full rounded-full progress-fill"
                style={{
                  width: `${pct}%`,
                  background: 'linear-gradient(90deg, #0284c7, #38bdf8)',
                  boxShadow: '0 0 8px rgba(56, 189, 248, 0.9), 0 0 16px rgba(56, 189, 248, 0.4)',
                }}
              />
            </div>

            {/* Time codes — monospace */}
            <div className="flex justify-between font-mono text-xs" style={{ color: '#303050', fontSize: '0.7rem' }}>
              <span>{formatTime(elapsed)}</span>
              <span>−{formatTime(remaining)}</span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSkip}
              disabled={isSkipping}
              aria-label={isSkipping ? 'Skipping...' : 'Skip to next track'}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono uppercase transition-all duration-200"
              style={{
                background: isSkipping ? 'rgba(13,13,26,0.5)' : 'rgba(19, 19, 39, 0.9)',
                border: '1px solid #1a1a32',
                color: isSkipping ? '#303050' : '#606080',
                letterSpacing: '0.1em',
                cursor: isSkipping ? 'not-allowed' : 'pointer',
              }}
              onMouseEnter={e => {
                if (!isSkipping) {
                  const el = e.currentTarget as HTMLElement
                  el.style.borderColor = 'rgba(56,189,248,0.3)'
                  el.style.color = '#38bdf8'
                  el.style.boxShadow = '0 0 12px rgba(56,189,248,0.15)'
                }
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.borderColor = '#1a1a32'
                el.style.color = '#606080'
                el.style.boxShadow = 'none'
              }}
            >
              {isSkipping ? (
                <>
                  <span className="w-3.5 h-3.5 rounded-full border border-t-transparent border-current animate-spin" />
                  <span>Skipping</span>
                </>
              ) : (
                <>
                  <SkipForwardIcon className="w-3.5 h-3.5" />
                  <span>Skip</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        className="px-5 py-2 flex justify-end"
        style={{ borderTop: '1px solid #0f0f20' }}
      >
        <Link
          to="/analytics"
          className="text-xs font-mono uppercase transition-colors"
          style={{ color: '#252540', letterSpacing: '0.1em', fontSize: '0.6rem' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#38bdf8' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#252540' }}
        >
          Analytics →
        </Link>
      </div>
    </section>
  )
}

export default NowPlaying
