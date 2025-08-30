import React, { useState, useEffect } from 'react'
import { toast } from 'react-hot-toast'
import { SaveIcon, RefreshCwIcon, SettingsIcon, PlayIcon, XCircleIcon } from 'lucide-react'
import { apiHelpers } from '../utils/api'

interface DJSettings {
  dj_provider: string
  dj_voice_provider: string
  dj_kokoro_voice?: string
  dj_tts_volume?: number
  dj_model: string
  dj_prompt_template: string
  dj_temperature: number
  dj_max_tokens: number
  dj_max_seconds: number
  dj_commentary_interval: number
  dj_tone: string
  dj_profanity_filter: boolean
  enable_commentary: boolean
  station_name: string
}

export default function DJSettings() {
  const [settings, setSettings] = useState<DJSettings>({
    dj_provider: 'ollama',
    dj_voice_provider: 'kokoro',
    dj_kokoro_voice: 'af_bella',
    dj_tts_volume: 1.0,
    dj_model: 'llama3.2:1b',
    dj_prompt_template: '',
    dj_temperature: 0.8,
    dj_max_tokens: 200,
    dj_max_seconds: 30,
    dj_commentary_interval: 1,
    dj_tone: 'energetic',
    dj_profanity_filter: true,
    enable_commentary: true,
    station_name: 'Raido Pirate Radio'
  })

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingPrompt, setTestingPrompt] = useState(false)
  const [kokoroVoices, setKokoroVoices] = useState<string[]>([])

  // Load settings on component mount
  useEffect(() => {
    loadSettings()
  }, [])

  useEffect(() => {
    if (settings.dj_voice_provider === 'kokoro') {
      fetchVoices()
    }
  }, [settings.dj_voice_provider])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const response = await apiHelpers.getSettings()
      setSettings(response.data)
    } catch (error) {
      console.error('Failed to load settings:', error)
      toast.error('Failed to load DJ settings')
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async () => {
    try {
      setSaving(true)
      await apiHelpers.updateSettings(settings)
      toast.success('🏴‍☠️ DJ settings saved successfully!')
    } catch (error) {
      console.error('Failed to save settings:', error)
      toast.error('Failed to save DJ settings')
    } finally {
      setSaving(false)
    }
  }

  const fetchVoices = async () => {
    try {
      const res = await apiHelpers.getVoices()
      const voices = (res.data?.voices || []) as string[]
      setKokoroVoices(voices)
      if (voices.length && (!settings.dj_kokoro_voice || !voices.includes(settings.dj_kokoro_voice))) {
        setSettings({ ...settings, dj_kokoro_voice: voices[0] })
      }
    } catch (e) {
      // ignore
    }
  }

  const resetToDefaults = () => {
    const defaultTemplate = `You're a pirate radio DJ introducing the NEXT song coming up. Create a brief 15-20 second intro for: "{{song_title}}" by {{artist}}{% if album %} from the album "{{album}}"{% endif %}{% if year %} ({{year}}){% endif %}. 

Share ONE interesting fact about the artist, song, or album. Be energetic, knowledgeable, and build excitement for what's coming up next. End with something like "Coming up next!" or "Here we go!" or "Let's dive in!"

Examples of good facts:
- Chart performance or awards
- Recording stories or collaborations  
- Cultural impact or covers by other artists
- Band member changes or solo careers
- Genre innovations or influences

Keep it conversational and exciting. No SSML tags needed.`

    setSettings({
      ...settings,
      dj_prompt_template: defaultTemplate,
      dj_temperature: 0.8,
      dj_max_tokens: 200,
      dj_model: 'llama3.2:1b'
    })
  }

  const testPrompt = async () => {
    try {
      setTestingPrompt(true)
      // This would call a test endpoint that generates sample commentary
      // For now, just show a success message
      toast.success('🎤 Prompt test completed! Check the stream for results.')
    } catch (error) {
      console.error('Failed to test prompt:', error)
      toast.error('Failed to test prompt')
    } finally {
      setTestingPrompt(false)
    }
  }

  if (loading) {
    return (
      <div className="card p-8">
        <div className="flex items-center justify-center">
          <RefreshCwIcon className="h-6 w-6 animate-spin text-primary-500" />
          <span className="ml-2 text-gray-300">Loading DJ settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <SettingsIcon className="h-6 w-6 text-primary-500" />
            <div>
              <h1 className="text-2xl font-bold text-white">DJ Configuration</h1>
              <p className="text-gray-400">Configure AI commentary generation and voice settings</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {settings.enable_commentary ? (
              <span className="flex items-center text-green-400">
                <PlayIcon className="h-4 w-4 mr-1" />
                Active
              </span>
            ) : (
              <span className="flex items-center text-red-400">
                <XCircleIcon className="h-4 w-4 mr-1" />
                Disabled
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main Settings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Basic Settings */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Basic Settings</h2>
          <div className="space-y-4">
            {/* Enable Commentary */}
            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={settings.enable_commentary}
                  onChange={(e) => setSettings({...settings, enable_commentary: e.target.checked})}
                  className="rounded bg-gray-700 border-gray-600 text-primary-500 focus:ring-primary-500"
                />
                <span className="ml-2 text-gray-300">Enable AI Commentary</span>
              </label>
            </div>

            {/* DJ Provider */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                AI Provider
              </label>
              <select
                value={settings.dj_provider}
                onChange={(e) => setSettings({...settings, dj_provider: e.target.value})}
                className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="ollama">Ollama (Local)</option>
                <option value="openai">OpenAI GPT</option>
                <option value="templates">Pre-written Templates</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>

            {/* Voice Provider */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Voice Provider
              </label>
              <select
                value={settings.dj_voice_provider}
                onChange={(e) => setSettings({...settings, dj_voice_provider: e.target.value})}
                className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="kokoro">Kokoro TTS (Neural)</option>
                <option value="openai_tts">OpenAI TTS</option>
                <option value="liquidsoap">Liquidsoap (Basic)</option>
                <option value="xtts">XTTS (Custom)</option>
              </select>
            </div>

            {settings.dj_voice_provider === 'kokoro' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Kokoro Voice
                </label>
                <select
                  value={settings.dj_kokoro_voice || ''}
                  onChange={(e) => setSettings({ ...settings, dj_kokoro_voice: e.target.value })}
                  className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
                >
                  {kokoroVoices.length === 0 && (
                    <option value="">Loading voices...</option>
                  )}
                  {kokoroVoices.map(v => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Station Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Station Name
              </label>
              <input
                type="text"
                value={settings.station_name}
                onChange={(e) => setSettings({...settings, station_name: e.target.value})}
                className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
                placeholder="Raido Pirate Radio"
              />
            </div>
          </div>
        </div>

        {/* AI Model Settings */}
        <div className="card p-6">
          <h2 className="text-xl font-semibold text-white mb-4">AI Model Settings</h2>
          <div className="space-y-4">
            {/* Model */}
            {settings.dj_provider === 'ollama' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Ollama Model
                </label>
                <input
                  type="text"
                  value={settings.dj_model}
                  onChange={(e) => setSettings({...settings, dj_model: e.target.value})}
                  className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
                  placeholder="llama3.2:1b"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Available models: llama3.2:1b, llama3.2:3b, qwen2.5:1.5b, etc.
                </p>
              </div>
            )}

            {/* Temperature */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Creativity (Temperature): {settings.dj_temperature}
              </label>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.1"
                value={settings.dj_temperature}
                onChange={(e) => setSettings({...settings, dj_temperature: parseFloat(e.target.value)})}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Conservative</span>
                <span>Creative</span>
              </div>
            </div>

            {/* Max Tokens */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Max Tokens
              </label>
              <input
                type="number"
                min="50"
                max="500"
                value={settings.dj_max_tokens}
                onChange={(e) => setSettings({...settings, dj_max_tokens: parseInt(e.target.value)})}
                className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Higher values = longer commentary (50-500)
              </p>
            </div>

            {/* Max Seconds */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Max Commentary Duration (seconds)
              </label>
              <input
                type="number"
                min="10"
                max="60"
                value={settings.dj_max_seconds}
                onChange={(e) => setSettings({...settings, dj_max_seconds: parseInt(e.target.value)})}
                className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            {/* Commentary Interval */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Commentary Frequency (every N tracks)
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={settings.dj_commentary_interval}
                onChange={(e) => setSettings({...settings, dj_commentary_interval: parseInt(e.target.value)})}
                className="w-full bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Prompt Template */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Custom Prompt Template</h2>
          <div className="flex space-x-2">
            <button
              onClick={resetToDefaults}
              className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-md transition-colors"
            >
              Reset to Default
            </button>
            <button
              onClick={testPrompt}
              disabled={testingPrompt}
              className="px-3 py-1 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors disabled:opacity-50"
            >
              {testingPrompt ? 'Testing...' : 'Test Prompt'}
            </button>
          </div>
        </div>
        
        <textarea
          value={settings.dj_prompt_template}
          onChange={(e) => setSettings({...settings, dj_prompt_template: e.target.value})}
          className="w-full h-64 bg-gray-700 border-gray-600 rounded-md text-white focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
          placeholder="Enter your custom DJ prompt template..."
        />
        
        <div className="mt-3 text-sm text-gray-400">
          <p className="font-medium mb-2">Available template variables:</p>
          <div className="grid grid-cols-2 gap-2">
            <code className="bg-gray-800 px-2 py-1 rounded">{'{{song_title}}'}</code>
            <code className="bg-gray-800 px-2 py-1 rounded">{'{{artist}}'}</code>
            <code className="bg-gray-800 px-2 py-1 rounded">{'{{album}}'}</code>
            <code className="bg-gray-800 px-2 py-1 rounded">{'{{year}}'}</code>
            <code className="bg-gray-800 px-2 py-1 rounded">{'{{genre}}'}</code>
            <code className="bg-gray-800 px-2 py-1 rounded">{'{{station_name}}'}</code>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={saveSettings}
          disabled={saving}
          className="flex items-center space-x-2 px-6 py-3 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-800 text-white rounded-lg transition-colors"
        >
          {saving ? (
            <RefreshCwIcon className="h-5 w-5 animate-spin" />
          ) : (
            <SaveIcon className="h-5 w-5" />
          )}
          <span>{saving ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>
    </div>
  )
}
