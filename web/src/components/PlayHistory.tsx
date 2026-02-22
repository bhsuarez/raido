import React from 'react'
import { Link } from 'react-router-dom'
import { ClockIcon, MusicIcon, MicIcon, SkipForwardIcon } from 'lucide-react'
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
      <div className="card">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center gap-2">
          <ClockIcon className="w-4 h-4 text-gray-500" />
          <span className="section-header">Play History</span>
        </div>
        <div className="divide-y divide-gray-800/60">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex items-center gap-3 px-5 py-3.5 animate-pulse">
              <div className="w-10 h-10 rounded-lg bg-gray-800 flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 bg-gray-800 rounded w-2/3" />
                <div className="h-3 bg-gray-800 rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error || !history) {
    return (
      <div className="card p-8 flex flex-col items-center gap-2 text-center">
        <ClockIcon className="w-8 h-8 text-gray-700" />
        <p className="text-gray-400 font-medium">Unable to load history</p>
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
        <MusicIcon className="w-8 h-8 text-gray-700" />
        <p className="text-gray-400 font-medium">No tracks played yet</p>
        <p className="text-gray-600 text-sm">Start the radio to see your play history</p>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ClockIcon className="w-4 h-4 text-gray-500" />
          <span className="section-header">Play History</span>
        </div>
        <span className="text-xs text-gray-600">{tracks.length} tracks</span>
      </div>

      <div className="divide-y divide-gray-800/60">
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
    <div className={`px-5 py-3.5 ${isRecent ? 'bg-primary-500/5' : ''}`}>
      <div className="flex items-center gap-3">
        {/* Artwork */}
        <div className="w-10 h-10 rounded-lg overflow-hidden bg-gray-800 flex-shrink-0">
          {track.artwork_url ? (
            <img
              src={track.artwork_url}
              alt={track.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <MusicIcon className="w-4 h-4 text-gray-600" />
            </div>
          )}
        </div>

        {/* Track info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <Link to={`/media/tracks/${track.id}`} className="text-sm font-medium text-gray-100 hover:text-primary-400 transition-colors truncate block">{track.title}</Link>
              <p className="text-xs text-gray-400 truncate">{track.artist}</p>
            </div>
            <div className="flex-shrink-0 text-right">
              <p className="text-xs text-gray-600">{timeAgo}</p>
              {play.was_skipped && (
                <div className="flex items-center gap-1 text-xs text-amber-600 mt-0.5 justify-end">
                  <SkipForwardIcon className="w-3 h-3" />
                  <span>Skipped</span>
                </div>
              )}
            </div>
          </div>

          {/* Tags */}
          {track.tags && track.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {track.tags.slice(0, 3).map((tag: string, i: number) => (
                <span key={i} className="text-xs bg-gray-800 text-gray-500 px-1.5 py-0.5 rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Commentary toggle */}
        {commentary && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex-shrink-0 p-1.5 rounded-lg text-primary-400 hover:bg-primary-500/10 transition-colors"
            aria-label={expanded ? 'Hide DJ commentary' : 'Show DJ commentary'}
          >
            <MicIcon className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Commentary expansion */}
      {commentary && expanded && (
        <div className="mt-3 ml-13 pl-3 border-l-2 border-primary-500/30">
          <p className="text-xs text-gray-400 leading-relaxed mb-2">{commentary.text}</p>
          {commentary.audio_url && (
            <audio controls className="w-full h-8" preload="metadata">
              <source src={commentary.audio_url} type="audio/mpeg" />
            </audio>
          )}
        </div>
      )}
    </div>
  )
}
