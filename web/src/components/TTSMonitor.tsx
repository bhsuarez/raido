import React, { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api, { apiHelpers } from '../utils/api'
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
}

interface TTSStatusResponse {
  status: string
  statistics: TTSStatistics
  recent_activity: TTSActivity[]
  system_status: SystemStatus
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
        case 'openai_tts':
          endpoint = '/admin/tts-test-openai'
          payload.voice = settings.openai_tts_voice || 'onyx'
          payload.model = settings.openai_tts_model || 'tts-1'
          break
          
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
      
      const res = await api.post(endpoint, payload)
      const url = res.data?.audio_url
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
      case 'openai_tts': return settings?.openai_tts_voice || 'onyx'
      case 'chatterbox': return settings?.chatterbox_voice || 'default'
      case 'xtts': return settings?.xtts_voice || 'coqui-tts:en_ljspeech'
      default: return settings?.kokoro_voice || 'af_bella'
    }
  }

  const getProviderDisplayName = () => {
    const provider = settings?.dj_voice_provider || 'kokoro'
    switch (provider) {
      case 'openai_tts': return 'OpenAI TTS'
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
          value={settings.dj_provider || 'ollama'}
          onChange={(e) => setSettings({...settings, dj_provider: e.target.value})}
        >
          <option value="ollama">Ollama</option>
          <option value="openai">OpenAI</option>
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
      case 'openai_tts':
        return ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
      case 'chatterbox':
        return chatterboxVoices.length ? chatterboxVoices : ['default', 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
      case 'xtts':
        return voices.length ? voices : []
      default: // kokoro
        return voices.length ? voices : [
          'af_bella', 'af_sarah', 'af_sky', 'am_onyx', 'am_michael', 'am_ryan', 
          'bf_ava', 'bf_sophie', 'bm_george', 'bm_james'
        ]
    }
  }

  const getVoiceFieldName = () => {
    switch (provider) {
      case 'openai_tts': return 'openai_tts_voice'
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
            <option value="openai_tts">OpenAI TTS</option>
            <option value="chatterbox">Chatterbox</option>
            <option value="xtts">XTTS</option>
            <option value="liquidsoap">Liquidsoap</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm text-gray-300 mb-1">
            {provider === 'openai_tts' ? 'OpenAI Voice' : 
             provider === 'chatterbox' ? 'Chatterbox Voice' :
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
              <option key={voice} value={voice}>{voice}</option>
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

const AIModelSection: React.FC<{ settings: any, setSettings: (s: any) => void }> = ({ settings, setSettings }) => {
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
            <optgroup label="🚀 Fast Models">
              <option value="llama3.2:1b">Llama 3.2 1B (Fastest)</option>
              <option value="llama3.2:3b">Llama 3.2 3B (Good Quality)</option>
              <option value="qwen2.5:3b">Qwen2.5 3B (Creative)</option>
            </optgroup>
            <optgroup label="⚡ Balanced Models">
              <option value="llama3.1:8b">Llama 3.1 8B</option>
              <option value="qwen2.5:7b">Qwen2.5 7B</option>
              <option value="mistral:7b">Mistral 7B</option>
            </optgroup>
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
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [saving, setSaving] = useState(false)
  const [voices, setVoices] = useState<string[]>([])
  const [chatterboxVoices, setChatterboxVoices] = useState<string[]>([])
  const [testText, setTestText] = useState("Welcome to Raido FM! This voice sounds crisp and clear for our pirate radio commentary.")

  // Admin settings state
  const [settings, setSettings] = useState<any | null>(null)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [settingsCollapsed, setSettingsCollapsed] = useState(false)

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
  }, [settings?.dj_voice_provider])

  const saveSettings = async () => {
    if (!settings) return
    setSaving(true)
    setSettingsError(null)
    try {
      await apiHelpers.updateSettings(settings)
      toast.success('Settings saved successfully! 🎛️')
    } catch (e: any) {
      const errorMsg = e?.response?.data?.detail || 'Failed to save settings'
      setSettingsError(errorMsg)
      toast.error(`Save failed: ${errorMsg}`)
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
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => setSettingsCollapsed(!settingsCollapsed)}
            className="flex items-center gap-3 text-2xl font-bold text-white hover:text-pirate-400 transition-colors"
          >
            <span className={`transform transition-transform ${settingsCollapsed ? 'rotate-0' : 'rotate-90'}`}>▶</span>
            <span>🎛️ DJ Settings</span>
          </button>
          <button
            onClick={saveSettings}
            disabled={!settings || saving}
            className={`px-4 py-2 rounded-lg text-white font-medium ${
              saving ? 'bg-gray-700' : 'bg-pirate-600 hover:bg-pirate-700'
            } transition-colors`}
          >
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
        </div>

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
              <AIModelSection settings={settings} setSettings={setSettings} />
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
                    <div className="flex-1 min-w-0 pr-2">
                      <h4 className="font-medium text-white whitespace-pre-wrap break-words">
                        {item.transcript ? item.transcript : stripTags(item.text)}
                      </h4>
                      <p className="text-sm text-gray-400">
                        {item.provider} • {item.voice_provider}
                        {item.voice_id ? ` • voice: ${item.voice_id}` : ''}
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
