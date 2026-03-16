// web/src/pages/ListenPage.tsx
import React from 'react'
import { Loader2, Play, Pause, MusicIcon } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api, apiHelpers } from '../utils/api'
import { useArtColor } from '../hooks/useArtColor'
import { NowPlaying } from '../store/radioStore'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMGQwZDFhIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iNjAiIGZpbGw9IiMxMzEzMjciLz4KPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTUwIiByPSIyMCIgZmlsbD0iIzFhMWEzMiIvPgo8L3N2Zz4K'

const BASE_STREAM_URL: string = (() => {
  const configured = ((import.meta as any)?.env?.VITE_STREAM_URL as string | undefined)?.trim()
  return configured && configured.length > 0 ? configured : '/stream/raido.mp3'
})()

export default function ListenPage() {
  const audioRef = React.useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [isBuffering, setIsBuffering] = React.useState(false)
  const [streamToken, setStreamToken] = React.useState<string | null>(null)
  const [tokenError, setTokenError] = React.useState(false)
  const [tokenLoading, setTokenLoading] = React.useState(true)
  const refreshRef = React.useRef<ReturnType<typeof setInterval> | null>(null)

  // Poll now-playing data — station hardcoded to 'main', no Zustand dependency
  const { data: nowPlaying } = useQuery<NowPlaying>({
    queryKey: ['listenPageNowPlaying'],
    queryFn: () => api.get('/now', { params: { station: 'main' } }).then(r => r.data),
    refetchInterval: 10000,
    staleTime: 5000,
    retry: 3,
  })

  const track = nowPlaying?.track
  const artSrc = track?.artwork_url
    ? apiHelpers.resolveStaticUrl(track.artwork_url) ?? FALLBACK_ART
    : FALLBACK_ART

  useArtColor(track?.artwork_url ?? null)

  // Fetch guest token on mount, schedule refresh
  const fetchToken = React.useCallback(async () => {
    try {
      // Use native fetch so axios interceptors (auth redirect, toast errors) don't fire
      const res = await fetch(apiHelpers.apiUrl('/api/v1/stream/guest-token'))
      if (!res.ok) throw new Error('Failed')
      const data = await res.json() as { token: string; expires_in: number }
      setStreamToken(data.token)
      setTokenError(false)
      setTokenLoading(false)
      // Schedule next refresh at 80% of TTL
      if (refreshRef.current) clearInterval(refreshRef.current)
      refreshRef.current = setInterval(fetchToken, data.expires_in * 0.8 * 1000)
    } catch {
      setTokenError(true)
      setTokenLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void fetchToken()
    return () => {
      if (refreshRef.current) clearInterval(refreshRef.current)
    }
  }, [fetchToken])

  // Wire up audio element events
  React.useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    const onPlay = () => { setIsPlaying(true); setIsBuffering(false) }
    const onPause = () => setIsPlaying(false)
    const onWaiting = () => setIsBuffering(true)
    const onPlaying = () => setIsBuffering(false)
    const onStalled = () => setIsBuffering(true)
    const onError = () => { setIsPlaying(false); setIsBuffering(false) }
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('waiting', onWaiting)
    audio.addEventListener('playing', onPlaying)
    audio.addEventListener('stalled', onStalled)
    audio.addEventListener('error', onError)
    return () => {
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('waiting', onWaiting)
      audio.removeEventListener('playing', onPlaying)
      audio.removeEventListener('stalled', onStalled)
      audio.removeEventListener('error', onError)
    }
  }, [])

  const streamUrl = streamToken ? `${BASE_STREAM_URL}?token=${streamToken}` : undefined

  const handleToggle = React.useCallback(async () => {
    const audio = audioRef.current
    if (!audio || !streamUrl) return
    if (isPlaying) {
      audio.pause()
    } else {
      setIsBuffering(true)
      try { await audio.play() } catch { setIsBuffering(false) }
    }
  }, [isPlaying, streamUrl])

  const playButtonDisabled = tokenLoading || tokenError || !streamUrl
  const playButtonTitle = tokenError ? 'Stream unavailable' : tokenLoading ? 'Loading…' : undefined

  return (
    <div
      className="relative flex flex-col items-center justify-center"
      style={{ minHeight: '100dvh', overflow: 'hidden', background: 'var(--art-bg)' }}
    >
      {/* Blurred artwork background */}
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
      {/* Dark vignette */}
      <div
        className="absolute inset-0 -z-10"
        style={{ background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.75) 100%)' }}
      />

      {/* RAIDO wordmark */}
      <span
        className="absolute top-5 font-display font-bold tracking-widest uppercase"
        style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.25)', letterSpacing: '0.3em' }}
      >
        RAIDO
      </span>

      {/* Main content */}
      <div className="flex flex-col items-center gap-6 px-6 w-full max-w-xs mx-auto">

        {/* Album art */}
        <div
          className="rounded-2xl overflow-hidden"
          style={{
            width: 'clamp(180px, 40vw, 280px)',
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
        </div>

        {/* Track info */}
        {track ? (
          <div className="text-center w-full space-y-1">
            <h1
              className="font-display font-bold leading-tight"
              style={{ fontSize: 'clamp(1.2rem, 5vw, 1.6rem)', color: '#f0f0ff' }}
            >
              {track.title}
            </h1>
            <p className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>
              {track.artist}
            </p>
          </div>
        ) : (
          <div className="text-center space-y-2">
            <MusicIcon className="w-8 h-8 mx-auto" style={{ color: '#252545' }} />
            <p className="font-display font-bold text-xs uppercase tracking-widest" style={{ color: '#404060' }}>
              Loading…
            </p>
          </div>
        )}

        {/* LIVE badge + play button */}
        <div className="flex flex-col items-center gap-3">
          {nowPlaying?.is_playing && (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-green-400 bg-green-500/10 border border-green-500/20 px-2.5 py-1 rounded-full">
              <span className="live-dot" />
              LIVE
            </span>
          )}

          <button
            type="button"
            onClick={handleToggle}
            disabled={playButtonDisabled}
            title={playButtonTitle}
            className="flex items-center justify-center rounded-full transition"
            style={{
              width: '56px',
              height: '56px',
              background: playButtonDisabled ? 'rgba(255,255,255,0.08)' : 'var(--art-accent)',
              cursor: playButtonDisabled ? 'not-allowed' : 'pointer',
              boxShadow: playButtonDisabled ? 'none' : '0 4px 24px color-mix(in srgb, var(--art-accent) 50%, transparent)',
              opacity: playButtonDisabled ? 0.5 : 1,
            }}
            aria-label={isPlaying ? 'Pause' : 'Play live stream'}
          >
            {tokenLoading || isBuffering ? (
              <Loader2 className="w-6 h-6 text-white animate-spin" />
            ) : isPlaying ? (
              <Pause className="w-6 h-6 text-white" />
            ) : (
              <Play className="w-6 h-6 text-white pl-0.5" />
            )}
          </button>

          {tokenError && (
            <p className="text-xs text-red-400 text-center">Stream unavailable</p>
          )}
        </div>
      </div>

      <audio ref={audioRef} src={streamUrl} preload="none" className="hidden" />
    </div>
  )
}
