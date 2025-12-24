import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../utils/api'
// import { toast } from 'react-hot-toast'

const TTSMonitorSimple: React.FC = () => {
  const { data: ttsStatus, isLoading, error } = useQuery({
    queryKey: ['ttsStatus', 'christmas'],
    queryFn: () => api.get('/admin/tts-status', {
      params: { station: 'christmas' }
    }).then(res => res.data),
    refetchInterval: 30000,
  })

  const stripTags = (s: string) => s.replace(/<[^>]*>/g, '')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          🎙️ TTS Monitoring Dashboard
        </h2>
        <p className="text-gray-300 mt-2">
          Monitor AI commentary generation and system performance
        </p>
      </div>

      {/* Statistics */}
      {isLoading ? (
        <div className="bg-gray-800 rounded-xl p-6 text-center text-gray-400">
          Loading TTS statistics...
        </div>
      ) : error ? (
        <div className="bg-red-900/30 rounded-xl p-6 text-center text-red-400">
          Failed to load TTS statistics
        </div>
      ) : ttsStatus ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-gradient-to-br from-green-900/40 to-green-800/40 rounded-xl p-6 border border-green-600/20">
            <h3 className="text-green-300 font-semibold mb-2">Success Rate</h3>
            <p className="text-3xl font-bold text-white">{ttsStatus.statistics?.success_rate || 0}%</p>
            <p className="text-sm text-green-400">
              {ttsStatus.statistics?.success_24h || 0} of {ttsStatus.statistics?.total_24h || 0} in 24h
            </p>
          </div>

          <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/40 rounded-xl p-6 border border-blue-600/20">
            <h3 className="text-blue-300 font-semibold mb-2">Total Generated</h3>
            <p className="text-3xl font-bold text-white">{ttsStatus.statistics?.total_24h || 0}</p>
            <p className="text-sm text-blue-400">Last 24 hours</p>
          </div>

          <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/40 rounded-xl p-6 border border-purple-600/20">
            <h3 className="text-purple-300 font-semibold mb-2">System Status</h3>
            <p className="text-2xl font-bold text-green-400">🟢 Online</p>
            <p className="text-sm text-purple-400">All services running</p>
          </div>

          <div className="bg-gradient-to-br from-orange-900/40 to-orange-800/40 rounded-xl p-6 border border-orange-600/20">
            <h3 className="text-orange-300 font-semibold mb-2">Voice Engine</h3>
            <p className="text-2xl font-bold text-white">Kokoro</p>
            <p className="text-sm text-orange-400">High-quality TTS</p>
          </div>
        </div>
      ) : null}

      {/* Recent Activity */}
      {ttsStatus?.recent_activity && ttsStatus.recent_activity.length > 0 && (
        <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
          <h3 className="text-xl font-bold text-white mb-4">Recent Commentary</h3>
          <div className="space-y-3">
            {ttsStatus.recent_activity.slice(0, 3).map((item: any) => (
              <div key={item.id} className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/20">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-white font-medium mb-2 whitespace-pre-wrap break-words flex-1">
                    {(item as any).transcript ? (item as any).transcript : stripTags(item.text)}
                  </p>
                </div>
                <div className="flex items-center justify-between text-sm text-gray-400">
                  <span>{item.provider} • {item.voice_provider}</span>
                  <span>{new Date(item.created_at).toLocaleTimeString()}</span>
                </div>
                {item.audio_url && (
                  <audio controls className="w-full mt-2 h-8">
                    <source src={item.audio_url} type="audio/mpeg" />
                  </audio>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default TTSMonitorSimple
