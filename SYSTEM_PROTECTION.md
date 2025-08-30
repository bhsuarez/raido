# System Protection Guide

This document explains how to prevent infinite TTS retry loops and system crashes in the Raido project.

## What Happened

The system experienced infinite retry loops when the Kokoro TTS service was unavailable, causing:
- Load averages exceeding 67
- System resource exhaustion
- Container crashes
- Proxmox host instability

## Prevention Mechanisms Implemented

### 1. **Circuit Breaker Pattern** (Most Critical)

**Location**: `services/dj-worker/app/services/kokoro_client.py`

**How it works**:
- Tracks consecutive failures (max: 5)
- Opens circuit after repeated failures
- Blocks requests for 5 minutes during protection
- Automatically resets after timeout

**Key Settings**:
```python
_max_failures = 5           # Failures before circuit opens
_reset_timeout = 300        # 5 minutes protection time
_max_requests_per_minute = 10  # Rate limiting
```

### 2. **System Health Monitoring**

**Location**: `services/dj-worker/app/services/system_monitor.py`

**What it monitors**:
- CPU usage (warning: 80%, critical: 95%)
- Memory usage (warning: 80%, critical: 95%)  
- Load average (critical: >10.0)

**Protection Features**:
- Automatic TTS generation blocking during high resource usage
- System protection mode activation
- 5-minute cooldown periods

### 3. **Retry Logic Improvements**

**Before**: Unlimited retries with short delays
**After**: Maximum 2 attempts with exponential backoff (4-16 seconds)

### 4. **Timeout Reductions**

**HTTP Timeouts**: Reduced from 30s to 15s
**Connection Timeouts**: Faster failure detection

## Critical Environment Variables

### Essential Settings in `.env`:

```bash
# CRITICAL: Prevents infinite loops
DJ_PROVIDER=disabled              # Set to "disabled" to prevent TTS issues
DJ_VOICE_PROVIDER=templates       # Fallback when kokoro fails

# System Protection Thresholds
KOKORO_BASE_URL=http://kokoro-tts:8090
KOKORO_VOICE=af_bella
KOKORO_SPEED=1.0

# Worker Settings
MAX_CONCURRENT_JOBS=2             # Limit concurrent TTS jobs
WORKER_POLL_INTERVAL=5            # Seconds between worker checks
```

## How to Safely Enable TTS Again

1. **Verify Kokoro Service is Running**:
   ```bash
   curl http://localhost:8090/health
   ```

2. **Enable with Protection**:
   ```bash
   # In .env file
   DJ_PROVIDER=kokoro              # Enable TTS
   DJ_VOICE_PROVIDER=kokoro        # Use kokoro for voice
   ```

3. **Monitor System Health**:
   ```bash
   # Watch system load
   watch -n 1 uptime
   
   # Monitor container logs
   docker logs -f raido_dj-worker_1
   ```

4. **Emergency Disable**:
   ```bash
   # Quickly disable if issues occur
   echo "DJ_PROVIDER=disabled" >> .env
   docker compose restart dj-worker
   ```

## System Health Monitoring Commands

### Check Current Status:
```bash
# System load
uptime

# Memory usage
free -h

# Container resource usage
docker stats

# DJ Worker logs
docker logs --tail 50 raido_dj-worker_1
```

### Warning Signs to Watch:
- Load average > 5.0
- Memory usage > 80%
- DJ Worker errors in logs
- Container restarts
- TTS generation failures

## Automatic Recovery Features

1. **Circuit Breaker**: Automatically opens after 5 failures
2. **System Protection**: Activates during high resource usage
3. **Rate Limiting**: Prevents too many concurrent requests
4. **Graceful Degradation**: Falls back to templates when TTS fails

## Testing the Protection

### Safe Test (Recommended):
```bash
# 1. Ensure protection is active
DJ_PROVIDER=disabled

# 2. Verify logs show protection working
docker logs raido_dj-worker_1 | grep -i "protection\|circuit\|health"
```

### Advanced Test (Only if needed):
```bash
# 1. Temporarily block kokoro service
# Block Docker service (not recommended - use DJ_PROVIDER=disabled instead)
docker compose stop kokoro-tts

# 2. Enable TTS and watch circuit breaker activate
DJ_PROVIDER=kokoro

# 3. Monitor logs for circuit breaker activation
docker logs -f raido_dj-worker_1

# 4. Restore access
docker compose start kokoro-tts
```

## Key Files Modified

1. `services/dj-worker/app/services/kokoro_client.py` - Circuit breaker
2. `services/dj-worker/app/services/system_monitor.py` - Health monitoring  
3. `services/dj-worker/app/worker/dj_worker.py` - Worker protection
4. `.env` - Critical configuration

## Recovery Checklist

If system issues occur again:

- [ ] Check load average: `uptime`
- [ ] Disable TTS: `DJ_PROVIDER=disabled`
- [ ] Restart services: `docker compose restart`
- [ ] Monitor logs: `docker logs raido_dj-worker_1`
- [ ] Verify circuit breaker logs
- [ ] Check system resources stabilize
- [ ] Investigate root cause before re-enabling

## Contact/Debug Info

- System protection logs: Look for "CIRCUIT BREAKER" and "SYSTEM PROTECTION" messages
- Health check logs: Look for CPU/memory warnings
- All protection features log at WARNING/ERROR level for visibility
