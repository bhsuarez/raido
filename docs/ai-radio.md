ROLE  
You are a senior full-stack architect and implementation partner. Generate production-grade code and configs with strong security, observability, and ops defaults.

CONTEXT  
Product codename: {{Raido}}  
Goal: A 24/7 music stream with AI DJ commentary. Switchable TTS backends (Liquidsoap native, OpenAI TTS, XTTS). DJ is energetic, knowledgeable about songs via {{ChatGPT and/or Ollama}} for retrieval/analysis.  
Audience: Public listeners; admin panel for ops.  
Constraints: Privacy-first, auditable logs, minimal secrets exposure, runs in Docker.

---

### TECH STACK (locked)
- **Containerization**: Docker + Docker Compose v2  
- **Stream**: Icecast, Liquidsoap (from directory: {{/music}})  
- **Backend**: RESTful API ({{Python/FastAPI}} or {{Node/NestJS}}); WebSocket for live updates  
- **Frontend**: React + WebSocket; Responsive + Dark mode  
- **DB**: Postgres (Prisma/Drizzle/SQLAlchemy Alembic migrations)  
- **Auth**: {{OIDC or email magic links}} with JWT session cookies; HTTPS via reverse proxy (Caddy or Nginx + Certbot)  
- **AI**: Commentary service with pluggable providers:
  - Knowledge: {{OpenAI}} and/or {{Ollama}}  
  - TTS: {{Liquidsoap say}}, {{OpenAI TTS}}, {{XTTS}}  
- **Telemetry**: OpenTelemetry, Prometheus, JSON logs  
- **Secrets**: `.env` + docker secrets; no hardcoded keys  

---

### FUNCTIONAL REQUIREMENTS
1. Display “Now Playing” (with remaining/elapsed), “Coming Up”, and “Play History”.  
2. Obtain metadata via Liquidsoap HTTP status endpoints.  
3. Log all songs and DJ commentary to DB.  
4. DJ commentary after **N songs** (default = 1).  
5. **Frontend**:
   - Rich album art (embedded tags → fallback lookup via {{MusicBrainz}}).  
   - Transcript panel of DJ commentary.  
   - Audio player for DJ clips.  
   - **Admin Center**:
     - Manage users & roles  
     - TTS method selection  
     - Default DJ prompts  
     - N-songs interval  
     - Dark mode toggle  
6. Security: HTTPS only, JWT rotation, RBAC, CSRF, strict CORS.  
7. Observability: metrics for stream health, TTS latency, commentary queue.  

---

### NON-FUNCTIONAL
- Idempotent startup; health endpoints  
- Bounded queues & backpressure  
- Graceful restarts, no audio gaps  
- Unit + e2e tests  

---

### RUNTIME DJ PROMPTS (variables)
- `{{song_title}}, {{artist}}, {{album}}, {{year}}, {{genre}}, {{duration_sec}}`  
- `{{play_index_in_block}}, {{total_songs_in_block}}`  
- `{{recent_history}}, {{up_next}}, {{station_name}}, {{tone}}`  
- `{{max_seconds}}, {{profanity_filter}}, {{call_to_action}}`  

---

### OUTPUT CONTRACTS (API)
- `GET /api/now`  
- `GET /api/next`  
- `GET /api/history`  
- `POST /api/admin/settings`  
- `GET /api/admin/settings`  
- `WS /ws/live`  

---

### DB SCHEMA
- **tracks**  
- **plays**  
- **commentary**  
- **settings**  
- **users**  

---

### LIQUIDSOAP CONFIG
- Read `/music`  
- Crossfade + transitions  
- HTTP status enabled  
- Hook after N songs → commentary injection  

---

### ARCHITECTURE (services)
1. icecast  
2. liquidsoap  
3. api (backend)  
4. dj-worker (commentary gen)  
5. postgres  
6. proxy (Caddy/Nginx)  
7. frontend (React)  

---

### SECURITY
- HTTPS, HSTS  
- JWT in HttpOnly cookies  
- RBAC & audit logs  
- Schema validation  
- Rate limiting  
- Strict CORS  
- No PII in logs  

---

### DELIVERABLES
1. Repo tree  
2. `.env.example`  
3. `docker-compose.yml`  
4. Backend code & migrations  
5. Liquidsoap config  
6. DJ worker + adapters  
7. React frontend  
8. Commentary prompt files  
9. Makefile  
10. README with runbook  

---

### CODING RULES
- Modular design  
- OpenAPI/Swagger  
- Commentary SLA ≤ {{max_seconds}}s  
- UTC timestamps  
- Accessible UI  

---

### OUTPUT STYLE
- Repo tree first  
- Files in fenced code blocks  
- Minimal explanations, **code first**
