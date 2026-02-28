import React, { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api, { apiHelpers, ttsApi } from '../utils/api'
import LoadingSpinner from './LoadingSpinner'
import { toast } from 'react-hot-toast'

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
  voice_id?: string | null
  generation_time_ms: number | null
  tts_time_ms: number | null
  created_at: string
  audio_url: string | null
}

interface SystemStatus {
  tts_service: string
  dj_worker: string
  kokoro_tts: string
  chatterbox_tts?: string
}

interface TTSStatusResponse {
  status: string
  statistics: TTSStatistics
  recent_activity: TTSActivity[]
  pagination?: {
    limit: number
    offset: number
    total: number
    has_more: boolean
  }
  system_status: SystemStatus
  chatterbox_health?: {
    status: string
    detail?: string | null
    endpoint?: string | null
  }
}

// Voice Testing Component
const VoiceTestSection: React.FC<{
  settings: any
  testText: string
  setTestText: (text: string) => void
}> = ({ settings, testText, setTestText }) => {
  const [testing, setTesting] = useState(false)
  const [testUrl, setTestUrl] = useState<string | null>(null)

  const testVoice = async () => {
    if (!settings) return
    
    setTesting(true)
    setTestUrl(null)
    
    try {
      const provider = settings.dj_voice_provider || 'kokoro'
      let endpoint = '/admin/tts-test'
      let payload: any = { text: testText }
      
      // Route to correct endpoint based on provider
      switch (provider) {
        case 'chatterbox':
          endpoint = '/admin/tts-test-chatterbox'
          payload.voice = settings.chatterbox_voice || 'default'
          payload.exaggeration = settings.chatterbox_exaggeration
          payload.cfg_weight = settings.chatterbox_cfg_weight
          break
          
        case 'xtts':
          endpoint = '/admin/tts-test-xtts'
          payload.voice = settings.xtts_voice || 'coqui-tts:en_ljspeech'
          payload.speaker = settings.xtts_speaker
          break
          
        default: // kokoro
          payload.voice = settings.kokoro_voice || 'af_bella'
          payload.speed = settings.kokoro_speed
          payload.volume = settings.dj_tts_volume
          break
      }
      
      const res = await ttsApi.post(endpoint, payload)
      const url = apiHelpers.resolveStaticUrl(res.data?.audio_url)
      if (url) {
        setTestUrl(url)
        toast.success(`${provider.toUpperCase()} voice test generated!`)
      }
    } catch (e: any) {
      const errorMsg = e?.response?.data?.detail || 'Voice test failed'
      toast.error(errorMsg)
    } finally {
      setTesting(false)
    }
  }

  const getVoiceName = () => {
    const provider = settings?.dj_voice_provider || 'kokoro'
    switch (provider) {
      case 'chatterbox': return settings?.chatterbox_voice || 'default'
      case 'xtts': return settings?.xtts_voice || 'coqui-tts:en_ljspeech'
      default: return settings?.kokoro_voice || 'af_bella'
    }
  }

  const getProviderDisplayName = () => {
    const provider = settings?.dj_voice_provider || 'kokoro'
    switch (provider) {
      case 'chatterbox': return 'Chatterbox'
      case 'xtts': return 'XTTS'
      default: return 'Kokoro'
    }
  }

  return (
    <div className="bg-gradient-to-br from-pirate-800/30 to-pirate-900/30 rounded-xl p-6 border border-pirate-600/20">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        🎤 Voice Testing
      </h3>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-gray-300 mb-2">Test Text</label>
          <input
            type="text"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm"
            placeholder="Enter text to test the voice..."
          />
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={testVoice}
            disabled={testing || !settings}
            className={`px-4 py-2 rounded-lg text-white font-medium ${
              testing ? 'bg-gray-700' : 'bg-pirate-600 hover:bg-pirate-700'
            } transition-colors`}
          >
            {testing ? (
              <>
                <span className="animate-spin inline-block mr-2">⏳</span>
                Testing...
              </>
            ) : (
              `Test ${getProviderDisplayName()} Voice`
            )}
          </button>
          
          <div className="text-sm text-gray-400">
            Voice: <span className="text-white">{getVoiceName()}</span>
          </div>
        </div>
        
        {testUrl && (
          <div className="bg-gray-800/50 rounded-lg p-3">
            <div className="text-sm text-gray-300 mb-2">Generated Audio:</div>
            <audio controls className="w-full h-8">
              <source src={testUrl} type="audio/mpeg" />
              Your browser does not support audio playback.
            </audio>
          </div>
        )}
      </div>
    </div>
  )
}

// Settings Section Components
const GeneralSettingsSection: React.FC<{ settings: any, setSettings: (s: any) => void }> = ({ settings, setSettings }) => (
  <div className="space-y-4">
    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
      ⚙️ General Settings
    </h3>
    
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label className="block text-sm text-gray-300 mb-1">Commentary Provider</label>
        <select
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
          value={settings.dj_provider || 'templates'}
          onChange={(e) => setSettings({...settings, dj_provider: e.target.value})}
        >
          <option value="ollama">Ollama</option>
          <option value="templates">Templates</option>
          <option value="disabled">Disabled</option>
        </select>
      </div>
      
      <div>
        <label className="block text-sm text-gray-300 mb-1">Max Intro Duration (seconds)</label>
        <div className="flex items-center gap-3">
          <input
            type="range"
            min={5}
            max={60}
            step={1}
            value={Number(settings.dj_max_seconds ?? 30)}
            onChange={(e) => setSettings({...settings, dj_max_seconds: parseInt(e.target.value || '0', 10)})}
            className="flex-1"
          />
          <input
            type="number"
            min={5}
            max={60}
            step={1}
            value={Number(settings.dj_max_seconds ?? 30)}
            onChange={(e) => setSettings({...settings, dj_max_seconds: parseInt(e.target.value || '0', 10)})}
            className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
          />
        </div>
      </div>
    </div>
  </div>
)

const VoiceProviderSection: React.FC<{ 
  settings: any, 
  setSettings: (s: any) => void,
  voices: string[],
  chatterboxVoices: string[]
}> = ({ settings, setSettings, voices, chatterboxVoices }) => {
  const provider = settings?.dj_voice_provider || 'kokoro'
  
  const getVoiceOptions = () => {
    switch (provider) {
      case 'chatterbox': {
        const base = chatterboxVoices.length ? chatterboxVoices : ['default']
        const cur = settings?.chatterbox_voice
        // Ensure currently selected voice stays visible even if not in the fetched list
        return cur && !base.includes(cur) ? [cur, ...base] : base
      }
      case 'xtts':
        return voices.length ? voices : []
      default: // kokoro
        return voices.length ? voices : [
          'af_bella', 'af_sarah', 'af_sky', 'am_onyx', 'am_michael', 'am_ryan',
          'bf_ava', 'bf_sophie', 'bm_george', 'bm_james'
        ]
    }
  }

  const formatVoiceName = (voiceId: string) => {
    // Format voice IDs for display in dropdown
    if (provider === 'chatterbox') {
      // Remove "custom-" prefix and capitalize
      const cleaned = voiceId.replace(/^custom-/, '')
      return cleaned.split('-').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
      ).join(' ')
    }
    return voiceId
  }

  const getVoiceFieldName = () => {
    switch (provider) {
      case 'chatterbox': return 'chatterbox_voice'
      case 'xtts': return 'xtts_voice'
      default: return 'kokoro_voice'
    }
  }

  const getCurrentVoice = () => {
    const fieldName = getVoiceFieldName()
    return settings[fieldName] || getVoiceOptions()[0] || ''
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        🔊 Voice & TTS Settings
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Voice Provider</label>
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            value={provider}
            onChange={(e) => setSettings({...settings, dj_voice_provider: e.target.value})}
          >
            <option value="kokoro">Kokoro TTS</option>
            <option value="chatterbox">Chatterbox</option>
            <option value="xtts">XTTS</option>
            <option value="liquidsoap">Liquidsoap</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm text-gray-300 mb-1">
            {provider === 'chatterbox' ? 'Chatterbox Voice' :
             provider === 'xtts' ? 'XTTS Voice' : 'Kokoro Voice'}
          </label>
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            value={getCurrentVoice()}
            onChange={(e) => {
              const fieldName = getVoiceFieldName()
              setSettings({...settings, [fieldName]: e.target.value})
            }}
          >
            {getVoiceOptions().map(voice => (
              <option key={voice} value={voice}>{formatVoiceName(voice)}</option>
            ))}
          </select>
        </div>

        {/* Provider-specific settings */}
        {provider === 'kokoro' && (
          <>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Kokoro Speed</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.5}
                  max={1.5}
                  step={0.05}
                  value={Number(settings.kokoro_speed ?? 1.0)}
                  onChange={(e) => setSettings({...settings, kokoro_speed: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.5}
                  max={1.5}
                  step={0.05}
                  value={Number(settings.kokoro_speed ?? 1.0)}
                  onChange={(e) => setSettings({...settings, kokoro_speed: parseFloat(e.target.value)})}
                  className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm text-gray-300 mb-1">TTS Volume</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={Number(settings.dj_tts_volume ?? 1.0)}
                  onChange={(e) => setSettings({...settings, dj_tts_volume: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={Number(settings.dj_tts_volume ?? 1.0)}
                  onChange={(e) => setSettings({...settings, dj_tts_volume: parseFloat(e.target.value)})}
                  className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                />
              </div>
            </div>
          </>
        )}

        {provider === 'chatterbox' && (
          <>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Custom Voice (optional)</label>
              <input
                type="text"
                placeholder="e.g., brian"
                value={settings.chatterbox_voice || ''}
                onChange={(e) => setSettings({ ...settings, chatterbox_voice: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              />
              <p className="text-xs text-gray-400 mt-1">If your Chatterbox server supports named voices, enter it here.</p>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">Chatterbox Voices API URL</label>
              <input
                type="text"
                placeholder="http://192.168.1.170:8080/api/voices"
                value={settings.chatterbox_voices_url || ''}
                onChange={(e) => setSettings({ ...settings, chatterbox_voices_url: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
              />
              <p className="text-xs text-gray-400 mt-1">Used for listing voices only. TTS generation uses the configured Chatterbox base URL.</p>
            </div>
            <div>
              <label className="block text-sm text-gray-300 mb-1">TTS Volume</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={Number(settings.dj_tts_volume ?? 1.0)}
                  onChange={(e) => setSettings({...settings, dj_tts_volume: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={Number(settings.dj_tts_volume ?? 1.0)}
                  onChange={(e) => setSettings({...settings, dj_tts_volume: parseFloat(e.target.value)})}
                  className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-300 mb-1">Exaggeration</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.25}
                  max={2.0}
                  step={0.05}
                  value={Number(settings.chatterbox_exaggeration ?? 1.0)}
                  onChange={(e) => setSettings({...settings, chatterbox_exaggeration: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.25}
                  max={2.0}
                  step={0.05}
                  value={Number(settings.chatterbox_exaggeration ?? 1.0)}
                  onChange={(e) => setSettings({...settings, chatterbox_exaggeration: parseFloat(e.target.value)})}
                  className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm text-gray-300 mb-1">CFG Weight</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.0}
                  max={1.0}
                  step={0.05}
                  value={Number(settings.chatterbox_cfg_weight ?? 0.5)}
                  onChange={(e) => setSettings({...settings, chatterbox_cfg_weight: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.0}
                  max={1.0}
                  step={0.05}
                  value={Number(settings.chatterbox_cfg_weight ?? 0.5)}
                  onChange={(e) => setSettings({...settings, chatterbox_cfg_weight: parseFloat(e.target.value)})}
                  className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
                />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

const AIModelSection: React.FC<{
  settings: any,
  setSettings: (s: any) => void,
  ollamaModels: string[]
}> = ({ settings, setSettings, ollamaModels }) => {
  const currentProvider = settings?.dj_provider || 'templates'
  const currentModel = settings?.dj_model || settings?.ollama_model || 'llama3.2:1b'

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        🤖 AI Model Settings
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Ollama Model</label>
          <select
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
            value={currentModel}
            onChange={(e) => setSettings({
              ...settings,
              dj_model: e.target.value,
              ollama_model: e.target.value,
            })}
          >
            {ollamaModels.length > 0 ? (
              ollamaModels.map(model => (
                <option key={model} value={model}>{model}</option>
              ))
            ) : (
              <option value={currentModel}>{currentModel} (server offline)</option>
            )}
          </select>
        </div>
        
        <div>
          <label className="block text-sm text-gray-300 mb-1">Temperature</label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={2}
              step={0.1}
              value={Number(settings.dj_temperature ?? 0.8)}
              onChange={(e) => setSettings({...settings, dj_temperature: parseFloat(e.target.value)})}
              className="flex-1"
            />
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={Number(settings.dj_temperature ?? 0.8)}
              onChange={(e) => setSettings({...settings, dj_temperature: parseFloat(e.target.value)})}
              className="w-20 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        <div>
          <label className="block text-sm text-gray-300 mb-1">Commentary Prompt Template (Ollama/OpenAI)</label>
          <textarea
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm min-h-[160px]"
            placeholder={
              "You're a pirate radio DJ introducing the NEXT song... Use {{song_title}}, {{artist}}, {{album}}, {{year}}."
            }
            value={settings.dj_prompt_template ?? ''}
            onChange={(e) => setSettings({ ...settings, dj_prompt_template: e.target.value })}
          />
          <p className="text-xs text-gray-400 mt-2">
            Used when provider is Ollama or OpenAI. Supports Jinja variables like {`{{song_title}}`}, {`{{artist}}`}, {`{{album}}`}, {`{{year}}`}.
          </p>
        </div>
      </div>
    </div>
  )
}

const TTSMonitor: React.FC = () => {
  const AUTO_REFRESH_INTERVAL_MS = 30000
  const [saving, setSaving] = useState(false)
  const [voices, setVoices] = useState<string[]>([])
  const [chatterboxVoices, setChatterboxVoices] = useState<string[]>([])
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [testText, setTestText] = useState("Welcome to Raido FM! This voice sounds crisp and clear for our pirate radio commentary.")

  // Admin settings state
  const [settings, setSettings] = useState<any | null>(null)
  const [originalSettings, setOriginalSettings] = useState<any | null>(null)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [settingsCollapsed, setSettingsCollapsed] = useState(true)
  const [monitoringCollapsed, setMonitoringCollapsed] = useState(true)
  const compact = true

  // Gating status (interval / next-up visibility)
  const [gating, setGating] = useState<{
    interval: number,
    tracksSince: number,
    nextTrack?: { id?: number, title?: string, artist?: string } | null,
  }>({ interval: 1, tracksSince: 0, nextTrack: null })

  useEffect(() => {
    apiHelpers.getSettings()
      .then(res => {
        setSettings(res.data)
        setOriginalSettings(res.data)
      })
      .catch(() => setSettingsError('Failed to load settings'))
  }, [])

  // Compute simple gating info similar to worker logic: tracks since last commentary vs interval
  useEffect(() => {
    const run = async () => {
      try {
        const interval = Number(settings?.dj_commentary_interval ?? 1)
        // Fetch recent history (interval+1 to be safe)
        const histRes = await apiHelpers.getHistory(interval + 1, 0)
        const tracks = histRes.data?.tracks || []
        let tracksSince = 0
        for (const t of tracks) {
          if (t?.commentary) break
          tracksSince += 1
        }
        // Fetch next-up
        const nextRes = await apiHelpers.getNextUp(1)
        const next = nextRes.data?.next_tracks?.[0]?.track || null
        setGating({ interval, tracksSince, nextTrack: next ? { id: next.id, title: next.title, artist: next.artist } : null })
      } catch {
        // Leave gating as-is on failure
      }
    }
    if (settings) run()
  }, [settings?.dj_commentary_interval, settings?.enable_commentary, settings?.dj_provider])

  // Fetch voices based on selected provider
  useEffect(() => {
    const provider = settings?.dj_voice_provider || 'kokoro'
    const load = async () => {
      try {
        if (provider === 'xtts') {
          const res = await api.get('/admin/voices-xtts')
          setVoices(res.data?.voices || [])
        } else if (provider === 'chatterbox') {
          const res = await api.get('/admin/voices-chatterbox')
          setChatterboxVoices(res.data?.voices || [])
        } else {
          const res = await api.get('/admin/voices')
          setVoices(res.data?.voices || [])
        }
      } catch {
        setVoices([])
        setChatterboxVoices([])
      }
    }
    load()
  }, [settings?.dj_voice_provider, settings?.chatterbox_voices_url])

  // Fetch Ollama models
  useEffect(() => {
    const loadOllamaModels = async () => {
      try {
        const res = await api.get('/admin/ollama-models')
        setOllamaModels(res.data?.models || [])
      } catch {
        setOllamaModels([])
      }
    }
    loadOllamaModels()
  }, [settings?.dj_provider]) // Reload when provider changes

  const hasUnsavedChanges = Boolean(
    settings && originalSettings && JSON.stringify(settings) !== JSON.stringify(originalSettings)
  )

  const saveSettings = async () => {
    if (!settings) return
    setSaving(true)
    setSettingsError(null)
    try {
      await apiHelpers.updateSettings(settings)
      toast.success('Settings saved successfully! 🎛️')
      setOriginalSettings(settings)
    } catch (e: any) {
      const errorMsg = e?.response?.data?.detail || 'Failed to save settings'
      setSettingsError(errorMsg)
      toast.error(`Save failed: ${errorMsg}`)
    } finally {
      setSaving(false)
    }
  }

  const stripTags = (s: string) => s.replace(/<[^>]*>/g, '')

  const getAudioFileName = (audioPath: string | null, fallbackId: number) => {
    if (!audioPath) return `tts-commentary-${fallbackId}.mp3`
    const segments = audioPath.split('/').filter(Boolean)
    const lastSegment = segments[segments.length - 1] || ''
    const cleaned = lastSegment.split('?')[0]
    const sanitized = cleaned.replace(/[^a-zA-Z0-9._-]/g, '_')
    return sanitized || `tts-commentary-${fallbackId}.mp3`
  }

  // Pagination state
  const [currentPage, setCurrentPage] = useState(0)
  const itemsPerPage = 20

  const { data: ttsStatus, isLoading, error, refetch } = useQuery<TTSStatusResponse>({
    queryKey: ['ttsStatus', 'christmas', currentPage],
    queryFn: () => api.get('/admin/tts-status', {
      params: {
        station: 'christmas',
        window_hours: 24,
        limit: itemsPerPage,
        offset: currentPage * itemsPerPage,
      }
    }).then(res => res.data),
    refetchInterval: AUTO_REFRESH_INTERVAL_MS,
    staleTime: 10000,
    keepPreviousData: true,
  })

  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  const deleteCommentary = async (commentaryId: number) => {
    if (!confirm('Delete this TTS entry? This will also remove the audio file.')) return
    
    try {
      await apiHelpers.deleteCommentary(commentaryId)
      refetch()
    } catch (error) {
      console.error('Failed to delete commentary:', error)
    }
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

  const getStatusToneClasses = (status?: string) => {
    switch (status) {
      case 'running':
        return {
          container: 'border-green-600/30 bg-green-900/20 text-green-200',
          badge: 'border-green-500/40 bg-green-500/10 text-green-200',
        }
      case 'warning':
        return {
          container: 'border-yellow-600/30 bg-yellow-900/20 text-yellow-200',
          badge: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200',
        }
      case 'stopped':
        return {
          container: 'border-red-600/30 bg-red-900/20 text-red-200',
          badge: 'border-red-500/40 bg-red-500/10 text-red-200',
        }
      default:
        return {
          container: 'border-gray-600/30 bg-gray-800/30 text-gray-200',
          badge: 'border-gray-500/40 bg-gray-700/40 text-gray-200',
        }
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
  const chatterboxHealth = ttsStatus?.chatterbox_health
  const rawChatterboxStatus = chatterboxHealth?.status || systemStatus?.chatterbox_tts
  const effectiveChatterboxStatus = rawChatterboxStatus || (chatterboxHealth?.detail ? 'unknown' : undefined)
  const chatterboxTone = getStatusToneClasses(effectiveChatterboxStatus)
  const chatterboxMessage = (() => {
    if (!effectiveChatterboxStatus) return ''
    const detail = chatterboxHealth?.detail?.trim()
    if (detail) {
      return detail
    }
    switch (effectiveChatterboxStatus) {
      case 'running':
        return 'Chatterbox TTS is responding normally.'
      case 'warning':
        return 'Chatterbox TTS responded but indicated an issue.'
      case 'stopped':
        return 'Unable to reach Chatterbox TTS. Check the shim container and network.'
      default:
        return 'Chatterbox TTS status is unknown.'
    }
  })()

  return (
    <div className="space-y-6">
      {effectiveChatterboxStatus && (
        <div className={`rounded-2xl border shadow-2xl px-4 py-4 sm:px-6 ${chatterboxTone.container}`}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <span className="text-2xl" aria-hidden>🗣️</span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold uppercase tracking-wide text-gray-300">
                    Chatterbox Service
                  </span>
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold border ${chatterboxTone.badge}`}>
                    <span>{getServiceStatusIcon(effectiveChatterboxStatus)}</span>
                    <span className="capitalize">{effectiveChatterboxStatus}</span>
                  </span>
                </div>
                {chatterboxMessage && (
                  <p className="mt-1 text-sm text-gray-100">
                    {chatterboxMessage}
                  </p>
                )}
                {chatterboxHealth?.endpoint && (
                  <p className="mt-1 text-xs text-gray-300">
                    Endpoint: <span className="text-gray-100">{chatterboxHealth.endpoint}</span>
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-300">
              <span>Tip:</span>
              {chatterboxHealth?.endpoint ? (
                <span className="text-gray-100">
                  Run <code className="bg-gray-800 px-1.5 py-0.5 rounded">curl {chatterboxHealth.endpoint}/health</code> from the host.
                </span>
              ) : (
                <span className="text-gray-100">
                  Set the Chatterbox base URL under Voice &amp; TTS settings.
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Settings Panel */}
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-6 shadow-2xl border border-gray-700/50">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => setSettingsCollapsed(!settingsCollapsed)}
            className="flex items-center gap-3 text-2xl font-bold text-white hover:text-pirate-400 transition-colors"
          >
            <span className={`transform transition-transform ${settingsCollapsed ? 'rotate-0' : 'rotate-90'}`}>▶</span>
            <span>🎛️ DJ Settings</span>
          </button>
          <div className="flex items-center gap-3">
            {hasUnsavedChanges && (
              <span className="text-xs px-2 py-1 rounded bg-yellow-500/10 text-yellow-300 border border-yellow-500/20">Unsaved changes</span>
            )}
            <button
              onClick={saveSettings}
              disabled={!settings || saving || !hasUnsavedChanges}
              className={`px-4 py-2 rounded-lg text-white font-medium ${
                saving || !hasUnsavedChanges ? 'bg-gray-700 cursor-not-allowed' : 'bg-pirate-600 hover:bg-pirate-700'
              } transition-colors`}
            >
              {saving ? 'Saving…' : 'Save Settings'}
            </button>
          </div>
        </div>

        {/* Generation status banner */}
        {!settingsCollapsed && settings && (
          <div className="mb-4">
            {(!settings.enable_commentary || settings.dj_provider === 'disabled') ? (
              <div className="px-3 py-2 rounded border border-red-600/30 bg-red-900/20 text-red-300 text-sm">
                Commentary is currently disabled. Enable it and pick a provider to resume generation.
              </div>
            ) : (
              <>
                {gating.tracksSince < (gating.interval || 1) ? (
                  <div className="px-3 py-2 rounded border border-yellow-600/30 bg-yellow-900/20 text-yellow-200 text-sm">
                    Waiting for interval: {gating.tracksSince} of {gating.interval} tracks since last commentary. Generation will trigger once the interval is reached.
                  </div>
                ) : (
                  <div className="px-3 py-2 rounded border border-green-600/30 bg-green-900/20 text-green-200 text-sm">
                    Eligible to generate on the next cycle.
                  </div>
                )}
                <div className="mt-2 text-xs text-gray-400">
                  Tip: If the next-up track already had an intro in the last hour, deduplication may skip generating again. You can skip the current track or restart the DJ worker to force a new intro.
                  {gating.nextTrack && (
                    <span className="ml-2 text-gray-300">Next up: {gating.nextTrack.artist} — {gating.nextTrack.title}</span>
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {settingsError && !settingsCollapsed && (
          <div className="text-red-400 text-sm mb-4 p-3 bg-red-900/20 rounded-lg border border-red-600/20">
            {settingsError}
          </div>
        )}

        {!settingsCollapsed && settings && (
          <div className="space-y-8">
            {/* General Settings */}
            <GeneralSettingsSection settings={settings} setSettings={setSettings} />
            
            {/* Voice Provider Settings */}
            <VoiceProviderSection 
              settings={settings} 
              setSettings={setSettings}
              voices={voices}
              chatterboxVoices={chatterboxVoices}
            />
            
            {/* AI Model Settings - only show if using Ollama */}
            {settings.dj_provider === 'ollama' && (
              <AIModelSection
                settings={settings}
                setSettings={setSettings}
                ollamaModels={ollamaModels}
              />
            )}
            
            {/* Voice Testing */}
            <VoiceTestSection 
              settings={settings}
              testText={testText}
              setTestText={setTestText}
            />
          </div>
        )}
      </div>

      {/* Monitoring Header (collapsible) */}
      <div className="bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl p-4 shadow-2xl border border-gray-700/50">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setMonitoringCollapsed(!monitoringCollapsed)}
            className="flex items-center gap-3 text-xl font-bold text-white hover:text-pirate-400 transition-colors"
            aria-expanded={!monitoringCollapsed}
          >
            <span className={`transform transition-transform ${monitoringCollapsed ? 'rotate-0' : 'rotate-90'}`}>▶</span>
            <span>🎙️ TTS Monitoring Dashboard</span>
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      {!monitoringCollapsed && (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className={`bg-gradient-to-br from-green-900/40 to-green-800/40 rounded-xl ${compact ? 'p-3' : 'p-6'} border border-green-600/20`}>
          <div className="flex items-center gap-3 mb-2">
            <div className={`${compact ? 'w-8 h-8' : 'w-10 h-10'} rounded-full bg-green-600 flex items-center justify-center`}>
              <span className={`${compact ? 'text-lg' : 'text-xl'}`}>✅</span>
            </div>
            <div>
              <h3 className="font-semibold text-green-300">Success Rate</h3>
              <p className={`${compact ? 'text-xl' : 'text-2xl'} font-bold text-white`}>{stats?.success_rate || 0}%</p>
            </div>
          </div>
          <p className="text-sm text-green-400">
            {stats?.success_24h || 0} of {stats?.total_24h || 0} in 24h
          </p>
        </div>

        <div className={`bg-gradient-to-br from-blue-900/40 to-blue-800/40 rounded-xl ${compact ? 'p-3' : 'p-6'} border border-blue-600/20`}>
          <div className="flex items-center gap-3 mb-2">
            <div className={`${compact ? 'w-8 h-8' : 'w-10 h-10'} rounded-full bg-blue-600 flex items-center justify-center`}>
              <span className={`${compact ? 'text-lg' : 'text-xl'}`}>🎵</span>
            </div>
            <div>
              <h3 className="font-semibold text-blue-300">Total Generated</h3>
              <p className={`${compact ? 'text-xl' : 'text-2xl'} font-bold text-white`}>{stats?.total_24h || 0}</p>
            </div>
          </div>
          <p className="text-sm text-blue-400">Last 24 hours</p>
        </div>

        <div className={`bg-gradient-to-br from-purple-900/40 to-purple-800/40 rounded-xl ${compact ? 'p-3' : 'p-6'} border border-purple-600/20`}>
          <div className="flex items-center gap-3 mb-2">
            <div className={`${compact ? 'w-8 h-8' : 'w-10 h-10'} rounded-full bg-purple-600 flex items-center justify-center`}>
              <span className={`${compact ? 'text-lg' : 'text-xl'}`}>⚡</span>
            </div>
            <div>
              <h3 className="font-semibold text-purple-300">Avg Gen Time</h3>
              <p className={`${compact ? 'text-xl' : 'text-2xl'} font-bold text-white`}>
                {formatDuration(stats?.avg_generation_time_ms || null)}
              </p>
            </div>
          </div>
          <p className="text-sm text-purple-400">Generation speed</p>
        </div>

        <div className={`bg-gradient-to-br from-orange-900/40 to-orange-800/40 rounded-xl ${compact ? 'p-3' : 'p-6'} border border-orange-600/20`}>
          <div className="flex items-center gap-3 mb-2">
            <div className={`${compact ? 'w-8 h-8' : 'w-10 h-10'} rounded-full bg-orange-600 flex items-center justify-center`}>
              <span className={`${compact ? 'text-lg' : 'text-xl'}`}>🔊</span>
            </div>
            <div>
              <h3 className="font-semibold text-orange-300">Avg TTS Time</h3>
              <p className={`${compact ? 'text-xl' : 'text-2xl'} font-bold text-white`}>
                {formatDuration(stats?.avg_tts_time_ms || null)}
              </p>
            </div>
          </div>
          <p className="text-sm text-orange-400">Voice synthesis</p>
        </div>
      </div>
      )}

      {/* System Status */}
      {systemStatus && !monitoringCollapsed && (
        <div className={`bg-gray-900/60 border border-gray-800/60 rounded-xl ${compact ? 'p-3' : 'p-4'} shadow-inner`}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-300">
            <span className="text-sm">⚙️</span>
            System Status
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/70 border border-gray-700/60 rounded-full text-xs">
              <span className="text-base">{getServiceStatusIcon(systemStatus.tts_service)}</span>
              <span className="text-gray-200">TTS Service</span>
              <span className={`font-semibold capitalize ${getStatusColor(systemStatus.tts_service)}`}>
                {systemStatus.tts_service}
              </span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/70 border border-gray-700/60 rounded-full text-xs">
              <span className="text-base">{getServiceStatusIcon(systemStatus.dj_worker)}</span>
              <span className="text-gray-200">DJ Worker</span>
              <span className={`font-semibold capitalize ${getStatusColor(systemStatus.dj_worker)}`}>
                {systemStatus.dj_worker}
              </span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/70 border border-gray-700/60 rounded-full text-xs">
              <span className="text-base">{getServiceStatusIcon(systemStatus.kokoro_tts)}</span>
              <span className="text-gray-200">Kokoro TTS</span>
              <span className={`font-semibold capitalize ${getStatusColor(systemStatus.kokoro_tts)}`}>
                {systemStatus.kokoro_tts}
              </span>
            </div>

            {systemStatus.chatterbox_tts && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/70 border border-gray-700/60 rounded-full text-xs">
                <span className="text-base">{getServiceStatusIcon(systemStatus.chatterbox_tts)}</span>
                <span className="text-gray-200">Chatterbox</span>
                <span className={`font-semibold capitalize ${getStatusColor(systemStatus.chatterbox_tts)}`}>
                  {systemStatus.chatterbox_tts}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {!monitoringCollapsed && (
      <div className={`bg-gradient-to-br from-gray-800 via-gray-900 to-pirate-900 rounded-2xl ${compact ? 'p-4' : 'p-6'} shadow-2xl border border-gray-700/50`}>
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <span>📋</span>
          Recent TTS Activity
        </h3>

        {activity.length === 0 ? (
          <div className="text-center text-gray-400 py-8">
            <p>No recent TTS activity</p>
          </div>
        ) : (
          <div className={`space-y-${compact ? '2' : '3'}`}> 
            {activity.map((item) => {
              const audioSrc = apiHelpers.resolveStaticUrl(item.audio_url)
              const downloadFileName = getAudioFileName(item.audio_url, item.id)

              return (
                <div
                  key={item.id}
                  className={`flex items-start ${compact ? 'gap-3 p-2' : 'gap-4 p-4'} bg-gray-800/30 rounded-lg border border-gray-700/20`}
                >
                  {item.status === 'running' ? (
                    <span
                      className="mt-1.5 inline-block w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"
                      aria-label="Generating"
                      title="Generating"
                    />
                  ) : (
                    <div className={`w-3 h-3 rounded-full mt-2 ${
                      item.status === 'ready' ? 'bg-green-400' :
                      item.status === 'failed' ? 'bg-red-400' :
                      'bg-yellow-400'
                    }`}></div>
                  )}
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0 pr-2">
                        <h4 className="font-medium text-white whitespace-pre-wrap break-words">
                          {item.transcript ? item.transcript : stripTags(item.text)}
                        </h4>
                        <p className="text-sm text-gray-400 flex items-center gap-2 flex-wrap">
                          <span>{item.provider} • {item.voice_provider}</span>
                          {item.voice_id ? <span>• voice: {item.voice_id}</span> : null}
                          {item.provider === 'ollama' && item.llm_mode === 'nonstream' && (
                            <span className="text-xxs px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-300 border border-yellow-500/20">
                              non‑streaming fallback
                            </span>
                          )}
                        </p>
                      </div>
                      <div className="flex items-start gap-2 flex-shrink-0">
                        <div className="text-right text-sm text-gray-400">
                          <div>{new Date(item.created_at).toLocaleTimeString()}</div>
                          {(item.generation_time_ms || item.tts_time_ms) && (
                            <div className="text-xs">
                              {item.generation_time_ms && `Gen: ${formatDuration(item.generation_time_ms)}`}
                              {item.generation_time_ms && item.tts_time_ms && ' • '}
                              {item.tts_time_ms && `TTS: ${formatDuration(item.tts_time_ms)}`}
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => deleteCommentary(item.id)}
                          className="text-red-400 hover:text-red-300 p-1 rounded transition-colors"
                          title="Delete TTS entry"
                        >
                          <span className="text-sm">🗑️</span>
                        </button>
                      </div>
                    </div>
                    
                    {audioSrc && (
                      <div className="mt-2 space-y-2">
                        <audio 
                          controls 
                          className={`w-full ${compact ? 'h-6' : 'h-8'}`}
                          preload="metadata"
                        >
                          <source src={audioSrc} type="audio/mpeg" />
                          Your browser does not support audio playback.
                        </audio>
                        <div className="flex items-center justify-between gap-2 text-xs text-gray-400">
                          <span className="truncate" title={downloadFileName}>{downloadFileName}</span>
                          <a
                            href={audioSrc}
                            download={downloadFileName}
                            className="inline-flex items-center gap-1 text-sm text-pirate-300 hover:text-pirate-200"
                          >
                            <span aria-hidden="true">⬇️</span>
                            <span>Download</span>
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {/* Pagination Controls */}
            {ttsStatus?.pagination && ttsStatus.pagination.total > itemsPerPage && (
              <div className="flex items-center justify-between pt-4 mt-4 border-t border-gray-700/50">
                <div className="text-sm text-gray-400">
                  Showing {ttsStatus.pagination.offset + 1}-{Math.min(ttsStatus.pagination.offset + activity.length, ttsStatus.pagination.total)} of {ttsStatus.pagination.total}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                    disabled={currentPage === 0}
                    className="px-3 py-1 bg-gray-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
                  >
                    Previous
                  </button>

                  <span className="px-3 py-1 text-gray-300">
                    Page {currentPage + 1} of {Math.ceil(ttsStatus.pagination.total / itemsPerPage)}
                  </span>

                  <button
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={!ttsStatus.pagination.has_more}
                    className="px-3 py-1 bg-gray-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      )}
    </div>
  )
}

export default TTSMonitor
