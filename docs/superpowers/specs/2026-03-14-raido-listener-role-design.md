# Raido Listener Role & Analytics Design

**Date:** 2026-03-14
**Status:** Approved
**Branch:** `feature/listener-role`

---

## Overview

Enable Raido to be shared with a small group of friends before making it public. Friends self-register, get a Pingos notification sent to the admin for approval, and once approved can listen and switch stations. Only registered and approved users can access the stream. The admin gets a listener analytics page showing active sessions, session history, duration, IP-based location, and device metadata.

---

## Goals

- Real stream access enforcement (not just UI-gating)
- Self-registration with admin approval gate
- Listener session tracking: duration, location (IP geo), device metadata
- Admin pages: user management + listener session analytics
- Listener UI: now playing, station switcher, play history, commentary transcripts only
- Admin Pingos notification on new registration

---

## Non-Goals

- Email verification or email-based invites
- OIDC / social login
- Redis-backed immediate token revocation (short TTL is sufficient for friend group)
- Stream re-encoding or full stream proxy through FastAPI

---

## Architecture

### Stream Access Gating

The Icecast stream is currently accessible directly on port 8000. After this change:

1. Icecast binds to Docker-internal only (not exposed on host port 8000)
2. All stream access routes through Caddy
3. Caddy uses `forward_auth` to validate a short-lived stream token before proxying to Icecast
4. The API issues stream tokens via `GET /api/v1/stream/token` (requires valid user JWT)
5. The React player appends the token as a query param to the audio `src`
6. The frontend silently refreshes the stream token every 10 minutes

Stream token properties:
- TTL: 15 minutes
- Signed with a separate `STREAM_TOKEN_SECRET` (not the main JWT secret)
- Payload: `{ user_id, exp, type: "stream" }`
- Validated by `GET /api/v1/stream/validate?token=<t>` (called by Caddy forward_auth)

### Caddy Configuration

```
route /stream/* {
  forward_auth http://api:8000 {
    uri /api/v1/stream/validate?token={query.token}
    copy_headers X-User-Id
  }
  reverse_proxy icecast:8000
}
```

---

## Data Model

### User State Machine

```
POST /auth/register
  → is_active=False, is_verified=False, role=listener  [pending]

POST /api/v1/admin/users/{id}/approve
  → is_active=True, is_verified=True  [active]

POST /api/v1/admin/users/{id}/suspend
  → is_active=False  [suspended]
```

The existing `User` model already has all required columns (`role`, `is_active`, `is_verified`, `deleted_at`). No migration needed for the users table.

### New Table: `listener_sessions`

```sql
CREATE TABLE listener_sessions (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    station         VARCHAR(100) NOT NULL,

    -- Timing
    started_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_heartbeat_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    ended_at            TIMESTAMP WITH TIME ZONE,
    duration_seconds    INTEGER,  -- written on session close

    -- Location (IP geo)
    ip_address      VARCHAR(45),
    city            VARCHAR(100),
    region          VARCHAR(100),
    country         VARCHAR(100),
    country_code    VARCHAR(2),
    latitude        FLOAT,
    longitude       FLOAT,

    -- Device metadata
    user_agent      TEXT,
    browser         VARCHAR(100),
    os              VARCHAR(100),
    device_type     VARCHAR(20)  -- mobile, tablet, desktop
);

CREATE INDEX ON listener_sessions (user_id);
CREATE INDEX ON listener_sessions (started_at);
CREATE INDEX ON listener_sessions (ended_at) WHERE ended_at IS NULL;
```

### Session State

A session is considered **active** when:
- `ended_at IS NULL`
- `last_heartbeat_at > now() - interval '90 seconds'`

A background task runs every 60 seconds and closes stale sessions:
```python
UPDATE listener_sessions
SET ended_at = last_heartbeat_at,
    duration_seconds = EXTRACT(EPOCH FROM (last_heartbeat_at - started_at))::int
WHERE ended_at IS NULL
  AND last_heartbeat_at < now() - interval '90 seconds'
```

---

## API Endpoints

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | Public | Self-register. Creates pending user. Fires Pingos notify. |
| POST | `/auth/login` | Public | Existing — unchanged |
| GET | `/auth/me` | JWT | Fix to return current user profile (id, email, role, is_active) |

Registration rate limit: 5 requests/hour per IP (via `slowapi`).

Pingos notification on register:
```
POST http://192.168.1.116:8090/api/notify
{"message": "New Raido registration: <name> (<email>) is waiting for approval."}
```

### Stream Tokens

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/stream/token` | JWT (active user) | Issues 15-min stream token |
| GET | `/api/v1/stream/validate` | None (called by Caddy) | Validates `?token=` query param. Returns 200 or 401. |

### Listener Sessions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/listeners/sessions` | JWT | Start a session. Geolocates IP. Returns `session_id`. |
| POST | `/api/v1/listeners/sessions/{id}/heartbeat` | JWT | Update `last_heartbeat_at`. |
| POST | `/api/v1/listeners/sessions/{id}/end` | JWT | Close session, write `duration_seconds`. |

### Admin — User Management

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/users` | Admin | List users. `?status=pending\|active\|suspended` |
| POST | `/api/v1/admin/users` | Admin | Create user directly (bypasses approval). |
| POST | `/api/v1/admin/users/{id}/approve` | Admin | Approve pending user. |
| POST | `/api/v1/admin/users/{id}/suspend` | Admin | Suspend active user. |
| DELETE | `/api/v1/admin/users/{id}` | Admin | Soft-delete user. |

### Admin — Listener Analytics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/listener-sessions` | Admin | Session history. Filters: `user_id`, `station`, `from`, `to`, `active_only`. |
| GET | `/api/v1/admin/listener-sessions/active` | Admin | Currently active sessions. |
| GET | `/api/v1/admin/listener-sessions/summary` | Admin | Per-user totals: session count, total duration, last seen. |

---

## Frontend

### Route Guards

Two wrapper components added to `App.tsx`:

- `<RequireAuth>` — redirects to `/login` if no token in auth store
- `<RequireAdmin>` — redirects to `/` if `role !== 'admin'`

All existing routes wrap in `<RequireAuth>`. Admin-only routes additionally wrap in `<RequireAdmin>`.

### Role-Based Navigation

`Layout.tsx` nav renders conditionally based on `role` from auth store:

| Nav Item | Listener | Admin |
|----------|----------|-------|
| Now Playing | ✅ | ✅ |
| History | ✅ | ✅ |
| Transcripts | ✅ | ✅ |
| Analytics | ❌ | ✅ |
| TTS / DJ | ❌ | ✅ |
| Stations | ❌ | ✅ |
| Media | ❌ | ✅ |
| Users (new) | ❌ | ✅ |
| Listeners (new) | ❌ | ✅ |

### New Pages

**`/admin/users` — User Management**
- Pending queue at top: name, email, registered date, Approve / Reject buttons
- Full user table: name, email, role, status, last login, actions (suspend/activate/delete)
- "Create user" button for admin-direct creation

**`/admin/listeners` — Listener Sessions**
- "Active Now" section: user, station, duration so far, location (city/country flag), device
- Session history table: filterable by user, station, date range
- Per-user summary: total time, session count, last seen, most common location

### Registration Flow

Login page gains a "Create account" link that switches to register mode (name, email, password fields). After submit shows: *"Your account has been submitted for approval. You'll be able to log in once an admin approves it."*

### Stream Token in RadioPlayer

```
mount → GET /api/v1/stream/token → set audio src with ?token=<t>
setInterval(10min) → GET /api/v1/stream/token → swap src if not playing, else queue swap
station switch → end current session → GET new token → new session → swap src
beforeunload / pause → POST /api/v1/listeners/sessions/{id}/end
play → POST /api/v1/listeners/sessions (if no active session)
```

---

## GeoIP

- Library: `geoip2` (Python)
- Database: MaxMind GeoLite2-City (free, requires free account for license key)
- Database file volume-mounted into the API container at `/app/geoip/GeoLite2-City.mmdb`
- Monthly update cron on PCT 127 host: download new DB, replace file (hot-reload on next lookup)
- Fallback: if IP lookup fails (private IP, missing DB), all geo fields stored as `null`

---

## Stability Notes

| Risk | Mitigation |
|------|-----------|
| Icecast port 8000 still reachable externally | Remove host port mapping from `docker-compose.yml`; Caddy is the only path in |
| Stream token active after user suspension | 15-min TTL limits window; session cleanup closes the tracking record |
| Registration spam | `slowapi` rate limit: 5 req/hour per IP on `/auth/register` |
| Stale sessions from crashes/disconnects | Background task closes sessions with no heartbeat in >90s |
| GeoLite2 DB going stale | Monthly cron on PCT 127 to pull latest DB |
| IP privacy | Registration form includes note: "We log your approximate location for listener analytics" |
| `/auth/me` currently broken | Fix as part of this work to return full user profile |
| Two tabs refreshing stream token simultaneously | Last-writer-wins is safe; both get valid tokens |

---

## Migration Plan

1. New Alembic migration: `010_add_listener_sessions`
2. No changes to `users` table schema (all columns already exist)
3. Add `STREAM_TOKEN_SECRET` to `.env` (new required config var)
4. Add `GEOIP_DB_PATH` to `.env` (path to GeoLite2-City.mmdb)
5. Remove Icecast port 8000 from `docker-compose.yml` host mapping
6. Update Caddy config for stream forward_auth

---

## Out of Scope (Future)

- Email verification
- Invite link flow
- Token denylist for immediate revocation
- Per-listener stream quality preferences
- Listener-facing "my listening history" page
