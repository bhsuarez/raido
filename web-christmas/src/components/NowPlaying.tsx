import React from 'react'
import { useIcecastMetadata } from '../hooks/useIcecastMetadata'

const NowPlaying: React.FC = () => {
  const { metadata, isLoading } = useIcecastMetadata()

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-blue-900/50 via-blue-800/50 to-blue-900/50 rounded-2xl p-8 shadow-2xl border border-blue-500/30">
        <div className="text-center text-gray-400">
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  if (!metadata) {
    return (
      <div className="bg-gradient-to-br from-blue-900/50 via-blue-800/50 to-blue-900/50 rounded-2xl p-8 shadow-2xl border border-blue-500/30">
        <div className="text-center text-gray-400">
          <p className="text-xl mb-2">❄️ Stream Starting</p>
          <p>No track currently playing</p>
        </div>
      </div>
    )
  }

  return (
    <section className="bg-gradient-to-br from-blue-900/50 via-blue-800/50 to-blue-900/50 rounded-2xl p-8 shadow-2xl border border-blue-500/30">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
        <h1 className="text-2xl font-bold text-white">
          ❄️ Now Playing
        </h1>
      </div>

      {/* Track Display with Artwork */}
      <div className="flex flex-col md:flex-row items-center gap-6">
        {/* Album Artwork */}
        <div className="flex-shrink-0">
          <div className="w-48 h-48 rounded-xl overflow-hidden shadow-2xl border-4 border-blue-500/30">
            {metadata.artwork_url ? (
              <img
                src={metadata.artwork_url}
                alt={`Album artwork for ${metadata.title}`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  const target = e.target as HTMLImageElement
                  target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMWUzYTVmIi8+Cjx0ZXh0IHg9IjE1MCIgeT0iMTUwIiBmb250LXNpemU9IjgwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiBmaWxsPSJ3aGl0ZSI+4p2EPC90ZXh0Pgo8L3N2Zz4='
                }}
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-blue-700 to-blue-900 flex items-center justify-center text-6xl">
                ❄️
              </div>
            )}
          </div>
        </div>

        {/* Track Info */}
        <div className="flex-1 text-center md:text-left space-y-3">
          <h2 className="text-3xl md:text-4xl font-bold text-white">
            {metadata.title}
          </h2>
          <h3 className="text-xl md:text-2xl text-blue-300">
            {metadata.artist}
          </h3>
        </div>
      </div>
    </section>
  )
}

export default NowPlaying
