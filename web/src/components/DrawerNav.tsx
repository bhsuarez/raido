import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { SettingsIcon, LibraryIcon, RadioIcon, XIcon, UsersIcon, UserIcon } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useAuthStore } from '../store/authStore'
import { apiHelpers } from '../utils/api'

interface Station {
  id: number
  identifier: string
  name: string
  is_active: boolean
}

interface DrawerNavProps {
  open: boolean
  onClose: () => void
}

export default function DrawerNav({ open, onClose }: DrawerNavProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [stations, setStations] = useState<Station[]>([])
  const { selectedStation, setSelectedStation, isConnected } = useRadioStore((s) => ({
    selectedStation: s.selectedStation,
    setSelectedStation: s.setSelectedStation,
    isConnected: s.isConnected,
  }))
  const { role, fullName, displayName, avatarUrl, email } = useAuthStore()
  const isAdmin = role === 'admin'

  useEffect(() => {
    apiHelpers.getStations()
      .then((res) => setStations((res.data || []).filter((s: Station) => s.is_active)))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  function goTo(path: string) {
    navigate(path)
    onClose()
  }

  function selectStation(id: string) {
    setSelectedStation(id)
    if (location.pathname.includes('/admin')) {
      navigate(id === 'main' ? '/raido/admin' : `/${id}/admin`)
      onClose()
    }
  }

  function openStationAdmin(id: string) {
    setSelectedStation(id)
    navigate(id === 'main' ? '/raido/admin' : `/${id}/admin`)
    onClose()
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 z-40 transition-opacity duration-300"
        style={{
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(2px)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
        }}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        className="fixed top-0 left-0 bottom-0 z-50 flex flex-col"
        style={{
          width: 'min(320px, 80vw)',
          background: 'rgba(8, 8, 18, 0.97)',
          borderRight: '1px solid #1a1a32',
          backdropFilter: 'blur(20px)',
          transform: open ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.28s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid #1a1a32' }}>
          <span className="font-display font-bold text-xs uppercase tracking-widest" style={{ color: '#38bdf8', letterSpacing: '0.16em' }}>
            RAIDO
          </span>
          <button onClick={onClose} style={{ color: '#404060' }} className="hover:text-gray-300 transition-colors p-1">
            <XIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Stations list */}
        <div className="flex-1 overflow-y-auto py-4">
          <p className="section-header px-5 mb-3">Stations</p>

          {stations.length === 0 && (
            <p className="px-5 text-xs" style={{ color: '#303050' }}>Loading…</p>
          )}

          {stations.map((station) => {
            const isSelected = selectedStation === station.identifier
            const isLive = isConnected && isSelected
            return (
              <div
                key={station.identifier}
                className="flex items-center gap-3 px-5 py-3 transition-colors"
                style={{ background: isSelected ? 'rgba(56,189,248,0.06)' : 'transparent' }}
              >
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0 mt-0.5"
                  style={{
                    background: isLive ? '#4ade80' : isSelected ? '#38bdf8' : '#2a2a48',
                    boxShadow: isLive ? '0 0 6px rgba(74,222,128,0.7)' : 'none',
                  }}
                />
                <button
                  onClick={() => selectStation(station.identifier)}
                  className="flex-1 text-left text-sm font-medium transition-colors"
                  style={{ color: isSelected ? '#e0e0f0' : '#606080' }}
                >
                  {station.name}
                </button>
                <button
                  onClick={() => openStationAdmin(station.identifier)}
                  className="p-1.5 rounded-lg transition-colors flex-shrink-0"
                  style={{ color: '#303050' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#38bdf8' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#303050' }}
                  aria-label={`DJ Admin for ${station.name}`}
                  title={`DJ Admin: ${station.name}`}
                >
                  <SettingsIcon className="w-3.5 h-3.5" />
                </button>
              </div>
            )
          })}

          <div className="mx-5 my-4" style={{ height: '1px', background: '#0f0f20' }} />

          <button
            onClick={() => goTo('/library')}
            className="w-full flex items-center gap-3 px-5 py-3 transition-colors text-sm font-medium"
            style={{ color: location.pathname.startsWith('/library') ? '#38bdf8' : '#505070' }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
            onMouseLeave={e => {
              const isActive = location.pathname.startsWith('/library')
              ;(e.currentTarget as HTMLElement).style.color = isActive ? '#38bdf8' : '#505070'
            }}
          >
            <LibraryIcon className="w-4 h-4 flex-shrink-0" />
            Library
          </button>

          <button
            onClick={() => goTo('/now-playing')}
            className="w-full flex items-center gap-3 px-5 py-3 transition-colors text-sm font-medium"
            style={{ color: location.pathname === '/now-playing' ? '#38bdf8' : '#505070' }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
            onMouseLeave={e => {
              const isActive = location.pathname === '/now-playing'
              ;(e.currentTarget as HTMLElement).style.color = isActive ? '#38bdf8' : '#505070'
            }}
          >
            <RadioIcon className="w-4 h-4 flex-shrink-0" />
            Now Playing
          </button>

          {isAdmin && (
            <>
              <div className="mx-5 my-4" style={{ height: '1px', background: '#0f0f20' }} />
              <p className="section-header px-5 mb-3">Admin</p>
              <button
                onClick={() => goTo('/admin/users')}
                className="w-full flex items-center gap-3 px-5 py-3 transition-colors text-sm font-medium"
                style={{ color: location.pathname === '/admin/users' ? '#38bdf8' : '#505070' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
                onMouseLeave={e => {
                  const isActive = location.pathname === '/admin/users'
                  ;(e.currentTarget as HTMLElement).style.color = isActive ? '#38bdf8' : '#505070'
                }}
              >
                <UsersIcon className="w-4 h-4 flex-shrink-0" />
                Users
              </button>
            </>
          )}
        </div>

        {/* Profile + footer */}
        <div style={{ borderTop: '1px solid #0f0f20' }}>
          <button
            onClick={() => goTo('/profile')}
            className="w-full flex items-center gap-3 px-5 py-3 transition-colors"
            style={{ color: location.pathname === '/profile' ? '#38bdf8' : '#505070' }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
            onMouseLeave={e => {
              const isActive = location.pathname === '/profile'
              ;(e.currentTarget as HTMLElement).style.color = isActive ? '#38bdf8' : '#505070'
            }}
          >
            {(() => {
              const label = displayName || fullName || email || ''
              const initials = label.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2) || '?'
              return avatarUrl ? (
                <img src={avatarUrl} alt="Avatar" className="w-6 h-6 rounded-full object-cover flex-shrink-0" />
              ) : (
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold"
                  style={{ background: '#1a1a32', color: '#38bdf8', border: '1px solid #2a2a48' }}
                >
                  {initials}
                </div>
              )
            })()}
            <span className="text-sm font-medium">{displayName || fullName || 'Profile'}</span>
          </button>

          <div className="px-5 pb-3">
            <div className="flex items-center gap-2">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: isConnected ? '#4ade80' : '#503030' }}
              />
              <span className="font-mono text-xs" style={{ color: '#303050', letterSpacing: '0.08em', fontSize: '0.6rem' }}>
                {isConnected ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
