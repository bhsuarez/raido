import React from 'react'
import { Link } from 'react-router-dom'
import { MusicIcon, MicIcon, SkipForwardIcon } from 'lucide-react'
import { usePlayHistory } from '../hooks/useNowPlaying'
import { formatDistanceToNow } from 'date-fns'

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export default function PlayHistory() {
  const { data: history, isLoading, error } = usePlayHistory()

  if (isLoading) {
    return (
      <div className="card overflow-hidden">
        <div className="px-5 py-3" style={{ borderBottom: '1px solid #0f0f20' }}>
          <span className="section-header">Play History</span>
        </div>
        <div>
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="flex items-center gap-3 px-5 py-3 animate-pulse"
              style={{ borderBottom: '1px solid #0a0a18' }}
            >
              <div className="w-9 h-9 rounded-lg skeleton flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3 skeleton rounded w-2/3" />
                <div className="h-2.5 skeleton rounded w-1/3" />
              </div>
              <div className="h-2.5 skeleton rounded w-12 flex-shrink-0" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error || !history) {
    return (
      <div className="card p-8 flex flex-col items-center gap-2 text-center">
        <MusicIcon className="w-8 h-8" style={{ color: '#1a1a32' }} />
        <p className="text-sm font-display font-bold uppercase tracking-widest" style={{ color: '#303050' }}>
          Unable to load history
        </p>
      </div>
    )
  }

  const tracks = (history.tracks || []).filter((item: any) => {
    const t = item?.track || {}
    const isUnknown = (s?: string) => !s || s.toLowerCase().startsWith('unknown')
    return !(isUnknown(t.title) && isUnknown(t.artist))
  })

  if (tracks.length === 0) {
    return (
      <div className="card p-10 flex flex-col items-center gap-2 text-center">
        <MusicIcon className="w-8 h-8" style={{ color: '#1a1a32' }} />
        <p className="text-sm font-display font-bold uppercase tracking-widest" style={{ color: '#303050' }}>
          No tracks played yet
        </p>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      <div
        className="px-5 py-3 flex items-center justify-between"
        style={{ borderBottom: '1px solid #0f0f20' }}
      >
        <span className="section-header">Play History</span>
        <span className="font-mono" style={{ color: '#252540', fontSize: '0.65rem' }}>
          {tracks.length} tracks
        </span>
      </div>

      <div>
        {tracks.map((item: any, index: number) => (
          <HistoryRow key={`${item.play.id}-${index}`} item={item} isRecent={index < 3} />
        ))}
      </div>
    </div>
  )
}

interface HistoryRowProps {
  item: any
  isRecent: boolean
}

function HistoryRow({ item, isRecent }: HistoryRowProps) {
  const { track, play, commentary } = item
  const [expanded, setExpanded] = React.useState(false)

  const timeAgo = formatDistanceToNow(new Date(play.started_at), { addSuffix: true })

  return (
    <div
      style={{ borderBottom: '1px solid #0a0a18' }}
    >
      <div className="flex items-center gap-3 px-5 py-3">

        {/* Recent accent bar */}
        {isRecent && (
          <div
            className="w-0.5 self-stretch rounded-full flex-shrink-0"
            style={{ background: 'rgba(56, 189, 248, 0.35)', minHeight: '2rem' }}
          />
        )}

        {/* Artwork */}
        <div
          className="w-9 h-9 rounded-lg overflow-hidden flex-shrink-0"
          style={{ background: '#0d0d1a' }}
        >
          {track.artwork_url ? (
            <img src={track.artwork_url} alt={track.title} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <MusicIcon className="w-3.5 h-3.5" style={{ color: '#252545' }} />
            </div>
          )}
        </div>

        {/* Track info */}
        <div className="flex-1 min-w-0">
          <Link
            to={`/media/tracks/${track.id}`}
            className="text-sm font-medium truncate block transition-colors"
            style={{ color: isRecent ? '#a0a0c8' : '#606080' }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#38bdf8' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = isRecent ? '#a0a0c8' : '#606080' }}
          >
            {track.title}
          </Link>
          <p className="text-xs truncate" style={{ color: '#303050', fontSize: '0.7rem' }}>
            {track.artist}
          </p>
        </div>

        {/* Meta: time + skip */}
        <div className="flex-shrink-0 flex flex-col items-end gap-0.5">
          <span className="font-mono" style={{ color: '#252540', fontSize: '0.62rem' }}>
            {timeAgo}
          </span>
          {play.was_skipped && (
            <div className="flex items-center gap-0.5" style={{ color: '#6b3a1a' }}>
              <SkipForwardIcon className="w-2.5 h-2.5" />
              <span className="font-mono" style={{ fontSize: '0.58rem' }}>skipped</span>
            </div>
          )}
        </div>

        {/* Commentary toggle */}
        {commentary && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex-shrink-0 p-1.5 rounded-lg transition-colors"
            style={{
              color: expanded ? '#d946ef' : '#303050',
              background: expanded ? 'rgba(217,70,239,0.1)' : 'transparent',
            }}
            aria-label={expanded ? 'Hide commentary' : 'Show commentary'}
          >
            <MicIcon className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Expanded commentary */}
      {commentary && expanded && (
        <div
          className="mx-5 mb-3 pl-3 py-2 rounded-lg"
          style={{
            background: 'rgba(26, 5, 32, 0.5)',
            borderLeft: '2px solid rgba(217,70,239,0.3)',
          }}
        >
          <p className="text-xs leading-relaxed" style={{ color: '#806090', lineHeight: '1.6' }}>
            {commentary.text}
          </p>
          {commentary.audio_url && (
            <audio controls className="w-full mt-2" style={{ height: '28px' }} preload="metadata">
              <source src={commentary.audio_url} type="audio/mpeg" />
            </audio>
          )}
        </div>
      )}
    </div>
  )
}
