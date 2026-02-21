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


def _mb_search_releases(artist: str, title: str) -> dict:
    """Search for releases containing this track (run in executor)."""
    musicbrainzngs.set_useragent("Raido", "1.0", settings.MB_USER_AGENT)
    # Lucene query: find releases that contain a track with this title by this artist
    query = f'track:"{title}" AND artist:"{artist}"'
    return musicbrainzngs.search_releases(query=query, limit=settings.MB_SEARCH_LIMIT)


def _mb_get_release(release_mbid: str) -> dict:
    """Fetch a release with full track listing (run in executor)."""
    musicbrainzngs.set_useragent("Raido", "1.0", settings.MB_USER_AGENT)
    return musicbrainzngs.get_release_by_id(
        release_mbid,
        includes=["artists", "recordings", "labels", "tags"],
    )


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
    Search MusicBrainz releases for a track, insert candidates, return number inserted.
    Respects rate limit via caller's sleep.
    """
    loop = asyncio.get_event_loop()
    try:
        search_result = await loop.run_in_executor(
            None, functools.partial(_mb_search_releases, artist, title)
        )
    except Exception as e:
        logger.warning("MB release search failed", track_id=track_id, error=str(e))
        return 0

    releases = search_result.get("release-list", []) or []
    if not releases:
        logger.debug("No MB release results", track_id=track_id, title=title, artist=artist)
        return 0

    inserted = 0
    seen_release_mbids: set[str] = set()
    title_lower = title.lower().strip()

    for rel_stub in releases:
        release_mbid = rel_stub.get("id")
        if not release_mbid or release_mbid in seen_release_mbids:
            continue
        seen_release_mbids.add(release_mbid)

        score = None
        try:
            score = float(rel_stub.get("ext:score", 0))
        except (ValueError, TypeError):
            pass

        # Fetch full release with track listing
        await asyncio.sleep(settings.MB_REQUEST_INTERVAL)
        try:
            rel_result = await loop.run_in_executor(
                None, functools.partial(_mb_get_release, release_mbid)
            )
        except Exception as e:
            logger.warning("MB get_release failed", release_mbid=release_mbid, error=str(e))
            continue

        rel = rel_result.get("release", {})
        album = rel.get("title")
        country = rel.get("country")
        rel_artist = (rel.get("artist-credit-phrase") or "").strip() or artist

        year = None
        date_str = rel.get("date", "")
        if date_str and len(date_str) >= 4:
            try:
                year = int(date_str[:4])
            except ValueError:
                pass

        label = None
        for li in rel.get("label-info-list") or []:
            label_entry = li.get("label") if isinstance(li, dict) else None
            if label_entry and label_entry.get("name"):
                label = label_entry["name"]
                break

        genre = None
        tags = rel.get("tag-list") or []
        filtered = [t for t in tags if t.get("name", "").lower() not in _NON_GENRE_TAGS]
        if filtered:
            top = max(filtered, key=lambda t: int(t.get("count", 0)))
            genre = top["name"].title()

        # Find the recording in the release whose title matches
        recording_mbid = None
        rec_title = title
        rec_artist = rel_artist
        for medium in rel.get("medium-list") or []:
            for tr in medium.get("track-list") or []:
                rec = tr.get("recording") or {}
                if rec.get("title", "").lower().strip() == title_lower:
                    recording_mbid = rec.get("id")
                    rec_title = rec.get("title") or title
                    rec_artist = (rec.get("artist-credit-phrase") or "").strip() or rel_artist
                    break
            if recording_mbid:
                break

        # Artwork
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
            mb_raw_response=rel,
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
