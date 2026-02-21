"""
MusicBrainz enricher worker.

Continuously scans for tracks without recording_mbid and no existing pending/skipped
candidates, searches MusicBrainz, and inserts MBCandidate rows for you to review.

Rate: ~1 MB API request per second (respects MusicBrainz ToS).
"""
import asyncio
import enum
import functools
import structlog
from datetime import datetime, timezone
from typing import Optional

import musicbrainzngs
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session

logger = structlog.get_logger()

# Inline enums / model mirrors (avoids importing from the API service)
# These must match services/api/app/models/mb_candidate.py exactly.
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, relationship


class _Base(DeclarativeBase):
    pass


class _CandidateStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    skipped = "skipped"


# Lightweight mirrors of the API models — read-only usage
class _Track(sa.orm.MappedAsDataclass, _Base):
    __tablename__ = "tracks"
    __table_args__ = {"extend_existing": True}
    id: sa.orm.Mapped[int] = sa.orm.mapped_column(primary_key=True)
    title: sa.orm.Mapped[str]
    artist: sa.orm.Mapped[str]
    album: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    recording_mbid: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)


class _MBCandidate(sa.orm.MappedAsDataclass, _Base):
    __tablename__ = "mb_candidates"
    __table_args__ = {"extend_existing": True}
    id: sa.orm.Mapped[int] = sa.orm.mapped_column(primary_key=True, init=False)
    track_id: sa.orm.Mapped[int]
    status: sa.orm.Mapped[_CandidateStatus] = sa.orm.mapped_column(
        sa.Enum(_CandidateStatus, name="candidatestatus", create_type=False)
    )
    score: sa.orm.Mapped[Optional[float]] = sa.orm.mapped_column(default=None)
    mb_recording_id: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    mb_release_id: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_title: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_artist: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_album: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_year: sa.orm.Mapped[Optional[int]] = sa.orm.mapped_column(default=None)
    proposed_genre: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_isrc: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_country: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_label: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    proposed_artwork_url: sa.orm.Mapped[Optional[str]] = sa.orm.mapped_column(default=None)
    mb_raw_response: sa.orm.Mapped[Optional[dict]] = sa.orm.mapped_column(sa.JSON, default=None)
    reviewed_at: sa.orm.Mapped[Optional[datetime]] = sa.orm.mapped_column(default=None)
    reviewed_by: sa.orm.Mapped[Optional[int]] = sa.orm.mapped_column(default=None)
    created_at: sa.orm.Mapped[datetime] = sa.orm.mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), init=False
    )
    updated_at: sa.orm.Mapped[datetime] = sa.orm.mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), init=False
    )


_NON_GENRE_TAGS = {
    "animal on cover", "dog on cover", "cat on cover", "energetic", "playful",
    "melancholic", "uplifting", "eclectic", "melodic", "sarcastic", "satirical",
    "quirky", "urban", "aggressive", "dark", "romantic", "happy", "sad",
    "instrumental", "live", "compilation", "reissue", "remixed",
}


def _top_genre(tags: list) -> Optional[str]:
    filtered = [t for t in tags if t.get("name", "").lower() not in _NON_GENRE_TAGS]
    if not filtered:
        return None
    top = max(filtered, key=lambda t: int(t.get("count", 0)))
    return top["name"].title()


def _mb_search_recordings(artist: str, title: str) -> list:
    """Search recordings by artist + title. Returns recording dicts."""
    musicbrainzngs.set_useragent("Raido", "1.0", settings.MB_USER_AGENT)
    clean_title = " ".join(title.split())
    clean_artist = " ".join(artist.split())
    result = musicbrainzngs.search_recordings(
        artist=clean_artist, recording=clean_title, limit=settings.MB_SEARCH_LIMIT
    )
    return result.get("recording-list") or []


def _mb_get_release(release_mbid: str) -> dict:
    """Fetch a release with full track listing (run in executor)."""
    musicbrainzngs.set_useragent("Raido", "1.0", settings.MB_USER_AGENT)
    return musicbrainzngs.get_release_by_id(
        release_mbid,
        includes=["artists", "recordings", "labels", "tags"],
    )


# Release type preference: lower = better
_RELEASE_TYPE_RANK = {"Album": 0, "Single": 1, "EP": 2, "Broadcast": 3, "Other": 4}
_RELEASE_STATUS_RANK = {"Official": 0, "Promotion": 1, "Bootleg": 2, "Pseudo-Release": 3}


def _best_release(releases: list) -> dict:
    """Pick the most relevant release from a recording's release list."""
    if not releases:
        return {}

    def _rank(r: dict) -> tuple:
        rg = r.get("release-group", {})
        type_rank = _RELEASE_TYPE_RANK.get(rg.get("type", ""), 5)
        status_rank = _RELEASE_STATUS_RANK.get(r.get("status", ""), 5)
        # Prefer releases with a date and country; prefer older (original) releases
        date = r.get("date", "9999")
        year = int(date[:4]) if date and len(date) >= 4 and date[:4].isdigit() else 9999
        has_country = 0 if r.get("country") else 1
        return (type_rank, status_rank, has_country, year)

    return min(releases, key=_rank)


async def _fetch_genre(release_mbid: str) -> Optional[str]:
    """Fetch release tags from MB REST API to derive genre."""
    import httpx
    try:
        async with httpx.AsyncClient(
            timeout=5.0,
            headers={"User-Agent": settings.MB_USER_AGENT},
        ) as client:
            resp = await client.get(
                f"https://musicbrainz.org/ws/2/release/{release_mbid}",
                params={"inc": "tags release-groups", "fmt": "json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                all_tags = data.get("tags", []) + data.get("release-group", {}).get("tags", [])
                return _top_genre(all_tags)
    except Exception:
        pass
    return None


async def _fetch_artwork_url(release_mbid: str) -> Optional[str]:
    """Check Cover Art Archive for front artwork."""
    import httpx
    url = f"https://coverartarchive.org/release/{release_mbid}/front-500"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                return str(resp.url)
    except Exception:
        pass
    return None


async def process_track(track_id: int, title: str, artist: str, db: AsyncSession) -> int:
    """
    Search MusicBrainz recordings for a track, pick the best release for each,
    insert candidates, return number inserted.
    """
    loop = asyncio.get_event_loop()

    try:
        recordings = await loop.run_in_executor(
            None, functools.partial(_mb_search_recordings, artist, title)
        )
    except Exception as e:
        logger.warning("MB recording search failed", track_id=track_id, error=str(e))
        return 0

    if not recordings:
        logger.debug("No MB results", track_id=track_id, title=title, artist=artist)
        return 0

    inserted = 0
    seen_mbids: set[str] = set()

    # Fetch genre once from the best release of the top result
    first_release_mbid = None
    for rec in recordings:
        releases = rec.get("release-list") or []
        best = _best_release(releases)
        if best.get("id"):
            first_release_mbid = best["id"]
            break

    genre: Optional[str] = None
    if first_release_mbid:
        await asyncio.sleep(settings.MB_REQUEST_INTERVAL)
        genre = await _fetch_genre(first_release_mbid)

    for rec in recordings:
        recording_mbid = rec.get("id")
        if not recording_mbid or recording_mbid in seen_mbids:
            continue
        seen_mbids.add(recording_mbid)

        rec_title = rec.get("title", title)
        rec_artist = (rec.get("artist-credit-phrase") or "").strip() or artist

        releases = rec.get("release-list") or []
        release = _best_release(releases)
        release_mbid = release.get("id")
        album = release.get("title")
        country = release.get("country")

        year = None
        date_str = release.get("date", "")
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except ValueError:
                pass

        label = None
        for li in release.get("label-info-list") or []:
            label_entry = li.get("label") if isinstance(li, dict) else None
            if label_entry and label_entry.get("name"):
                label = label_entry["name"]
                break

        score = None
        try:
            score = float(rec.get("ext:score", 0))
        except (ValueError, TypeError):
            pass

        artwork_url = None
        if release_mbid:
            await asyncio.sleep(settings.MB_REQUEST_INTERVAL)
            artwork_url = await _fetch_artwork_url(release_mbid)

        candidate = _MBCandidate(
            track_id=track_id,
            status=_CandidateStatus.pending,
            score=score,
            mb_recording_id=recording_mbid,
            mb_release_id=release_mbid,
            proposed_title=rec_title,
            proposed_artist=rec_artist,
            proposed_album=album,
            proposed_year=year,
            proposed_genre=genre,
            proposed_country=country,
            proposed_label=label,
            proposed_artwork_url=artwork_url,
            mb_raw_response=rec,
        )
        db.add(candidate)
        inserted += 1

    await db.commit()
    logger.info("Candidates inserted", track_id=track_id, count=inserted, title=title, artist=artist)
    return inserted


class MBEnricher:
    """Main enricher loop."""

    def __init__(self):
        self.running = False

    async def run(self):
        self.running = True
        logger.info("MBEnricher started")
        while self.running:
            try:
                processed = await self._run_batch()
                if processed == 0:
                    logger.info("No tracks to enrich, sleeping", seconds=settings.IDLE_PAUSE)
                    await asyncio.sleep(settings.IDLE_PAUSE)
                else:
                    await asyncio.sleep(settings.BATCH_PAUSE)
            except Exception as e:
                logger.error("Enricher batch error", error=str(e))
                await asyncio.sleep(30)

    async def stop(self):
        self.running = False

    async def _run_batch(self) -> int:
        """Process one batch of tracks. Returns count processed."""
        async with get_db_session() as db:
            # Tracks that have no recording_mbid and no existing candidate of any status
            existing_track_ids_q = select(_MBCandidate.track_id).distinct()
            q = (
                select(_Track.id, _Track.title, _Track.artist)
                .where(_Track.recording_mbid.is_(None))
                .where(_Track.id.notin_(existing_track_ids_q))
                .order_by(_Track.id)
                .limit(settings.MB_BATCH_SIZE)
            )
            result = await db.execute(q)
            rows = result.all()

        if not rows:
            return 0

        processed = 0
        for track_id, title, artist in rows:
            if not self.running:
                break
            async with get_db_session() as db:
                count = await process_track(track_id, title, artist, db)
                processed += 1
            # Rate limit between tracks
            await asyncio.sleep(settings.MB_REQUEST_INTERVAL)

        return processed
