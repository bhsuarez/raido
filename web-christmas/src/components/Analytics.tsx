import React, { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../utils/api'
import LoadingSpinner from './LoadingSpinner'

interface GenreStats {
  genre: string
  count: number
  percentage: number
  total_duration: number
  avg_duration: number
}

interface WordFrequency {
  word: string
  count: number
}

interface AnalyticsData {
  genre_breakdown: GenreStats[]
  total_tracks: number
  word_cloud_data: WordFrequency[]
  date_range: {
    start: string
    end: string
  }
}

const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState('7d') // 1d, 7d, 30d, all
  const [genreCollapsed, setGenreCollapsed] = useState(false)
  const [showAllGenres, setShowAllGenres] = useState(false)

  const { data: analytics, isLoading, error, refetch } = useQuery<AnalyticsData>({
    queryKey: ['analytics', timeRange],
    queryFn: () => api.get(`/admin/analytics?range=${timeRange}`).then(res => res.data),
    staleTime: 30000, // 30 seconds
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner message="Loading analytics data..." />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-center text-red-400">
              <p className="text-xl mb-2">⚠️ Error Loading Analytics</p>
              <p>Unable to fetch analytics data</p>
              <button 
                onClick={() => refetch()}
                className="mt-4 px-4 py-2 bg-pirate-600 hover:bg-pirate-700 text-white rounded-lg transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const maxGenreCount = Math.max(...(analytics?.genre_breakdown || []).map(g => g.count))
  
  // Determine which genres to show
  const genresToShow = analytics?.genre_breakdown ? 
    (showAllGenres ? analytics.genre_breakdown : analytics.genre_breakdown.slice(0, 25)) : 
    []

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-pirate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-2">
                📊 Raido Analytics
              </h1>
              <p className="text-gray-300 mt-2">
                Track insights and content analysis for your AI radio station
              </p>
            </div>
            
            {/* Time Range Selector */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-300">Time Range:</label>
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm"
              >
                <option value="1d">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="all">All Time</option>
              </select>
            </div>
          </div>
          
          {analytics?.date_range && (
            <div className="text-sm text-gray-400">
              Data from {new Date(analytics.date_range.start).toLocaleDateString()} to {new Date(analytics.date_range.end).toLocaleDateString()}
              {analytics.total_tracks && (
                <span className="ml-4">• {analytics.total_tracks} tracks analyzed</span>
              )}
            </div>
          )}
        </div>

        {/* Genre Breakdown */}
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <div className="flex items-center justify-between mb-6">
            <button
              onClick={() => setGenreCollapsed(!genreCollapsed)}
              className="flex items-center gap-2 text-2xl font-bold text-white hover:text-pirate-400 transition-colors"
            >
              <span className={`transform transition-transform ${genreCollapsed ? 'rotate-0' : 'rotate-90'}`}>▶</span>
              <span>🎵 Genre Breakdown</span>
              <span className="text-sm font-normal text-gray-400">
                ({analytics?.genre_breakdown?.length || 0} genres total)
              </span>
            </button>
            
            {!genreCollapsed && analytics?.genre_breakdown && analytics.genre_breakdown.length > 25 && (
              <button
                onClick={() => setShowAllGenres(!showAllGenres)}
                className="px-3 py-1 text-sm bg-pirate-600 hover:bg-pirate-700 text-white rounded-lg transition-colors"
              >
                {showAllGenres ? 'Show Top 25' : `Show All ${analytics.genre_breakdown.length}`}
              </button>
            )}
          </div>
          
          {!genreCollapsed && (
            analytics?.genre_breakdown && analytics.genre_breakdown.length > 0 ? (
              <div className="space-y-4">
                {genresToShow.map((genre, index) => (
                <div key={genre.genre} className="relative">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-semibold text-white">
                        #{index + 1}
                      </span>
                      <span className="text-white font-medium">
                        {genre.genre || 'Unknown'}
                      </span>
                    </div>
                    <div className="text-right text-sm text-gray-300">
                      <div>{genre.count} tracks ({genre.percentage.toFixed(1)}%)</div>
                      {genre.avg_duration && (
                        <div className="text-xs">
                          Avg: {Math.round(genre.avg_duration / 60)}m {Math.round(genre.avg_duration % 60)}s
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-pirate-500 to-pirate-400 transition-all duration-500"
                      style={{ width: `${(genre.count / maxGenreCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            ) : (
              <div className="text-center py-12 text-gray-400">
                <p className="text-xl mb-2">📭 No Genre Data Available</p>
                <p>Start playing some music to see genre analytics!</p>
              </div>
            )
          )}
        </div>

        {/* Word Cloud Placeholder */}
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            ☁️ TTS Commentary Word Cloud
          </h2>
          
          {analytics?.word_cloud_data && analytics.word_cloud_data.length > 0 ? (
            <div className="min-h-[400px] flex items-center justify-center bg-gray-800/50 rounded-lg border border-gray-700">
              {/* Simple word frequency list for now */}
              <div className="w-full p-6">
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {analytics.word_cloud_data.slice(0, 20).map((word, index) => (
                    <div
                      key={word.word}
                      className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg border border-gray-600/50"
                    >
                      <span 
                        className="font-medium text-white"
                        style={{ 
                          fontSize: `${Math.max(0.8, Math.min(1.5, word.count / 10))}rem` 
                        }}
                      >
                        {word.word}
                      </span>
                      <span className="text-sm text-gray-400">
                        {word.count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="min-h-[400px] flex items-center justify-center bg-gray-800/50 rounded-lg border border-gray-700">
              <div className="text-center text-gray-400">
                <p className="text-xl mb-2">💬 No Commentary Data</p>
                <p>TTS commentary word analysis will appear here</p>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}

export default Analytics