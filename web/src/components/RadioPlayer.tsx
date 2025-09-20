import React from 'react'
import { Pause, Play, Volume1, Volume2, VolumeX, Loader2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { shallow } from 'zustand/shallow'
import { useRadioStore } from '../store/radioStore'

const fallbackStreamPath = '/stream/raido.mp3'
const configuredStream = ((import.meta as any)?.env?.VITE_STREAM_URL as string | undefined)?.trim()
const streamSource = configuredStream && configuredStream.length > 0 ? configuredStream : fallbackStreamPath

const normalizeVolume = (value: number | undefined): number => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return 75
  }
  return Math.min(100, Math.max(0, Math.round(value)))
}

const formatTrackDisplay = (title?: string, artist?: string) => {
  if (title && artist) return `${title} — ${artist}`
  if (title) return title
  if (artist) return `Artist: ${artist}`
  return 'Live Stream Ready'
}

const RadioPlayer: React.FC = () => {
  const audioRef = React.useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [isBuffering, setIsBuffering] = React.useState(false)
  const [hadInteraction, setHadInteraction] = React.useState(false)
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)

  const { nowPlaying, volume, setVolume, isMuted, toggleMute } = useRadioStore(
    (state) => ({
      nowPlaying: state.nowPlaying,
      volume: state.volume,
      setVolume: state.setVolume,
      isMuted: state.isMuted,
      toggleMute: state.toggleMute,
    }),
    shallow,
  )

  const safeVolume = React.useMemo(() => normalizeVolume(volume), [volume])

  // Ensure persisted volume is always a valid number
  React.useEffect(() => {
    if (volume !== safeVolume) {
      setVolume(safeVolume)
    }
  }, [safeVolume, setVolume, volume])

  React.useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    audio.volume = isMuted ? 0 : safeVolume / 100
    audio.muted = isMuted
  }, [safeVolume, isMuted])

  React.useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handlePlay = () => {
      setIsPlaying(true)
      setIsBuffering(false)
      setErrorMessage(null)
    }
    const handlePause = () => {
      setIsPlaying(false)
    }
    const handleWaiting = () => {
      setIsBuffering(true)
    }
    const handlePlaying = () => {
      setIsBuffering(false)
    }
    const handleStalled = () => {
      setIsBuffering(true)
    }
    const handleError = () => {
      setIsPlaying(false)
      setIsBuffering(false)
      const message = 'Unable to load the stream. Please try again.'
      setErrorMessage(message)
    }

    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)
    audio.addEventListener('waiting', handleWaiting)
    audio.addEventListener('playing', handlePlaying)
    audio.addEventListener('stalled', handleStalled)
    audio.addEventListener('error', handleError)

    return () => {
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      audio.removeEventListener('waiting', handleWaiting)
      audio.removeEventListener('playing', handlePlaying)
      audio.removeEventListener('stalled', handleStalled)
      audio.removeEventListener('error', handleError)
    }
  }, [])

  const startPlayback = React.useCallback(async () => {
    const audio = audioRef.current
    if (!audio) return

    setHadInteraction(true)
    setErrorMessage(null)
    setIsBuffering(true)

    try {
      await audio.play()
    } catch (err) {
      setIsPlaying(false)
      setIsBuffering(false)
      const isAutoplayBlock = err instanceof DOMException && err.name === 'NotAllowedError'
      const message = isAutoplayBlock
        ? 'Autoplay blocked. Click play to start the stream.'
        : 'Failed to start playback.'
      setErrorMessage(message)
      toast.error(message)
    }
  }, [])

  const pausePlayback = React.useCallback(() => {
    const audio = audioRef.current
    if (!audio) return
    audio.pause()
  }, [])

  const handleTogglePlayback = React.useCallback(() => {
    if (isPlaying) {
      pausePlayback()
    } else {
      void startPlayback()
    }
  }, [isPlaying, pausePlayback, startPlayback])

  const handleVolumeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const nextValue = Number(event.target.value)
    if (Number.isNaN(nextValue)) return

    setVolume(nextValue)
    if (isMuted && nextValue > 0) {
      toggleMute()
    }
  }

  const handleToggleMute = () => {
    toggleMute()
  }

  const renderVolumeIcon = () => {
    if (isMuted || safeVolume === 0) {
      return <VolumeX className="h-5 w-5" aria-hidden />
    }
    if (safeVolume < 50) {
      return <Volume1 className="h-5 w-5" aria-hidden />
    }
    return <Volume2 className="h-5 w-5" aria-hidden />
  }

  const trackTitle = nowPlaying?.track?.title
  const trackArtist = nowPlaying?.track?.artist

  return (
    <div className="fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
      <div className="w-full max-w-4xl rounded-2xl border border-gray-700 bg-gray-900/95 px-4 py-3 shadow-2xl backdrop-blur">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5">
          <button
            type="button"
            onClick={handleTogglePlayback}
            className="flex h-12 w-12 items-center justify-center rounded-full bg-pirate-600 text-white shadow-lg transition hover:bg-pirate-500 focus:outline-none focus:ring-2 focus:ring-pirate-400 focus:ring-offset-2 focus:ring-offset-gray-900"
            aria-label={isPlaying ? 'Pause live stream' : 'Play live stream'}
          >
            {isBuffering ? (
              <Loader2 className="h-6 w-6 animate-spin" aria-hidden />
            ) : isPlaying ? (
              <Pause className="h-6 w-6" aria-hidden />
            ) : (
              <Play className="h-6 w-6 pl-1" aria-hidden />
            )}
          </button>

          <div className="min-w-0 flex-1 text-sm text-gray-200">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-green-400">
                <span className="h-2 w-2 rounded-full bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.8)]" aria-hidden />
                Live
              </span>
              <span className="truncate font-medium text-white" title={formatTrackDisplay(trackTitle, trackArtist)}>
                {formatTrackDisplay(trackTitle, trackArtist)}
              </span>
            </div>
            {isBuffering && (
              <p className="mt-1 flex items-center gap-2 text-xs text-yellow-300">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                Buffering the stream...
              </p>
            )}
            {errorMessage && (
              <p className="mt-1 text-xs text-red-400" role="alert">
                {errorMessage}
              </p>
            )}
            {!hadInteraction && !isPlaying && !errorMessage && (
              <p className="mt-1 text-xs text-gray-400">
                Hit play to listen while you explore the dashboard.
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleToggleMute}
              className="rounded-full p-2 text-gray-300 transition hover:bg-gray-800 hover:text-white focus:outline-none focus:ring-2 focus:ring-pirate-400 focus:ring-offset-2 focus:ring-offset-gray-900"
              aria-label={isMuted ? 'Unmute stream' : 'Mute stream'}
            >
              {renderVolumeIcon()}
            </button>
            <input
              type="range"
              min={0}
              max={100}
              value={safeVolume}
              onChange={handleVolumeChange}
              aria-label="Adjust stream volume"
              className="h-1 w-36 cursor-pointer appearance-none rounded-full bg-gray-700 accent-pirate-400"
            />
          </div>
        </div>
        <audio ref={audioRef} src={streamSource} preload="none" className="hidden" />
      </div>
    </div>
  )
}

export default RadioPlayer
