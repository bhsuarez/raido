# Listen Page Design

**Date:** 2026-03-15
**Status:** Approved

## Summary

Add a public `/listen` route — no login required — so anyone can open a browser and stream Raido. The existing Triode/Icecast URL keeps working unchanged. This page also works as a shareable link.

## Visual Design

Full-screen immersive layout matching the existing `NowPlayingPage`:
- Dark background (`#07070f`) with blurred artwork-driven color accent behind artwork
- Centered album art responsive to `clamp(180px, 40vw, 280px)`
- Track title + artist below artwork
- Green LIVE badge
- Large play/pause button (44px, primary cyan color)
- `RAIDO` wordmark at top — a `<span>`, not a React Router `<Link>` (no redirect to auth-protected routes)
- No header, no navigation drawer — standalone page
- Mobile-first, single-column layout

## Architecture

### New files
- `web/src/pages/ListenPage.tsx` — the full page component

### Changed files
- `web/src/App.tsx` — add `/listen` route **outside and before** the `<RequireAuth>` wrapper. The current app wraps the 404 catch-all inside `<RequireAuth>`, so `/listen` must be placed explicitly above that wrapper or it silently redirects to `/login`.
- `services/api/app/api/v1/endpoints/stream.py` — add `GET /api/v1/stream/guest-token`; fix `str(payload["user_id"])` → `str(payload.get("user_id", ""))` in the validate endpoint (defensive hardening)

### Data flow
1. Page mounts → fetches guest stream token (`GET /api/v1/stream/guest-token`). Play button shows a loading spinner during this fetch.
2. Token arrives → play button becomes active. Token refresh scheduled at `720000` ms (12 min), matching `RadioPlayer`.
3. `useNowPlaying` polling hook fetches now-playing data every 10s, called with `station='main'` hardcoded (do not read from `useRadioStore` — the listen page is always main station).
4. User clicks play → `<audio>` streams `/stream/raido.mp3?token={guestToken}`
5. If token fetch fails → play button renders disabled with "Stream unavailable". No retry.

### Guest token endpoint

`GET /api/v1/stream/guest-token` — no auth required. Rate-limited (same limit as other public endpoints in `limiter.py`). Calls `create_stream_token(user_id=0)` using `0` as the guest sentinel. Returns `{"token": "...", "expires_in": <seconds>}`.

### Now-playing data

Use `useNowPlaying` polling hook only (no WebSocket). Pass `station='main'` directly rather than reading from `useRadioStore`, so the listen page is isolated from any station the logged-in user may have selected in another tab.

### CORS note

`useArtColor` uses canvas `drawImage` with `crossOrigin = 'anonymous'`. Same behavior as the authenticated `NowPlayingPage` — already working for iTunes artwork URLs.

## What's out of scope
- Track history / queue display
- Skip button (admin-only feature)
- DJ commentary display
- Volume control (browser native controls suffice)
- Listener session tracking (guests are anonymous)
- Station selection (always plays main station)
