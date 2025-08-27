import React from 'react'
import { SettingsIcon, UsersIcon, BarChart3Icon, MicIcon } from 'lucide-react'

export default function AdminPanel() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <h1 className="text-2xl font-bold text-white mb-2 flex items-center space-x-2">
          <SettingsIcon className="w-6 h-6" />
          <span>Admin Panel</span>
        </h1>
        <p className="text-gray-400">
          🏴‍☠️ Ahoy! Manage your pirate radio station from here, captain.
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Listeners"
          value="0"
          icon={<UsersIcon className="w-5 h-5" />}
          color="blue"
        />
        <StatCard
          title="Tracks Played"
          value="0"
          icon={<BarChart3Icon className="w-5 h-5" />}
          color="green"
        />
        <StatCard
          title="Commentary Generated"
          value="0"
          icon={<MicIcon className="w-5 h-5" />}
          color="purple"
        />
        <StatCard
          title="Uptime"
          value="0h 0m"
          icon={<SettingsIcon className="w-5 h-5" />}
          color="yellow"
        />
      </div>

      {/* Settings Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* DJ Settings */}
        <div className="card p-6">
          <h2 className="text-xl font-bold text-white mb-4">DJ Configuration</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Commentary Interval
              </label>
              <select className="input w-full">
                <option value="1">After every song</option>
                <option value="2">Every 2 songs</option>
                <option value="3">Every 3 songs</option>
                <option value="5">Every 5 songs</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                DJ Tone
              </label>
              <select className="input w-full">
                <option value="energetic">Energetic Pirate</option>
                <option value="chill">Chill Seafarer</option>
                <option value="professional">Professional Captain</option>
                <option value="funny">Comedic Buccaneer</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Commentary Length
              </label>
              <input
                type="number"
                min="10"
                max="60"
                defaultValue="30"
                className="input w-full"
                placeholder="Seconds"
              />
            </div>
          </div>
        </div>

        {/* Stream Settings */}
        <div className="card p-6">
          <h2 className="text-xl font-bold text-white mb-4">Stream Configuration</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Bitrate
              </label>
              <select className="input w-full">
                <option value="96">96 kbps</option>
                <option value="128">128 kbps</option>
                <option value="192">192 kbps</option>
                <option value="320">320 kbps</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Crossfade Duration
              </label>
              <input
                type="number"
                min="0"
                max="10"
                step="0.5"
                defaultValue="2"
                className="input w-full"
                placeholder="Seconds"
              />
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="enable_commentary"
                defaultChecked
                className="rounded bg-gray-700 border-gray-600 text-primary-500 focus:ring-primary-500 focus:ring-offset-0"
              />
              <label htmlFor="enable_commentary" className="text-sm text-gray-300">
                Enable DJ Commentary
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* AI Provider Settings */}
      <div className="card p-6">
        <h2 className="text-xl font-bold text-white mb-4">AI Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Commentary Provider
            </label>
            <select className="input w-full">
              <option value="openai">OpenAI GPT-4</option>
              <option value="ollama">Ollama (Local)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Voice Provider
            </label>
            <select className="input w-full">
              <option value="openai_tts">OpenAI TTS</option>
              <option value="liquidsoap">Liquidsoap (Basic)</option>
              <option value="xtts">XTTS (Advanced)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="card p-6">
        <h2 className="text-xl font-bold text-white mb-4">Actions</h2>
        <div className="flex flex-wrap gap-4">
          <button className="btn-primary">
            Save Settings
          </button>
          <button className="btn-secondary">
            Restart Stream
          </button>
          <button className="btn-secondary">
            Clear Commentary Cache
          </button>
          <button className="btn-secondary">
            Export Settings
          </button>
        </div>
      </div>
    </div>
  )
}

interface StatCardProps {
  title: string
  value: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'purple' | 'yellow'
}

function StatCard({ title, value, icon, color }: StatCardProps) {
  const colorClasses = {
    blue: 'text-blue-400 bg-blue-900',
    green: 'text-green-400 bg-green-900',
    purple: 'text-purple-400 bg-purple-900',
    yellow: 'text-yellow-400 bg-yellow-900',
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">{title}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]} bg-opacity-20`}>
          {icon}
        </div>
      </div>
    </div>
  )
}