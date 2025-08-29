import React from 'react'
import { useNextUp } from '../hooks/useNowPlaying'
import LoadingSpinner from './LoadingSpinner'

const ComingUp: React.FC = () => {
  const { data: nextUpData, isLoading, error } = useNextUp()
  
  // Debug logging
  console.log('ComingUp nextUpData:', nextUpData)
  console.log('ComingUp isLoading:', isLoading) 
  console.log('ComingUp error:', error)
  
  // Simple visibility check
  console.log('ComingUp component is rendering!')
  
  // Check if we have real upcoming tracks and transform the data structure
  const hasRealTracks = Array.isArray(nextUpData?.next_tracks) && nextUpData!.next_tracks.length > 0
  const upcomingTracks = hasRealTracks
    ? nextUpData!.next_tracks.map((item) => {
        const t = item?.track ?? ({} as any)
        const durationVal = typeof t.duration_sec === 'number' && isFinite(t.duration_sec) && t.duration_sec > 0
          ? t.duration_sec
          : 0
        return {
          id: typeof t.id === 'number' ? t.id : 0,
          title: t.title || 'Unknown',
          artist: t.artist || 'Unknown Artist',
          album: t.album || '',
          year: typeof t.year === 'number' ? t.year : undefined,
          genre: t.genre || 'Various',
          duration: durationVal,
          artwork:
            t.artwork_url ||
            'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjgwIiBoZWlnaHQ9IjgwIiBmaWxsPSIjMzc0MTUxIi8+Cjx0ZXh0IHg9IjQwIiB5PSI0MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzlCOUI5NSIgZm9udC1mYW1pbHk9InN5c3RlbS11aSIgZm9udC1zaXplPSIyNCI+8J+NtTwvdGV4dD4KPHN2Zz4K',
          commentary: null,
        }
      })
    : []

  const formatTime = (seconds: unknown) => {
    const n = typeof seconds === 'number' ? seconds : Number(seconds)
    if (!isFinite(n) || n <= 0) return '0:00'
    const totalSeconds = Math.floor(n)
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <div className="flex items-center justify-center h-32">
          <LoadingSpinner message="Loading upcoming tracks..." />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          🎵 Coming Up Next
        </h2>
        <div className="text-sm text-gray-400 bg-gray-800/50 px-3 py-1 rounded-full">
          {hasRealTracks ? 'Live Queue' : 'No Queue Data'}
        </div>
      </div>

      {/* Content */}
      {upcomingTracks.length === 0 ? (
        <div className="text-center text-gray-400 py-12">
          <div className="w-24 h-24 mx-auto mb-4 opacity-30">
            🎵
          </div>
          <h3 className="text-lg font-semibold mb-2">No Upcoming Tracks</h3>
          <p className="text-sm">
            Liquidsoap is not providing queue information.
            <br />
            Tracks are played dynamically from the music library.
          </p>
        </div>
      ) : (
        <>
          {/* Next Track (Featured) */}
          <div className="mb-8">
            <div className="bg-gradient-to-r from-pirate-800/40 to-gray-800/40 rounded-xl p-6 border border-pirate-600/20">
              <div className="flex items-start gap-6">
                {/* Album Art */}
                <div className="w-20 h-20 rounded-lg overflow-hidden shadow-lg flex-shrink-0 bg-gray-700">
                  <img
                    src={upcomingTracks[0].artwork}
                    alt={`${upcomingTracks[0].album || 'Unknown Album'} by ${upcomingTracks[0].artist}`}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement
                      target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjgwIiBoZWlnaHQ9IjgwIiBmaWxsPSIjMzc0MTUxIi8+Cjx0ZXh0IHg9IjQwIiB5PSI0MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzlCOUI5NSIgZm9udC1mYW1pbHk9InN5c3RlbS11aSIgZm9udC1zaXplPSIyNCI+8J+NtTwvdGV4dD4KPHN2Zz4K'
                    }}
                  />
                </div>

                {/* Track Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-lg font-bold text-white truncate">
                        {upcomingTracks[0].title}
                      </h3>
                      <p className="text-pirate-300 font-medium truncate">
                        {upcomingTracks[0].artist}
                      </p>
                      <p className="text-gray-400 text-sm truncate">
                        {upcomingTracks[0].album || 'Unknown Album'} {upcomingTracks[0].year && `• ${upcomingTracks[0].year}`}
                      </p>
                    </div>
                    <div className="text-right text-sm text-gray-400 flex-shrink-0 ml-4">
                      <div>{formatTime(upcomingTracks[0].duration)}</div>
                      <div className="bg-gray-700 px-2 py-1 rounded text-xs mt-1">
                        {upcomingTracks[0].genre || 'Various'}
                      </div>
                    </div>
                  </div>

                  {/* Commentary Preview */}
                  {upcomingTracks[0].commentary && (
                    <div className="bg-pirate-900/30 rounded-lg p-4 border border-pirate-600/20 mt-3">
                      <div className="flex items-start gap-2">
                        <div className="w-6 h-6 rounded-full bg-gradient-to-r from-pirate-500 to-pirate-400 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <span className="text-white text-xs">🤖</span>
                        </div>
                        <div className="flex-1">
                          <p className="text-sm text-gray-300 leading-relaxed">
                            <strong className="text-pirate-300">AI DJ Preview:</strong>{' '}
                            {upcomingTracks[0].commentary}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Additional Upcoming Tracks */}
          {upcomingTracks.length > 1 && (
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-gray-300 flex items-center gap-2">
                <span className="text-pirate-400">📋</span>
                Following Tracks
              </h3>
              {upcomingTracks.slice(1).map((track, index) => (
                <div
                  key={`${track.id ?? 0}-${index}-${track.title}-${track.artist}`}
                  className="flex items-center gap-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/20 hover:bg-gray-800/50 transition-colors"
                >
                  {/* Position */}
                  <div className="w-8 h-8 rounded-full bg-pirate-800 flex items-center justify-center text-pirate-300 font-bold text-sm flex-shrink-0">
                    {index + 2}
                  </div>

                  {/* Small Album Art */}
                  <div className="w-12 h-12 rounded overflow-hidden shadow flex-shrink-0 bg-gray-700">
                    <img
                      src={track.artwork}
                      alt={`${track.album || 'Unknown Album'} by ${track.artist}`}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement
                        target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDgiIGhlaWdodD0iNDgiIHZpZXdCb3g9IjAgMCA0OCA0OCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjQ4IiBoZWlnaHQ9IjQ4IiBmaWxsPSIjMzc0MTUxIi8+Cjx0ZXh0IHg9IjI0IiB5PSIyNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzlCOUI5NSIgZm9udC1mYW1pbHk9InN5c3RlbS11aSIgZm9udC1zaXplPSIxNiI+8J+NtTwvdGV4dD4KPHN2Zz4K'
                      }}
                    />
                  </div>

                  {/* Track Info */}
                  <div className="flex-1 min-w-0">
                    <div className="text-white font-medium truncate">
                      {track.title}
                    </div>
                    <div className="text-gray-400 text-sm truncate">
                      {track.artist} {track.album && `• ${track.album}`}
                    </div>
                  </div>

                  {/* Duration & Genre */}
                  <div className="text-right text-sm text-gray-400 flex-shrink-0">
                    <div>{formatTime(track.duration)}</div>
                    <div className="text-xs text-gray-500">{track.genre || 'Various'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* DJ Commentary Status */}
      <div className="mt-6 pt-4 border-t border-gray-700/50">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-gray-400">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span>AI Commentary generation active</span>
          </div>
          <div className="text-pirate-300 font-medium">
            Powered by Kokoro TTS
          </div>
        </div>
      </div>
    </div>
  )
}

export default ComingUp
