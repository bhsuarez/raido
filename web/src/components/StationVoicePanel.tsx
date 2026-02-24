import React, { useEffect, useState } from 'react'
import { ExternalLinkIcon } from 'lucide-react'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'

interface Props {
  stationIdentifier: string
  stationName: string
}

const FALLBACK_KOKORO_VOICES = [
  'af_bella', 'af_sarah', 'af_sky', 'am_onyx', 'am_michael', 'am_ryan',
  'bf_ava', 'bf_sophie', 'bm_george', 'bm_james',
]
const OPENAI_VOICES = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']

export default function StationVoicePanel({ stationIdentifier, stationName }: Props) {
  const [settings, setSettings] = useState<any>(null)
  const [voices, setVoices] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  const adminPath = stationIdentifier === 'main' ? '/raido/admin' : `/${stationIdentifier}/admin`

  // Load settings when station changes
  useEffect(() => {
    setSettings(null)
    setHasChanges(false)
    apiHelpers.getSettings(stationIdentifier).then(r => setSettings(r.data)).catch(() => {})
  }, [stationIdentifier])

  // Load voice list when provider changes
  useEffect(() => {
    const provider = settings?.dj_voice_provider || 'kokoro'
    if (provider === 'kokoro') {
      fetch('/api/v1/admin/voices')
        .then(r => r.json())
        .then(data => setVoices(Array.isArray(data) ? data : FALLBACK_KOKORO_VOICES))
        .catch(() => setVoices(FALLBACK_KOKORO_VOICES))
    } else {
      setVoices([])
    }
  }, [settings?.dj_voice_provider])

  const handleChange = (updates: Record<string, any>) => {
    setSettings((s: any) => ({ ...s, ...updates }))
    setHasChanges(true)
  }

  const save = async () => {
    if (!settings) return
    setSaving(true)
    try {
      await apiHelpers.updateSettings(settings, stationIdentifier)
      toast.success('DJ settings saved')
      setHasChanges(false)
    } catch {
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (!settings) return null

  const provider = settings.dj_voice_provider || 'kokoro'

  const getVoiceOptions = (): string[] => {
    if (provider === 'openai_tts') return OPENAI_VOICES
    if (provider === 'kokoro') {
      const base = voices.length ? voices : FALLBACK_KOKORO_VOICES
      const cur = settings.kokoro_voice
      return cur && !base.includes(cur) ? [cur, ...base] : base
    }
    return voices
  }

  const getVoiceFieldName = (): string => {
    switch (provider) {
      case 'openai_tts': return 'openai_tts_voice'
      case 'xtts': return 'xtts_voice'
      case 'chatterbox': return 'chatterbox_voice'
      default: return 'kokoro_voice'
    }
  }

  const currentVoice = settings[getVoiceFieldName()] || getVoiceOptions()[0] || ''

  return (
    <div className="card p-4 mb-3 border border-primary-500/20">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-primary-400">DJ — {stationName}</p>
        <a
          href={adminPath}
          className="text-xs text-gray-400 hover:text-gray-100 flex items-center gap-1"
          target="_blank"
          rel="noopener noreferrer"
        >
          Full admin <ExternalLinkIcon className="h-3 w-3" />
        </a>
      </div>

      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Provider</label>
          <select
            className="input text-sm py-1.5"
            value={provider}
            onChange={e => handleChange({ dj_voice_provider: e.target.value })}
          >
            <option value="kokoro">Kokoro TTS</option>
            <option value="openai_tts">OpenAI TTS</option>
            <option value="xtts">XTTS</option>
            <option value="liquidsoap">Liquidsoap</option>
            <option value="chatterbox">Chatterbox</option>
          </select>
        </div>

        {provider !== 'liquidsoap' && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">Voice</label>
            <select
              className="input text-sm py-1.5"
              value={currentVoice}
              onChange={e => handleChange({ [getVoiceFieldName()]: e.target.value })}
            >
              {getVoiceOptions().map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>
        )}

        {hasChanges && (
          <button
            className="btn-primary text-sm py-1.5"
            onClick={save}
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        )}
      </div>
    </div>
  )
}
