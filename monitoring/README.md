# Raido Monitoring System

Automated monitoring with Signal notifications when services go down.

## Quick Setup

1. **Copy environment file:**
   ```bash
   cp monitoring/.env.monitoring.example monitoring/.env.monitoring
   ```

2. **Configure Signal:**
   - Register your phone number with Signal
   - Edit `monitoring/.env.monitoring`:
     ```bash
     SIGNAL_PHONE_NUMBER=+1234567890      # Your Signal number
     SIGNAL_RECIPIENT_NUMBER=+1234567890   # Where to send alerts
     GITHUB_RECOVERY_URL=https://github.com/yourusername/raido/blob/master/RECOVERY.md
     ```

3. **Start monitoring:**
   ```bash
   cd monitoring
   docker compose -f docker-compose.monitoring.yml up -d
   ```

4. **Register Signal number (first time only):**
   ```bash
   # Get verification code
   curl -X POST http://localhost:8082/v1/register/+1234567890
   
   # Enter the code you receive
   curl -X POST http://localhost:8082/v1/register/+1234567890/verify/123456
   ```

## What It Monitors

**Critical Services (triggers urgent alerts):**
- `raido-api-1` - Backend API
- `raido-db-1` - Database
- `raido-liquidsoap-1` - Audio streaming
- `raido-icecast-1` - Stream server
- API health endpoints
- Audio stream availability

**Optional Services (triggers warnings):**
- `raido-dj-worker-1` - AI commentary
- `raido-kokoro-tts-1` - Text-to-speech
- `raido-ollama-1` - Local LLM
- `raido-web-dev-1` - Frontend
- Recent track activity

## Alert Examples

**🚨 Urgent Alert:**
```
🚨 URGENT: Raido system has critical issues:

• raido-api-1 (stopped)
• Stream: Stream unreachable: Connection refused

🔧 Recovery Guide: https://github.com/yourusername/raido/blob/master/RECOVERY.md
```

**⚠️ Warning Alert:**
```
Raido system warnings:

• raido-dj-worker-1 (stopped)
• Activity: No activity for 1:30:00 (last: Pink Floyd - Comfortably Numb)

🔧 Recovery Guide: https://github.com/yourusername/raido/blob/master/RECOVERY.md
```

## Commands

```bash
# Start monitoring
cd monitoring
docker compose -f docker-compose.monitoring.yml up -d

# View logs
docker compose -f docker-compose.monitoring.yml logs -f raido-monitor

# Stop monitoring
docker compose -f docker-compose.monitoring.yml down

# Test Signal setup
curl -X POST http://localhost:8082/v2/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test message from Raido monitoring",
    "number": "+1234567890",
    "recipients": ["+1234567890"]
  }'
```

## Configuration

Edit `monitoring/.env.monitoring`:

- `CHECK_INTERVAL=300` - How often to check (seconds)
- Alert cooldown: 30 minutes (prevents spam)
- Monitors Docker services, API health, stream status
- Includes recovery guide link in all alerts

## Troubleshooting

**Signal not working:**
1. Check Signal registration: `docker compose -f docker-compose.monitoring.yml logs signal-cli`
2. Test API: `curl http://localhost:8082/v1/health`
3. Re-register if needed

**Monitor not running:**
1. Check logs: `docker compose -f docker-compose.monitoring.yml logs raido-monitor`
2. Verify environment file exists and has correct values
3. Ensure Docker socket is accessible

**False alerts:**
1. Adjust `CHECK_INTERVAL` in `.env.monitoring`
2. Check if services are actually down: `docker compose ps`
3. Review monitor logs for connection issues