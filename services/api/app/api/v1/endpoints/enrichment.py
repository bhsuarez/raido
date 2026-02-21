"""MusicBrainz enrichment review queue API."""
import asyncio
import re
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import musicbrainzngs
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
import structlog

from app.core.database import get_db
from app.core.deps import require_admin
from app.models import Track
from app.models.mb_candidate import MBCandidate, CandidateStatus
from app.models.users import User

router = APIRouter()
logger = structlog.get_logger()


# ── Schemas ──────────────────────────────────────────────────────────────────

class CandidateRead(BaseModel):
    id: int
    track_id: int
    status: CandidateStatus
    score: Optional[float] = None
    mb_recording_id: Optional[str] = None
    mb_release_id: Optional[str] = None
    proposed_title: Optional[str] = None
    proposed_artist: Optional[str] = None
    proposed_album: Optional[str] = None
    proposed_year: Optional[int] = None
    proposed_genre: Optional[str] = None
    proposed_isrc: Optional[str] = None
    proposed_country: Optional[str] = None
    proposed_label: Optional[str] = None
    proposed_artwork_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TrackWithCandidates(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    artwork_url: Optional[str] = None
    recording_mbid: Optional[str] = None
    candidates: List[CandidateRead] = []

    class Config:
        from_attributes = True


class EnrichmentStats(BaseModel):
    total_tracks: int
    tracks_with_mbid: int
    tracks_pending: int
    tracks_approved: int
    tracks_rejected: int
    tracks_skipped: int
    tracks_unqueued: int


class LookupRequest(BaseModel):
    mb_url: str


_MB_UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)
_NON_GENRE_TAGS = {
    "animal on cover", "dog on cover", "cat on cover", "energetic", "playful",
    "melancholic", "uplifting", "eclectic", "melodic", "sarcastic", "satirical",
    "quirky", "urban", "aggressive", "dark", "romantic", "happy", "sad",
    "instrumental", "live", "compilation", "reissue", "remixed",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _apply_candidate_to_track(track: Track, candidate: MBCandidate) -> None:
    """Write candidate proposed values onto the track model (does not commit)."""
    if candidate.proposed_title:
        track.title = candidate.proposed_title
    if candidate.proposed_artist:
        track.artist = candidate.proposed_artist
    if candidate.proposed_album:
        track.album = candidate.proposed_album
    if candidate.proposed_year:
        track.year = candidate.proposed_year
    if candidate.proposed_genre:
        track.genre = candidate.proposed_genre
    if candidate.mb_recording_id:
        track.recording_mbid = candidate.mb_recording_id
    if candidate.mb_release_id:
        track.release_mbid = candidate.mb_release_id
    if candidate.proposed_isrc:
        track.isrc = candidate.proposed_isrc
    if candidate.proposed_artwork_url:
        track.artwork_url = candidate.proposed_artwork_url


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=EnrichmentStats)
async def get_enrichment_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Overall enrichment progress stats."""
    total = (await db.execute(select(func.count(Track.id)))).scalar_one()
    with_mbid = (await db.execute(
        select(func.count(Track.id)).where(Track.recording_mbid.isnot(None))
    )).scalar_one()

    # Tracks that have at least one candidate in each status
    def _count_tracks_with_status(status: CandidateStatus):
        return (
            select(func.count(func.distinct(MBCandidate.track_id)))
            .where(MBCandidate.status == status)
        )

    pending_tracks = (await db.execute(_count_tracks_with_status(CandidateStatus.pending))).scalar_one()
    approved_tracks = (await db.execute(_count_tracks_with_status(CandidateStatus.approved))).scalar_one()
    rejected_tracks = (await db.execute(_count_tracks_with_status(CandidateStatus.rejected))).scalar_one()
    skipped_tracks = (await db.execute(_count_tracks_with_status(CandidateStatus.skipped))).scalar_one()

    # Tracks with no candidates at all and no mbid
    queued_track_ids_q = select(MBCandidate.track_id).distinct()
    unqueued = (await db.execute(
        select(func.count(Track.id))
        .where(Track.recording_mbid.is_(None))
        .where(Track.id.notin_(queued_track_ids_q))
    )).scalar_one()

    return EnrichmentStats(
        total_tracks=total,
        tracks_with_mbid=with_mbid,
        tracks_pending=pending_tracks,
        tracks_approved=approved_tracks,
        tracks_rejected=rejected_tracks,
        tracks_skipped=skipped_tracks,
        tracks_unqueued=unqueued,
    )


@router.get("/queue", response_model=List[TrackWithCandidates])
async def get_enrichment_queue(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status: Optional[CandidateStatus] = Query(CandidateStatus.pending),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Paginated list of tracks that have candidates in the given status."""
    # Get track IDs that have candidates with the requested status
    subq = (
        select(MBCandidate.track_id)
        .where(MBCandidate.status == status)
        .distinct()
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    track_ids_result = await db.execute(subq)
    track_ids = [r[0] for r in track_ids_result.all()]

    if not track_ids:
        return []

    # Fetch tracks
    tracks_result = await db.execute(
        select(Track).where(Track.id.in_(track_ids)).order_by(Track.artist, Track.title)
    )
    tracks = tracks_result.scalars().all()

    # Fetch all candidates for these tracks
    cands_result = await db.execute(
        select(MBCandidate)
        .where(MBCandidate.track_id.in_(track_ids))
        .order_by(MBCandidate.score.desc().nullslast())
    )
    cands = cands_result.scalars().all()

    cands_by_track: dict[int, list] = {}
    for c in cands:
        cands_by_track.setdefault(c.track_id, []).append(c)

    return [
        TrackWithCandidates(
            id=t.id,
            title=t.title,
            artist=t.artist,
            album=t.album,
            year=t.year,
            genre=t.genre,
            artwork_url=t.artwork_url,
            recording_mbid=t.recording_mbid,
            candidates=cands_by_track.get(t.id, []),
        )
        for t in tracks
    ]


@router.get("/track/{track_id}", response_model=TrackWithCandidates)
async def get_track_candidates(
    track_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Get a single track and all its MB candidates."""
    track = (await db.execute(select(Track).where(Track.id == track_id))).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    cands_result = await db.execute(
        select(MBCandidate)
        .where(MBCandidate.track_id == track_id)
        .order_by(MBCandidate.score.desc().nullslast())
    )
    cands = cands_result.scalars().all()

    return TrackWithCandidates(
        id=track.id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        year=track.year,
        genre=track.genre,
        artwork_url=track.artwork_url,
        recording_mbid=track.recording_mbid,
        candidates=cands,
    )


@router.post("/candidate/{candidate_id}/approve")
async def approve_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Approve a candidate: apply its proposed values to the track,
    and reject all other pending candidates for that track.
    """
    candidate = (await db.execute(
        select(MBCandidate).where(MBCandidate.id == candidate_id)
    )).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    track = (await db.execute(select(Track).where(Track.id == candidate.track_id))).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Apply metadata to track
    await _apply_candidate_to_track(track, candidate)

    # Mark this candidate approved
    candidate.status = CandidateStatus.approved
    candidate.reviewed_at = datetime.now(timezone.utc)
    candidate.reviewed_by = user.id

    # Reject all other pending candidates for this track
    await db.execute(
        update(MBCandidate)
        .where(MBCandidate.track_id == candidate.track_id)
        .where(MBCandidate.id != candidate_id)
        .where(MBCandidate.status == CandidateStatus.pending)
        .values(status=CandidateStatus.rejected, reviewed_at=datetime.now(timezone.utc))
    )

    await db.commit()
    logger.info("Candidate approved", candidate_id=candidate_id, track_id=track.id)
    return {"status": "approved", "track_id": track.id}


@router.post("/candidate/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Reject a single candidate."""
    candidate = (await db.execute(
        select(MBCandidate).where(MBCandidate.id == candidate_id)
    )).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.status = CandidateStatus.rejected
    candidate.reviewed_at = datetime.now(timezone.utc)
    candidate.reviewed_by = user.id
    await db.commit()
    return {"status": "rejected"}


@router.post("/track/{track_id}/skip")
async def skip_track(
    track_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Skip a track: mark all its pending candidates as skipped
    so it won't appear in the review queue again.
    """
    track = (await db.execute(select(Track).where(Track.id == track_id))).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(MBCandidate)
        .where(MBCandidate.track_id == track_id)
        .where(MBCandidate.status == CandidateStatus.pending)
        .values(status=CandidateStatus.skipped, reviewed_at=now)
    )

    # If no candidates exist yet, insert a skipped sentinel so the enricher won't re-queue it
    if result.rowcount == 0:
        db.add(MBCandidate(
            track_id=track_id,
            status=CandidateStatus.skipped,
            reviewed_at=now,
            reviewed_by=user.id,
        ))

    await db.commit()
    logger.info("Track skipped", track_id=track_id)
    return {"status": "skipped", "track_id": track_id}


@router.post("/track/{track_id}/lookup", response_model=CandidateRead, status_code=201)
async def lookup_mb_release(
    track_id: int,
    payload: LookupRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """
    Look up a MusicBrainz release by URL or UUID, match the track title to a
    recording within it, and add as a top-scored pending candidate.
    """
    m = _MB_UUID_RE.search(payload.mb_url.strip())
    if not m:
        raise HTTPException(status_code=422, detail="No valid MusicBrainz UUID found in input")
    release_mbid = m.group(0).lower()

    track = (await db.execute(select(Track).where(Track.id == track_id))).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Fetch release from MusicBrainz
    loop = asyncio.get_event_loop()
    try:
        def _fetch():
            musicbrainzngs.set_useragent("Raido", "1.0", "raido@local")
            return musicbrainzngs.get_release_by_id(
                release_mbid,
                includes=["artists", "recordings", "labels"],
            )
        result = await loop.run_in_executor(None, _fetch)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MusicBrainz lookup failed: {e}")

    rel = result.get("release", {})
    album = rel.get("title")
    country = rel.get("country")
    rel_artist = (rel.get("artist-credit-phrase") or "").strip() or track.artist

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

    # Find the recording in the release that matches the track title
    recording_mbid = None
    rec_title = track.title
    rec_artist = rel_artist
    track_title_lower = track.title.lower().strip()

    for medium in rel.get("medium-list") or []:
        for tr in medium.get("track-list") or []:
            rec = tr.get("recording") or {}
            if rec.get("title", "").lower().strip() == track_title_lower:
                recording_mbid = rec.get("id")
                rec_title = rec.get("title") or track.title
                rec_artist = (rec.get("artist-credit-phrase") or "").strip() or rel_artist
                break
        if recording_mbid:
            break

    # If already have a candidate with this release+recording combo, re-pend it
    existing_q = select(MBCandidate).where(MBCandidate.track_id == track_id).where(MBCandidate.mb_release_id == release_mbid)
    if recording_mbid:
        existing_q = existing_q.where(MBCandidate.mb_recording_id == recording_mbid)
    existing = (await db.execute(existing_q)).scalar_one_or_none()
    if existing:
        if existing.status != CandidateStatus.pending:
            existing.status = CandidateStatus.pending
            existing.score = 100.0
            await db.commit()
            await db.refresh(existing)
        return existing

    # Artwork from Cover Art Archive
    artwork_url = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://coverartarchive.org/release/{release_mbid}/front-500",
                follow_redirects=True,
            )
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                artwork_url = str(resp.url)
    except Exception:
        pass

    candidate = MBCandidate(
        track_id=track_id,
        status=CandidateStatus.pending,
        score=100.0,
        mb_recording_id=recording_mbid,
        mb_release_id=release_mbid,
        proposed_title=rec_title,
        proposed_artist=rec_artist,
        proposed_album=album,
        proposed_year=year,
        proposed_country=country,
        proposed_label=label,
        proposed_artwork_url=artwork_url,
        reviewed_by=user.id,
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)
    logger.info("Manual MB release lookup candidate added", track_id=track_id, release_mbid=release_mbid, recording_mbid=recording_mbid)
    return candidate
