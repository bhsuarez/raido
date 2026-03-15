import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { useAuthStore } from '../store/authStore'
import { toast } from 'react-hot-toast'
import { UserIcon } from 'lucide-react'

export default function ProfilePage() {
  const { email, role, fullName, displayName, avatarUrl, setProfile } = useAuthStore()

  const [form, setForm] = useState({
    full_name: fullName || '',
    display_name: displayName || '',
    avatar_url: avatarUrl || '',
  })
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [saving, setSaving] = useState(false)
  const [changingPw, setChangingPw] = useState(false)

  // Fetch latest profile from API on mount
  useEffect(() => {
    api.get('/auth/me').then((res) => {
      const d = res.data
      setForm({
        full_name: d.full_name || '',
        display_name: d.display_name || '',
        avatar_url: d.avatar_url || '',
      })
      setProfile({ full_name: d.full_name, display_name: d.display_name, avatar_url: d.avatar_url })
    }).catch(() => {})
  }, [])

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await api.patch('/auth/me', {
        full_name: form.full_name || null,
        display_name: form.display_name || null,
        avatar_url: form.avatar_url || null,
      })
      setProfile({ full_name: res.data.full_name, display_name: res.data.display_name, avatar_url: res.data.avatar_url })
      toast.success('Profile saved')
    } catch {
      // toast handled by interceptor
    } finally {
      setSaving(false)
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault()
    if (pwForm.new_password !== pwForm.confirm_password) {
      toast.error('Passwords do not match')
      return
    }
    if (pwForm.new_password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setChangingPw(true)
    try {
      await api.patch('/auth/me', {
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      })
      setPwForm({ current_password: '', new_password: '', confirm_password: '' })
      toast.success('Password changed')
    } catch {
      // toast handled by interceptor
    } finally {
      setChangingPw(false)
    }
  }

  const displayLabel = displayName || fullName || email || ''
  const initials = displayLabel
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || '?'

  return (
    <div className="max-w-lg mx-auto py-8 flex flex-col gap-6">
      <h1 className="text-lg font-bold tracking-wide" style={{ color: '#c0c0e0' }}>Profile</h1>

      {/* Avatar preview */}
      <div className="flex items-center gap-4">
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center overflow-hidden flex-shrink-0"
          style={{ background: '#1a1a32', border: '1px solid #2a2a48' }}
        >
          {(form.avatar_url || avatarUrl) ? (
            <img
              src={form.avatar_url || avatarUrl || undefined}
              alt="Avatar"
              className="w-full h-full object-cover"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
            />
          ) : (
            <span className="text-lg font-bold" style={{ color: '#38bdf8' }}>{initials}</span>
          )}
        </div>
        <div>
          <p className="text-sm font-medium" style={{ color: '#c0c0e0' }}>{displayLabel}</p>
          <p className="text-xs" style={{ color: '#404060' }}>{email}</p>
          <p className="text-xs mt-0.5 capitalize" style={{ color: '#303050' }}>{role}</p>
        </div>
      </div>

      {/* Profile info form */}
      <form onSubmit={handleSaveProfile} className="card p-5 flex flex-col gap-4">
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#505070' }}>Profile Info</p>

        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: '#505070' }}>Full Name</label>
          <input
            className="input-field"
            value={form.full_name}
            onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
            placeholder="Your name"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: '#505070' }}>Display Name <span style={{ color: '#303050' }}>(shown in UI)</span></label>
          <input
            className="input-field"
            value={form.display_name}
            onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
            placeholder="Nickname or alias"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: '#505070' }}>Avatar URL</label>
          <input
            className="input-field"
            type="url"
            value={form.avatar_url}
            onChange={(e) => setForm((f) => ({ ...f, avatar_url: e.target.value }))}
            placeholder="https://..."
          />
          <p className="text-xs" style={{ color: '#303050' }}>Paste any image URL — gravatar, GitHub avatar, etc.</p>
        </div>

        <div className="flex justify-end">
          <button type="submit" className="btn-primary text-sm" disabled={saving}>
            {saving ? 'Saving…' : 'Save Profile'}
          </button>
        </div>
      </form>

      {/* Change password form */}
      <form onSubmit={handleChangePassword} className="card p-5 flex flex-col gap-4">
        <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#505070' }}>Change Password</p>

        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: '#505070' }}>Current Password</label>
          <input
            className="input-field"
            type="password"
            value={pwForm.current_password}
            onChange={(e) => setPwForm((f) => ({ ...f, current_password: e.target.value }))}
            autoComplete="current-password"
            required
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: '#505070' }}>New Password</label>
          <input
            className="input-field"
            type="password"
            value={pwForm.new_password}
            onChange={(e) => setPwForm((f) => ({ ...f, new_password: e.target.value }))}
            autoComplete="new-password"
            minLength={8}
            required
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs" style={{ color: '#505070' }}>Confirm New Password</label>
          <input
            className="input-field"
            type="password"
            value={pwForm.confirm_password}
            onChange={(e) => setPwForm((f) => ({ ...f, confirm_password: e.target.value }))}
            autoComplete="new-password"
            required
          />
        </div>

        <div className="flex justify-end">
          <button type="submit" className="btn-primary text-sm" disabled={changingPw}>
            {changingPw ? 'Changing…' : 'Change Password'}
          </button>
        </div>
      </form>

      {/* Account info (read-only) */}
      <div className="card p-5 flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#505070' }}>Account</p>
        <div className="flex justify-between text-sm">
          <span style={{ color: '#404060' }}>Email</span>
          <span style={{ color: '#808090' }}>{email}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span style={{ color: '#404060' }}>Role</span>
          <span className="capitalize" style={{ color: '#808090' }}>{role}</span>
        </div>
      </div>
    </div>
  )
}
