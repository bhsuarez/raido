import asyncio
from datetime import datetime, timezone

from app.worker.dj_worker import DJWorker
from app.services.commentary_generator import CommentaryGenerator


def _mk_worker() -> DJWorker:
    # Use a dummy TTS service to avoid filesystem side effects
    return DJWorker(CommentaryGenerator(), object())  # type: ignore[arg-type]


def test_has_recent_commentary_prunes_old_entries(monkeypatch):
    w = _mk_worker()
    # Pretend two entries, one old, one recent
    import time as _time
    now = 1_000_000.0
    old = now - 7200
    recent = now - 10
    w._recent_intros = {1: old, 2: recent}

    monkeypatch.setattr("time.time", lambda: now)
    # Track 1 should be pruned/not recent, track 2 recent
    is_recent_1 = asyncio.run(w._has_recent_commentary(1))
    is_recent_2 = asyncio.run(w._has_recent_commentary(2))
    assert is_recent_1 is False
    assert is_recent_2 is True
