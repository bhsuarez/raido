import React from 'react'
import { Link } from 'react-router-dom'
import { ListMusicIcon } from 'lucide-react'
import { useNextUp } from '../hooks/useNowPlaying'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iODAiIGhlaWdodD0iODAiIGZpbGw9IiMwZDBkMWEiLz48L3N2Zz4='

function formatTime(seconds: unknown): string {
  const n = typeof seconds === 'number' ? seconds : Number(seconds)
  if (!isFinite(n) || n <= 0) return ''
  return `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, '0')}`
}

const ComingUp: React.FC = () => {
  const { data: nextUpData, isLoading } = useNextUp()

  const hasRealTracks = Array.isArray(nextUpData?.next_tracks) && nextUpData!.next_tracks.length > 0
  const tracks = hasRealTracks
    ? nextUpData!.next_tracks.map((item) => {
        const t = item?.track ?? ({} as any)
        return {
          id: t.id ?? 0,
          title: t.title || 'Unknown',
          artist: t.artist || 'Unknown Artist',
          genre: t.genre || '',
          duration: typeof t.duration_sec === 'number' && isFinite(t.duration_sec) ? t.duration_sec : 0,
          artwork: t.artwork_url || FALLBACK_ART,
        }
      })
    : []

  if (isLoading) {
    return (
      <div className="card p-5">
        <div className="section-header mb-4">Up Next</div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 animate-pulse">
              <div className="w-1 h-10 rounded-full skeleton flex-shrink-0" />
              <div className="w-10 h-10 rounded-lg skeleton flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3 skeleton rounded w-2/3" />
                <div className="h-2.5 skeleton rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (tracks.length === 0) {
    return (
      <div className="card p-8 flex flex-col items-center gap-2 text-center">
        <ListMusicIcon className="w-8 h-8" style={{ color: '#1a1a32' }} />
        <p className="text-sm font-display font-bold uppercase tracking-widest" style={{ color: '#303050' }}>
          No Queue
        </p>
      </div>
    )
  }

  const [featured, ...rest] = tracks

  return (
    <div className="card overflow-hidden">

      {/* ── Section header ─────────────────────────────── */}
      <div
        className="px-5 py-3 flex items-center justify-between"
        style={{ borderBottom: '1px solid #0f0f20' }}
      >
        <span className="section-header">Up Next</span>
        <span className="font-mono text-xs" style={{ color: '#252540', fontSize: '0.65rem' }}>
          {tracks.length} queued
        </span>
      </div>

      {/* ── Featured next track ─────────────────────────── */}
      <div className="flex gap-4 p-5" style={{ borderBottom: '1px solid #0f0f20' }}>
        {/* Accent bar */}
        <div className="w-0.5 rounded-full flex-shrink-0" style={{ background: 'rgba(56,189,248,0.4)' }} />

        {/* Artwork */}
        <div
          className="flex-shrink-0 w-14 h-14 rounded-xl overflow-hidden"
          style={{ background: '#0d0d1a' }}
        >
          <img
            src={featured.artwork}
            alt={featured.title}
            className="w-full h-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
          />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 flex flex-col justify-center gap-1">
          <Link
            to={`/media/tracks/${featured.id}`}
            className="font-display font-bold text-sm leading-tight truncate transition-colors"
            style={{ color: '#ddddf0' }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#38bdf8' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#ddddf0' }}
          >
            {featured.title}
          </Link>
          <p className="text-xs truncate" style={{ color: '#505070' }}>{featured.artist}</p>
          <div className="flex items-center gap-2">
            {featured.genre && (
              <span
                className="text-xs font-mono uppercase"
                style={{
                  fontSize: '0.6rem',
                  letterSpacing: '0.08em',
                  color: '#303058',
                }}
              >
                {featured.genre}
              </span>
            )}
            {featured.duration > 0 && (
              <span className="font-mono text-xs" style={{ color: '#303050', fontSize: '0.65rem' }}>
                {formatTime(featured.duration)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Queue list ─────────────────────────────────── */}
      {rest.length > 0 && (
        <div>
          {rest.map((track, i) => (
            <div
              key={`${track.id}-${i}`}
              className="flex items-center gap-3 px-5 py-2.5"
              style={{ borderBottom: i < rest.length - 1 ? '1px solid #0a0a18' : 'none' }}
            >
              {/* Track number — mono */}
              <span
                className="font-mono flex-shrink-0 text-right"
                style={{ width: '1.2rem', color: '#252540', fontSize: '0.65rem' }}
              >
                {i + 2}
              </span>

              {/* Tiny artwork */}
              <div
                className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0"
                style={{ background: '#0d0d1a' }}
              >
                <img
                  src={track.artwork}
                  alt={track.title}
                  className="w-full h-full object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
                />
              </div>

              {/* Title / artist */}
              <div className="flex-1 min-w-0">
                <Link
                  to={`/media/tracks/${track.id}`}
                  className="text-xs font-medium truncate block transition-colors"
                  style={{ color: '#7070a0' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#38bdf8' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#7070a0' }}
                >
                  {track.title}
                </Link>
                <p className="text-xs truncate" style={{ color: '#303050', fontSize: '0.65rem' }}>
                  {track.artist}
                </p>
              </div>

              {/* Duration */}
              {track.duration > 0 && (
                <span className="font-mono flex-shrink-0" style={{ color: '#252540', fontSize: '0.65rem' }}>
                  {formatTime(track.duration)}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Footer — AI indicator */}
      <div
        className="px-5 py-2.5 flex items-center gap-2"
        style={{ borderTop: '1px solid #0a0a18' }}
      >
        <span className="live-dot" style={{ width: '6px', height: '6px' }} />
        <span className="font-mono uppercase" style={{ color: '#252540', fontSize: '0.58rem', letterSpacing: '0.1em' }}>
          AI commentary active
        </span>
      </div>
    </div>
  )
}

export default ComingUp
