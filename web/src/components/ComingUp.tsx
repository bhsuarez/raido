import React from 'react'
import { MusicIcon, ListMusicIcon, BotIcon } from 'lucide-react'
import { useNextUp } from '../hooks/useNowPlaying'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjgwIiBoZWlnaHQ9IjgwIiBmaWxsPSIjMWYyOTM3Ii8+CjwvcmVjdD4KPC9zdmc+Cg=='

function formatTime(seconds: unknown): string {
  const n = typeof seconds === 'number' ? seconds : Number(seconds)
  if (!isFinite(n) || n <= 0) return ''
  const mins = Math.floor(n / 60)
  const secs = Math.floor(n % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const ComingUp: React.FC = () => {
  const { data: nextUpData, isLoading } = useNextUp()

  const hasRealTracks = Array.isArray(nextUpData?.next_tracks) && nextUpData!.next_tracks.length > 0
  const tracks = hasRealTracks
    ? nextUpData!.next_tracks.map((item) => {
        const t = item?.track ?? ({} as any)
        const dur = typeof t.duration_sec === 'number' && isFinite(t.duration_sec) ? t.duration_sec : 0
        return {
          id: t.id ?? 0,
          title: t.title || 'Unknown',
          artist: t.artist || 'Unknown Artist',
          album: t.album || '',
          year: typeof t.year === 'number' ? t.year : undefined,
          genre: t.genre || '',
          duration: dur,
          artwork: t.artwork_url || FALLBACK_ART,
          commentary: null as string | null,
        }
      })
    : []

  if (isLoading) {
    return (
      <div className="card p-5">
        <div className="section-header mb-4">Up Next</div>
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-center gap-3 animate-pulse">
              <div className="w-11 h-11 rounded-lg bg-gray-800 flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3.5 bg-gray-800 rounded w-2/3" />
                <div className="h-3 bg-gray-800 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (tracks.length === 0) {
    return (
      <div className="card p-6 flex flex-col items-center gap-2 text-center text-gray-500 py-10">
        <ListMusicIcon className="w-8 h-8 text-gray-700" />
        <p className="text-sm font-medium text-gray-400">No queue data</p>
        <p className="text-xs">Tracks are played dynamically from the library</p>
      </div>
    )
  }

  const [featured, ...rest] = tracks

  return (
    <div className="card overflow-hidden">
      {/* Featured next track */}
      <div className="flex gap-4 p-5 border-b border-gray-800">
        <div className="flex-shrink-0 w-16 h-16 rounded-xl overflow-hidden bg-gray-800">
          <img
            src={featured.artwork}
            alt={`${featured.album || featured.title} artwork`}
            className="w-full h-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
          />
        </div>
        <div className="flex-1 min-w-0">
          <p className="section-header mb-1">Up Next</p>
          <p className="font-semibold text-white truncate">{featured.title}</p>
          <p className="text-sm text-gray-400 truncate">{featured.artist}</p>
          <div className="flex items-center gap-2 mt-1">
            {featured.genre && (
              <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full border border-gray-700">
                {featured.genre}
              </span>
            )}
            {featured.duration > 0 && (
              <span className="text-xs text-gray-500">{formatTime(featured.duration)}</span>
            )}
          </div>
        </div>
      </div>

      {/* Commentary preview if available */}
      {featured.commentary && (
        <div className="px-5 py-3 bg-gray-800/40 border-b border-gray-800 flex gap-2 items-start">
          <BotIcon className="w-4 h-4 text-primary-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-gray-300 leading-relaxed">{featured.commentary}</p>
        </div>
      )}

      {/* Rest of queue */}
      {rest.length > 0 && (
        <div className="divide-y divide-gray-800/60">
          {rest.map((track, i) => (
            <div key={`${track.id}-${i}`} className="flex items-center gap-3 px-5 py-3">
              <span className="text-xs font-medium text-gray-600 w-4 text-center flex-shrink-0">
                {i + 2}
              </span>
              <div className="w-9 h-9 rounded-lg overflow-hidden bg-gray-800 flex-shrink-0">
                <img
                  src={track.artwork}
                  alt={track.title}
                  className="w-full h-full object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
                />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200 truncate">{track.title}</p>
                <p className="text-xs text-gray-500 truncate">{track.artist}</p>
              </div>
              {track.duration > 0 && (
                <span className="text-xs text-gray-600 flex-shrink-0">{formatTime(track.duration)}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <span className="live-dot" />
          <span>AI commentary active</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-600">
          <MusicIcon className="w-3 h-3" />
          <span>{tracks.length} queued</span>
        </div>
      </div>
    </div>
  )
}

export default ComingUp
