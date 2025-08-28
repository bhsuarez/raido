import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
import LoadingSpinner from './LoadingSpinner'
import { formatDistanceToNow } from 'date-fns'

interface TTSStatistics {
  total_24h: number
  success_24h: number
  failed_24h: number
  success_rate: number
  avg_generation_time_ms: number | null
  avg_tts_time_ms: number | null
}

interface TTSActivity {
  id: number
  text: string
  status: string
  provider: string
  voice_provider: string
  generation_time_ms: number | null
  tts_time_ms: number | null
  created_at: string
  audio_url: string | null
}

interface SystemStatus {
  tts_service: string
  dj_worker: string
  kokoro_tts: string
}

interface TTSStatusResponse {
  status: string
  statistics: TTSStatistics
  recent_activity: TTSActivity[]
  system_status: SystemStatus
}

const TTSMonitor: React.FC = () => {
  const [autoRefresh, setAutoRefresh] = useState(true)

  const { data: ttsStatus, isLoading, error, refetch } = useQuery<TTSStatusResponse>({
    queryKey: ['ttsStatus'],
    queryFn: () => api.get('/admin/tts-status').then(res => res.data),
    refetchInterval: autoRefresh ? 30000 : false, // Refresh every 30 seconds if auto-refresh is on
    staleTime: 10000,
  })

  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'text-green-400'
      case 'failed': return 'text-red-400'
      case 'running': return 'text-blue-400'
      case 'pending': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  const getServiceStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return '🟢'
      case 'stopped': return '🔴'
      case 'warning': return '🟡'
      default: return '⚪'
    }
  }

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner message="Loading TTS monitoring data..." />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <div className="flex items-center justify-center h-64">
          <div className="text-center text-red-400">
            <p className="text-xl mb-2">⚠️ Error Loading TTS Status</p>
            <p>Unable to fetch TTS monitoring data</p>
            <button 
              onClick={() => refetch()}
              className="mt-4 px-4 py-2 bg-pirate-600 hover:bg-pirate-700 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  const stats = ttsStatus?.statistics
  const activity = ttsStatus?.recent_activity || []
  const systemStatus = ttsStatus?.system_status

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            🎙️ TTS Monitoring Dashboard
          </h2>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-600 text-pirate-500 focus:ring-pirate-500"
              />
              Auto-refresh
            </label>
            <button
              onClick={() => refetch()}
              className="px-3 py-1 bg-pirate-600 hover:bg-pirate-700 text-white rounded-lg text-sm transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-gradient-to-br from-green-900/40 to-green-800/40 rounded-xl p-6 border border-green-600/20">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-green-600 flex items-center justify-center">
              <span className="text-xl">✅</span>
            </div>
            <div>
              <h3 className="font-semibold text-green-300">Success Rate</h3>
              <p className="text-2xl font-bold text-white">{stats?.success_rate || 0}%</p>
            </div>
          </div>
          <p className="text-sm text-green-400">
            {stats?.success_24h || 0} of {stats?.total_24h || 0} in 24h
          </p>
        </div>

        <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/40 rounded-xl p-6 border border-blue-600/20">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center">
              <span className="text-xl">🎵</span>
            </div>
            <div>
              <h3 className="font-semibold text-blue-300">Total Generated</h3>
              <p className="text-2xl font-bold text-white">{stats?.total_24h || 0}</p>
            </div>
          </div>
          <p className="text-sm text-blue-400">Last 24 hours</p>
        </div>

        <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/40 rounded-xl p-6 border border-purple-600/20">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center">
              <span className="text-xl">⚡</span>
            </div>
            <div>
              <h3 className="font-semibold text-purple-300">Avg Gen Time</h3>
              <p className="text-2xl font-bold text-white">
                {formatDuration(stats?.avg_generation_time_ms || null)}
              </p>
            </div>
          </div>
          <p className="text-sm text-purple-400">Generation speed</p>
        </div>

        <div className="bg-gradient-to-br from-orange-900/40 to-orange-800/40 rounded-xl p-6 border border-orange-600/20">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center">
              <span className="text-xl">🔊</span>
            </div>
            <div>
              <h3 className="font-semibold text-orange-300">Avg TTS Time</h3>
              <p className="text-2xl font-bold text-white">
                {formatDuration(stats?.avg_tts_time_ms || null)}
              </p>
            </div>
          </div>
          <p className="text-sm text-orange-400">Voice synthesis</p>
        </div>
      </div>

      {/* System Status */}
      {systemStatus && (
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <span>⚙️</span>
            System Status
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3 p-4 bg-gray-800/50 rounded-lg">
              <span className="text-2xl">{getServiceStatusIcon(systemStatus.tts_service)}</span>
              <div>
                <h4 className="font-semibold text-white">TTS Service</h4>
                <p className={`text-sm capitalize ${getStatusColor(systemStatus.tts_service)}`}>
                  {systemStatus.tts_service}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3 p-4 bg-gray-800/50 rounded-lg">
              <span className="text-2xl">{getServiceStatusIcon(systemStatus.dj_worker)}</span>
              <div>
                <h4 className="font-semibold text-white">DJ Worker</h4>
                <p className={`text-sm capitalize ${getStatusColor(systemStatus.dj_worker)}`}>
                  {systemStatus.dj_worker}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3 p-4 bg-gray-800/50 rounded-lg">
              <span className="text-2xl">{getServiceStatusIcon(systemStatus.kokoro_tts)}</span>
              <div>
                <h4 className="font-semibold text-white">Kokoro TTS</h4>
                <p className={`text-sm capitalize ${getStatusColor(systemStatus.kokoro_tts)}`}>
                  {systemStatus.kokoro_tts}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <span>📋</span>
          Recent TTS Activity
        </h3>

        {activity.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            <p>No recent TTS activity</p>
          </div>
        ) : (
          <div className="space-y-3">
            {activity.map((item) => (
              <div
                key={item.id}
                className="flex items-start gap-4 p-4 bg-gray-800/30 rounded-lg border border-gray-700/20"
              >
                <div className={`w-3 h-3 rounded-full mt-2 ${
                  item.status === 'ready' ? 'bg-green-400' :
                  item.status === 'failed' ? 'bg-red-400' :
                  'bg-yellow-400'
                }`}></div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-medium text-white truncate">
                        {item.text.replace(/<[^>]*>/g, '')} {/* Strip HTML tags */}
                      </h4>
                      <p className="text-sm text-gray-400">
                        {item.provider} • {item.voice_provider}
                      </p>
                    </div>
                    <div className="text-right text-sm text-gray-400 flex-shrink-0 ml-4">
                      <div>{formatDistanceToNow(new Date(item.created_at), { addSuffix: true })}</div>
                      {(item.generation_time_ms || item.tts_time_ms) && (
                        <div className="text-xs">
                          {item.generation_time_ms && `Gen: ${formatDuration(item.generation_time_ms)}`}
                          {item.generation_time_ms && item.tts_time_ms && ' • '}
                          {item.tts_time_ms && `TTS: ${formatDuration(item.tts_time_ms)}`}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {item.audio_url && (
                    <div className="mt-2">
                      <audio 
                        controls 
                        className="w-full h-8"
                        preload="metadata"
                      >
                        <source src={item.audio_url} type="audio/mpeg" />
                        Your browser does not support audio playback.
                      </audio>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default TTSMonitor