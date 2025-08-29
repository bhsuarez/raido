import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useNowPlaying } from '../hooks/useNowPlaying'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'
import LoadingSpinner from './LoadingSpinner'

const NowPlaying: React.FC = () => {
  const { data: nowPlaying, isLoading, error } = useNowPlaying()
  const [isSkipping, setIsSkipping] = useState(false)
  
  const handleSkipTrack = async () => {
    if (isSkipping) return
    
    setIsSkipping(true)
    try {
      await apiHelpers.skipTrack()
      toast.success('🎵 Track skipped!')
    } catch (error) {
      console.error('Failed to skip track:', error)
      toast.error('Failed to skip track')
    } finally {
      setTimeout(() => setIsSkipping(false), 2000) // Prevent rapid clicking
    }
  }
  
  // Show loading state
  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-pirate-900 via-pirate-800 to-gray-800 rounded-2xl p-8 shadow-2xl border border-pirate-600/30">
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" message="Loading current track..." />
        </div>
      </div>
    )
  }
  
  // Show error or no data state
  if (error || !nowPlaying?.track) {
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

  const currentTrack = useMemo(() => ({
    title: nowPlaying.track.title,
    artist: nowPlaying.track.artist,
    album: nowPlaying.track.album || 'Unknown Album',
    year: nowPlaying.track.year,
    duration: nowPlaying.track.duration_sec || 0,
    position: nowPlaying.progress?.elapsed_seconds || 0,
    artwork: nowPlaying.track.artwork_url || '',
    genre: nowPlaying.track.genre || 'Unknown'
  }), [nowPlaying])

  const [elapsed, setElapsed] = useState<number>(currentTrack.position)
  const prevTrackId = useRef<number | undefined>(nowPlaying.track.id)

  useEffect(() => {
    if (prevTrackId.current !== nowPlaying.track.id) {
      prevTrackId.current = nowPlaying.track.id
      setElapsed(nowPlaying.progress?.elapsed_seconds || 0)
    } else {
      setElapsed(nowPlaying.progress?.elapsed_seconds || currentTrack.position)
    }
    const interval = setInterval(() => {
      setElapsed((e) => {
        const next = e + 1
        if (currentTrack.duration > 0 && next > currentTrack.duration) return currentTrack.duration
        return next
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [nowPlaying.track.id, nowPlaying.progress?.elapsed_seconds, currentTrack.duration, currentTrack.position])

  const progress = useMemo(() => ({
    percentage: currentTrack.duration > 0 ? (elapsed / currentTrack.duration) * 100 : 0
  }), [elapsed, currentTrack.duration])

  const formatTime = (seconds: number | null | undefined) => {
    if (!seconds || isNaN(seconds)) return '0:00'
    const totalSeconds = Math.floor(seconds)
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-gradient-to-br from-pirate-900 via-pirate-800 to-gray-800 rounded-2xl p-8 shadow-2xl border border-pirate-600/30">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/50"></div>
          <h2 className="text-2xl font-bold text-white">
            🏴‍☠️ Now Playing on Raido
          </h2>
        </div>
        <div className="text-sm text-pirate-300 bg-pirate-800/50 px-3 py-1 rounded-full">
          LIVE STREAM
        </div>
      </div>

      {/* Main Display */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Large Album Art */}
        <div className="lg:col-span-1">
          <div className="relative group">
            <div className="w-full aspect-square rounded-2xl overflow-hidden shadow-2xl border-4 border-pirate-600/30">
              {currentTrack.artwork ? (
                <img
                  src={currentTrack.artwork}
                  alt={`${currentTrack.album} by ${currentTrack.artist}`}
                  className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMzc0MTUxIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iMTAwIiBmaWxsPSIjMjkyODMxIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iNjAiIGZpbGw9IiM0MzQxNGEiLz4KPHJlY3QgeD0iMTQ1IiB5PSI4MCIgd2lkdGg9IjEwIiBoZWlnaHQ9IjE0MCIgZmlsbD0iI0U2RTZFNiIvPgo8L3N2Zz4K'
                  }}
                />
              ) : (
                <div className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-6xl">🎵</div>
              )}
              {/* Vinyl record overlay effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-black/20 rounded-2xl"></div>
            </div>
            
            {/* Album info overlay */}
            <div className="absolute bottom-4 left-4 right-4 bg-black/60 backdrop-blur-sm rounded-lg p-3">
              <div className="text-white text-sm font-medium truncate">
                {currentTrack.album}
              </div>
              <div className="text-gray-300 text-xs">
                {currentTrack.year}
              </div>
            </div>
          </div>
        </div>

        {/* Track Info & Controls */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Track Title & Artist */}
          <div className="space-y-2">
            <h1 className="text-4xl font-bold text-white leading-tight">
              {currentTrack.title}
            </h1>
            <h2 className="text-2xl text-pirate-300 font-semibold">
              by {currentTrack.artist}
            </h2>
            <div className="flex items-center gap-4 text-gray-400">
              <span className="bg-gray-700 px-3 py-1 rounded-full text-sm">
                🎸 {currentTrack.genre}
              </span>
              <span className="text-sm">
                {currentTrack.album} • {currentTrack.year}
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-3">
            <div className="flex justify-between text-sm text-gray-400">
              <span>{formatTime(elapsed)}</span>
              <span>{formatTime(currentTrack.duration)}</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-3 shadow-inner">
              <div
                className="bg-gradient-to-r from-pirate-500 via-pirate-400 to-pirate-300 h-3 rounded-full shadow-lg transition-all duration-1000 relative overflow-hidden"
                style={{ width: `${progress.percentage}%` }}
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
              className={`
                flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm shadow-lg transition-all duration-200
                ${isSkipping 
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed' 
                  : 'bg-gradient-to-r from-pirate-600 to-pirate-500 text-white hover:from-pirate-700 hover:to-pirate-600 hover:scale-105 active:scale-95'
                }
              `}
            >
              {isSkipping ? (
                <>
                  <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                  Skipping...
                </>
              ) : (
                <>
                  ⏭️ Skip Track
                </>
              )}
            </button>
          </div>

          {/* Stream Info */}
          <div className="bg-pirate-800/30 rounded-xl p-6 border border-pirate-600/20">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Stream Connection</h3>
              <div className="flex items-center gap-2 text-green-400">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium">LIVE</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-gray-400 min-w-0 flex-shrink-0">Stream URL:</span>
                <code className="bg-gray-900 text-pirate-300 px-3 py-1 rounded font-mono text-sm flex-1 truncate">
                  http://localhost:8000/stream/raido.mp3
                </code>
              </div>
              <div className="text-sm text-gray-400">
                🎧 <strong>VLC Instructions:</strong> Media → Open Network Stream → Paste URL above
              </div>
            </div>
          </div>

          {/* AI Features */}
          <div className="flex items-center gap-3 flex-wrap">
            <Link 
              to="/tts"
              className="bg-gradient-to-r from-pirate-600 to-pirate-500 hover:from-pirate-700 hover:to-pirate-600 text-white px-4 py-2 rounded-full text-sm font-medium shadow-lg transition-all duration-200 hover:scale-105 cursor-pointer"
            >
              🤖 AI Commentary Active - Monitor
            </Link>
            <span className="bg-gradient-to-r from-purple-600 to-purple-500 text-white px-4 py-2 rounded-full text-sm font-medium shadow-lg">
              🎙️ Kokoro TTS
            </span>
            <span className="bg-gradient-to-r from-blue-600 to-blue-500 text-white px-4 py-2 rounded-full text-sm font-medium shadow-lg">
              📻 24/7 Live
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NowPlaying
