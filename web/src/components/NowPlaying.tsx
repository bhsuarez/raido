import React from 'react'
import { Link } from 'react-router-dom'
import { SkipForwardIcon, MusicIcon, BarChart2Icon, PencilIcon } from 'lucide-react'
import { useNowPlaying } from '../hooks/useNowPlaying'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'
import { NowPlayingSkeleton } from './LoadingSkeleton'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMWYyOTM3Ii8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iODAiIGZpbGw9IiMyZDM3NDgiLz4KPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTUwIiByPSIzMCIgZmlsbD0iIzM3NDE1MSIvPgo8L3N2Zz4K'

function formatTime(seconds: number | null | undefined): string {
  if (!seconds || isNaN(seconds)) return '0:00'
  const total = Math.floor(seconds)
  const mins = Math.floor(total / 60)
  const secs = total % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

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
      setElapsed(prev => Math.min(prev + 1, total))
    }, 1000)
    return () => clearInterval(interval)
  }, [track?.id, total])

  const handleSkip = async () => {
    if (isSkipping) return
    setIsSkipping(true)
    try {
      await apiHelpers.skipTrack()
      toast.success('Track skipped')
    } catch {
      toast.error('Failed to skip track')
    } finally {
      setTimeout(() => setIsSkipping(false), 2000)
    }
  }

  if (isLoading) return <NowPlayingSkeleton />

  if (error || !track) {
    return (
      <div className="card p-10 flex flex-col items-center justify-center gap-3 text-center min-h-[200px]">
        <MusicIcon className="w-10 h-10 text-gray-600" />
        <p className="text-gray-400 font-medium">Radio offline</p>
        <p className="text-gray-600 text-sm">No track currently playing</p>
      </div>
    )
  }

  const pct = total ? Math.min(100, (elapsed / total) * 100) : 0
  const remaining = total ? Math.max(0, total - elapsed) : 0

  return (
    <section className="card overflow-hidden" aria-label="Now Playing">
      {/* Layout: stacked on mobile, side-by-side on lg+ */}
      <div className="flex flex-col lg:flex-row">

        {/* Album Art */}
        <div className="lg:w-72 lg:flex-shrink-0">
          <div className="relative aspect-square lg:h-72 lg:w-72 bg-gray-800 overflow-hidden">
            <img
              src={track.artwork_url || FALLBACK_ART}
              alt={`${track.album || track.title} artwork`}
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
            />
            {/* Live badge over art */}
            <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur-sm px-2.5 py-1 rounded-full">
              <span className="live-dot" />
              <span className="text-xs font-semibold text-white">LIVE</span>
            </div>
          </div>
        </div>

        {/* Track Info & Controls */}
        <div className="flex-1 p-5 lg:p-7 flex flex-col justify-between gap-5">
          {/* Track metadata */}
          <div className="space-y-1">
            <div className="flex items-start gap-2">
              <h2 className="text-2xl sm:text-3xl font-bold text-white leading-tight flex-1">
                {track.title}
              </h2>
              <Link
                to={`/media/tracks/${track.id}`}
                title="Edit track metadata"
                className="flex-shrink-0 mt-1 p-1.5 rounded-lg text-gray-500 hover:text-gray-200 hover:bg-gray-800 transition-colors"
              >
                <PencilIcon className="w-4 h-4" />
              </Link>
            </div>
            <p className="text-lg text-gray-300 font-medium">{track.artist}</p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              {track.genre && (
                <span className="text-xs font-medium bg-gray-800 text-gray-300 px-2.5 py-1 rounded-full border border-gray-700">
                  {track.genre}
                </span>
              )}
              {(track.album || track.year) && (
                <span className="text-sm text-gray-500">
                  {[track.album, track.year].filter(Boolean).join(' · ')}
                </span>
              )}
            </div>
          </div>

          {/* Progress */}
          <div className="space-y-2" role="region" aria-label="Track progress">
            <div
              className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={elapsed}
              aria-valuemin={0}
              aria-valuemax={total}
            >
              <div
                className="h-full bg-primary-500 rounded-full progress-fill"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>{formatTime(elapsed)}</span>
              <span>-{formatTime(remaining)}</span>
            </div>
          </div>

          {/* Skip */}
          <div>
            <button
              onClick={handleSkip}
              disabled={isSkipping}
              aria-label={isSkipping ? 'Skipping...' : 'Skip to next track'}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm transition-all
                ${isSkipping
                  ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                  : 'bg-gray-800 hover:bg-gray-700 active:bg-gray-900 text-gray-200 border border-gray-700'
                }`}
            >
              {isSkipping ? (
                <>
                  <span className="w-4 h-4 border-2 border-gray-600 border-t-gray-300 rounded-full animate-spin" />
                  <span>Skipping...</span>
                </>
              ) : (
                <>
                  <SkipForwardIcon className="w-4 h-4" />
                  <span>Skip Track</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Analytics link */}
      <div className="border-t border-gray-800 px-5 py-2.5 flex justify-end">
        <Link
          to="/analytics"
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          <BarChart2Icon className="w-3.5 h-3.5" />
          Analytics
        </Link>
      </div>
    </section>
  )
}

export default NowPlaying
