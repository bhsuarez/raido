import React from 'react'
import { Link } from 'react-router-dom'
import { useNowPlaying } from '../hooks/useNowPlaying'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'
import LoadingSpinner from './LoadingSpinner'
import { NowPlayingSkeleton } from './LoadingSkeleton'

const NowPlaying: React.FC = () => {
  const { data: nowPlaying, isLoading, error } = useNowPlaying()

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
      setElapsed(prev => {
        const next = prev + 1
        return next > total ? total : next
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [track?.id, total])

  const remaining = total ? Math.max(0, total - elapsed) : 0

  const handleSkipTrack = async () => {
    if (isSkipping) return
    setIsSkipping(true)
    try {
      await apiHelpers.skipTrack()
      toast.success('🎵 Track skipped!')
    } catch (err) {
      console.error('Failed to skip track:', err)
      toast.error('Failed to skip track')
    } finally {
      setTimeout(() => setIsSkipping(false), 2000)
    }
  }

  // Loading state
  if (isLoading) {
    return <NowPlayingSkeleton />
  }

  // Offline or no data
  if (error || !track) {
    return (
      <div className="bg-gradient-to-br from-pirate-900 via-pirate-800 to-gray-800 rounded-2xl p-8 shadow-2xl border border-pirate-600/30">
        <div className="flex items-center justify-center h-64">
          <div className="text-center text-gray-400">
            <p className="text-xl mb-2">🏴‍☠️ Radio Offline</p>
            <p>No track currently playing</p>
          </div>
        </div>
      </div>
    )
  }

  const formatTime = (seconds: number | null | undefined) => {
    if (!seconds || isNaN(seconds)) return '0:00'
    const totalSeconds = Math.floor(seconds)
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <section 
      className="bg-gradient-to-br from-pirate-900 via-pirate-800 to-gray-800 rounded-2xl p-8 shadow-2xl border border-pirate-600/30"
      aria-label="Now Playing"
      role="main"
    >
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div 
            className="w-3 h-3 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/50"
            aria-label="Live indicator"
            role="status"
          ></div>
          <h1 className="text-2xl font-bold text-white">
            🏴‍☠️ Now Playing on Raido
          </h1>
        </div>
        <div 
          className="text-sm text-pirate-300 bg-pirate-800/50 px-3 py-1 rounded-full"
          aria-label="Stream status"
        >
          LIVE STREAM
        </div>
      </header>

      {/* Main Display */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
        
        {/* Large Album Art */}
        <div className="lg:col-span-1">
          <figure className="relative group">
            <div className="w-full max-w-sm mx-auto lg:max-w-none aspect-square rounded-2xl overflow-hidden shadow-2xl border-4 border-pirate-600/30">
              {track.artwork_url ? (
                <img
                  src={track.artwork_url}
                  alt={`Album artwork for ${track.album} by ${track.artist}`}
                  className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMzc0MTUxIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iMTAwIiBmaWxsPSIjMjkyODMxIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iNjAiIGZpbGw9IiM0MzQxNGEiLz4KPHJlY3QgeD0iMTQ1IiB5PSI4MCIgd2lkdGg9IjEwIiBoZWlnaHQ9IjE0MCIgZmlsbD0iI0U2RTZFNiIvPgo8L3N2Zz4K'
                  }}
                />
              ) : (
                <div 
                  className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-6xl"
                  role="img"
                  aria-label="Default music note icon"
                >🎵</div>
              )}
              {/* Vinyl record overlay effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-black/20 rounded-2xl"></div>
            </div>
            
            {/* Album info overlay */}
            <figcaption className="absolute bottom-4 left-4 right-4 bg-black/60 backdrop-blur-sm rounded-lg p-3">
              <div className="text-white text-sm font-medium truncate">
                {track.album}
              </div>
              <div className="text-gray-300 text-xs">
                {track.year}
              </div>
            </figcaption>
          </figure>
        </div>

        {/* Track Info & Controls */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Track Title & Artist */}
          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-white leading-tight">
              {track.title}
            </h2>
            <h3 className="text-lg sm:text-xl lg:text-2xl text-pirate-300 font-semibold">
              by {track.artist}
            </h3>
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-gray-400">
              <span 
                className="bg-gray-700 px-3 py-1 rounded-full text-sm w-fit"
                aria-label={`Genre: ${track.genre}`}
              >
                🎸 {track.genre}
              </span>
              <span className="text-sm" aria-label={`Album: ${track.album}, Year: ${track.year}`}>
                {track.album} • {track.year}
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-3" role="region" aria-label="Track progress">
            <div className="flex justify-between text-sm text-gray-400">
              <span aria-label={`Elapsed time: ${formatTime(elapsed)}`}>{formatTime(elapsed)}</span>
              <span aria-label={`Remaining time: ${formatTime(remaining)}`}>-{formatTime(remaining)}</span>
            </div>
            <div 
              className="w-full bg-gray-700 rounded-full h-3 shadow-inner"
              role="progressbar"
              aria-valuenow={elapsed}
              aria-valuemin={0}
              aria-valuemax={total}
              aria-label={`Track progress: ${formatTime(elapsed)} of ${formatTime(total)}`}
            >
              <div
                  className="bg-gradient-to-r from-pirate-500 via-pirate-400 to-pirate-300 h-3 rounded-full shadow-lg relative overflow-hidden transition-all duration-1000"
                  style={{ width: `${total ? Math.min(100, (elapsed / total) * 100) : 0}%` }}
              >
                {/* Animated shimmer effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent skew-x-12 animate-pulse"></div>
              </div>
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex justify-center pt-4">
            <button
              onClick={handleSkipTrack}
              disabled={isSkipping}
              aria-label={isSkipping ? 'Skipping track' : 'Skip to next track'}
              className={`
                flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm shadow-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-pirate-400 focus:ring-opacity-50
                ${isSkipping 
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                  : 'bg-gradient-to-r from-pirate-600 to-pirate-500 text-white hover:from-pirate-700 hover:to-pirate-600 hover:scale-105 active:scale-95'
                }
              `}
            >
              {isSkipping ? (
                <>
                  <div 
                    className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"
                    aria-hidden="true"
                  ></div>
                  <span>Skipping...</span>
                </>
              ) : (
                <>
                  <span aria-hidden="true">⏭️</span>
                  <span>Skip Track</span>
                </>
              )}
            </button>
          </div>

        </div>
      </div>
    </section>
  )
}

export default NowPlaying
