/**
 * VoicingProgress — Library-wide voicing engine progress panel.
 *
 * Shows:
 *  - Scripts progress bar (scripted / total tracks) + worker controls
 *  - Audio (TTS) progress bar (audio ready / scripted) + TTS worker controls
 *  - Budget spend (daily + project total)
 *  - Budget limit configuration
 */

import React, { useEffect, useState, useCallback } from 'react'
import { apiHelpers } from '../utils/api'

interface VoicingStats {
  total_tracks: number
  voiced_count: number
  scripts_only_count: number
  audio_ready_count: number
  failed_count: number
  generating_count: number
  pending_count: number
  progress_pct: number
  total_spent_usd: number
  daily_spent_usd: number
  worker_running: boolean
  tts_is_running: boolean
  dry_run_mode: boolean
  daily_limit_usd: number
  project_limit_usd: number
  paused_reason: string | null
}

interface VoicingConfig {
  is_running: boolean
  tts_is_running: boolean
  dry_run_mode: boolean
  daily_spend_limit_usd: number
  total_project_limit_usd: number
  rate_limit_per_minute: number
  total_spent_usd: number
  dry_run_projected_cost_usd: number | null
  paused_reason: string | null
}

async function fetchStats(): Promise<VoicingStats | null> {
  try {
    const r = await fetch(apiHelpers.apiUrl('/api/v1/voicing/stats'))
    if (!r.ok) return null
    return r.json()
  } catch {
    return null
  }
}

async function fetchConfig(): Promise<VoicingConfig | null> {
  try {
    const r = await fetch(apiHelpers.apiUrl('/api/v1/voicing/config'))
    if (!r.ok) return null
    return r.json()
  } catch {
    return null
  }
}

async function patchConfig(payload: Partial<VoicingConfig>): Promise<boolean> {
  try {
    const r = await fetch(apiHelpers.apiUrl('/api/v1/voicing/config'), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return r.ok
  } catch {
    return false
  }
}

export default function VoicingProgress() {
  const [stats, setStats] = useState<VoicingStats | null>(null)
  const [config, setConfig] = useState<VoicingConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Editable limit fields
  const [dailyLimit, setDailyLimit] = useState('1.00')
  const [projectLimit, setProjectLimit] = useState('10.00')
  const [rateLimit, setRateLimit] = useState('10')

  const reload = useCallback(async () => {
    const [s, c] = await Promise.all([fetchStats(), fetchConfig()])
    setStats(s)
    setConfig(c)
    if (c) {
      setDailyLimit(String(c.daily_spend_limit_usd))
      setProjectLimit(String(c.total_project_limit_usd))
      setRateLimit(String(c.rate_limit_per_minute))
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    reload()
    const interval = setInterval(reload, 10_000)
    return () => clearInterval(interval)
  }, [reload])

  const handleStart = async () => {
    await patchConfig({ is_running: true, dry_run_mode: false })
    await reload()
  }

  const handleStop = async () => {
    await patchConfig({ is_running: false })
    await reload()
  }

  const handleDryRun = async () => {
    await patchConfig({ is_running: true, dry_run_mode: true })
    await reload()
  }

  const handleStartTts = async () => {
    await patchConfig({ tts_is_running: true } as Partial<VoicingConfig>)
    await reload()
  }

  const handleStopTts = async () => {
    await patchConfig({ tts_is_running: false } as Partial<VoicingConfig>)
    await reload()
  }

  const handleSaveLimits = async () => {
    setSaving(true)
    await patchConfig({
      daily_spend_limit_usd: parseFloat(dailyLimit) || 1.0,
      total_project_limit_usd: parseFloat(projectLimit) || 10.0,
      rate_limit_per_minute: parseInt(rateLimit, 10) || 10,
    })
    setSaving(false)
    await reload()
  }

  if (loading) {
    return (
      <div className="card p-6 space-y-3">
        <div className="h-4 bg-gray-700 rounded animate-pulse w-1/3" />
        <div className="h-2 bg-gray-700 rounded animate-pulse" />
      </div>
    )
  }

  if (!stats || !config) {
    return (
      <div className="card p-4 text-sm text-red-400">
        Voicing engine status unavailable.
      </div>
    )
  }

  // Scripts progress: (scripts_only + audio_ready) / total
  const scriptedCount = (stats.scripts_only_count ?? 0) + (stats.audio_ready_count ?? 0)
  const scriptPct = Math.round(scriptedCount / Math.max(stats.total_tracks, 1) * 100 * 10) / 10
  const scriptProgressColor =
    scriptPct >= 90 ? 'bg-green-500' : scriptPct >= 50 ? 'bg-blue-500' : 'bg-primary-500'

  // TTS progress: audio_ready / scripted
  const ttsTotal = scriptedCount
  const ttsReady = stats.audio_ready_count ?? 0
  const ttsPct = ttsTotal > 0 ? Math.round(ttsReady / ttsTotal * 100 * 10) / 10 : 0
  const ttsProgressColor =
    ttsPct >= 90 ? 'bg-green-500' : ttsPct >= 50 ? 'bg-purple-500' : 'bg-violet-500'

  return (
    <div className="card p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">Voice of Raido — Engine</h2>
      </div>

      {/* ── Scripts Phase ─────────────────────────────────────────── */}
      <div className="space-y-3 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-300">Phase 1 — Script Generation</span>
          {stats.worker_running ? (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
              {stats.dry_run_mode ? 'Dry Run' : 'Running'}
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-400 border border-gray-600">
              Stopped
            </span>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-gray-400">
            <span>{scriptedCount.toLocaleString()} scripted</span>
            <span>{scriptPct}%</span>
            <span>{stats.total_tracks.toLocaleString()} total</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2.5">
            <div
              className={`${scriptProgressColor} h-2.5 rounded-full transition-all duration-500`}
              style={{ width: `${scriptPct}%` }}
            />
          </div>
          <div className="flex gap-4 text-xs text-gray-500 pt-0.5">
            {stats.generating_count > 0 && (
              <span className="text-yellow-400">{stats.generating_count} generating</span>
            )}
            {stats.failed_count > 0 && (
              <span className="text-red-400">{stats.failed_count} failed</span>
            )}
            <span>{stats.pending_count.toLocaleString()} pending</span>
          </div>
        </div>

        {stats.paused_reason && !stats.worker_running && (
          <div className="text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-2">
            Paused: {stats.paused_reason}
          </div>
        )}

        {config.dry_run_projected_cost_usd !== null && config.dry_run_projected_cost_usd !== undefined && (
          <div className="text-xs text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-2">
            Dry-run projection: ${config.dry_run_projected_cost_usd.toFixed(2)} for full library
          </div>
        )}

        <div className="flex gap-2">
          {!stats.worker_running ? (
            <>
              <button onClick={handleStart} className="btn-primary text-sm py-1.5 px-3 flex-1">
                Start Engine
              </button>
              <button
                onClick={handleDryRun}
                className="btn-secondary text-sm py-1.5 px-3"
                title="Calculate projected cost without calling the API"
              >
                Dry Run
              </button>
            </>
          ) : (
            <button
              onClick={handleStop}
              className="btn-secondary text-sm py-1.5 px-3 flex-1 border-red-500/40 text-red-400"
            >
              Stop Engine
            </button>
          )}
        </div>
      </div>

      {/* ── TTS Phase ─────────────────────────────────────────────── */}
      <div className="space-y-3 border border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-300">Phase 2 — TTS Audio</span>
          {stats.tts_is_running ? (
            <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">
              Running
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-400 border border-gray-600">
              Stopped
            </span>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-gray-400">
            <span>{ttsReady.toLocaleString()} with audio</span>
            <span>{ttsPct}%</span>
            <span>{ttsTotal.toLocaleString()} scripted</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2.5">
            <div
              className={`${ttsProgressColor} h-2.5 rounded-full transition-all duration-500`}
              style={{ width: `${ttsPct}%` }}
            />
          </div>
          <div className="text-xs text-gray-500">
            {(ttsTotal - ttsReady).toLocaleString()} scripts awaiting audio
          </div>
        </div>

        <div className="flex gap-2">
          {!stats.tts_is_running ? (
            <button onClick={handleStartTts} className="btn-primary text-sm py-1.5 px-3 flex-1"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #6d28d9)' }}>
              Start TTS Worker
            </button>
          ) : (
            <button
              onClick={handleStopTts}
              className="btn-secondary text-sm py-1.5 px-3 flex-1 border-purple-500/40 text-purple-400"
            >
              Stop TTS Worker
            </button>
          )}
        </div>
      </div>

      {/* Budget stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-800 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-0.5">Today's spend</p>
          <p className="text-sm font-medium text-white">${stats.daily_spent_usd.toFixed(4)}</p>
          <p className="text-xs text-gray-600">limit: ${stats.daily_limit_usd.toFixed(2)}</p>
          <div className="mt-1.5 w-full bg-gray-700 rounded-full h-1">
            <div
              className="bg-orange-400 h-1 rounded-full"
              style={{ width: `${Math.min(100, (stats.daily_spent_usd / Math.max(stats.daily_limit_usd, 0.001)) * 100)}%` }}
            />
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-0.5">Total spent</p>
          <p className="text-sm font-medium text-white">${stats.total_spent_usd.toFixed(4)}</p>
          <p className="text-xs text-gray-600">limit: ${stats.project_limit_usd.toFixed(2)}</p>
          <div className="mt-1.5 w-full bg-gray-700 rounded-full h-1">
            <div
              className="bg-red-400 h-1 rounded-full"
              style={{ width: `${Math.min(100, (stats.total_spent_usd / Math.max(stats.project_limit_usd, 0.001)) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Budget limit editor */}
      <details className="group">
        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300 select-none">
          Budget &amp; Rate Settings
        </summary>
        <div className="mt-3 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Daily limit ($)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={dailyLimit}
                onChange={e => setDailyLimit(e.target.value)}
                className="input w-full text-sm py-1"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Project limit ($)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={projectLimit}
                onChange={e => setProjectLimit(e.target.value)}
                className="input w-full text-sm py-1"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Rate / min</label>
              <input
                type="number"
                step="1"
                min="1"
                value={rateLimit}
                onChange={e => setRateLimit(e.target.value)}
                className="input w-full text-sm py-1"
              />
            </div>
          </div>
          <button
            onClick={handleSaveLimits}
            disabled={saving}
            className="btn-secondary text-xs py-1 px-3"
          >
            {saving ? 'Saving…' : 'Save limits'}
          </button>
        </div>
      </details>
    </div>
  )
}
