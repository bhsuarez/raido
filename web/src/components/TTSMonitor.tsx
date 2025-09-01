import React, { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api, { apiHelpers } from '../utils/api'
import LoadingSpinner from './LoadingSpinner'
import { toast } from 'react-hot-toast'
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

const TTSMonitor: React.FC = () => {
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [saving, setSaving] = useState(false)
  const [voices, setVoices] = useState<string[]>([])
  const [xttsVoicesMap, setXttsVoicesMap] = useState<Record<string, any>>({})
  const [showAllXttsVoices, setShowAllXttsVoices] = useState(false)
  const [testUrl, setTestUrl] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [chatterboxVoices, setChatterboxVoices] = useState<string[]>([])
  const [testText, setTestText] = useState("Welcome to Raido FM! This voice sounds crisp and clear for our pirate radio commentary.")

  // Admin settings state
  const [settings, setSettings] = useState<any | null>(null)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [settingsCollapsed, setSettingsCollapsed] = useState(true)

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
          setXttsVoicesMap((res.data?.voices_map && typeof res.data.voices_map === 'object') ? res.data.voices_map : {})
        } else if (provider === 'chatterbox') {
          const res = await api.get('/admin/voices-chatterbox')
          const vs = res.data?.voices
          if (Array.isArray(vs)) setChatterboxVoices(vs)
          else setChatterboxVoices([])
          setVoices([])
          setXttsVoicesMap({})
        } else {
          const res = await api.get('/admin/voices')
          const vs = res.data?.voices
          if (Array.isArray(vs)) setVoices(vs)
          else setVoices([])
          setXttsVoicesMap({})
          setChatterboxVoices([])
        }
      } catch {
        setVoices([])
        setXttsVoicesMap({})
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
    } catch (e:any) {
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
      refetch() // Refresh the list after deletion
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
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => setSettingsCollapsed(!settingsCollapsed)}
            className="flex items-center gap-2 text-xl font-bold text-white hover:text-pirate-400 transition-colors"
          >
            <span className={`transform transition-transform ${settingsCollapsed ? 'rotate-0' : 'rotate-90'}`}>▶</span>
            <span>⚙️ DJ Settings</span>
            <span className="text-sm font-normal text-gray-400">({settingsCollapsed ? 'Click to expand' : 'Click to collapse'})</span>
          </button>
          <button
            onClick={saveSettings}
            disabled={!settings || saving}
            className={`px-3 py-2 rounded-lg text-white text-sm ${saving ? 'bg-gray-700' : 'bg-pirate-600 hover:bg-pirate-700'} transition-colors`}
          >{saving ? 'Saving…' : 'Save Settings'}</button>
        </div>
        {settingsError && !settingsCollapsed && (
          <div className="text-red-400 text-sm mb-3">{settingsError}</div>
        )}
        {!settingsCollapsed && (
          settings ? (
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
                <option value="chatterbox">Chatterbox</option>
              </select>
            </div>
            {/* Voice selection (switches between Kokoro, XTTS, and Chatterbox) */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">
                {settings.dj_voice_provider === 'xtts' ? 'XTTS Voice' : 
                 settings.dj_voice_provider === 'chatterbox' ? 'Chatterbox Voice' : 'Kokoro Voice'}
              </label>
              {(() => {
                let list = []
                if (settings.dj_voice_provider === 'chatterbox') {
                  list = chatterboxVoices.length ? chatterboxVoices : [
                    'default', 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'
                  ]
                } else if (settings.dj_voice_provider === 'xtts') {
                  list = voices.length ? voices : []
                  // For XTTS: filter to only show available downloaded models unless user opts to show all
                  if (!showAllXttsVoices) {
                    const availableModels = ['coqui-tts:en_ljspeech', 'coqui-tts:en_vctk']
                    list = list.filter(v => availableModels.includes(v))
                  }
                } else {
                  list = voices.length ? voices : [
                    // American Female voices
                    'af_bella', 'af_sarah', 'af_sky', 'af_aria', 'af_grace', 'af_nicole', 
                    'af_jenny', 'af_emma', 'af_allison', 'af_riley', 'af_samantha',
                    
                    // American Male voices  
                    'am_onyx', 'am_michael', 'am_ryan', 'am_alex', 'am_eric', 'am_adam', 
                    'am_daniel', 'am_noah', 'am_liam', 'am_mason', 'am_jacob',
                    
                    // British Female voices
                    'bf_ava', 'bf_sophie', 'bf_emma', 'bf_lily', 'bf_alice', 'bf_chloe',
                    'bf_olivia', 'bf_amelia', 'bf_isabella', 'bf_charlotte',
                    
                    // British Male voices
                    'bm_george', 'bm_james', 'bm_william', 'bm_oliver', 'bm_harry',
                    'bm_thomas', 'bm_charlie', 'bm_jacob', 'bm_alexander', 'bm_henry'
                  ]
                }
                
                const field = settings.dj_voice_provider === 'xtts' ? 'xtts_voice' : 
                             settings.dj_voice_provider === 'chatterbox' ? 'chatterbox_voice' : 'kokoro_voice'
                const current = settings[field] || ''
                const isCustom = current && !list.includes(current)
                const value = isCustom ? 'custom' : (current || (list[0] || ''))
                return (
                  <div className="space-y-2">
                    {settings.dj_voice_provider === 'xtts' && (
                      <label className="flex items-center gap-2 text-xs text-gray-400">
                        <input type="checkbox" className="rounded border-gray-600" checked={showAllXttsVoices} onChange={(e)=>setShowAllXttsVoices(e.target.checked)} />
                        Show all XTTS voices (includes espeak/festival/larynx/etc.)
                      </label>
                    )}
                    <select
                      className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                      value={value}
                      onChange={(e)=>{
                        const v = e.target.value
                        if (v === 'custom') return
                        setSettings({...settings, [field]: v})
                      }}
                    >
                      {settings.dj_voice_provider === 'kokoro' && !voices.length ? (
                        <>
                          <optgroup label="👩🏻 American Female">
                            <option value="af_bella">af_bella (Warm, Natural)</option>
                            <option value="af_sarah">af_sarah (Clear, Professional)</option>
                            <option value="af_sky">af_sky (Bright, Energetic)</option>
                            <option value="af_aria">af_aria (Smooth, Elegant)</option>
                            <option value="af_grace">af_grace (Gentle, Soothing)</option>
                            <option value="af_nicole">af_nicole (Confident, Clear)</option>
                            <option value="af_jenny">af_jenny (Friendly, Upbeat)</option>
                            <option value="af_emma">af_emma (Youthful, Bright)</option>
                            <option value="af_allison">af_allison (Professional)</option>
                            <option value="af_riley">af_riley (Dynamic, Modern)</option>
                            <option value="af_samantha">af_samantha (Versatile)</option>
                          </optgroup>
                          <optgroup label="👨🏻 American Male">
                            <option value="am_onyx">am_onyx (Deep, Authoritative)</option>
                            <option value="am_michael">am_michael (Classic, Trustworthy)</option>
                            <option value="am_ryan">am_ryan (Casual, Friendly)</option>
                            <option value="am_alex">am_alex (Versatile, Clear)</option>
                            <option value="am_eric">am_eric (Mature, Professional)</option>
                            <option value="am_adam">am_adam (Warm, Engaging)</option>
                            <option value="am_daniel">am_daniel (Smooth, Confident)</option>
                            <option value="am_noah">am_noah (Young, Energetic)</option>
                            <option value="am_liam">am_liam (Modern, Dynamic)</option>
                            <option value="am_mason">am_mason (Strong, Clear)</option>
                            <option value="am_jacob">am_jacob (Reliable, Steady)</option>
                          </optgroup>
                          <optgroup label="👩🏼 British Female">
                            <option value="bf_ava">bf_ava (Elegant, Sophisticated)</option>
                            <option value="bf_sophie">bf_sophie (Refined, Articulate)</option>
                            <option value="bf_emma">bf_emma (Charming, Polished)</option>
                            <option value="bf_lily">bf_lily (Sweet, Melodic)</option>
                            <option value="bf_alice">bf_alice (Classic, Distinguished)</option>
                            <option value="bf_chloe">bf_chloe (Modern, Crisp)</option>
                            <option value="bf_olivia">bf_olivia (Graceful, Clear)</option>
                            <option value="bf_amelia">bf_amelia (Gentle, Refined)</option>
                            <option value="bf_isabella">bf_isabella (Luxurious)</option>
                            <option value="bf_charlotte">bf_charlotte (Sophisticated)</option>
                          </optgroup>
                          <optgroup label="👨🏼 British Male">
                            <option value="bm_george">bm_george (Distinguished, Authoritative)</option>
                            <option value="bm_james">bm_james (Classic, Professional)</option>
                            <option value="bm_william">bm_william (Noble, Articulate)</option>
                            <option value="bm_oliver">bm_oliver (Modern, Engaging)</option>
                            <option value="bm_harry">bm_harry (Friendly, Approachable)</option>
                            <option value="bm_thomas">bm_thomas (Reliable, Clear)</option>
                            <option value="bm_charlie">bm_charlie (Upbeat, Charismatic)</option>
                            <option value="bm_jacob">bm_jacob (Steady, Trustworthy)</option>
                            <option value="bm_alexander">bm_alexander (Commanding)</option>
                            <option value="bm_henry">bm_henry (Warm, Distinguished)</option>
                          </optgroup>
                        </>
                      ) : (
                        list.map(v => <option key={v} value={v}>{v}</option>)
                      )}
                      <option value="custom">Custom…</option>
                    </select>
                    {(isCustom || (current==='')) && (
                      <input
                        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                        value={current}
                        onChange={(e)=>setSettings({...settings, [field]: e.target.value})}
                        placeholder={settings.dj_voice_provider === 'xtts' ? 'Enter XTTS voice id' : 
                                   settings.dj_voice_provider === 'chatterbox' ? 'Enter Chatterbox voice id' : 'Enter Kokoro voice id'}
                      />
                    )}
                    {settings.dj_voice_provider === 'xtts' && (() => {
                      const meta = xttsVoicesMap[current]
                      const speakers = meta && typeof meta === 'object' ? meta.speakers : null
                      const speakerNames = speakers && typeof speakers === 'object' ? Object.keys(speakers) : []
                      if (!speakerNames.length) return null
                      const currentSpeaker = settings.xtts_speaker || ''
                      const speakerValue = currentSpeaker && speakerNames.includes(currentSpeaker) ? currentSpeaker : speakerNames[0]
                      return (
                        <div className="space-y-1">
                          <label className="block text-xs text-gray-400">XTTS Speaker</label>
                          <select
                            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                            value={speakerValue}
                            onChange={(e)=>setSettings({...settings, xtts_speaker: e.target.value})}
                          >
                            {speakerNames.map(n => <option key={n} value={n}>{n}</option>)}
                          </select>
                        </div>
                      )
                    })()}
                  </div>
                )
              })()}
              {settings.dj_voice_provider === 'chatterbox' && (
                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={async ()=>{
                      if (!settings) return
                      setTesting(true)
                      setTestUrl(null)
                      try {
                        const sample = `Welcome to Raido. Testing Chatterbox voice ${settings.chatterbox_voice || 'default'}.`
                        const res = await api.post('/admin/tts-test-chatterbox', {
                          text: sample,
                          voice: settings.chatterbox_voice,
                          exaggeration: settings.chatterbox_exaggeration,
                          cfg_weight: settings.chatterbox_cfg_weight,
                        })
                        const url = res.data?.audio_url
                        if (url) setTestUrl(url)
                      } catch (e) {
                        setSettingsError('Chatterbox TTS test failed')
                      } finally {
                        setTesting(false)
                      }
                    }}
                    disabled={testing}
                    className={`px-3 py-2 rounded-lg text-white text-sm ${testing ? 'bg-gray-700' : 'bg-pirate-600 hover:bg-pirate-700'} transition-colors`}
                  >{testing ? 'Testing…' : 'Test Chatterbox Voice'}</button>
                  {testUrl && (
                    <audio controls className="h-8">
                      <source src={testUrl} type="audio/mpeg" />
                    </audio>
                  )}
                </div>
              )}
              {(settings.dj_voice_provider !== 'xtts' && settings.dj_voice_provider !== 'chatterbox') && (
                <div className="mt-3 space-y-3">
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
                    onClick={async ()=>{
                      if (!settings) return
                      setTesting(true)
                      setTestUrl(null)
                      try {
                        const res = await api.post('/admin/tts-test', {
                          text: testText,
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
            {/* Kokoro Silence Duration */}
            {(settings.dj_voice_provider === 'kokoro' || !settings.dj_voice_provider) && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">Kokoro Silence Duration</label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0.0}
                    max={2.0}
                    step={0.1}
                    value={Number(settings.kokoro_silence ?? 0.2)}
                    onChange={(e)=>setSettings({...settings, kokoro_silence: parseFloat(e.target.value)})}
                    className="flex-1"
                  />
                  <input
                    type="number"
                    min={0.0}
                    max={2.0}
                    step={0.1}
                    value={Number(settings.kokoro_silence ?? 0.2)}
                    onChange={(e)=>setSettings({...settings, kokoro_silence: parseFloat(e.target.value)})}
                    className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">Pause duration between sentences (0-2s). Higher = more natural pauses.</p>
              </div>
            )}
            {/* Kokoro Emotional Tone */}
            {(settings.dj_voice_provider === 'kokoro' || !settings.dj_voice_provider) && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">Kokoro Emotional Style</label>
                <select
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  value={settings.kokoro_style || 'neutral'}
                  onChange={(e)=>setSettings({...settings, kokoro_style: e.target.value})}
                >
                  <option value="neutral">Neutral (Default)</option>
                  <option value="excited">Excited/Energetic</option>
                  <option value="calm">Calm/Relaxed</option>
                  <option value="warm">Warm/Friendly</option>
                  <option value="professional">Professional</option>
                  <option value="casual">Casual/Conversational</option>
                </select>
                <p className="text-xs text-gray-400 mt-1">Emotional tone hint for voice generation (experimental).</p>
              </div>
            )}
            {/* Kokoro Pitch */}
            {(settings.dj_voice_provider === 'kokoro' || !settings.dj_voice_provider) && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">Kokoro Pitch Adjustment</label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0.8}
                    max={1.2}
                    step={0.05}
                    value={Number(settings.kokoro_pitch ?? 1.0)}
                    onChange={(e)=>setSettings({...settings, kokoro_pitch: parseFloat(e.target.value)})}
                    className="flex-1"
                  />
                  <input
                    type="number"
                    min={0.8}
                    max={1.2}
                    step={0.05}
                    value={Number(settings.kokoro_pitch ?? 1.0)}
                    onChange={(e)=>setSettings({...settings, kokoro_pitch: parseFloat(e.target.value)})}
                    className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">Pitch multiplier (0.8×-1.2×). 1.0 = natural, higher = higher pitch.</p>
              </div>
            )}
            {/* Chatterbox Exaggeration */}
            {settings.dj_voice_provider === 'chatterbox' && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">Chatterbox Exaggeration</label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0.25}
                    max={2.0}
                    step={0.05}
                    value={Number(settings.chatterbox_exaggeration ?? 1.0)}
                    onChange={(e)=>setSettings({...settings, chatterbox_exaggeration: parseFloat(e.target.value)})}
                    className="flex-1"
                  />
                  <input
                    type="number"
                    min={0.25}
                    max={2.0}
                    step={0.05}
                    value={Number(settings.chatterbox_exaggeration ?? 1.0)}
                    onChange={(e)=>setSettings({...settings, chatterbox_exaggeration: parseFloat(e.target.value)})}
                    className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">Emotion intensity (0.25×–2.0×). Higher = more expressive.</p>
              </div>
            )}
            {/* Chatterbox CFG Weight */}
            {settings.dj_voice_provider === 'chatterbox' && (
              <div>
                <label className="block text-sm text-gray-300 mb-1">Chatterbox CFG Weight</label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min={0.0}
                    max={1.0}
                    step={0.05}
                    value={Number(settings.chatterbox_cfg_weight ?? 0.5)}
                    onChange={(e)=>setSettings({...settings, chatterbox_cfg_weight: parseFloat(e.target.value)})}
                    className="flex-1"
                  />
                  <input
                    type="number"
                    min={0.0}
                    max={1.0}
                    step={0.05}
                    value={Number(settings.chatterbox_cfg_weight ?? 0.5)}
                    onChange={(e)=>setSettings({...settings, chatterbox_cfg_weight: parseFloat(e.target.value)})}
                    className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  />
                </div>
                <p className="text-xs text-gray-400 mt-1">Pace control (0.0–1.0). Higher = slower, more deliberate.</p>
              </div>
            )}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Ollama Model</label>
              <div className="space-y-2">
                <select
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                  value={settings.ollama_model || ''}
                  onChange={(e)=>setSettings({...settings, ollama_model: e.target.value})}
                >
                  <option value="">Select a model...</option>
                  
                  {/* Popular Chat Models */}
                  <optgroup label="🗣️ Chat Models (Recommended)">
                    <option value="llama3.2:3b">Llama 3.2 3B (Fast, Good Quality)</option>
                    <option value="llama3.2:1b">Llama 3.2 1B (Fastest, Basic Quality)</option>
                    <option value="llama3.1:8b">Llama 3.1 8B (Balanced)</option>
                    <option value="llama3.1:70b">Llama 3.1 70B (Best Quality, Slow)</option>
                    <option value="qwen2.5:3b">Qwen2.5 3B (Fast, Creative)</option>
                    <option value="qwen2.5:7b">Qwen2.5 7B (Good Balance)</option>
                    <option value="qwen2.5:14b">Qwen2.5 14B (High Quality)</option>
                    <option value="gemma2:2b">Gemma2 2B (Efficient)</option>
                    <option value="gemma2:9b">Gemma2 9B (Quality)</option>
                    <option value="phi3:3.8b">Phi3 3.8B (Creative)</option>
                    <option value="mistral:7b">Mistral 7B (Classic)</option>
                    <option value="mixtral:8x7b">Mixtral 8x7B (Expert Mix)</option>
                  </optgroup>
                  
                  {/* Specialized Models */}
                  <optgroup label="🎯 Specialized Models">
                    <option value="dolphin-mixtral:8x7b">Dolphin Mixtral (Uncensored)</option>
                    <option value="neural-chat:7b">Neural Chat 7B (Conversational)</option>
                    <option value="deepseek-coder:6.7b">DeepSeek Coder (Technical)</option>
                    <option value="wizardcoder:7b">WizardCoder 7B (Programming)</option>
                    <option value="orca-mini:3b">Orca Mini 3B (Efficient Chat)</option>
                    <option value="vicuna:7b">Vicuna 7B (Assistant)</option>
                    <option value="starling-lm:7b">Starling LM 7B (Helpful)</option>
                  </optgroup>
                  
                  {/* Small/Fast Models */}
                  <optgroup label="⚡ Fast Models (Good for Radio)">
                    <option value="tinyllama:1.1b">TinyLlama 1.1B (Ultra Fast)</option>
                    <option value="qwen2:0.5b">Qwen2 0.5B (Lightning Fast)</option>
                    <option value="stablelm2:1.6b">StableLM2 1.6B (Stable, Fast)</option>
                    <option value="phi3.5:3.8b">Phi3.5 3.8B (Microsoft, Creative)</option>
                  </optgroup>
                  
                  <option value="custom">Custom Model...</option>
                </select>
                
                {(!settings.ollama_model || settings.ollama_model === 'custom') && (
                  <input
                    className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                    value={settings.ollama_model === 'custom' ? '' : (settings.ollama_model || '')}
                    onChange={(e)=>setSettings({...settings, ollama_model: e.target.value})}
                    placeholder="Enter custom model name (e.g. llama3.1:8b-instruct-q4_0)"
                  />
                )}
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Choose based on your hardware: 3B models for fast generation, 7B+ for better quality.
              </p>
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
            {/* Ollama Top-K */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Ollama Top-K Sampling</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={1}
                  max={100}
                  step={1}
                  value={Number(settings.ollama_top_k ?? 40)}
                  onChange={(e)=>setSettings({...settings, ollama_top_k: parseInt(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={1}
                  max={100}
                  step={1}
                  value={Number(settings.ollama_top_k ?? 40)}
                  onChange={(e)=>setSettings({...settings, ollama_top_k: parseInt(e.target.value || '40')})}
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Limits vocabulary to top K tokens. Lower = more focused.</p>
            </div>
            {/* Ollama Top-P */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Ollama Top-P (Nucleus)</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.1}
                  max={1.0}
                  step={0.05}
                  value={Number(settings.ollama_top_p ?? 0.9)}
                  onChange={(e)=>setSettings({...settings, ollama_top_p: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.1}
                  max={1.0}
                  step={0.05}
                  value={Number(settings.ollama_top_p ?? 0.9)}
                  onChange={(e)=>setSettings({...settings, ollama_top_p: parseFloat(e.target.value)})}
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Cumulative probability cutoff. 0.9 = focus on top 90% likely words.</p>
            </div>
            {/* Ollama Repeat Penalty */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Repeat Penalty</label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.8}
                  max={1.5}
                  step={0.05}
                  value={Number(settings.ollama_repeat_penalty ?? 1.1)}
                  onChange={(e)=>setSettings({...settings, ollama_repeat_penalty: parseFloat(e.target.value)})}
                  className="flex-1"
                />
                <input
                  type="number"
                  min={0.8}
                  max={1.5}
                  step={0.05}
                  value={Number(settings.ollama_repeat_penalty ?? 1.1)}
                  onChange={(e)=>setSettings({...settings, ollama_repeat_penalty: parseFloat(e.target.value)})}
                  className="w-24 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Penalizes repetition. 1.1 = slight penalty, 1.0 = no penalty.</p>
            </div>
            {/* Ollama Context Length */}
            <div>
              <label className="block text-sm text-gray-300 mb-1">Context Length</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white"
                value={settings.ollama_context_length || '2048'}
                onChange={(e)=>setSettings({...settings, ollama_context_length: parseInt(e.target.value)})}
              >
                <option value="1024">1024 (Fast, Small)</option>
                <option value="2048">2048 (Balanced)</option>
                <option value="4096">4096 (More Context)</option>
                <option value="8192">8192 (Large Context)</option>
                <option value="16384">16384 (Very Large)</option>
              </select>
              <p className="text-xs text-gray-400 mt-1">Max tokens in model context. Higher = more memory usage.</p>
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
          )
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
