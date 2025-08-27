# CLAUDE.md – Raido Project

This document is the **authoritative prompt** for Claude Code to generate, extend, and maintain the **Raido** project: a 24/7 AI-powered radio stream with DJ commentary.

---

## ROLE

You are a **senior full-stack architect** and implementation partner.  
Generate **production-grade code** and configs with:

- Security-first principles  
- Observability (metrics + logs + traces)  
- Testability and maintainability  
- Dockerized reproducibility  

---

## PROJECT CONTEXT

**Codename:** Raido  
**Goal:**  
- Create a 24/7 music stream with AI DJ commentary.  
- Commentary personality: energetic, factual, knowledgeable.  
- Switchable TTS backends: Liquidsoap native, OpenAI TTS, XTTS.  
- Knowledge sources: OpenAI + Ollama for song metadata/facts.  

**Audience:**  
- Private listeners.  
- Admins for configuration and ops.  

**Constraints:**  
- Runs in Docker + docker-compose.  
- Privacy-first (minimal exposure of secrets).  
- HTTPS enforced end-to-end.  

---

## TECH STACK (Locked)

- **Stream**: Icecast + Liquidsoap (music from `/music`)  
- **Backend**: RESTful API (FastAPI or NestJS) + WebSocket live updates  
- **Frontend**: React, responsive design, dark mode, WebSocket updates  
- **Database**: Postgres (with migrations)  
- **Auth**: OIDC or passwordless magic links → JWT cookies
- **Enganced Music Knowledge**
  - Use song_facts.json as a schema for enriched song facts
- **AI Commentary**:
  - Knowledge: OpenAI + Ollama  
  - TTS: Liquidsoap `say`, OpenAI TTS, XTTS  
- **Infra**: Caddy/Nginx for HTTPS, OpenTelemetry, Prometheus  
- **Secrets**: `.env` + Docker secrets


---

## FUNCTIONAL REQUIREMENTS

1. **Now Playing**: current track, elapsed/remaining time, rich transitions.  
2. **Coming Up**: preview next track + commentary snippet.  
3. **History**: songs and DJ commentary log.  
4. **DJ Commentary**: generated every _N_ songs (default = 1).  
5. **Frontend**:
   - Rich album art (ID3 → MusicBrainz fallback).  
   - Commentary transcript + playback.  
   - Admin center:
     - User + role management  
     - Configure TTS + AI prompts  
     - N-songs interval toggle  
     - Dark mode toggle  
6. **Logging**: All tracks + commentary to Postgres.  
7. **Security**: HTTPS, RBAC, rate limiting, audit logging.  

---

## DB SCHEMA

- **tracks**: id, title, artist, album, year, duration, artwork, tags  
- **plays**: id, track_id, started_at, ended_at, elapsed_ms, liquidsoap_id  
- **commentary**: id, text, ssml, provider, audio_url, transcript, duration_ms, created_at, fk to play/next track  
- **settings**: singleton row for N-songs interval, TTS provider, voice, tone, filters, model prefs  
- **users**: id, email, role, created_at  

Indexes on `plays.started_at` and `commentary.created_at`.  

---

## API CONTRACT
