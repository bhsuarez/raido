import React, { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api, { apiHelpers } from '../utils/api'
import LoadingSpinner from './LoadingSpinner'
// import { toast } from 'react-hot-toast'
// Removed date-fns import to avoid build issues

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
  transcript?: string | null
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
  const [saving, setSaving] = useState(false)
  const [voices, setVoices] = useState<string[]>([])
  const [testUrl, setTestUrl] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)

  // Admin settings state
  const [settings, setSettings] = useState<any | null>(null)
  const [settingsError, setSettingsError] = useState<string | null>(null)

  useEffect(() => {
    apiHelpers.getSettings()
      .then(res => setSettings(res.data))
      .catch(() => setSettingsError('Failed to load settings'))
  }, [])

  // Fetch voices based on selected provider
  useEffect(() => {
    const provider = settings?.dj_voice_provider || 'kokoro'
    const load = async () => {
      try {
        if (provider === 'xtts') {
          const res = await api.get('/admin/voices-xtts')
          const vs = res.data?.voices
          if (Array.isArray(vs)) setVoices(vs)
          else setVoices([])
        } else {
          const res = await api.get('/admin/voices')
          const vs = res.data?.voices
          if (Array.isArray(vs)) setVoices(vs)
          else setVoices([])
        }
      } catch {
        setVoices([])
      }
    }
    load()
  }, [settings?.dj_voice_provider])

  const saveSettings = async () => {
    if (!settings) return
    setSaving(true)
    setSettingsError(null)
    try {
      await apiHelpers.updateSettings(settings)
    } catch (e:any) {
      setSettingsError(e?.response?.data?.detail || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const stripTags = (s: string) => s.replace(/<[^>]*>/g, '')

  const { data: ttsStatus, isLoading, error, refetch } = useQuery<TTSStatusResponse>({
    queryKey: ['ttsStatus', autoRefresh],
    queryFn: () => api.get('/admin/tts-status?window_hours=24&limit=100').then(res => res.data),
    refetchInterval: autoRefresh ? 30000 : false,
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
      {/* Settings Panel */}
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">⚙️ DJ Settings</h2>
          <button
            onClick={saveSettings}
            disabled={!settings || saving}
            className={`px-3 py-2 rounded-lg text-white text-sm ${saving ? 'bg-gray-700' : 'bg-pirate-600 hover:bg-pirate-700'} transition-colors`}
          >{saving ? 'Saving…' : 'Save Settings'}</button>
        </div>
        {settingsError && (
          <div className="text-red-400 text-sm mb-3">{settingsError}</div>
        )}
        {settings ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Max Intro Duration */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Max Intro Duration (seconds)</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={5}
                  max={60}
                  step={1}
                  value={Number(settings.dj_max_seconds ?? 30)}
                  onChange={(e)=>setSettings({...settings, dj_max_seconds: parseInt(e.target.value || '0', 10)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={5}
                  max={60}
                  step={1}
                  value={Number(settings.dj_max_seconds ?? 30)}
                  onChange={(e)=>setSettings({...settings, dj_max_seconds: parseInt(e.target.value || '0', 10)})}
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Target length used to trim commentary naturally.</p>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Commentary Provider</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                value={settings.dj_provider || 'ollama'}
                onChange={(e)=>setSettings({...settings, dj_provider: e.target.value})}
              >
                <option value="ollama">Ollama</option>
                <option value="openai">OpenAI</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Voice Provider</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                value={settings.dj_voice_provider || 'kokoro'}
                onChange={(e)=>setSettings({...settings, dj_voice_provider: e.target.value})}
              >
                <option value="kokoro">Kokoro</option>
                <option value="openai_tts">OpenAI TTS</option>
                <option value="liquidsoap">Liquidsoap</option>
                <option value="xtts">XTTS</option>
              </select>
            </div>
            {/* Voice selection (switches between Kokoro and XTTS) */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">
                {settings.dj_voice_provider === 'xtts' ? 'XTTS Voice' : 'Kokoro Voice'}
              </label>
              {(() => {
                const list = voices.length ? voices : (
                  settings.dj_voice_provider === 'xtts'
                    ? []
                    : [
                        'af_bella','af_aria','af_sky','af_nicole',
                        'am_onyx','am_michael','am_ryan','am_alex',
                        'bf_ava','bf_sophie','bm_george','bm_james'
                      ]
                )
                const field = settings.dj_voice_provider === 'xtts' ? 'xtts_voice' : 'kokoro_voice'
                const current = settings[field] || ''
                const isCustom = current && !list.includes(current)
                const value = isCustom ? 'custom' : (current || (list[0] || ''))
                return (
                  <div className="space-y-2">
                    <select
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                      value={value}
                      onChange={(e)=>{
                        const v = e.target.value
                        if (v === 'custom') return
                        setSettings({...settings, [field]: v})
                      }}
                    >
                      {list.map(v => <option key={v} value={v}>{v}</option>)}
                      <option value="custom">Custom…</option>
                    </select>
                    {(isCustom || (current==='')) && (
                      <input
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                        value={current}
                        onChange={(e)=>setSettings({...settings, [field]: e.target.value})}
                        placeholder={settings.dj_voice_provider === 'xtts' ? 'Enter XTTS voice id' : 'Enter Kokoro voice id'}
                      />
                    )}
                  </div>
                )
              })()}
              {settings.dj_voice_provider !== 'xtts' && (
                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={async ()=>{
                      if (!settings) return
                      setTesting(true)
                      setTestUrl(null)
                      try {
                        const sample = `Welcome to Raido. Testing voice ${settings.kokoro_voice || 'af_bella'} at speed ${settings.kokoro_speed ?? 1.0}.`
                        const res = await api.post('/admin/tts-test', {
                          text: sample,
                          voice: settings.kokoro_voice,
                          speed: settings.kokoro_speed,
                          volume: settings.dj_tts_volume,
                        })
                        const url = res.data?.audio_url
                        if (url) setTestUrl(url)
                      } catch (e) {
                        setSettingsError('TTS test failed')
                      } finally {
                        setTesting(false)
                      }
                    }}
                    disabled={testing}
                    className={`px-3 py-2 rounded-lg text-white text-sm ${testing ? 'bg-gray-700' : 'bg-pirate-600 hover:bg-pirate-700'} transition-colors`}
                  >{testing ? 'Testing…' : 'Test Kokoro Voice'}</button>
                  {testUrl && (
                    <audio controls className="h-8">
                      <source src={testUrl} type="audio/mpeg" />
                    </audio>
                  )}
                </div>
              )}
            </div>
            {/* TTS Gain / Volume */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">TTS Gain (Volume Multiplier)</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={Number(settings.dj_tts_volume ?? 1.0)}
                  onChange={(e)=>setSettings({...settings, dj_tts_volume: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={Number(settings.dj_tts_volume ?? 1.0)}
                  onChange={(e)=>setSettings({...settings, dj_tts_volume: parseFloat(e.target.value)})}
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Boost quiet clips (0.5×–2.0×). Applied to Kokoro.</p>
            </div>
            {/* Kokoro Speed */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Kokoro Speed</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.5}
                  max={1.5}
                  step={0.05}
                  value={Number(settings.kokoro_speed ?? 1.0)}
                  onChange={(e)=>setSettings({...settings, kokoro_speed: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.5}
                  max={1.5}
                  step={0.05}
                  value={Number(settings.kokoro_speed ?? 1.0)}
                  onChange={(e)=>setSettings({...settings, kokoro_speed: parseFloat(e.target.value)})}
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Playback speed multiplier (0.5×–1.5×). Kokoro only.</p>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Ollama Model</label>
              <input
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                value={settings.ollama_model || ''}
                onChange={(e)=>setSettings({...settings, ollama_model: e.target.value})}
                placeholder="e.g. llama3.1:8b"
              />
            </div>
            {/* Ollama Temperature */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Ollama Temperature</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0}
                  max={2}
                  step={0.1}
                  value={Number(settings.dj_temperature ?? 0.8)}
                  onChange={(e)=>setSettings({...settings, dj_temperature: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={Number(settings.dj_temperature ?? 0.8)}
                  onChange={(e)=>setSettings({...settings, dj_temperature: parseFloat(e.target.value)})}
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Higher = more creative, lower = more consistent.</p>
            </div>
            {/* Ollama Max Tokens */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Ollama Max Tokens</label>
              <input
                type="number"
                min={50}
                max={1000}
                step={10}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                value={Number(settings.dj_max_tokens ?? 200)}
                onChange={(e)=>setSettings({...settings, dj_max_tokens: parseInt(e.target.value || '0', 10)})}
                placeholder="e.g. 200"
              />
              <p className="text-xs text-gray-400 mt-1">Caps commentary length; real cap also based on time.</p>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm text-gray-300 mb-1">Default DJ Prompt</label>
              <textarea
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white h-28"
                value={settings.dj_prompt_template || ''}
                onChange={(e)=>setSettings({...settings, dj_prompt_template: e.target.value})}
                placeholder="Write the prompt template used to generate commentary…"
              />
              <p className="text-xs text-gray-400 mt-1">Supports Jinja templating; validated server-side.</p>
            </div>
          </div>
        ) : (
          <div className="text-gray-400 text-sm">Loading settings…</div>
        )}
      </div>
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
                      <h4 className="font-medium text-white whitespace-pre-wrap break-words">
                        {item.transcript ? item.transcript : stripTags(item.text)}
                      </h4>
                      <p className="text-sm text-gray-400">
                        {item.provider} • {item.voice_provider}
                      </p>
                    </div>
                    <div className="text-right text-sm text-gray-400 flex-shrink-0 ml-4">
                      <div>{new Date(item.created_at).toLocaleTimeString()}</div>
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
