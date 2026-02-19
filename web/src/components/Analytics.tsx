import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart2Icon, CloudIcon, ChevronDownIcon, ChevronRightIcon } from 'lucide-react'
import api from '../utils/api'

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
  date_range: { start: string; end: string }
}

const TIME_RANGES = [
  { value: '1d', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: 'all', label: 'All' },
]

const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState('7d')
  const [genreCollapsed, setGenreCollapsed] = useState(false)
  const [showAllGenres, setShowAllGenres] = useState(false)

  const { data: analytics, isLoading, error, refetch } = useQuery<AnalyticsData>({
    queryKey: ['analytics', timeRange],
    queryFn: () => api.get(`/admin/analytics?range=${timeRange}`).then(r => r.data),
    staleTime: 30000,
  })

  const maxGenreCount = Math.max(...(analytics?.genre_breakdown || []).map(g => g.count), 1)
  const genresToShow = analytics?.genre_breakdown
    ? (showAllGenres ? analytics.genre_breakdown : analytics.genre_breakdown.slice(0, 25))
    : []

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Analytics</h1>
          {analytics?.date_range && (
            <p className="text-xs text-gray-500 mt-0.5">
              {new Date(analytics.date_range.start).toLocaleDateString()} –{' '}
              {new Date(analytics.date_range.end).toLocaleDateString()}
              {analytics.total_tracks > 0 && ` · ${analytics.total_tracks} tracks`}
            </p>
          )}
        </div>

        {/* Time range pills */}
        <div className="flex items-center gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1">
          {TIME_RANGES.map(r => (
            <button
              key={r.value}
              onClick={() => setTimeRange(r.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                timeRange === r.value
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Genre Breakdown */}
      <div className="card overflow-hidden">
        <button
          onClick={() => setGenreCollapsed(v => !v)}
          className="w-full flex items-center justify-between px-5 py-4 border-b border-gray-800 hover:bg-gray-800/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <BarChart2Icon className="w-4 h-4 text-gray-500" />
            <span className="section-header">Genre Breakdown</span>
            {analytics?.genre_breakdown && (
              <span className="text-xs text-gray-600">({analytics.genre_breakdown.length})</span>
            )}
          </div>
          {genreCollapsed ? (
            <ChevronRightIcon className="w-4 h-4 text-gray-600" />
          ) : (
            <ChevronDownIcon className="w-4 h-4 text-gray-600" />
          )}
        </button>

        {!genreCollapsed && (
          <div className="p-5">
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="animate-pulse space-y-1.5">
                    <div className="flex justify-between">
                      <div className="h-3 bg-gray-800 rounded w-1/4" />
                      <div className="h-3 bg-gray-800 rounded w-16" />
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full w-full" />
                  </div>
                ))}
              </div>
            ) : error ? (
              <div className="text-center py-8 space-y-3">
                <p className="text-gray-400">Failed to load analytics</p>
                <button onClick={() => refetch()} className="btn-secondary text-sm">
                  Retry
                </button>
              </div>
            ) : genresToShow.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <BarChart2Icon className="w-8 h-8 mx-auto mb-2 text-gray-700" />
                <p className="text-sm">No genre data yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {genresToShow.map((genre, i) => (
                  <div key={genre.genre}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xs text-gray-600 w-5 text-right flex-shrink-0">
                          {i + 1}
                        </span>
                        <span className="text-sm text-gray-200 font-medium truncate">
                          {genre.genre || 'Unknown'}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 flex-shrink-0 ml-3">
                        {genre.count} · {genre.percentage.toFixed(1)}%
                      </div>
                    </div>
                    <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 rounded-full transition-all duration-500"
                        style={{ width: `${(genre.count / maxGenreCount) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}

                {analytics?.genre_breakdown && analytics.genre_breakdown.length > 25 && (
                  <button
                    onClick={() => setShowAllGenres(v => !v)}
                    className="text-sm text-primary-400 hover:text-primary-300 transition-colors mt-2"
                  >
                    {showAllGenres
                      ? 'Show top 25'
                      : `Show all ${analytics.genre_breakdown.length} genres`}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Word Cloud */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center gap-2">
          <CloudIcon className="w-4 h-4 text-gray-500" />
          <span className="section-header">Commentary Word Frequency</span>
        </div>

        <div className="p-5">
          {isLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-10 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : analytics?.word_cloud_data && analytics.word_cloud_data.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {analytics.word_cloud_data.slice(0, 20).map((w) => (
                <div
                  key={w.word}
                  className="flex items-center justify-between px-3 py-2 bg-gray-800 rounded-xl border border-gray-700/50"
                >
                  <span
                    className="font-medium text-gray-200 truncate"
                    style={{ fontSize: `${Math.max(0.75, Math.min(1.1, w.count / 10))}rem` }}
                  >
                    {w.word}
                  </span>
                  <span className="text-xs text-gray-600 ml-2 flex-shrink-0">{w.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <CloudIcon className="w-8 h-8 mx-auto mb-2 text-gray-700" />
              <p className="text-sm">No commentary data yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Analytics
