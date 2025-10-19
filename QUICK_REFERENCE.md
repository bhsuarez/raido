# 🎵 Raido Multi-Station Quick Reference

## Adding a New Station (3 Minutes)

### 1. Edit Configuration
```bash
vim stations.yml
```

Add your station:
```yaml
jazz:
  display_name: "Jazz Lounge 24/7"
  identifier: "jazz"
  description: "Smooth jazz all day"
  liquidsoap:
    config_file: "./infra/liquidsoap/jazz.liq"
    telnet_port: 1236
    icecast_mount: "/jazz"
  dj_worker:
    enabled: true
    default_voice: "af_bella"
  frontend:
    enabled: true
    port: 9002
  music:
    path: "/mnt/music"
```

### 2. Create Liquidsoap Config
```bash
cp infra/liquidsoap/radio.liq infra/liquidsoap/jazz.liq
```

Edit `jazz.liq`:
- Change telnet port: `set("server.telnet.port", 1236)`
- Change mount: `mount="/jazz"`
- Change station name

### 3. Deploy
```bash
make stations-generate    # Generate docker-compose config
make stations-up          # Start all stations
make stations-sync        # Sync to database
```

### 4. Verify
```bash
make station-status STATION=jazz
curl http://localhost:8001/api/v1/now/?station=jazz | jq .
```

## Common Commands

### Station Management
```bash
make stations-list                    # List all stations
make stations-generate                # Regenerate docker-compose.stations.yml
make stations-sync                    # Sync stations to database
make stations-up                      # Start all stations
make stations-restart                 # Restart with new config
```

### Monitor Specific Station
```bash
make station-status STATION=christmas # Check status
make station-logs STATION=christmas   # View logs
```

### Manual Operations
```bash
# View now playing
curl "http://localhost:8001/api/v1/now/?station=jazz" | jq .

# View next up
curl "http://localhost:8001/api/v1/now/next?station=jazz" | jq .

# View settings
curl "http://localhost:8001/api/v1/admin/settings?station=jazz" | jq .

# Listen to stream
mpv http://localhost:8000/jazz
```

## Port Allocation Guide

| Station    | Liquidsoap Telnet | Frontend | Icecast Mount |
|------------|-------------------|----------|---------------|
| main       | 1234              | 80       | /stream       |
| christmas  | 1235              | 9000     | /christmas    |
| **jazz**   | **1236**          | **9002** | **/jazz**     |
| **rock**   | **1237**          | **9003** | **/rock**     |
| **lofi**   | **1238**          | **9004** | **/lofi**     |

## Configuration Templates

### Minimal Station (Music Only, No DJ)
```yaml
minimal:
  display_name: "Minimal Station"
  identifier: "minimal"
  liquidsoap:
    config_file: "./infra/liquidsoap/minimal.liq"
    telnet_port: 1240
    icecast_mount: "/minimal"
  dj_worker:
    enabled: false
  frontend:
    enabled: false
  music:
    path: "/mnt/music"
```

### Full-Featured Station
```yaml
deluxe:
  display_name: "Deluxe Station"
  identifier: "deluxe"
  description: "Full-featured radio with AI DJ"
  liquidsoap:
    config_file: "./infra/liquidsoap/deluxe.liq"
    telnet_port: 1241
    http_port: 8081
    icecast_mount: "/deluxe"
  dj_worker:
    enabled: true
    default_provider: "ollama"
    default_voice_provider: "kokoro"
    default_voice: "af_bella"
    commentary_interval: 2
    max_seconds: 25
    memory_limit: "1g"
    cpu_limit: "0.50"
    prompt_template: |
      Custom DJ prompt goes here...
  frontend:
    enabled: true
    port: 9010
    theme: "dark"
    custom_branding: true
  music:
    path: "/mnt/music"
    filter:
      genre: ["Jazz", "Blues"]
```

## Troubleshooting Checklist

### Station Not Starting
- [ ] Check port conflicts: `docker compose ps | grep <port>`
- [ ] Verify liquidsoap config exists: `ls infra/liquidsoap/<station>.liq`
- [ ] Check logs: `make station-logs STATION=<station>`
- [ ] Regenerate config: `make stations-generate`

### DJ Not Working
- [ ] Check station name: `docker compose exec <station>-dj-worker env | grep STATION`
- [ ] Verify API responds: `curl "http://localhost:8001/api/v1/now/?station=<station>"`
- [ ] Check settings: `curl "http://localhost:8001/api/v1/admin/settings?station=<station>"`
- [ ] Sync database: `make stations-sync`

### Stream Silent
- [ ] Check music path: `docker compose exec <station>-liquidsoap ls /mnt/music`
- [ ] Verify liquidsoap telnet: `echo "request.all" | telnet localhost <port>`
- [ ] Check Icecast: `curl -I http://localhost:8000/<mount>`
- [ ] Review liquidsoap logs: `docker compose logs <station>-liquidsoap`

## File Structure

```
raido/
├── stations.yml                    # ← EDIT THIS to add stations
├── docker-compose.stations.yml     # Generated automatically
├── scripts/
│   ├── generate-station-services.py
│   └── sync-stations-db.py
├── infra/liquidsoap/
│   ├── radio.liq                   # Main station
│   ├── christmas.liq               # Christmas station
│   └── <station>.liq               # ← CREATE for new stations
└── web-<station>/                  # Optional custom frontend
```

## Architecture Diagram

```
┌─────────────┐
│ stations.yml│ ← Single source of truth
└──────┬──────┘
       │
       ├─────────────────────────────────────┐
       │                                     │
       ▼                                     ▼
┌──────────────┐                    ┌────────────────┐
│   Generator  │                    │  Sync Script   │
│   Script     │                    │                │
└──────┬───────┘                    └────────┬───────┘
       │                                     │
       ▼                                     ▼
┌──────────────────────────┐       ┌─────────────────┐
│ docker-compose.stations  │       │    Database     │
│         .yml             │       │   (stations)    │
└──────┬───────────────────┘       └─────────────────┘
       │
       │ Creates services for each station:
       │
       ├─── <station>-liquidsoap (Audio streaming)
       ├─── <station>-dj-worker (AI commentary)
       └─── <station>-web (Optional frontend)
```

## Best Practices

1. **Always use stations.yml** - Don't edit docker-compose files directly
2. **Unique ports** - Check port allocation before adding stations
3. **Test incrementally** - Add one station, test it, then add more
4. **Resource limits** - Set appropriate CPU/memory for each station
5. **Backup first** - Run `make backup-db` before major changes

## Quick Migration Checklist

Moving existing station config to new system:

1. [ ] Add station to `stations.yml`
2. [ ] Move liquidsoap config to `infra/liquidsoap/<station>.liq`
3. [ ] Run `make stations-generate`
4. [ ] Run `make stations-sync`
5. [ ] Update any hardcoded URLs/references
6. [ ] Test with `make station-status STATION=<station>`
7. [ ] Update monitoring/alerts

## Resources

- Full documentation: [STATIONS.md](STATIONS.md)
- Architecture overview: [CLAUDE.md](CLAUDE.md)
- Recovery procedures: [RECOVERY.md](RECOVERY.md)
