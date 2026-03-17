# DJ Commentary Last-Track Fallback

**Date:** 2026-03-17
**Status:** Approved

## Problem

On stations with finite playlists (new releases, christmas, recent), the DJ worker skips commentary for the last song in each playlist cycle. The worker generates commentary for the *next* track, so when the queue is empty (last song playing, next cycle not yet pre-fetched), `_get_next_track_for_commentary()` returns `None` and commentary is dropped.

The main station is unaffected because it scans the whole `/mnt/music` directory and Liquidsoap always has tracks pre-queued.

## Solution

Fall back to the currently-playing track when no next track is queued. The commentary plays in the gap between the last song and the next cycle's first track — normal radio behavior.

**Scope:** `services/dj-worker/app/worker/dj_worker.py` only.

## Changes

### `_get_next_track_for_commentary()` → returns a tuple

Change the return type from `Optional[Dict]` to `Tuple[Optional[Dict], bool]` where the second value is `is_current_fallback`. This avoids polluting the track dict with internal flags.

After the existing loop finds nothing, call `get_now_playing()`. If the current track has valid metadata and no recent commentary, return `(track_dict, True)`. Otherwise return `(None, False)`.

```python
# After existing loop returns nothing...
now_playing = await self.api_client.get_now_playing()
if now_playing and now_playing.get('track'):
    track = now_playing['track']
    track_id = track.get('id')
    if (track_id and track_id != 0
            and track.get('title') not in ['Unknown', '']
            and track.get('artist') not in ['Unknown Artist', 'Unknown', '']):
        if not await self._has_recent_commentary(track_id):
            logger.info("No next track queued; falling back to current track for commentary")
            return {'track': track}, True
return None, False
```

### `_process_pending_jobs()`

Unpack the tuple from `_get_next_track_for_commentary()` and pass `is_current_fallback` into `CommentaryJob`.

### `CommentaryJob`

Add an `is_current_fallback: bool = False` field.

### `_inject_commentary()`

**Guard 1** (`current_id == target_id` → discard):

For the normal case this guard prevents an intro from playing while the target song is already live. For the fallback case `target_id` IS the current track by design, so this guard always fires and must be bypassed.

Replace the existing guard with branched logic:

```python
if is_current_fallback:
    # Only inject if the target track is still playing.
    # If the song changed during TTS generation, we're too late — discard
    # to prevent pairing commentary with the wrong track.
    if not current_id or int(current_id) != int(target_id):
        logger.warning("Current-track fallback: song already changed — discarding")
        return
    # Track still playing — proceed to inject; commentary plays after the track ends
else:
    # Normal case: if target is already playing we missed our window
    if current_id and int(current_id) == int(target_id):
        logger.warning("Commentary target is already playing — discarding")
        return
```

**Guard 2** (`target_id not in next_ids` → discard):

This guard has a pre-existing passthrough: `if next_ids and ...`. When no next track is queued (the exact fallback condition), `next_ids` is empty and the guard is already skipped. No change needed for guard 2.

## Edge Cases

**Timing race:** TTS generation takes several seconds. Between generation start and `_inject_commentary`, the last track may finish and the next cycle may start. The revised Guard 1 handles this: if `current_id != target_id` when we reach injection, we discard. Commentary is wasted but no wrong pairing occurs.

**Cycle restart deduplication:** After fallback commentary is generated, `_has_recent_commentary` records the track_id with a TTL of `max(300s, interval_minutes * 60s)` (minimum 5 minutes). If the cycle length is less than 5 minutes, the same track appearing at the start of the next cycle will be suppressed — no double commentary.

**`_is_current_fallback` and persistence:** By returning a tuple instead of mutating the track dict, no internal flag leaks into `job.track_info` or the DB.
