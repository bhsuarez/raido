// web/src/pages/NowPlayingPage.tsx
import React from 'react'
import { Link } from 'react-router-dom'
import { SkipForwardIcon, MusicIcon } from 'lucide-react'
import { useNowPlaying } from '../hooks/useNowPlaying'
import { useRadioStore } from '../store/radioStore'
import { useArtColor } from '../hooks/useArtColor'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMGQwZDFhIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iNjAiIGZpbGw9IiMxMzEzMjciLz4KPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTUwIiByPSIyMCIgZmlsbD0iIzFhMWEzMiIvPgo8L3N2Zz4K'

function fmt(s: number | null | undefined) {
  if (!s || isNaN(s)) return '0:00'
  const t = Math.floor(s)
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`
}

export default function NowPlayingPage() {
  const { data: nowPlaying, isLoading } = useNowPlaying()
  const { commentaryText, isGeneratingCommentary, selectedStation } = useRadioStore((s) => ({
    commentaryText: s.commentaryText,
    isGeneratingCommentary: s.isGeneratingCommentary,
    selectedStation: s.selectedStation,
  }))

  const track = nowPlaying?.track
  const progress = nowPlaying?.progress
  const total = track?.duration_sec ?? progress?.total_seconds ?? 0
  const [elapsed, setElapsed] = React.useState(progress?.elapsed_seconds ?? 0)
  const [isSkipping, setIsSkipping] = React.useState(false)

  // Drive color extraction from current artwork
  useArtColor(track?.artwork_url ?? null)

  React.useEffect(() => {
    setElapsed(progress?.elapsed_seconds ?? 0)
  }, [progress?.elapsed_seconds, track?.id])

  React.useEffect(() => {
    if (!track || !total) return
    const id = setInterval(() => setElapsed(p => Math.min(p + 1, total)), 1000)
    return () => clearInterval(id)
  }, [track?.id, total])

  async function handleSkip() {
    if (isSkipping) return
    setIsSkipping(true)
    try {
      await apiHelpers.skipTrack(selectedStation)
      toast.success('Skipped')
    } catch {
      toast.error('Failed to skip')
    } finally {
      setTimeout(() => setIsSkipping(false), 2000)
    }
  }

  const pct = total ? Math.min(100, (elapsed / total) * 100) : 0
  const remaining = total ? Math.max(0, total - elapsed) : 0
  const artSrc = track?.artwork_url || FALLBACK_ART

  return (
    <div
      className="relative flex flex-col items-center justify-center"
      style={{ minHeight: 'calc(100vh - 44px)', overflow: 'hidden' }}
    >
      {/* Full-bleed blurred art background */}
      <div
        className="absolute inset-0 -z-10"
        style={{
          backgroundImage: `url(${artSrc})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'blur(60px) saturate(0.6)',
          transform: 'scale(1.15)',
          opacity: 0.35,
          transition: 'background-image 1s ease',
        }}
      />
      {/* Dark vignette over the blurred bg */}
      <div
        className="absolute inset-0 -z-10"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.75) 100%)',
        }}
      />

      {/* Content */}
      <div className="flex flex-col items-center gap-5 px-6 w-full max-w-sm mx-auto">

        {/* Album art — crisp */}
        {isLoading ? (
          <div className="w-64 h-64 rounded-2xl skeleton" />
        ) : (
          <div
            className="relative rounded-2xl overflow-hidden"
            style={{
              width: 'min(280px, 72vw)',
              aspectRatio: '1',
              boxShadow: '0 20px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.06)',
            }}
          >
            <img
              src={artSrc}
              alt={track?.album || track?.title || 'Album art'}
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
            />
            {/* ON AIR badge */}
            {nowPlaying?.is_playing && (
              <div
                className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 rounded-full"
                style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(8px)' }}
              >
                <span className="live-dot glow-live" style={{ width: '6px', height: '6px' }} />
                <span className="font-mono text-white uppercase" style={{ fontSize: '0.55rem', letterSpacing: '0.14em' }}>
                  Live
                </span>
              </div>
            )}
          </div>
        )}

        {/* Track info */}
        {track ? (
          <div className="text-center w-full space-y-1.5">
            {/* Title */}
            <h1
              className="font-display font-bold leading-tight"
              style={{ fontSize: 'clamp(1.3rem, 5vw, 1.75rem)', color: '#f0f0ff' }}
            >
              <Link
                to={`/media/tracks/${track.id}`}
                style={{ color: 'inherit' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--art-accent)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#f0f0ff' }}
              >
                {track.title}
              </Link>
            </h1>

            {/* Artist */}
            <p className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.55)' }}>
              {track.artist}
              {track.genre && <span style={{ color: 'rgba(255,255,255,0.25)' }}> · {track.genre}</span>}
            </p>
          </div>
        ) : !isLoading ? (
          <div className="text-center space-y-2">
            <MusicIcon className="w-10 h-10 mx-auto" style={{ color: '#252545' }} />
            <p className="font-display font-bold text-sm uppercase tracking-widest" style={{ color: '#404060' }}>
              Signal Lost
            </p>
          </div>
        ) : null}

        {/* Progress + controls */}
        {track && (
          <div className="w-full space-y-2">
            {/* EQ bars */}
            {nowPlaying?.is_playing && (
              <div className="flex items-end justify-center gap-0.5" style={{ height: '16px' }}>
                {[0,1,2,3,4,5,6].map(i => (
                  <div
                    key={i}
                    className="audio-bar rounded-sm"
                    style={{ width: '3px', animationDelay: `${i * -0.18}s`, background: 'var(--art-accent)' }}
                  />
                ))}
              </div>
            )}

            {/* Progress bar */}
            <div
              className="relative w-full overflow-hidden rounded-full"
              style={{ height: '2px', background: 'rgba(255,255,255,0.12)' }}
              role="progressbar"
              aria-valuenow={elapsed}
              aria-valuemin={0}
              aria-valuemax={total}
            >
              <div
                className="absolute left-0 top-0 h-full rounded-full progress-fill"
                style={{
                  width: `${pct}%`,
                  background: 'var(--art-accent)',
                  boxShadow: '0 0 8px var(--art-accent)',
                }}
              />
            </div>

            {/* Time codes */}
            <div className="flex justify-between font-mono" style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.65rem' }}>
              <span>{fmt(elapsed)}</span>
              <span>−{fmt(remaining)}</span>
            </div>
          </div>
        )}

        {/* DJ Commentary */}
        {(commentaryText || isGeneratingCommentary) && (
          <div
            className="w-full rounded-xl px-4 py-3 text-center"
            style={{
              background: 'rgba(0,0,0,0.4)',
              backdropFilter: 'blur(8px)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)', fontStyle: 'italic' }}>
              {commentaryText}
              {isGeneratingCommentary && (
                <span
                  className="inline-block w-0.5 h-3.5 ml-0.5 align-middle rounded-sm"
                  style={{ background: 'var(--art-accent)', animation: 'blink 1s step-end infinite' }}
                />
              )}
            </p>
          </div>
        )}

        {/* Skip button */}
        {track && (
          <button
            onClick={handleSkip}
            disabled={isSkipping}
            className="flex items-center gap-2 px-5 py-2 rounded-xl font-mono uppercase text-xs transition-all"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.3)',
              letterSpacing: '0.1em',
              cursor: isSkipping ? 'not-allowed' : 'pointer',
            }}
            onMouseEnter={e => {
              if (!isSkipping) {
                const el = e.currentTarget as HTMLElement
                el.style.borderColor = 'var(--art-accent)'
                el.style.color = 'var(--art-accent)'
              }
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLElement
              el.style.borderColor = 'rgba(255,255,255,0.08)'
              el.style.color = 'rgba(255,255,255,0.3)'
            }}
          >
            {isSkipping ? (
              <span className="w-3 h-3 rounded-full border border-t-transparent border-current animate-spin" />
            ) : (
              <SkipForwardIcon className="w-3.5 h-3.5" />
            )}
            <span>{isSkipping ? 'Skipping' : 'Skip'}</span>
          </button>
        )}
      </div>
    </div>
  )
}
