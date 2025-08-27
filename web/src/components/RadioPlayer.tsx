import React, { useState, useRef, useEffect } from 'react'
import { 
  PlayIcon, 
  PauseIcon, 
  VolumeXIcon, 
  Volume2Icon, 
  RadioIcon,
  MusicIcon
} from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import type { NowPlaying } from '../store/radioStore'

interface RadioPlayerProps {
  nowPlaying?: NowPlaying
}

export default function RadioPlayer({ nowPlaying }: RadioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)
  
  const { volume, setVolume, isMuted, toggleMute } = useRadioStore()

  const streamUrl = '/stream/raido.mp3'

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume / 100
    }
  }, [volume, isMuted])

  const handlePlayPause = async () => {
    if (!audioRef.current) return

    try {
      setIsLoading(true)
      
      if (isPlaying) {
        audioRef.current.pause()
        setIsPlaying(false)
      } else {
        await audioRef.current.play()
        setIsPlaying(true)
      }
    } catch (error) {
      console.error('Audio playback error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseInt(e.target.value)
    setVolume(newVolume)
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const track = nowPlaying?.track
  const progress = nowPlaying?.progress

  return (
    <div className="card p-6">
      {/* Audio element */}
      <audio
        ref={audioRef}
        src={streamUrl}
        onLoadStart={() => setIsLoading(true)}
        onCanPlay={() => setIsLoading(false)}
        onError={(e) => {
          console.error('Audio error:', e)
          setIsLoading(false)
          setIsPlaying(false)
        }}
        preload="none"
      />

      <div className="flex items-start space-x-6">
        {/* Album Art */}
        <div className="flex-shrink-0">
          <div className="w-32 h-32 bg-gradient-to-br from-pirate-600 to-pirate-800 rounded-lg shadow-lg flex items-center justify-center overflow-hidden">
            {track?.artwork_url ? (
              <img 
                src={track.artwork_url} 
                alt={`${track.title} artwork`}
                className="w-full h-full object-cover"
              />
            ) : (
              <MusicIcon className="w-12 h-12 text-pirate-300" />
            )}
          </div>
        </div>

        {/* Track Info and Controls */}
        <div className="flex-grow min-w-0">
          {/* Track Information */}
          <div className="mb-4">
            {track ? (
              <>
                <h2 className="text-2xl font-bold text-white mb-1 truncate">
                  {track.title}
                </h2>
                <p className="text-lg text-gray-300 mb-1 truncate">
                  {track.artist}
                </p>
                {track.album && (
                  <p className="text-sm text-gray-400 truncate">
                    {track.album}
                    {track.year && ` (${track.year})`}
                  </p>
                )}
                {track.genre && (
                  <span className="inline-block bg-primary-900 text-primary-200 px-2 py-1 rounded text-xs mt-2">
                    {track.genre}
                  </span>
                )}
              </>
            ) : (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-700 rounded mb-2"></div>
                <div className="h-6 bg-gray-700 rounded mb-2 w-3/4"></div>
                <div className="h-4 bg-gray-700 rounded w-1/2"></div>
              </div>
            )}
          </div>

          {/* Progress Bar */}
          {progress && (
            <div className="mb-4">
              <div className="flex items-center justify-between text-sm text-gray-400 mb-1">
                <span>{formatTime(progress.elapsed_seconds)}</span>
                <span>{formatTime(progress.total_seconds)}</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-primary-500 to-primary-400 h-2 rounded-full transition-all duration-1000"
                  style={{ width: `${progress.percentage}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Controls */}
          <div className="flex items-center space-x-4">
            {/* Play/Pause */}
            <button
              onClick={handlePlayPause}
              disabled={isLoading}
              className="btn-primary flex items-center space-x-2 px-6 py-3 text-lg"
            >
              {isLoading ? (
                <div className="spinner w-6 h-6"></div>
              ) : isPlaying ? (
                <PauseIcon className="w-6 h-6" />
              ) : (
                <PlayIcon className="w-6 h-6 ml-1" />
              )}
              <span>
                {isLoading ? 'Loading...' : isPlaying ? 'Pause' : 'Listen Live'}
              </span>
            </button>

            {/* Volume Controls */}
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleMute}
                className="p-2 text-gray-400 hover:text-white transition-colors"
              >
                {isMuted ? (
                  <VolumeXIcon className="w-5 h-5" />
                ) : (
                  <Volume2Icon className="w-5 h-5" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="100"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-20 accent-primary-500"
              />
              <span className="text-sm text-gray-400 w-8">
                {isMuted ? 0 : volume}
              </span>
            </div>

            {/* Live Indicator */}
            <div className="flex items-center space-x-2 text-red-500">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium">LIVE</span>
            </div>
          </div>
        </div>

        {/* Audio Visualizer */}
        <div className="flex-shrink-0 flex items-end space-x-1 h-20">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className={`w-3 audio-bar ${isPlaying ? 'animate-wave' : 'h-4'}`}
              style={{
                animationDelay: `${i * 0.1}s`,
                height: isPlaying ? undefined : '1rem'
              }}
            ></div>
          ))}
        </div>
      </div>

      {/* Station Info */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-700">
        <div className="flex items-center space-x-2 text-gray-400">
          <RadioIcon className="w-4 h-4" />
          <span className="text-sm font-pirate">🏴‍☠️ Raido Pirate Radio</span>
        </div>
        <div className="text-xs text-gray-500">
          128 kbps • MP3 • Stereo
        </div>
      </div>
    </div>
  )
}