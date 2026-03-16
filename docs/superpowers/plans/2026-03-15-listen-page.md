# Listen Page Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public `/listen` route with a full-screen immersive audio player — no login required — so anyone can stream Raido from a browser.

**Architecture:** A new `GET /api/v1/stream/guest-token` endpoint issues short-lived stream tokens without auth (rate-limited). A new `ListenPage.tsx` page fetches that token, polls now-playing data directly via React Query (station hardcoded to `'main'`), and drives an `<audio>` element pointing at the Icecast stream. Route added to `App.tsx` outside `<RequireAuth>`.

**Tech Stack:** FastAPI + slowapi (backend), React + TypeScript + Tailwind + React Query (frontend), existing `useArtColor` hook, existing `FALLBACK_ART` constant pattern from `NowPlayingPage`.

---

## Chunk 1: Backend — guest stream token endpoint

### Task 1: Fix validate endpoint + add guest-token route

**Files:**
- Modify: `services/api/app/api/v1/endpoints/stream.py`

- [ ] **Step 1: Fix the validate endpoint's defensive `.get()`**

In `stream.py` line 62, change:
```python
headers = {"X-User-Id": str(payload["user_id"])}
```
to:
```python
headers = {"X-User-Id": str(payload.get("user_id", ""))}
```
This prevents a `KeyError` if a malformed token somehow passes `validate_stream_token` without a `user_id` key. For `user_id=0` (guest tokens), this is a no-op — `0` is a valid dict value.

- [ ] **Step 2: Add the guest-token endpoint**

Add this import at the top of `stream.py` (after existing imports):
```python
from app.core.limiter import limiter
```

Also add `settings` to the existing imports at the top of the file:
```python
from app.core.config import settings
```
(Check if it's already imported — if so, skip.)

Then add this endpoint after the existing `/token` route:
```python
@router.get("/guest-token")
@limiter.limit("20/minute")
async def get_guest_stream_token(request: Request):
    """Issue a short-lived stream token for unauthenticated (guest) listeners."""
    token = create_stream_token(user_id=0)
    return {"token": token, "expires_in": settings.STREAM_TOKEN_EXPIRE_MINUTES * 60}
```

Note: `request: Request` is required as the first parameter for slowapi rate limiting to work — it reads the client IP from the request object.

- [ ] **Step 3: Verify the endpoint works manually**

```bash
curl -s http://192.168.1.41/api/v1/stream/guest-token | python3 -m json.tool
```
Expected output (approximately):
```json
{
    "token": "eyJ...",
    "expires_in": 900
}
```

- [ ] **Step 4: Commit**

```bash
git add services/api/app/api/v1/endpoints/stream.py
git commit -m "feat: add public guest-token stream endpoint, harden validate endpoint"
```

---

## Chunk 2: Frontend — ListenPage + routing

### Task 2: Create ListenPage.tsx

**Files:**
- Create: `web/src/pages/ListenPage.tsx`

- [ ] **Step 1: Create the file**

```tsx
// web/src/pages/ListenPage.tsx
import React from 'react'
import { Loader2, Play, Pause, MusicIcon } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api, apiHelpers } from '../utils/api'
import { useArtColor } from '../hooks/useArtColor'
import { NowPlaying } from '../store/radioStore'

const FALLBACK_ART = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDMwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIzMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMGQwZDFhIi8+CjxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iNjAiIGZpbGw9IiMxMzEzMjciLz4KPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTUwIiByPSIyMCIgZmlsbD0iIzFhMWEzMiIvPgo8L3N2Zz4K'

const BASE_STREAM_URL: string = (() => {
  const configured = ((import.meta as any)?.env?.VITE_STREAM_URL as string | undefined)?.trim()
  return configured && configured.length > 0 ? configured : '/stream/raido.mp3'
})()

export default function ListenPage() {
  const audioRef = React.useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = React.useState(false)
  const [isBuffering, setIsBuffering] = React.useState(false)
  const [streamToken, setStreamToken] = React.useState<string | null>(null)
  const [tokenError, setTokenError] = React.useState(false)
  const [tokenLoading, setTokenLoading] = React.useState(true)
  const refreshRef = React.useRef<ReturnType<typeof setInterval> | null>(null)

  // Poll now-playing data — station hardcoded to 'main', no Zustand dependency
  const { data: nowPlaying } = useQuery<NowPlaying>({
    queryKey: ['listenPageNowPlaying'],
    queryFn: () => api.get('/now', { params: { station: 'main' } }).then(r => r.data),
    refetchInterval: 10000,
    staleTime: 5000,
    retry: 3,
  })

  const track = nowPlaying?.track
  const artSrc = track?.artwork_url
    ? apiHelpers.resolveStaticUrl(track.artwork_url) ?? FALLBACK_ART
    : FALLBACK_ART

  useArtColor(track?.artwork_url ?? null)

  // Fetch guest token on mount, schedule refresh
  const fetchToken = React.useCallback(async () => {
    try {
      // Use native fetch so axios interceptors (auth redirect, toast errors) don't fire
      const res = await fetch(apiHelpers.apiUrl('/api/v1/stream/guest-token'))
      if (!res.ok) throw new Error('Failed')
      const data = await res.json() as { token: string; expires_in: number }
      setStreamToken(data.token)
      setTokenError(false)
      setTokenLoading(false)
      // Schedule next refresh at 80% of TTL
      if (refreshRef.current) clearInterval(refreshRef.current)
      refreshRef.current = setInterval(fetchToken, data.expires_in * 0.8 * 1000)
    } catch {
      setTokenError(true)
      setTokenLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void fetchToken()
    return () => {
      if (refreshRef.current) clearInterval(refreshRef.current)
    }
  }, [fetchToken])

  // Wire up audio element events
  React.useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    const onPlay = () => { setIsPlaying(true); setIsBuffering(false) }
    const onPause = () => setIsPlaying(false)
    const onWaiting = () => setIsBuffering(true)
    const onPlaying = () => setIsBuffering(false)
    const onStalled = () => setIsBuffering(true)
    const onError = () => { setIsPlaying(false); setIsBuffering(false) }
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('waiting', onWaiting)
    audio.addEventListener('playing', onPlaying)
    audio.addEventListener('stalled', onStalled)
    audio.addEventListener('error', onError)
    return () => {
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('waiting', onWaiting)
      audio.removeEventListener('playing', onPlaying)
      audio.removeEventListener('stalled', onStalled)
      audio.removeEventListener('error', onError)
    }
  }, [])

  const streamUrl = streamToken ? `${BASE_STREAM_URL}?token=${streamToken}` : undefined

  const handleToggle = React.useCallback(async () => {
    const audio = audioRef.current
    if (!audio || !streamUrl) return
    if (isPlaying) {
      audio.pause()
    } else {
      setIsBuffering(true)
      try { await audio.play() } catch { setIsBuffering(false) }
    }
  }, [isPlaying, streamUrl])

  const playButtonDisabled = tokenLoading || tokenError || !streamUrl
  const playButtonTitle = tokenError ? 'Stream unavailable' : tokenLoading ? 'Loading…' : undefined

  return (
    <div
      className="relative flex flex-col items-center justify-center"
      style={{ minHeight: '100dvh', overflow: 'hidden', background: 'var(--art-bg)' }}
    >
      {/* Blurred artwork background */}
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
      {/* Dark vignette */}
      <div
        className="absolute inset-0 -z-10"
        style={{ background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.75) 100%)' }}
      />

      {/* RAIDO wordmark */}
      <span
        className="absolute top-5 font-display font-bold tracking-widest uppercase"
        style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.25)', letterSpacing: '0.3em' }}
      >
        RAIDO
      </span>

      {/* Main content */}
      <div className="flex flex-col items-center gap-6 px-6 w-full max-w-xs mx-auto">

        {/* Album art */}
        <div
          className="rounded-2xl overflow-hidden"
          style={{
            width: 'clamp(180px, 40vw, 280px)',
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
        </div>

        {/* Track info */}
        {track ? (
          <div className="text-center w-full space-y-1">
            <h1
              className="font-display font-bold leading-tight"
              style={{ fontSize: 'clamp(1.2rem, 5vw, 1.6rem)', color: '#f0f0ff' }}
            >
              {track.title}
            </h1>
            <p className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>
              {track.artist}
            </p>
          </div>
        ) : (
          <div className="text-center space-y-2">
            <MusicIcon className="w-8 h-8 mx-auto" style={{ color: '#252545' }} />
            <p className="font-display font-bold text-xs uppercase tracking-widest" style={{ color: '#404060' }}>
              Loading…
            </p>
          </div>
        )}

        {/* LIVE badge + play button */}
        <div className="flex flex-col items-center gap-3">
          {nowPlaying?.is_playing && (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-green-400 bg-green-500/10 border border-green-500/20 px-2.5 py-1 rounded-full">
              <span className="live-dot" />
              LIVE
            </span>
          )}

          <button
            type="button"
            onClick={handleToggle}
            disabled={playButtonDisabled}
            title={playButtonTitle}
            className="flex items-center justify-center rounded-full transition"
            style={{
              width: '56px',
              height: '56px',
              background: playButtonDisabled ? 'rgba(255,255,255,0.08)' : 'var(--art-accent)',
              cursor: playButtonDisabled ? 'not-allowed' : 'pointer',
              boxShadow: playButtonDisabled ? 'none' : '0 4px 24px color-mix(in srgb, var(--art-accent) 50%, transparent)',
              opacity: playButtonDisabled ? 0.5 : 1,
            }}
            aria-label={isPlaying ? 'Pause' : 'Play live stream'}
          >
            {tokenLoading || isBuffering ? (
              <Loader2 className="w-6 h-6 text-white animate-spin" />
            ) : isPlaying ? (
              <Pause className="w-6 h-6 text-white" />
            ) : (
              <Play className="w-6 h-6 text-white pl-0.5" />
            )}
          </button>

          {tokenError && (
            <p className="text-xs text-red-400 text-center">Stream unavailable</p>
          )}
        </div>
      </div>

      <audio ref={audioRef} src={streamUrl} preload="none" className="hidden" />
    </div>
  )
}
```

- [ ] **Step 2: Verify it compiles (TypeScript check)**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -30
```
Expected: no errors (or only pre-existing errors unrelated to ListenPage).

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/ListenPage.tsx
git commit -m "feat: add ListenPage public audio player"
```

---

### Task 3: Add `/listen` route to App.tsx

**Files:**
- Modify: `web/src/App.tsx`

- [ ] **Step 1: Add import for ListenPage**

At the top of `App.tsx`, add after the existing page imports:
```tsx
import ListenPage from './pages/ListenPage'
```

- [ ] **Step 2: Add the route before `<RequireAuth>`**

In `App.tsx`, the public routes block currently ends at:
```tsx
<Route path="/register" element={<RegisterPage />} />
```

Add the `/listen` route immediately after it, before the `<Route element={<RequireAuth />}>` line:
```tsx
<Route path="/listen" element={<ListenPage />} />
```

Final public routes block should look like:
```tsx
{/* Public routes */}
<Route path="/login" element={<LoginPage />} />
<Route path="/register" element={<RegisterPage />} />
<Route path="/listen" element={<ListenPage />} />
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd /root/claude/raido-src/web && npx tsc --noEmit 2>&1 | head -30
```
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/App.tsx
git commit -m "feat: register /listen as public route"
```

---

## Chunk 3: Deploy and verify

### Task 4: Build, push, deploy

- [ ] **Step 1: Push to origin and Gitea**

```bash
git push origin redesign-with-auth
git push gitea redesign-with-auth
```

- [ ] **Step 2: Pull on PCT 127**

```bash
pct exec 127 -- bash -c "cd /opt/raido && git pull raido redesign-with-auth"
```

Note: This pulls the `redesign-with-auth` feature branch. PCT 127's remote (`raido`) tracks GitHub. If this branch has been merged to `main` before deploying, use `git pull raido main` instead.

- [ ] **Step 3: Build API and web containers**

```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose build api web"
```

- [ ] **Step 4: Restart services**

```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose up -d api web"
```

- [ ] **Step 5: Check containers came up cleanly**

```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose ps && docker compose logs api --tail 20"
```
Expected: `api` and `web` containers show `running`, no Python tracebacks in API logs.

- [ ] **Step 6: Smoke test guest-token endpoint**

```bash
curl -s http://192.168.1.41/api/v1/stream/guest-token | python3 -m json.tool
```
Expected:
```json
{
    "token": "eyJ...",
    "expires_in": 900
}
```

- [ ] **Step 7: Open listen page in browser**

Navigate to `http://192.168.1.41/listen`

Verify:
- Page loads without redirect to `/login`
- Album art and track info display
- LIVE badge is green
- Play button works and audio streams
- Page looks good on mobile (resize browser or use devtools)
