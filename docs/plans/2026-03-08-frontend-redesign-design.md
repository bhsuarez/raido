# Raido Frontend Redesign — Design Document
**Date:** 2026-03-08
**Branch:** `frontend-redesign`
**Status:** Approved, ready for implementation

---

## Problem Statement

The current Raido frontend is a traditional nav-bar dashboard. It has too many top-level pages, a broken station-switching workflow, and doesn't reflect the primary use case: a single admin monitoring and tuning an AI radio station across multiple stations. The UI fights for attention instead of receding behind the content.

---

## Goals

- Album art is the visual centerpiece — colors, gradients, and text all derive from it
- Navigation is hidden by default, revealed on demand
- Station context is first-class — switching stations updates everything globally
- Remove noise: fewer pages, fewer clicks to reach common tasks
- Lay the groundwork for a future public listener mode (Now Playing only)

---

## Non-Goals

- Listener mode implementation (future work)
- Authentication/permissions UI changes
- Backend API changes
- Mobile app

---

## Design

### Screen Structure

The default view is full-screen Now Playing. The album art fills the entire background — blurred, darkened, with a gradient vignette. On top of it:

- **Top bar** (slim, ~44px): hamburger `≡` left, station name + RAIDO wordmark right. Tinted by extracted art color.
- **Center**: crisp album art (~280px square, not blurred), track title in Syne display font, artist/genre below
- **Bottom**: thin progress bar (art-tinted), elapsed/remaining in mono, DJ commentary text when available, skip button

### Navigation Drawer

Single `≡` opens a drawer sliding in from the left (~320px wide, 75% on mobile). Background behind drawer dims but blurred art remains visible. Clicking outside closes it.

Drawer contents (top to bottom):
1. **STATIONS** section header
   - List of all active stations, each with: live dot (if playing), station name, `⚙` gear icon
   - Active/selected station highlighted
   - Clicking station name switches global station context (updates Now Playing art/colors)
   - Clicking `⚙` opens that station's DJ Admin and closes drawer
2. **LIBRARY** nav item — opens Library view
3. **NOW PLAYING** nav item — closes drawer, returns to full-screen art view

### Station Context

A `selectedStation` value lives in global state (Zustand) and localStorage. All pages — Now Playing, DJ Admin, Library — read from it. Switching stations in the drawer immediately:
- Updates the Now Playing view (new art, new track, new colors)
- Changes which station's DJ Admin the `⚙` button opens
- Filters Library by station if applicable

### DJ Admin View

Replaces the full-screen art view. Top bar shows `← Now Playing` back button + `STATION · DJ ADMIN`. The `≡` drawer is still accessible to switch stations.

Sections (scrollable):
1. **Commentary** — provider dropdown, max duration
2. **Voice & TTS** — provider, voice, speed, test button + inline audio player
3. **Recent Commentary** — compact activity log (status icon, text preview, timestamp). Replaces the separate Transcripts page.
4. **Stats summary** — single row: success rate %, avg gen time, 24h count

### Library View

Replaces the full-screen art view. Top bar shows `← Now Playing` + `LIBRARY`. Two tabs:

- **Browse** — search bar, filter chips (genre, artist, sort), track list with artwork thumbnail + voicing status badge. Tapping a track opens a detail panel (slide-up on mobile, right panel on desktop) with metadata editor, MusicBrainz search, and voicing controls.
- **Enrich** — the existing MBEnrich review flow (current track, candidates, approve/skip/reject, keyboard shortcuts)

### Color Extraction

On every track change, an offscreen HTML5 Canvas samples the album artwork to extract the dominant color. The extracted color is:
- **Darkened + desaturated** (`hsl(h, s*0.3, l*0.15)`) for background gradient
- **Lightened accent** (`hsl(h, s*0.8, 65%)`) for progress bar, active dots, links
- Applied via CSS custom properties (`--art-bg`, `--art-accent`) with `transition: 0.8s ease`
- Fallback: `#07070f` when no artwork

Implementation: `useArtColor(artworkUrl)` hook using canvas pixel sampling. No external library.

---

## Pages Removed

| Removed | Reason |
|---|---|
| `/stations` (StationControlPanel) | Replaced by drawer station list |
| `/transcripts` (CommentaryBrowser) | Commentary log moved into DJ Admin |
| Separate `/raido/enrich` route | Merged into Library as a tab |

## Pages Merged

| Before | After |
|---|---|
| `/media` + `/raido/enrich` | `/library` with Browse + Enrich tabs |
| `/raido/admin` + `/:station/admin` | DJ Admin opens from drawer `⚙`, station in URL |

---

## Component Plan

### New / Heavily Modified
- `Layout.tsx` — remove nav bar entirely, add drawer + top bar
- `NowPlayingPage.tsx` — full-screen immersive view (replaces current NowPlaying + page shell)
- `DrawerNav.tsx` — slide-out station list + nav
- `useArtColor.ts` — canvas-based dominant color extraction hook
- `LibraryPage.tsx` — Browse + Enrich tabs combined

### Carried Forward (minor updates)
- `TTSMonitor.tsx` → becomes `DJAdminPage.tsx`, add commentary log section
- `TrackMetadataPanel.tsx` — unchanged logic, new visual treatment
- `MBEnrich.tsx` — unchanged logic, lives inside LibraryPage Enrich tab
- `CommentaryTranscript.tsx` — simplified, integrated into NowPlayingPage

### Removed
- `StationControlPanel.tsx`
- `CommentaryBrowser.tsx`

---

## Future: Listener Mode

When implemented, unauthenticated users see only the full-screen Now Playing view. The `≡` hamburger and drawer are hidden. Listeners get: art, track info, progress, commentary. Nothing else.

---

## Open Questions

- Should the drawer show per-station now-playing info (current track thumbnail) next to each station name? Nice-to-have, adds API calls per station.
- Desktop layout: should DJ Admin and Library use the full viewport or be capped at max-width like today?
