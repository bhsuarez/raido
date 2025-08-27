import React from 'react'
import { ClockIcon, PlayIcon, MicIcon, MusicIcon } from 'lucide-react'
import { usePlayHistory } from '../hooks/useNowPlaying'
import { formatDistanceToNow } from 'date-fns'
import LoadingSpinner from './LoadingSpinner'

export default function PlayHistory() {
  const { data: history, isLoading, error } = usePlayHistory()
  
  // Debug logging
  console.log('PlayHistory debug:', { history, isLoading, error, tracks: history?.tracks?.length })

  if (isLoading) {
    return (
      <div className="card p-6">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
          <ClockIcon className="w-5 h-5" />
          <span>Play History</span>
        </h2>
        <LoadingSpinner />
      </div>
    )
  }

  if (error || !history) {
    return (
      <div className="card p-6">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
          <ClockIcon className="w-5 h-5" />
          <span>Play History</span>
        </h2>
        <div className="text-center text-gray-400 py-8">
          <p>Unable to load play history</p>
        </div>
      </div>
    )
  }

  const tracks = history.tracks || []

  return (
    <div className="card p-6">
      <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
        <ClockIcon className="w-5 h-5" />
        <span>Play History</span>
      </h2>

      {tracks.length === 0 ? (
        <div className="text-center text-gray-400 py-8">
          <MusicIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No tracks played yet</p>
          <p className="text-sm mt-1">Start the radio to see your play history!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tracks.map((item, index) => (
            <HistoryItem 
              key={`${item.play.id}-${index}`} 
              item={item} 
              isRecent={index < 3}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface HistoryItemProps {
  item: any // Could be enhanced with proper TypeScript interfaces
  isRecent: boolean
}

function HistoryItem({ item, isRecent }: HistoryItemProps) {
  const track = item.track
  const play = item.play
  const commentary = item.commentary

  const playedAt = new Date(play.started_at)
  const timeAgo = formatDistanceToNow(playedAt, { addSuffix: true })

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className={`flex items-start space-x-4 p-4 rounded-lg transition-all ${
      isRecent 
        ? 'bg-primary-900 bg-opacity-20 border border-primary-800' 
        : 'bg-gray-800 bg-opacity-50 hover:bg-opacity-80'
    }`}>
      {/* Album Art */}
      <div className="flex-shrink-0">
        <div className="w-12 h-12 bg-gradient-to-br from-pirate-600 to-pirate-800 rounded-md flex items-center justify-center overflow-hidden">
          {track.artwork_url ? (
            <img 
              src={track.artwork_url} 
              alt={`${track.title} artwork`}
              className="w-full h-full object-cover"
            />
          ) : (
            <MusicIcon className="w-6 h-6 text-pirate-300" />
          )}
        </div>
      </div>

      {/* Track Info */}
      <div className="flex-grow min-w-0">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-grow">
            <h3 className="font-semibold text-white truncate">
              {track.title}
            </h3>
            <p className="text-gray-300 text-sm truncate">
              {track.artist}
            </p>
            {track.album && (
              <p className="text-gray-400 text-xs truncate">
                {track.album}
                {track.year && ` • ${track.year}`}
              </p>
            )}
          </div>

          {/* Time and Duration */}
          <div className="flex-shrink-0 text-right ml-4">
            <div className="text-xs text-gray-400 mb-1">
              {timeAgo}
            </div>
            {track.duration_sec && (
              <div className="text-xs text-gray-500">
                {formatDuration(track.duration_sec)}
              </div>
            )}
          </div>
        </div>

        {/* Commentary */}
        {commentary && (
          <div className="mt-3 p-3 bg-gray-900 bg-opacity-50 rounded-md border border-gray-600">
            <div className="flex items-start space-x-2">
              <MicIcon className="w-4 h-4 text-primary-400 mt-0.5 flex-shrink-0" />
              <div className="min-w-0 flex-grow">
                <p className="text-sm text-gray-300">
                  {commentary.text}
                </p>
                {commentary.audio_url && (
                  <div className="mt-2">
                    <audio 
                      controls 
                      className="w-full h-8"
                      preload="metadata"
                    >
                      <source src={commentary.audio_url} type="audio/mpeg" />
                      Your browser does not support audio playback.
                    </audio>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tags */}
        {track.tags && track.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {track.tags.slice(0, 3).map((tag: string, tagIndex: number) => (
              <span 
                key={tagIndex}
                className="inline-block bg-gray-700 text-gray-300 px-2 py-1 rounded text-xs"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Play Status */}
      <div className="flex-shrink-0">
        {play.was_skipped ? (
          <div className="text-orange-400 text-xs">Skipped</div>
        ) : (
          <PlayIcon className="w-4 h-4 text-green-400" />
        )}
      </div>
    </div>
  )
}