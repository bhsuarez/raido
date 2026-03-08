# Raido Frontend Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the nav-bar dashboard with an immersive full-screen art-driven UI — album art fills the screen, colors extract dynamically from artwork, a slide-out drawer handles all navigation, and station context is global.

**Architecture:** All work is in `web/src/`. The design adds a `useArtColor` hook that extracts dominant color from album art via Canvas and sets CSS custom properties (`--art-bg`, `--art-accent`) on `document.documentElement`. A new Zustand slice tracks `selectedStation`. `Layout.tsx` becomes a slim top bar + `DrawerNav`. The old nav bar and five now-redundant pages (`/stations`, `/transcripts`, `/raido/enrich` standalone, `/history`) are removed.

**Tech Stack:** React 18, TypeScript, Zustand, React Router v6, TanStack Query, Tailwind CSS, Lucide icons. No new npm packages needed.

---

## Pre-flight

```bash
cd /root/claude/raido-src
git status   # should be on frontend-redesign branch
git log --oneline -3
```

Type-check command (run after each task):
```bash
cd web && npx tsc --noEmit 2>&1 | head -30
```

Build command (run at end):
```bash
cd web && npm run build 2>&1 | tail -20
```

---

## Task 1: Add `selectedStation` to Zustand store

**Files:**
- Modify: `web/src/store/radioStore.ts`

**Why:** Currently `selectedStation` lives in per-component `useState` + `localStorage`. Making it global means DrawerNav, NowPlayingPage, and DJAdminPage all read from one source.

**Step 1: Add the slice to `RadioState` interface**

In `radioStore.ts`, add to the `RadioState` interface after `isAdmin`:

```typescript
  // Station context
  selectedStation: string
  setSelectedStation: (station: string) => void
```

**Step 2: Add implementation inside `create()`**

After the `isAdmin` implementation:

```typescript
      // Station context
      selectedStation: localStorage.getItem('selectedStation') || 'main',
      setSelectedStation: (station) => {
        set({ selectedStation: station })
        localStorage.setItem('selectedStation', station)
      },
```

**Step 3: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `selectedStation`.

**Step 4: Remove selectedStation local state from Layout.tsx**

In `web/src/components/Layout.tsx`, remove:
- The `Station` interface (will be defined in DrawerNav)
- The `stations` useState and fetch useEffect
- The `selectedStation` useState
- The `handleStationChange` function
- The `djAdminHref` variable
- The station picker `<select>` block
- The `apiHelpers` import (if only used for stations)

Replace `djAdminHref` references in the nav with a computed value that reads from the store:
```typescript
const { isConnected, nowPlaying, selectedStation } = useRadioStore((state) => ({
  isConnected: state.isConnected,
  nowPlaying: state.nowPlaying,
  selectedStation: state.selectedStation,
}))
const djAdminHref = selectedStation === 'main' ? '/raido/admin' : `/${selectedStation}/admin`
```

**Step 5: Type-check again**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -20
```

**Step 6: Commit**

```bash
cd /root/claude/raido-src
git add web/src/store/radioStore.ts web/src/components/Layout.tsx
git commit -m "feat: add selectedStation to global Zustand store"
```

---

## Task 2: Create `useArtColor` hook

**Files:**
- Create: `web/src/hooks/useArtColor.ts`

**What it does:** Given an artwork URL, samples it via Canvas, extracts the dominant HSL color, and sets two CSS custom properties on `document.documentElement`:
- `--art-bg`: darkened/desaturated version for backgrounds
- `--art-accent`: brightened version for progress bars, active dots, links

**Step 1: Create the file**

```typescript
// web/src/hooks/useArtColor.ts
import { useEffect } from 'react'

function rgbToHsl(r: number, g: number, b: number): [number, number, number] {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  let h = 0, s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
      case g: h = ((b - r) / d + 2) / 6; break
      case b: h = ((r - g) / d + 4) / 6; break
    }
  }
  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)]
}

function applyArtColors(h: number, s: number, _l: number) {
  // bg: very dark, low saturation — readable background
  const bgS = Math.max(s * 0.35, 8)
  const bgL = 7
  // accent: vivid, bright — used for highlights
  const accentS = Math.min(s * 0.9 + 20, 90)
  const accentL = 62

  const root = document.documentElement
  root.style.setProperty('--art-bg',     `hsl(${h}, ${bgS}%, ${bgL}%)`)
  root.style.setProperty('--art-accent', `hsl(${h}, ${accentS}%, ${accentL}%)`)
  root.style.setProperty('--art-h',      String(h))
  root.style.setProperty('--art-s',      `${Math.round(s * 0.6)}%`)
}

function resetArtColors() {
  const root = document.documentElement
  root.style.setProperty('--art-bg',     'hsl(230, 15%, 7%)')
  root.style.setProperty('--art-accent', 'hsl(200, 70%, 62%)')
  root.style.setProperty('--art-h',      '230')
  root.style.setProperty('--art-s',      '15%')
}

export function useArtColor(artworkUrl: string | null | undefined) {
  useEffect(() => {
    if (!artworkUrl) {
      resetArtColors()
      return
    }

    const img = new Image()
    img.crossOrigin = 'anonymous'

    img.onload = () => {
      try {
        const SIZE = 40
        const canvas = document.createElement('canvas')
        canvas.width = SIZE
        canvas.height = SIZE
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        ctx.drawImage(img, 0, 0, SIZE, SIZE)
        const { data } = ctx.getImageData(0, 0, SIZE, SIZE)

        let r = 0, g = 0, b = 0, count = 0
        for (let i = 0; i < data.length; i += 4) {
          // skip near-black and near-white pixels — they skew results
          const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3
          if (brightness < 15 || brightness > 240) continue
          r += data[i]; g += data[i + 1]; b += data[i + 2]
          count++
        }
        if (count === 0) { resetArtColors(); return }
        const [h, s, l] = rgbToHsl(
          Math.round(r / count),
          Math.round(g / count),
          Math.round(b / count)
        )
        applyArtColors(h, s, l)
      } catch {
        resetArtColors()
      }
    }

    img.onerror = resetArtColors
    img.src = artworkUrl
  }, [artworkUrl])
}
```

**Step 2: Add CSS custom property defaults to `index.css`**

In `web/src/index.css`, inside the `:root` or `html` block (add after `@tailwind base;`):

```css
:root {
  --art-bg:     hsl(230, 15%, 7%);
  --art-accent: hsl(200, 70%, 62%);
  --art-h:      230;
  --art-s:      15%;
}
```

**Step 3: Add a smooth transition to body in `index.css`**

```css
body {
  transition: background-color 0.8s ease;
}
```

**Step 4: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -20
```

**Step 5: Commit**

```bash
cd /root/claude/raido-src
git add web/src/hooks/useArtColor.ts web/src/index.css
git commit -m "feat: add useArtColor hook for canvas-based art color extraction"
```

---

## Task 3: Create `DrawerNav` component

**Files:**
- Create: `web/src/components/DrawerNav.tsx`

**What it does:** A slide-out drawer triggered by a boolean prop. Lists all active stations with a live dot and gear icon. Has Library and Now Playing nav items at the bottom. Closes on outside click.

**Step 1: Create the component**

```typescript
// web/src/components/DrawerNav.tsx
import React, { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { SettingsIcon, LibraryIcon, RadioIcon, XIcon } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
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
  const overlayRef = useRef<HTMLDivElement>(null)
  const [stations, setStations] = useState<Station[]>([])
  const { selectedStation, setSelectedStation, isConnected } = useRadioStore((s) => ({
    selectedStation: s.selectedStation,
    setSelectedStation: s.setSelectedStation,
    isConnected: s.isConnected,
  }))

  // Load stations once
  useEffect(() => {
    apiHelpers.getStations()
      .then((res) => setStations((res.data || []).filter((s: Station) => s.is_active)))
      .catch(() => {})
  }, [])

  // Close on Escape
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
    // If currently on an admin page, navigate to new station's admin
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
        ref={overlayRef}
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
        {/* Drawer header */}
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
                {/* Live dot or inactive dot */}
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0 mt-0.5"
                  style={{
                    background: isLive ? '#4ade80' : isSelected ? '#38bdf8' : '#1a1a32',
                    boxShadow: isLive ? '0 0 6px rgba(74,222,128,0.7)' : 'none',
                  }}
                />

                {/* Station name — click to select context */}
                <button
                  onClick={() => selectStation(station.identifier)}
                  className="flex-1 text-left text-sm font-medium transition-colors"
                  style={{ color: isSelected ? '#e0e0f0' : '#606080' }}
                >
                  {station.name}
                </button>

                {/* Gear — click to open DJ Admin */}
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

          {/* Divider */}
          <div className="mx-5 my-4" style={{ height: '1px', background: '#0f0f20' }} />

          {/* Library nav item */}
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

          {/* Now Playing nav item */}
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
        </div>

        {/* Drawer footer — connection status */}
        <div className="px-5 py-3" style={{ borderTop: '1px solid #0f0f20' }}>
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
    </>
  )
}
```

**Step 2: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
cd /root/claude/raido-src
git add web/src/components/DrawerNav.tsx
git commit -m "feat: add DrawerNav slide-out component with per-station gear icons"
```

---

## Task 4: Rewrite `Layout.tsx` — slim top bar, no nav bar

**Files:**
- Modify: `web/src/components/Layout.tsx`

**What it does:** Layout becomes a minimal shell. The horizontal nav bar is gone. The top bar is ~44px: hamburger left, RAIDO wordmark + station name right. Drawer is wired up. Mobile bottom nav is removed (drawer replaces it).

**Step 1: Replace Layout.tsx entirely**

```typescript
// web/src/components/Layout.tsx
import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MenuIcon, LogOut, LogIn } from 'lucide-react'
import { useRadioStore } from '../store/radioStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuthStore } from '../store/authStore'
import DrawerNav from './DrawerNav'

interface LayoutProps {
  children: React.ReactNode
  /** When true, renders children full-screen (no padding). Used by NowPlayingPage. */
  fullscreen?: boolean
}

export default function Layout({ children, fullscreen = false }: LayoutProps) {
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { isConnected, selectedStation } = useRadioStore((s) => ({
    isConnected: s.isConnected,
    selectedStation: s.selectedStation,
  }))
  const { isAuthenticated, clearAuth } = useAuthStore()
  useWebSocket()

  function handleLogout() {
    clearAuth()
    navigate('/login')
  }

  const stationLabel = selectedStation === 'main' ? '' : selectedStation.toUpperCase()

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--art-bg, #07070f)', transition: 'background 0.8s ease' }}>

      {/* Slim top bar */}
      <header
        className="sticky top-0 z-30 flex items-center justify-between px-4"
        style={{
          height: '44px',
          background: 'rgba(0,0,0,0.35)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        {/* Hamburger */}
        <button
          onClick={() => setDrawerOpen(true)}
          className="p-1.5 rounded-lg transition-colors"
          style={{ color: '#505070' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#505070' }}
          aria-label="Open navigation"
        >
          <MenuIcon className="w-5 h-5" />
        </button>

        {/* Wordmark + station */}
        <div className="flex items-center gap-2">
          {stationLabel && (
            <span className="font-mono text-xs" style={{ color: '#303050', letterSpacing: '0.1em', fontSize: '0.6rem' }}>
              {stationLabel}
            </span>
          )}
          <Link
            to="/now-playing"
            className="font-display font-bold tracking-widest text-white uppercase select-none"
            style={{ fontSize: '13px', letterSpacing: '0.22em' }}
          >
            RAIDO
          </Link>
          {/* Live dot */}
          {isConnected && (
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: '#4ade80', boxShadow: '0 0 5px rgba(74,222,128,0.7)' }}
            />
          )}
        </div>

        {/* Auth */}
        <div>
          {isAuthenticated() ? (
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 transition-colors"
              style={{ color: '#303050' }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#a0a0c0' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#303050' }}
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          ) : (
            <Link
              to="/login"
              className="p-1.5 transition-colors"
              style={{ color: '#303050' }}
            >
              <LogIn className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>
      </header>

      {/* Drawer */}
      <DrawerNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      {/* Content */}
      {fullscreen ? (
        <div className="flex-1 relative">
          {children}
        </div>
      ) : (
        <main className="flex-1 max-w-3xl w-full mx-auto px-4 sm:px-6 py-6">
          {children}
        </main>
      )}
    </div>
  )
}
```

**Step 2: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -30
```

**Step 3: Commit**

```bash
cd /root/claude/raido-src
git add web/src/components/Layout.tsx
git commit -m "feat: replace nav bar with slim top bar and drawer-only navigation"
```

---

## Task 5: Create `NowPlayingPage` — immersive full-screen view

**Files:**
- Create: `web/src/pages/NowPlayingPage.tsx`

**What it does:** Full-screen view. Blurred art fills the background. Crisp art centered on top. Title, artist, progress, commentary, skip overlaid. Uses `useArtColor` to drive CSS vars. Replaces the old `/now-playing` route composition.

**Step 1: Create the file**

```typescript
// web/src/pages/NowPlayingPage.tsx
import React from 'react'
import { Link } from 'react-router-dom'
import { SkipForwardIcon, MusicIcon } from 'lucide-react'
import { useNowPlaying } from '../hooks/useNowPlaying'
import { useRadioStore } from '../store/radioStore'
import { useArtColor } from '../hooks/useArtColor'
import { apiHelpers } from '../utils/api'
import { toast } from 'react-hot-toast'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMGQwZDFhIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iNjAiIGZpbGw9IiMxMzEzMjciLz4KPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTUwIiByPSIyMCIgZmlsbD0iIzFhMWEzMiIvPgo8L3N2Zz4K'

function fmt(s: number | null | undefined) {
  if (!s || isNaN(s)) return '0:00'
  const t = Math.floor(s)
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`
}

export default function NowPlayingPage() {
  const { data: nowPlaying, isLoading } = useNowPlaying()
  const { commentaryText, isGeneratingCommentary } = useRadioStore((s) => ({
    commentaryText: s.commentaryText,
    isGeneratingCommentary: s.isGeneratingCommentary,
  }))

  const track = nowPlaying?.track
  const progress = nowPlaying?.progress
  const total = track?.duration_sec ?? progress?.total_seconds ?? 0
  const [elapsed, setElapsed] = React.useState(progress?.elapsed_seconds ?? 0)
  const [isSkipping, setIsSkipping] = React.useState(false)

  // Drive color extraction from current artwork
  useArtColor(track?.artwork_url ?? null)

  React.useEffect(() => {
    setElapsed(progress?.elapsed_seconds ?? 0)
  }, [progress?.elapsed_seconds, track?.id])

  React.useEffect(() => {
    if (!track || !total) return
    const id = setInterval(() => setElapsed(p => Math.min(p + 1, total)), 1000)
    return () => clearInterval(id)
  }, [track?.id, total])

  async function handleSkip() {
    if (isSkipping) return
    setIsSkipping(true)
    try {
      await apiHelpers.skipTrack()
      toast.success('Skipped')
    } catch {
      toast.error('Failed to skip')
    } finally {
      setTimeout(() => setIsSkipping(false), 2000)
    }
  }

  const pct = total ? Math.min(100, (elapsed / total) * 100) : 0
  const remaining = total ? Math.max(0, total - elapsed) : 0
  const artSrc = track?.artwork_url || FALLBACK_ART

  return (
    <div
      className="relative flex flex-col items-center justify-center"
      style={{ minHeight: 'calc(100vh - 44px)', overflow: 'hidden' }}
    >
      {/* Full-bleed blurred art background */}
      <div
        className="absolute inset-0 -z-10"
        style={{
          backgroundImage: `url(${artSrc})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'blur(60px) saturate(0.6)',
          transform: 'scale(1.15)',
          opacity: 0.35,
          transition: 'background-image 1s ease',
        }}
      />
      {/* Dark vignette over the blurred bg */}
      <div
        className="absolute inset-0 -z-10"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.75) 100%)',
        }}
      />

      {/* Content */}
      <div className="flex flex-col items-center gap-5 px-6 w-full max-w-sm mx-auto">

        {/* Album art — crisp */}
        {isLoading ? (
          <div className="w-64 h-64 rounded-2xl skeleton" />
        ) : (
          <div
            className="relative rounded-2xl overflow-hidden"
            style={{
              width: 'min(280px, 72vw)',
              aspectRatio: '1',
              boxShadow: '0 20px 60px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.06)',
            }}
          >
            <img
              src={artSrc}
              alt={track?.album || track?.title || 'Album art'}
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).src = FALLBACK_ART }}
            />
            {/* ON AIR badge */}
            {nowPlaying?.is_playing && (
              <div
                className="absolute top-3 left-3 flex items-center gap-1.5 px-2 py-1 rounded-full"
                style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(8px)' }}
              >
                <span className="live-dot glow-live" style={{ width: '6px', height: '6px' }} />
                <span className="font-mono text-white uppercase" style={{ fontSize: '0.55rem', letterSpacing: '0.14em' }}>
                  Live
                </span>
              </div>
            )}
          </div>
        )}

        {/* Track info */}
        {track ? (
          <div className="text-center w-full space-y-1.5">
            {/* Title */}
            <h1
              className="font-display font-bold leading-tight"
              style={{ fontSize: 'clamp(1.3rem, 5vw, 1.75rem)', color: '#f0f0ff' }}
            >
              <Link
                to={`/media/tracks/${track.id}`}
                style={{ color: 'inherit' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--art-accent)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = '#f0f0ff' }}
              >
                {track.title}
              </Link>
            </h1>

            {/* Artist */}
            <p className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.55)' }}>
              {track.artist}
              {track.genre && <span style={{ color: 'rgba(255,255,255,0.25)' }}> · {track.genre}</span>}
            </p>
          </div>
        ) : !isLoading ? (
          <div className="text-center space-y-2">
            <MusicIcon className="w-10 h-10 mx-auto" style={{ color: '#252545' }} />
            <p className="font-display font-bold text-sm uppercase tracking-widest" style={{ color: '#404060' }}>
              Signal Lost
            </p>
          </div>
        ) : null}

        {/* Progress + controls */}
        {track && (
          <div className="w-full space-y-2">
            {/* EQ bars */}
            {nowPlaying?.is_playing && (
              <div className="flex items-end justify-center gap-0.5" style={{ height: '16px' }}>
                {[0,1,2,3,4,5,6].map(i => (
                  <div
                    key={i}
                    className="audio-bar rounded-sm"
                    style={{ width: '3px', animationDelay: `${i * -0.18}s`, background: 'var(--art-accent)' }}
                  />
                ))}
              </div>
            )}

            {/* Progress bar */}
            <div
              className="relative w-full overflow-hidden rounded-full"
              style={{ height: '2px', background: 'rgba(255,255,255,0.12)' }}
              role="progressbar"
              aria-valuenow={elapsed}
              aria-valuemin={0}
              aria-valuemax={total}
            >
              <div
                className="absolute left-0 top-0 h-full rounded-full progress-fill"
                style={{
                  width: `${pct}%`,
                  background: 'var(--art-accent)',
                  boxShadow: '0 0 8px var(--art-accent)',
                }}
              />
            </div>

            {/* Time codes */}
            <div className="flex justify-between font-mono" style={{ color: 'rgba(255,255,255,0.3)', fontSize: '0.65rem' }}>
              <span>{fmt(elapsed)}</span>
              <span>−{fmt(remaining)}</span>
            </div>
          </div>
        )}

        {/* DJ Commentary */}
        {(commentaryText || isGeneratingCommentary) && (
          <div
            className="w-full rounded-xl px-4 py-3 text-center"
            style={{
              background: 'rgba(0,0,0,0.4)',
              backdropFilter: 'blur(8px)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.6)', fontStyle: 'italic' }}>
              {commentaryText}
              {isGeneratingCommentary && (
                <span
                  className="inline-block w-0.5 h-3.5 ml-0.5 align-middle rounded-sm"
                  style={{ background: 'var(--art-accent)', animation: 'blink 1s step-end infinite' }}
                />
              )}
            </p>
          </div>
        )}

        {/* Skip button */}
        {track && (
          <button
            onClick={handleSkip}
            disabled={isSkipping}
            className="flex items-center gap-2 px-5 py-2 rounded-xl font-mono uppercase text-xs transition-all"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(255,255,255,0.3)',
              letterSpacing: '0.1em',
              cursor: isSkipping ? 'not-allowed' : 'pointer',
            }}
            onMouseEnter={e => {
              if (!isSkipping) {
                const el = e.currentTarget as HTMLElement
                el.style.borderColor = 'var(--art-accent)'
                el.style.color = 'var(--art-accent)'
              }
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLElement
              el.style.borderColor = 'rgba(255,255,255,0.08)'
              el.style.color = 'rgba(255,255,255,0.3)'
            }}
          >
            {isSkipping ? (
              <span className="w-3 h-3 rounded-full border border-t-transparent border-current animate-spin" />
            ) : (
              <SkipForwardIcon className="w-3.5 h-3.5" />
            )}
            <span>{isSkipping ? 'Skipping' : 'Skip'}</span>
          </button>
        )}
      </div>
    </div>
  )
}
```

**Step 2: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -30
```

**Step 3: Commit**

```bash
cd /root/claude/raido-src
git add web/src/pages/NowPlayingPage.tsx
git commit -m "feat: add immersive full-screen NowPlayingPage with art color extraction"
```

---

## Task 6: Create `LibraryPage` — Browse + Enrich tabs

**Files:**
- Create: `web/src/pages/LibraryPage.tsx`

**What it does:** Single page with two tabs: Browse (MediaLibrary) and Enrich (MBEnrich). Tab state driven by `?tab=browse` or `?tab=enrich` URL param so it's bookmarkable and the browser back button works.

**Step 1: Create the file**

```typescript
// web/src/pages/LibraryPage.tsx
import React from 'react'
import { useSearchParams } from 'react-router-dom'
import MediaLibrary from '../components/MediaLibrary'
import MBEnrich from '../components/MBEnrich'

type Tab = 'browse' | 'enrich'

export default function LibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') as Tab) || 'browse'

  function setTab(t: Tab) {
    setSearchParams({ tab: t }, { replace: true })
  }

  return (
    <div className="space-y-4">
      {/* Tab switcher */}
      <div
        className="flex gap-1 p-1 rounded-xl w-fit"
        style={{ background: 'rgba(13,13,26,0.8)', border: '1px solid #1a1a32' }}
      >
        {(['browse', 'enrich'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-4 py-1.5 rounded-lg text-xs font-display font-bold uppercase transition-all"
            style={{
              letterSpacing: '0.12em',
              background: tab === t ? 'rgba(56,189,248,0.12)' : 'transparent',
              color: tab === t ? '#38bdf8' : '#404060',
              border: tab === t ? '1px solid rgba(56,189,248,0.2)' : '1px solid transparent',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'browse' && <MediaLibrary />}
      {tab === 'enrich' && <MBEnrich />}
    </div>
  )
}
```

**Step 2: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
cd /root/claude/raido-src
git add web/src/pages/LibraryPage.tsx
git commit -m "feat: add LibraryPage combining Browse and Enrich tabs"
```

---

## Task 7: Update `App.tsx` — new routes, fullscreen layout for NowPlayingPage

**Files:**
- Modify: `web/src/App.tsx`

**Step 1: Replace App.tsx**

```typescript
// web/src/App.tsx
import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import NowPlayingPage from './pages/NowPlayingPage'
import TTSMonitor from './components/TTSMonitor'
import Analytics from './components/Analytics'
import LoginPage from './components/LoginPage'
import LibraryPage from './pages/LibraryPage'

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Navigate to="/now-playing" replace />} />

        {/* Full-screen immersive view */}
        <Route
          path="/now-playing"
          element={
            <Layout fullscreen>
              <NowPlayingPage />
            </Layout>
          }
        />

        {/* DJ Admin — per station */}
        <Route
          path="/raido/admin"
          element={
            <Layout>
              <TTSMonitor />
            </Layout>
          }
        />
        <Route
          path="/:station/admin"
          element={
            <Layout>
              <TTSMonitor />
            </Layout>
          }
        />

        {/* Library — browse + enrich */}
        <Route
          path="/library"
          element={
            <Layout>
              <LibraryPage />
            </Layout>
          }
        />

        {/* Media track deep-link — redirect to library */}
        <Route path="/media/tracks/:trackId" element={<Navigate to="/library" replace />} />

        {/* Analytics */}
        <Route
          path="/analytics"
          element={
            <Layout>
              <Analytics />
            </Layout>
          }
        />

        {/* Auth */}
        <Route
          path="/login"
          element={
            <Layout>
              <LoginPage />
            </Layout>
          }
        />

        {/* Legacy redirects */}
        <Route path="/tts" element={<Navigate to="/raido/admin" replace />} />
        <Route path="/media" element={<Navigate to="/library" replace />} />
        <Route path="/raido/enrich" element={<Navigate to="/library?tab=enrich" replace />} />
        <Route path="/stations" element={<Navigate to="/now-playing" replace />} />
        <Route path="/transcripts" element={<Navigate to="/raido/admin" replace />} />
        <Route path="/history" element={<Navigate to="/now-playing" replace />} />

        {/* 404 */}
        <Route
          path="*"
          element={
            <Layout>
              <div className="card p-12 flex flex-col items-center gap-2 text-center mt-8">
                <p className="text-4xl font-bold" style={{ color: '#1a1a32' }}>404</p>
                <p className="text-sm font-medium" style={{ color: '#404060' }}>Page not found</p>
              </div>
            </Layout>
          }
        />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
```

**Step 2: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -30
```

**Step 3: Commit**

```bash
cd /root/claude/raido-src
git add web/src/App.tsx
git commit -m "feat: update routes — new immersive layout, library page, legacy redirects"
```

---

## Task 8: Update `index.css` — body background uses CSS var, audio bar uses art accent

**Files:**
- Modify: `web/src/index.css`

**Step 1: Update body background**

Change the `body` block to use `--art-bg`:

```css
body {
  @apply antialiased;
  background-color: var(--art-bg, #07070f);
  color: #ddddf0;
  transition: background-color 0.8s ease;
}
```

Remove the existing `background-image: radial-gradient(...)` from body (that effect now comes from the blurred art in NowPlayingPage).

**Step 2: Update `.audio-bar` to use `--art-accent`**

```css
.audio-bar {
  background: var(--art-accent, #38bdf8);
  border-radius: 9999px;
  animation: audioBar 1.5s ease-in-out infinite alternate;
}
```

**Step 3: Type-check + build**

```bash
cd /root/claude/raido-src/web && npm run build 2>&1 | tail -20
```

Expected: successful build, no errors.

**Step 4: Commit**

```bash
cd /root/claude/raido-src
git add web/src/index.css
git commit -m "feat: wire body background and audio bars to CSS art color vars"
```

---

## Task 9: Fix media track deep-link — Library needs to handle trackId URL param

**Files:**
- Modify: `web/src/pages/LibraryPage.tsx`
- Modify: `web/src/App.tsx`

**Background:** The old `/media/tracks/:trackId` route deep-linked into MediaLibrary. The redirect in Task 7 loses the trackId. Fix this properly.

**Step 1: Update the route in App.tsx**

Replace:
```typescript
<Route path="/media/tracks/:trackId" element={<Navigate to="/library" replace />} />
```

With:
```typescript
<Route
  path="/media/tracks/:trackId"
  element={
    <Layout>
      <LibraryPage />
    </Layout>
  }
/>
```

**Step 2: Type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
cd /root/claude/raido-src
git add web/src/App.tsx
git commit -m "fix: preserve trackId deep-link through library route"
```

---

## Task 10: Full build, deploy, smoke test

**Step 1: Final type-check**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit
```

Expected: zero errors.

**Step 2: Production build**

```bash
cd /root/claude/raido-src/web && npm run build 2>&1 | tail -10
```

Expected: `✓ built in Xs`

**Step 3: Push branch**

```bash
cd /root/claude/raido-src
git push origin frontend-redesign
```

**Step 4: Deploy to PCT 127**

```bash
pct exec 127 -- bash -c "cd /opt/raido && git pull raido frontend-redesign && docker compose build web && docker compose up -d --no-build web"
```

**Step 5: Smoke test checklist**

Visit `http://192.168.1.41` and verify:
- [ ] Full-screen album art background visible on Now Playing
- [ ] Background color shifts after a track change (within ~10s)
- [ ] `≡` hamburger opens drawer from left
- [ ] All active stations listed in drawer
- [ ] Gear icon next to each station navigates to that station's DJ Admin
- [ ] Clicking station name switches selected station context
- [ ] Library link in drawer opens `/library?tab=browse`
- [ ] Browse tab shows track list
- [ ] Enrich tab shows MBEnrich
- [ ] DJ Admin loads for correct station
- [ ] Old routes `/stations`, `/transcripts` redirect correctly
- [ ] Skip button works on Now Playing

**Step 6: Commit any fixes, then push**

```bash
cd /root/claude/raido-src
git push origin frontend-redesign
```

---

## Cleanup (after smoke test passes)

These files are now dead code. Remove them:

```bash
cd /root/claude/raido-src/web/src
# Safe to delete — replaced or redirected
rm components/StationControlPanel.tsx
rm components/CommentaryBrowser.tsx
# NowPlaying, ComingUp, PlayHistory still exist but are no longer routed
# Keep them for now — they may be useful for the listener mode later
```

```bash
git add -A
git commit -m "chore: remove obsolete StationControlPanel and CommentaryBrowser components"
```

---

## Notes for the Implementer

- **CSS vars `--art-bg` / `--art-accent`**: Set on `document.documentElement` by `useArtColor`. Any component can use them via `style={{ color: 'var(--art-accent)' }}`.
- **`fullscreen` prop on Layout**: When true, content fills the remaining viewport height without padding. NowPlayingPage uses this; all other pages don't.
- **Station switching in drawer**: `setSelectedStation` updates Zustand + localStorage. `TTSMonitor` reads `selectedStation` from the store via `useParams` already — no changes needed there as the URL reflects the station.
- **`useArtColor` and CORS**: Album art is served from iTunes CDN or the local Raido server. iTunes images may not have CORS headers. If Canvas throws a SecurityError, the hook catches it and falls back to the default color. This is handled in the `try/catch` block.
- **No new npm packages**: Everything uses existing dependencies.
