import React from 'react'
import { Pause, Play, Loader2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { shallow } from 'zustand/shallow'
import { useRadioStore } from '../store/radioStore'
import { useAuthStore } from '../store/authStore'
import { apiHelpers } from '../utils/api'

const fallbackStreamPath = '/stream/raido.mp3'
const configuredStream = ((import.meta as any)?.env?.VITE_STREAM_URL as string | undefined)?.trim()
const BASE_STREAM_URL = configuredStream && configuredStream.length > 0 ? configuredStream : fallbackStreamPath

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
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const [streamToken, setStreamToken] = React.useState<string | null>(null)
  const sessionIdRef = React.useRef<number | null>(null)
  const heartbeatRef = React.useRef<ReturnType<typeof setInterval> | null>(null)
  const tokenRefreshRef = React.useRef<ReturnType<typeof setInterval> | null>(null)

  const token = useAuthStore((state) => state.token)

  const { nowPlaying } = useRadioStore(
    (state) => ({
      nowPlaying: state.nowPlaying,
    }),
    shallow,
  )

  const fetchStreamToken = React.useCallback(async (): Promise<string | null> => {
    if (!token) return null
    try {
      const res = await fetch(apiHelpers.apiUrl('/api/v1/stream/token'), {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) return null
      const data = await res.json()
      return data.token as string
    } catch {
      return null
    }
  }, [token])

  const startSession = React.useCallback(async () => {
    if (!token) return
    try {
      const res = await fetch(apiHelpers.apiUrl('/api/v1/listeners/sessions'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ station: 'main' }),
      })
      if (res.ok) {
        const data = await res.json()
        sessionIdRef.current = data.session_id as number
      }
    } catch {}
  }, [token])

  const sendHeartbeat = React.useCallback(async (): Promise<boolean> => {
    if (!sessionIdRef.current || !token) return false
    try {
      const res = await fetch(
        apiHelpers.apiUrl(`/api/v1/listeners/sessions/${sessionIdRef.current}/heartbeat`),
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        },
      )
      return res.ok
    } catch {
      return false
    }
  }, [token])

  const endSession = React.useCallback(async () => {
    if (!sessionIdRef.current || !token) return
    try {
      await fetch(apiHelpers.apiUrl(`/api/v1/listeners/sessions/${sessionIdRef.current}`), {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch {}
    sessionIdRef.current = null
  }, [token])

  React.useEffect(() => {
    if (!token) return

    let mounted = true

    const initialize = async () => {
      const t = await fetchStreamToken()
      if (mounted && t) {
        setStreamToken(t)
        await startSession()

        // Heartbeat every 30s — restart session if stale
        heartbeatRef.current = setInterval(async () => {
          const ok = await sendHeartbeat()
          if (!ok) {
            await startSession()
          }
        }, 30000)

        // Refresh stream token every 12 minutes (before 15-min expiry)
        tokenRefreshRef.current = setInterval(async () => {
          const newToken = await fetchStreamToken()
          if (mounted && newToken) setStreamToken(newToken)
        }, 720000)
      }
    }

    void initialize()

    return () => {
      mounted = false
      if (heartbeatRef.current) clearInterval(heartbeatRef.current)
      if (tokenRefreshRef.current) clearInterval(tokenRefreshRef.current)
      void endSession()
    }
  }, [token, fetchStreamToken, startSession, sendHeartbeat, endSession])

  React.useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    audio.volume = 1
    audio.muted = false
  }, [])

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

  const trackTitle = nowPlaying?.track?.title
  const trackArtist = nowPlaying?.track?.artist

  const streamUrl = streamToken ? `${BASE_STREAM_URL}?token=${streamToken}` : undefined

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
          </div>

          <div className="h-12 w-12" aria-hidden />
        </div>
        <audio ref={audioRef} src={streamUrl} preload="none" className="hidden" />
      </div>
    </div>
  )
}

export default RadioPlayer
